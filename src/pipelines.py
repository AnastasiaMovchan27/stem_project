"""Пайплайни: послідовності стадій; результат кожної стадії - вхід наступної."""
import time

from src import image_io, metrics, stages
from src.common import clip_image

MIN_STAGES = 3
MIN_CATEGORIES = 3


def validate_pipeline(stage_names):
    """Перевіряє вимоги завдання: щонайменше 3 стадії з щонайменше 3 різних категорій."""
    if len(stage_names) < MIN_STAGES:
        raise ValueError("пайплайн має мати щонайменше 3 стадії")
    categories = set()
    for name in stage_names:
        if name not in stages.CATEGORIES:
            raise ValueError("Невідома стадія: " + str(name))
        categories.add(stages.CATEGORIES[name])
    if len(categories) < MIN_CATEGORIES:
        raise ValueError("потрібні стадії щонайменше з 3 різних категорій")
    return categories


def run_chain(image, stage_names, stage_params):
    """Виконує стадії по черзі й повертає список результатів усіх стадій.

    Після кожної стадії значення обрізаються до 0...255 (як у файлі).
    """
    outputs = []
    current = image
    for name in stage_names:
        current = clip_image(stages.run_stage(name, current, stage_params.get(name, {})))
        outputs.append(current)
    return outputs


def process_job(job):
    """Обробляє одне спотворене зображення (виконується в окремому процесі).

    job - кортеж (пайплайн, назви стадій, параметри стадій, ім'я знімка, назва спотворення, шлях до
    чистого, шлях до спотвореного, вікно й крок SSIM, папка для картинок або None).
    Повертає (рядок таблиці, повідомлення про помилку).
    """
    (pipeline, stage_names, stage_params, name, degradation, clean_path, noisy_path,
     window, step, out_folder) = job
    clean = image_io.load_image(clean_path)
    noisy = image_io.load_image(noisy_path)
    if clean is None or noisy is None:
        return None, "не вдалося відкрити " + name + " " + degradation
    started = time.perf_counter()
    outputs = run_chain(noisy, stage_names, stage_params)
    seconds = time.perf_counter() - started
    before = metrics.compare(clean, noisy, window, step)
    after = metrics.compare(clean, outputs[-1], window, step)
    row = {"pipeline": pipeline, "image": name, "degradation": degradation,
           "mse_noisy": before["mse"], "psnr_noisy": before["psnr"], "ssim_noisy": before["ssim"],
           "mse": after["mse"], "psnr": after["psnr"], "ssim": after["ssim"], "seconds": seconds}
    # PSNR після кожної стадії (для аналізу внеску стадій)
    for index in range(4):
        key = "psnr_stage" + str(index + 1)
        if index < len(outputs):
            row[key] = metrics.psnr(metrics.mse(clean, outputs[index]))
        else:
            row[key] = ""
    if out_folder:
        for index, output in enumerate(outputs):
            file_name = name + "__" + degradation + "__s" + str(index + 1) + "_" + stage_names[index] + ".png"
            image_io.save_image(output, out_folder + "/" + file_name)
    return row, None

"""Точка входу STEM-проєкту: підготовка вибірки, спотворення, пайплайни, метрики, аналіз.

Приклади запуску (з папки проєкту):
    python main.py prepare            # data/original -> data/prepared (квадрат 128 x 128, сірий)
    python main.py degrade            # data/prepared -> data/degraded (6 спотворень кожного знімка)
    python main.py run all            # обидва пайплайни на всіх спотворених знімках
    python main.py compare            # порівняння пайплайнів, таблиці в results/tables
    python main.py analyze            # внесок стадій, стабільність
    python main.py check              # перевірка сценаріїв з config.json
    python main.py plots              # графіки в results/figures
    python main.py stage bilateral in.png out.png --reference clean.png
    python main.py metrics a.png b.png
    python main.py tune pipeline1     # підбір параметрів на контрольних зображеннях
Усі параметри беруться з config.json (інший файл: --config шлях; інша папка результатів: --results папка).
"""
import argparse
import os
import sys
from multiprocessing import Pool

from src import (analysis, checks, comparison, degrade, image_io, metrics, pipelines, plots,
                 results_io, stages, tuning)

ROW_FIELDS = ["pipeline", "image", "degradation", "mse_noisy", "psnr_noisy", "ssim_noisy", "mse",
              "psnr", "ssim", "psnr_stage1", "psnr_stage2", "psnr_stage3", "psnr_stage4", "seconds"]


def load_config(path):
    """Читає config.json і перевіряє обов'язкові розділи й пайплайни."""
    try:
        config = results_io.read_json(path)
    except (OSError, ValueError) as error:
        raise SystemExit("Не вдалося прочитати файл конфігурації " + path + ": " + str(error)) from error
    for key in ("seed", "image_size", "paths", "degradations", "metrics", "stages", "pipelines"):
        if key not in config:
            raise SystemExit("У конфігурації немає розділу: " + key)
    for name, stage_names in config["pipelines"].items():
        try:
            pipelines.validate_pipeline(stage_names)
        except ValueError as error:
            raise SystemExit("Пайплайн " + name + ": " + str(error)) from error
    return config


def prepared_paths(config, limit=None):
    """Шляхи до підготовлених зображень (перші limit, якщо вказано)."""
    paths = image_io.list_images(config["paths"]["prepared"])
    return paths[:limit] if limit else paths


def command_prepare(config):
    """Готує вибірку: сіре зображення, квадрат із центру, розмір image_size, збереження в PNG."""
    saved = 0
    for path in image_io.list_images(config["paths"]["original"]):
        image = image_io.load_image(path)
        if image is None:
            print("Пропущено (файл пошкоджений або порожній):", path)
            continue
        small = image_io.square_resize(image, config["image_size"])
        name = os.path.splitext(os.path.basename(path))[0]
        image_io.save_image(small, os.path.join(config["paths"]["prepared"], name + ".png"))
        saved += 1
    if saved == 0:
        print("Немає зображень у папці", config["paths"]["original"])
    else:
        print("Підготовлено зображень:", saved)


def command_degrade(config):
    """Створює спотворені копії кожного підготовленого зображення й таблицю метрик спотворень."""
    window = config["metrics"]["ssim_window"]
    step = config["metrics"]["ssim_step"]
    rows = []
    for path in prepared_paths(config):
        clean = image_io.load_image(path)
        if clean is None:
            print("Пропущено:", path)
            continue
        name = os.path.splitext(os.path.basename(path))[0]
        for key, spec in config["degradations"].items():
            rng = degrade.make_rng(config["seed"], name, key)
            noisy = degrade.apply_degradation(clean, spec, rng)
            image_io.save_image(noisy, os.path.join(config["paths"]["degraded"], name + "__" + key + ".png"))
            row = {"image": name, "degradation": key}
            row.update(metrics.compare(clean, noisy, window, step))
            rows.append(row)
    if not rows:
        print("Немає підготовлених зображень: спочатку виконай команду prepare")
        return
    results_io.write_csv(os.path.join(config["paths"]["results"], "degradation_metrics.csv"),
                         rows, ["image", "degradation", "mse", "psnr", "ssim"])
    print("Створено спотворених копій:", len(rows))


def command_metrics(config, path_a, path_b):
    """Виводить MSE, PSNR і SSIM для двох файлів."""
    image_a = image_io.load_image(path_a)
    image_b = image_io.load_image(path_b)
    if image_a is None or image_b is None:
        print("Не вдалося відкрити одне із зображень")
        return
    if image_a.shape != image_b.shape:
        print("Розміри зображень різні:", image_a.shape, image_b.shape)
        return
    result = metrics.compare(image_a, image_b, config["metrics"]["ssim_window"],
                             config["metrics"]["ssim_step"])
    for name, value in result.items():
        print(name.upper(), "=", round(value, 4))


def command_stage(config, name, path_in, path_out, path_reference):
    """Застосовує одну стадію до файлу; якщо є еталон, друкує метрики до і після."""
    image = image_io.load_image(path_in)
    if image is None:
        print("Не вдалося відкрити зображення:", path_in)
        return
    try:
        result = stages.run_stage(name, image, config["stages"].get(name, {}))
    except (ValueError, KeyError) as error:
        print("Помилка стадії:", error)
        return
    image_io.save_image(result, path_out)
    print("Збережено:", path_out)
    if path_reference:
        reference = image_io.load_image(path_reference)
        if reference is None or reference.shape != image.shape:
            print("Еталон не відкрито або його розмір інший: метрики пропущено")
            return
        for label, current in (("до", image), ("після", result)):
            values = metrics.compare(reference, current, config["metrics"]["ssim_window"],
                                     config["metrics"]["ssim_step"])
            print(label, {key: round(value, 4) for key, value in values.items()})


def command_run(config, pipeline_name, limit):
    """Проганяє пайплайн (або all) по всіх спотворених копіях і записує results/<пайплайн>_metrics.csv."""
    names = list(config["pipelines"]) if pipeline_name == "all" else [pipeline_name]
    for name in names:
        if name not in config["pipelines"]:
            print("Невідомий пайплайн:", name)
            return
    window = config["metrics"]["ssim_window"]
    step = config["metrics"]["ssim_step"]
    for pipeline in names:
        stage_names = config["pipelines"][pipeline]
        out_folder = os.path.join(config["paths"]["results"], pipeline)
        jobs = []
        for path in prepared_paths(config, limit):
            image_name = os.path.splitext(os.path.basename(path))[0]
            save_to = out_folder if image_name in config.get("save_intermediate_for", []) else None
            for degradation in config["degradations"]:
                noisy_path = os.path.join(config["paths"]["degraded"], image_name + "__" + degradation + ".png")
                jobs.append((pipeline, stage_names, config["stages"], image_name, degradation, path,
                             noisy_path, window, step, save_to))
        if not jobs:
            print("Немає підготовлених зображень: спочатку виконай prepare і degrade")
            return
        workers = int(config.get("workers", 1))
        print(pipeline, ": завдань", len(jobs), ", процесів", workers)
        if workers > 1:
            with Pool(workers) as pool:
                results = pool.map(pipelines.process_job, jobs, chunksize=4)
        else:
            results = [pipelines.process_job(job) for job in jobs]
        rows = [row for row, error in results if row is not None]
        for _row, error in results:
            if error:
                print("Помилка:", error)
        results_io.write_csv(os.path.join(config["paths"]["results"], pipeline + "_metrics.csv"),
                             rows, ROW_FIELDS)
        print("Записано рядків:", len(rows))


def command_tune(config, pipeline_name):
    """Підбір параметрів на контрольних зображеннях; результат у results/tuning.csv."""
    if pipeline_name not in config["pipelines"]:
        print("Невідомий пайплайн:", pipeline_name)
        return
    rows = tuning.run_sweep(config, pipeline_name)
    path = os.path.join(config["paths"]["results"], "tuning_" + pipeline_name + ".csv")
    results_io.write_csv(path, rows, ["pipeline", "stage", "param", "value", "mean_psnr"])
    print("Збережено:", path)


def save_table(config, frame, name):
    """Зберігає таблицю pandas у results/tables/<name>.csv і друкує її."""
    path = os.path.join(config["paths"]["results"], "tables", name + ".csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    frame.to_csv(path, index=False)
    print("\n" + name + ":")
    print(frame.round(3).to_string(index=False))


def command_compare(config):
    """Середні метрики за спотвореннями й парне порівняння двох пайплайнів."""
    table = analysis.load_metrics(config)
    save_table(config, analysis.by_condition(table), "by_condition")
    names = list(config["pipelines"])
    if len(names) >= 2:
        save_table(config, comparison.paired_comparison(table, names[0], names[1]), "pairwise")


def command_analyze(config):
    """Внесок стадій (абляція) і стабільність результатів по зображеннях."""
    table = analysis.load_metrics(config)
    save_table(config, analysis.ablation(table), "ablation")
    save_table(config, analysis.stability(table), "stability")


def command_check(config):
    """Перевіряє сценарії з config.json і друкує OK / НЕ ОК для кожного."""
    import pandas as pd
    table = analysis.load_metrics(config)
    rows = checks.run_scenarios(config, table)
    for row in rows:
        mark = "OK" if row["ok"] else "НЕ ОК"
        print("Сценарій", row["id"], row["pipeline"], row["degradation"], ": значення", row["value"],
              ", поріг", row["threshold"], "->", mark)
    save_table(config, pd.DataFrame(rows), "scenarios_check")
    print("Пройдено:", sum(1 for row in rows if row["ok"]), "з", len(rows))


def command_plots(config):
    """Створює графіки в results/figures."""
    table = analysis.load_metrics(config)
    summary = analysis.by_condition(table)
    folder = os.path.join(config["paths"]["results"], "figures")
    plots.plot_metric_by_condition(summary, "psnr", "psnr_noisy", "Середній PSNR, дБ",
                                   os.path.join(folder, "psnr_by_condition.png"))
    plots.plot_metric_by_condition(summary, "ssim", "ssim_noisy", "Середній SSIM",
                                   os.path.join(folder, "ssim_by_condition.png"))
    ablation = analysis.ablation(table)
    for pipeline in config["pipelines"]:
        plots.plot_ablation(ablation, pipeline, os.path.join(folder, "ablation_" + pipeline + ".png"))
    for name in config.get("save_intermediate_for", []):
        plots.plot_examples(config, name, os.path.join(folder, "examples_" + name + ".png"))
    print("Графіки збережено в", folder)


def build_parser():
    """Описує команди командного рядка."""
    parser = argparse.ArgumentParser(description="STEM-проєкт: обробка й аналіз зображень")
    parser.add_argument("--config", default="config.json", help="шлях до файлу конфігурації")
    parser.add_argument("--results", default=None, help="інша папка результатів (щоб не затирати основні)")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("prepare", help="підготувати вибірку")
    sub.add_parser("degrade", help="створити спотворені копії")
    run = sub.add_parser("run", help="запустити пайплайн")
    run.add_argument("pipeline", help="назва пайплайна з config.json або all")
    run.add_argument("--limit", type=int, default=None, help="обробити лише перші N зображень")
    stage = sub.add_parser("stage", help="застосувати одну стадію до файлу")
    stage.add_argument("name")
    stage.add_argument("input")
    stage.add_argument("output")
    stage.add_argument("--reference", default=None, help="чисте зображення для метрик")
    metric = sub.add_parser("metrics", help="метрики двох файлів")
    metric.add_argument("first")
    metric.add_argument("second")
    tune = sub.add_parser("tune", help="підбір параметрів")
    tune.add_argument("pipeline")
    for name in ("compare", "analyze", "check", "plots"):
        sub.add_parser(name)
    return parser


def main(argv=None):
    """Розбирає аргументи, читає конфігурацію й викликає потрібну команду."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1
    config = load_config(args.config)
    if args.results:
        config["paths"]["results"] = args.results
    try:
        if args.command == "prepare":
            command_prepare(config)
        elif args.command == "degrade":
            command_degrade(config)
        elif args.command == "run":
            command_run(config, args.pipeline, args.limit)
        elif args.command == "stage":
            command_stage(config, args.name, args.input, args.output, args.reference)
        elif args.command == "metrics":
            command_metrics(config, args.first, args.second)
        elif args.command == "tune":
            command_tune(config, args.pipeline)
        elif args.command == "compare":
            command_compare(config)
        elif args.command == "analyze":
            command_analyze(config)
        elif args.command == "check":
            command_check(config)
        elif args.command == "plots":
            command_plots(config)
    except FileNotFoundError as error:
        print("Помилка:", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Підбір параметрів: перебір значень одного параметра на контрольних зображеннях.

Контрольні зображення - кожне step-те з підготовлених; вони НЕ беруть участі в підсумковому аналізі,
щоб параметри не підганялися під ті самі дані (див. analysis.load_metrics).
"""
import copy
import os

from src import image_io, metrics, pipelines
from src.degrade import apply_degradation, make_rng


def held_out_names(prepared_folder, step):
    """Назви контрольних зображень: кожне step-те за алфавітом, починаючи з першого."""
    names = [os.path.splitext(os.path.basename(path))[0]
             for path in image_io.list_images(prepared_folder)]
    return names[::step] if step > 0 else []


def mean_psnr(config, pipeline, stage_params, names, conditions):
    """Середній PSNR результату пайплайна на контрольних зображеннях у заданих спотвореннях."""
    stage_names = config["pipelines"][pipeline]
    values = []
    for name in names:
        clean = image_io.load_image(os.path.join(config["paths"]["prepared"], name + ".png"))
        for condition in conditions:
            rng = make_rng(config["seed"], name, condition)
            noisy = apply_degradation(clean, config["degradations"][condition], rng)
            output = pipelines.run_chain(noisy, stage_names, stage_params)[-1]
            values.append(metrics.psnr(metrics.mse(clean, output)))
    return sum(values) / len(values)


def run_sweep(config, pipeline):
    """Для кожного параметра зі списку sweeps перебирає значення (решта параметрів - як у конфігу).

    Повертає список рядків для results/tuning.csv.
    """
    names = held_out_names(config["paths"]["prepared"], config["tuning"]["step"])
    conditions = config["tuning"]["conditions"][pipeline]
    rows = []
    for sweep in config["tuning"]["sweeps"][pipeline]:
        for value in sweep["values"]:
            params = copy.deepcopy(config["stages"])
            params[sweep["stage"]][sweep["param"]] = value
            score = mean_psnr(config, pipeline, params, names, conditions)
            rows.append({"pipeline": pipeline, "stage": sweep["stage"], "param": sweep["param"],
                         "value": value, "mean_psnr": score})
            print(pipeline, sweep["stage"], sweep["param"], value, "PSNR =", round(score, 3))
    return rows

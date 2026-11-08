"""Аналіз збережених таблиць метрик: середні значення, внесок стадій, стабільність."""
import os

import pandas as pd

from src import results_io, tuning


def load_metrics(config):
    """Читає results/<пайплайн>_metrics.csv усіх пайплайнів у одну таблицю.

    Контрольні зображення (які використовувались для підбору параметрів) виключаються.
    До таблиці додаються стовпці приросту якості: gain_psnr = psnr - psnr_noisy, gain_ssim.
    """
    frames = []
    for pipeline in config["pipelines"]:
        path = os.path.join(config["paths"]["results"], pipeline + "_metrics.csv")
        if os.path.isfile(path):
            frames.append(pd.DataFrame(results_io.read_csv(path)))
    if not frames:
        raise FileNotFoundError("немає таблиць метрик: спочатку виконай команду run")
    table = pd.concat(frames, ignore_index=True)
    held = tuning.held_out_names(config["paths"]["prepared"], config["tuning"]["step"])
    table = table[~table["image"].isin(held)].copy()
    table["gain_psnr"] = table["psnr"] - table["psnr_noisy"]
    table["gain_ssim"] = table["ssim"] - table["ssim_noisy"]
    return table


def by_condition(table):
    """Середні метрики для кожної пари (пайплайн, спотворення)."""
    grouped = table.groupby(["pipeline", "degradation"], sort=False)
    result = grouped.agg(n=("image", "count"), psnr_noisy=("psnr_noisy", "mean"),
                         psnr=("psnr", "mean"), psnr_std=("psnr", "std"),
                         gain_psnr=("gain_psnr", "mean"), ssim_noisy=("ssim_noisy", "mean"),
                         ssim=("ssim", "mean"), gain_ssim=("gain_ssim", "mean"),
                         seconds=("seconds", "mean"))
    return result.reset_index()


def ablation(table):
    """Внесок кожної стадії: зміна PSNR після стадії відносно входу цієї стадії (у дБ)."""
    rows = []
    for (pipeline, degradation), group in table.groupby(["pipeline", "degradation"], sort=False):
        previous = group["psnr_noisy"]
        row = {"pipeline": pipeline, "degradation": degradation}
        for index in range(1, 5):
            column = "psnr_stage" + str(index)
            if group[column].notna().all():
                row["stage" + str(index)] = float((group[column] - previous).mean())
                previous = group[column]
        rows.append(row)
    return pd.DataFrame(rows)


def stability(table):
    """Розкид приросту PSNR по зображеннях: стандартне відхилення, найгірший випадок, частка втрат."""
    grouped = table.groupby(["pipeline", "degradation"], sort=False)["gain_psnr"]
    result = grouped.agg(std_gain="std", min_gain="min", max_gain="max")
    result["share_worse"] = grouped.apply(lambda values: float((values < 0).mean()))
    return result.reset_index()

"""Парне порівняння двох пайплайнів на одних і тих самих зображеннях."""
import math

import pandas as pd


def paired_comparison(table, first, second):
    """Для кожного спотворення: різниця метрик (second - first) на тому самому знімку.

    Повертає середню різницю PSNR і SSIM, 95 % довірчий інтервал (1,96 * s / sqrt(n)) і частку
    знімків, де кращий другий пайплайн.
    """
    rows = []
    for degradation in table["degradation"].unique():
        part = table[table["degradation"] == degradation]
        a = part[part["pipeline"] == first].set_index("image")
        b = part[part["pipeline"] == second].set_index("image")
        common = a.index.intersection(b.index)
        if len(common) < 2:
            continue
        diff_psnr = b.loc[common, "psnr"] - a.loc[common, "psnr"]
        diff_ssim = b.loc[common, "ssim"] - a.loc[common, "ssim"]
        count = len(common)
        half = 1.96 * diff_psnr.std() / math.sqrt(count)
        rows.append({"degradation": degradation, "n": count,
                     "mean_diff_psnr": diff_psnr.mean(), "ci_low": diff_psnr.mean() - half,
                     "ci_high": diff_psnr.mean() + half,
                     "mean_diff_ssim": diff_ssim.mean(),
                     "share_second_better": float((diff_psnr > 0).mean())})
    return pd.DataFrame(rows)

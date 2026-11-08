"""Графіки: середні метрики за спотвореннями, внесок стадій, приклади результатів."""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from src import image_io  # noqa: E402


def plot_metric_by_condition(summary, column, noisy_column, title, path):
    """Стовпчикова діаграма: спотворене зображення та кожен пайплайн за спотвореннями."""
    degradations = list(summary["degradation"].unique())
    pipelines = list(summary["pipeline"].unique())
    positions = np.arange(len(degradations))
    width = 0.8 / (len(pipelines) + 1)
    figure, axis = plt.subplots(figsize=(9, 4.5))
    noisy = [summary[summary["degradation"] == d][noisy_column].iloc[0] for d in degradations]
    axis.bar(positions, noisy, width, label="спотворене", color="#bbbbbb")
    for index, pipeline in enumerate(pipelines):
        values = [summary[(summary["degradation"] == d) & (summary["pipeline"] == pipeline)][column].iloc[0]
                  for d in degradations]
        axis.bar(positions + (index + 1) * width, values, width, label=pipeline)
    axis.set_xticks(positions + width * len(pipelines) / 2)
    axis.set_xticklabels(degradations)
    axis.set_title(title)
    axis.legend()
    figure.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    figure.savefig(path, dpi=150)
    plt.close(figure)


def plot_ablation(table, pipeline, path):
    """Теплова карта: внесок кожної стадії пайплайна (дБ) за спотвореннями."""
    part = table[table["pipeline"] == pipeline].dropna(axis=1, how="all")
    stage_columns = [c for c in part.columns if c.startswith("stage")]
    data = part[stage_columns].to_numpy(dtype=float)
    figure, axis = plt.subplots(figsize=(6, 4))
    limit = max(1.0, float(np.abs(data).max()))
    image = axis.imshow(data, cmap="RdYlGn", vmin=-limit, vmax=limit, aspect="auto")
    axis.set_xticks(range(len(stage_columns)))
    axis.set_xticklabels(stage_columns)
    axis.set_yticks(range(len(part)))
    axis.set_yticklabels(part["degradation"])
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            axis.text(j, i, "%+.1f" % data[i, j], ha="center", va="center", fontsize=8)
    axis.set_title("Внесок стадій, дБ: " + pipeline)
    figure.colorbar(image)
    figure.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    figure.savefig(path, dpi=150)
    plt.close(figure)


def plot_examples(config, name, path):
    """Приклад для одного знімка: чисте, спотворене, результат пайплайнів для кожного спотворення."""
    clean = image_io.load_image(os.path.join(config["paths"]["prepared"], name + ".png"))
    pipelines = list(config["pipelines"].items())
    degradations = list(config["degradations"])
    columns = 2 + len(pipelines)
    figure, axes = plt.subplots(len(degradations), columns, figsize=(2.2 * columns, 2.2 * len(degradations)))
    for row, degradation in enumerate(degradations):
        noisy = image_io.load_image(os.path.join(config["paths"]["degraded"], name + "__" + degradation + ".png"))
        shown = [("чисте", clean), ("спотворене", noisy)]
        for pipeline, stage_names in pipelines:
            last = len(stage_names)
            file_name = name + "__" + degradation + "__s" + str(last) + "_" + stage_names[-1] + ".png"
            result = image_io.load_image(os.path.join(config["paths"]["results"], pipeline, file_name))
            shown.append((pipeline, result))
        for col, (title, image) in enumerate(shown):
            axis = axes[row, col]
            if image is not None:
                axis.imshow(image, cmap="gray", vmin=0, vmax=255)
            axis.set_xticks([])
            axis.set_yticks([])
            if row == 0:
                axis.set_title(title, fontsize=9)
            if col == 0:
                axis.set_ylabel(degradation, fontsize=8)
    figure.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    figure.savefig(path, dpi=130)
    plt.close(figure)

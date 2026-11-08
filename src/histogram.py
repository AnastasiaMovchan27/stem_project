"""Гістограмна корекція: вирівнювання, CLAHE (обмежене адаптивне вирівнювання), розтягування контрасту."""
import numpy as np

from src.common import check_image, dynamic_range, to_levels

LEVELS = 256


def histogram(image):
    """Гістограма: hist[v] - кількість пікселів з рівнем яскравості v (v = 0...255)."""
    return np.bincount(to_levels(check_image(image)).ravel(), minlength=LEVELS)


def equalize_histogram(image):
    """Глобальне вирівнювання гістограми: new = round((cdf(v) - cdf_min) / (N - cdf_min) * 255).

    cdf - накопичена гістограма. Однотонне зображення повертається без змін.
    """
    arr = check_image(image)
    levels = to_levels(arr)
    hist = histogram(arr)
    cdf = np.cumsum(hist)
    cdf_min = cdf[np.nonzero(hist)[0][0]]
    total = levels.size
    if total == cdf_min:
        return arr.copy()
    table = np.round((cdf - cdf_min) / (total - cdf_min) * (LEVELS - 1))
    return table[levels].astype(np.float64)


def tile_table(tile_levels, clip_limit):
    """Таблиця перетворення яскравості для однієї плитки з обмеженням гістограми.

    Стовпчики вищі за clip_limit * (середня висота) зрізаються, надлишок рівномірно розподіляється
    по всіх рівнях; таблиця = накопичена гістограма, помножена на 255.
    """
    hist = np.bincount(tile_levels.ravel(), minlength=LEVELS).astype(np.float64)
    limit = max(1.0, clip_limit * tile_levels.size / LEVELS)
    excess = np.sum(np.maximum(hist - limit, 0.0))
    hist = np.minimum(hist, limit) + excess / LEVELS
    return np.cumsum(hist) / np.sum(hist) * (LEVELS - 1)


def clahe(image, tiles=8, clip_limit=2.0, range_threshold=None):
    """CLAHE (Zuiderveld, 1994).

    1) Зображення ділимо на tiles x tiles плиток. 2) Для кожної плитки будуємо таблицю з обмеженою
    гістограмою (tile_table). 3) Яскравість кожного пікселя рахуємо з таблиць чотирьох найближчих
    плиток і змішуємо білінійно (так немає видимих меж плиток).
    range_threshold: якщо вказано, корекція застосовується лише до зображень, у яких динамічний
    діапазон менший за цей поріг (контрастним зображенням вона не потрібна).
    """
    arr = check_image(image)
    if not isinstance(tiles, int) or tiles < 1:
        raise ValueError("tiles має бути цілим >= 1")
    if clip_limit < 1.0:
        raise ValueError("clip_limit має бути >= 1")
    if range_threshold is not None and dynamic_range(arr) >= range_threshold:
        return arr.copy()
    height, width = arr.shape
    tiles_y = min(tiles, height)
    tiles_x = min(tiles, width)
    levels = to_levels(arr)
    # таблиці всіх плиток
    tables = np.zeros((tiles_y, tiles_x, LEVELS))
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            top = ty * height // tiles_y
            bottom = (ty + 1) * height // tiles_y
            left = tx * width // tiles_x
            right = (tx + 1) * width // tiles_x
            tables[ty, tx] = tile_table(levels[top:bottom, left:right], clip_limit)
    result = np.zeros_like(arr)
    for i in range(height):
        # положення рядка відносно центрів плиток
        pos_y = (i + 0.5) * tiles_y / height - 0.5
        y0 = min(max(int(np.floor(pos_y)), 0), tiles_y - 1)
        y1 = min(y0 + 1, tiles_y - 1)
        wy = min(max(pos_y - y0, 0.0), 1.0)
        for j in range(width):
            pos_x = (j + 0.5) * tiles_x / width - 0.5
            x0 = min(max(int(np.floor(pos_x)), 0), tiles_x - 1)
            x1 = min(x0 + 1, tiles_x - 1)
            wx = min(max(pos_x - x0, 0.0), 1.0)
            v = levels[i, j]
            top_value = tables[y0, x0, v] * (1 - wx) + tables[y0, x1, v] * wx
            bottom_value = tables[y1, x0, v] * (1 - wx) + tables[y1, x1, v] * wx
            result[i, j] = top_value * (1 - wy) + bottom_value * wy
    return result


def percentile_level(levels, percent, upper):
    """Рівень яскравості за накопиченою гістограмою (percent у відсотках).

    upper=False: перший рівень, де cdf БІЛЬШЕ percent (0 % дає найтемніший рівень на знімку);
    upper=True: перший рівень, де cdf досягає percent (100 % дає найсвітліший рівень).
    """
    hist = np.bincount(levels.ravel(), minlength=LEVELS)
    cdf = np.cumsum(hist) / levels.size * 100.0
    if upper:
        index = np.searchsorted(cdf, percent - 1e-9, side="left")
    else:
        index = np.searchsorted(cdf, percent, side="right")
    return float(min(index, LEVELS - 1))


def contrast_stretch(image, low_percentile=0.0, high_percentile=100.0, range_threshold=None):
    """Лінійне розтягування контрасту: low -> 0, high -> 255, out = (I - low) * 255 / (high - low).

    range_threshold: розтягуємо лише зображення з динамічним діапазоном меншим за поріг.
    """
    arr = check_image(image)
    if not 0.0 <= low_percentile < high_percentile <= 100.0:
        raise ValueError("потрібно 0 <= low_percentile < high_percentile <= 100")
    levels = to_levels(arr)
    low = percentile_level(levels, low_percentile, False)
    high = percentile_level(levels, high_percentile, True)
    if high <= low or (range_threshold is not None and dynamic_range(arr) >= range_threshold):
        return arr.copy()
    return np.clip((arr - low) * 255.0 / (high - low), 0.0, 255.0)

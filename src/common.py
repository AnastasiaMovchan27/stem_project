"""Спільні дрібні функції: обрізання значень, відбивання країв, рівні яскравості."""
import numpy as np

MAX_VALUE = 255.0


def clip_image(image):
    """Обрізає значення до діапазону 0...255."""
    return np.clip(image, 0.0, MAX_VALUE)


def to_levels(image):
    """Округлює яскравості до цілих рівнів 0...255 (потрібно для гістограм)."""
    return np.clip(np.round(image), 0, 255).astype(np.int64)


def pad_image(image, pad):
    """Додає по краях pad пікселів, відбиваючи зображення дзеркально (щоб не було різких країв)."""
    if pad <= 0:
        return image.copy()
    height, width = image.shape
    # для дуже маленьких зображень відбиття неможливе, тоді повторюємо крайні пікселі
    mode = "reflect" if (height > pad and width > pad) else "edge"
    return np.pad(image, pad, mode=mode)


def check_image(image):
    """Перевіряє, що це непорожня таблиця 2D, і повертає її як числа з комою."""
    array = np.asarray(image, dtype=np.float64)
    if array.ndim != 2 or array.size == 0:
        raise ValueError("очікується непорожнє сіре зображення (2D)")
    return array


def dynamic_range(image):
    """Різниця між рівнями 99,5 % і 0,5 % гістограми: «справжній» діапазон яскравостей."""
    levels = to_levels(check_image(image))
    hist = np.bincount(levels.ravel(), minlength=256)
    cdf = np.cumsum(hist) / levels.size * 100.0
    low = np.searchsorted(cdf, 0.5, side="right")
    high = np.searchsorted(cdf, 99.5 - 1e-9, side="left")
    return float(min(high, 255) - low)

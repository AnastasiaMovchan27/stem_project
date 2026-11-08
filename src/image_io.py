"""Читання, підготовка й збереження зображень (Pillow лише читає й пише файли)."""
import os

import numpy as np
from PIL import Image

EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")


def list_images(folder):
    """Повертає відсортований список шляхів до зображень у папці (порожній, якщо папки немає)."""
    if not os.path.isdir(folder):
        return []
    names = sorted(name for name in os.listdir(folder) if name.lower().endswith(EXTENSIONS))
    return [os.path.join(folder, name) for name in names]


def to_gray(rgb):
    """Яскравість за формулою з Лаби 4: Y = 0.299 R + 0.587 G + 0.114 B."""
    return 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]


def load_image(path):
    """Читає файл як сіре зображення (числа 0...255). Повертає None, якщо файл порожній або пошкоджений."""
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        return None
    try:
        with Image.open(path) as handle:
            handle.load()
            mode = handle.mode
            if mode in ("I;16", "I;16L", "I;16B", "I"):
                # 16-бітні зображення зводимо до 0...255
                array = np.asarray(handle, dtype=np.float64)
                array = array / 257.0 if array.max() > 255 else array
            elif mode == "F":
                array = np.asarray(handle, dtype=np.float64)
            elif mode in ("L", "LA", "1"):
                array = np.asarray(handle.convert("L"), dtype=np.float64)
            else:
                # кольорові (RGB, RGBA, палітра): прозорість відкидаємо
                array = to_gray(np.asarray(handle.convert("RGB"), dtype=np.float64))
    except (OSError, ValueError):
        return None
    if array.ndim != 2 or array.size == 0:
        return None
    return np.clip(array, 0.0, 255.0)


def square_resize(image, size):
    """Вирізає квадрат із центру й зменшує його до size x size."""
    height, width = image.shape
    side = min(height, width)
    top = (height - side) // 2
    left = (width - side) // 2
    square = image[top:top + side, left:left + side]
    data = np.clip(np.round(square), 0, 255).astype(np.uint8)
    small = Image.fromarray(data).resize((size, size), Image.LANCZOS)
    return np.asarray(small, dtype=np.float64)


def save_image(image, path):
    """Зберігає сіре зображення як 8-бітний файл (папку створює, якщо її немає)."""
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    data = np.clip(np.round(image), 0, 255).astype(np.uint8)
    Image.fromarray(data).save(path)

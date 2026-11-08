"""Ретушування й покращення: усунення імпульсних пікселів, нерізке маскування, оцінка рівня шуму."""
import numpy as np

from src.common import check_image, pad_image


def estimate_noise_sigma(image):
    """Оцінка стандартного відхилення шуму (Immerkaer, 1996).

    Зображення згортається з маскою [[1,-2,1],[-2,4,-2],[1,-2,1]], яка прибирає плавні деталі й
    лишає шум: sigma = sqrt(pi/2) / (6 (W-2)(H-2)) * сума |згортка|.
    """
    arr = check_image(image)
    height, width = arr.shape
    if height < 3 or width < 3:
        return 0.0
    total = (arr[:-2, :-2] - 2 * arr[:-2, 1:-1] + arr[:-2, 2:]
             - 2 * arr[1:-1, :-2] + 4 * arr[1:-1, 1:-1] - 2 * arr[1:-1, 2:]
             + arr[2:, :-2] - 2 * arr[2:, 1:-1] + arr[2:, 2:])
    return float(np.sqrt(np.pi / 2.0) * np.abs(total).sum() / (6.0 * (width - 2) * (height - 2)))


def impulse_inpaint(image, max_window=7):
    """Усунення імпульсного шуму: піксель зі значенням 0 або 255 вважаємо зіпсованим.

    Зіпсований піксель замінюється середнім із НЕзіпсованих пікселів у найменшому вікні
    (3x3, 5x5, ... до max_window), де такі є. Незіпсовані пікселі не змінюються, тому чисті
    ділянки не розмиваються.
    """
    arr = check_image(image)
    if not isinstance(max_window, int) or max_window < 3 or max_window % 2 == 0:
        raise ValueError("max_window має бути непарним цілим >= 3")
    height, width = arr.shape
    bad = (arr <= 0) | (arr >= 255)
    radius_max = max_window // 2
    padded = np.pad(arr, radius_max, mode="constant")
    padded_bad = np.pad(bad, radius_max, mode="constant", constant_values=True)
    result = arr.copy()
    for i in range(height):
        for j in range(width):
            if not bad[i, j]:
                continue
            # збільшуємо вікно, доки не знайдемо хоча б один незіпсований піксель
            for size in range(3, max_window + 1, 2):
                r = size // 2
                top = i + radius_max - r
                left = j + radius_max - r
                window = padded[top:top + size, left:left + size]
                good = ~padded_bad[top:top + size, left:left + size]
                if good.any():
                    result[i, j] = window[good].mean()
                    break
    return result


def gaussian_kernel(sigma):
    """Маска Гаусса (2D) радіуса ceil(3 sigma), сума коефіцієнтів дорівнює 1."""
    radius = max(1, int(np.ceil(3.0 * sigma)))
    offsets = np.arange(-radius, radius + 1, dtype=np.float64)
    line = np.exp(-(offsets ** 2) / (2.0 * sigma ** 2))
    kernel = np.outer(line, line)
    return kernel / kernel.sum()


def gaussian_blur(image, sigma):
    """Розмиття маскою Гаусса: нове значення = сума (піксель * коефіцієнт маски)."""
    arr = check_image(image)
    kernel = gaussian_kernel(sigma)
    radius = kernel.shape[0] // 2
    padded = pad_image(arr, radius)
    height, width = arr.shape
    result = np.zeros_like(arr)
    for i in range(height):
        for j in range(width):
            window = padded[i:i + 2 * radius + 1, j:j + 2 * radius + 1]
            result[i, j] = np.sum(window * kernel)
    return result


def unsharp_mask(image, amount=0.6, sigma=1.0, threshold=0.0, noise_factor=0.0):
    """Нерізке маскування: out = I + amount * (I - blur(I)).

    Різниця I - blur(I) - «деталі». Деталі, менші за поріг, вважаємо шумом і не підсилюємо.
    Поріг = max(threshold, noise_factor * оцінений рівень шуму), тож на шумних зображеннях
    підсилення слабшає.
    """
    arr = check_image(image)
    if amount < 0 or sigma <= 0:
        raise ValueError("amount >= 0 і sigma > 0")
    detail = arr - gaussian_blur(arr, sigma)
    limit = max(threshold, noise_factor * estimate_noise_sigma(arr))
    if limit > 0:
        detail = np.where(np.abs(detail) >= limit, detail, 0.0)
    return arr + amount * detail

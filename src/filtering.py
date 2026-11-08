"""Фільтри шумозаглушення: білатеральний фільтр і анізотропна дифузія Переона-Маліка.

У лабораторних 5-6 були лінійні фільтри й фільтри за порядковими статистиками
(усереднення, Гаусс, медіана, мін, макс, середина діапазону); тут інші методи.
"""
import numpy as np

from src.common import check_image, pad_image


def bilateral_filter(image, radius, sigma_space, sigma_range):
    """Білатеральний фільтр (Tomasi, Manduchi, 1998): зважене середнє сусідів у вікні.

    Вага сусіда = exp(-d^2 / (2 sigma_space^2)) * exp(-c^2 / (2 sigma_range^2)),
    де d - відстань до центрального пікселя, c - різниця яскравостей.
    Сусіди з іншого боку краю мають іншу яскравість, тому майже не враховуються: краї лишаються чіткими.
    """
    arr = check_image(image)
    if not isinstance(radius, int) or radius < 1:
        raise ValueError("radius має бути цілим >= 1")
    if sigma_space <= 0 or sigma_range <= 0:
        raise ValueError("sigma_space і sigma_range мають бути додатними")
    height, width = arr.shape
    padded = pad_image(arr, radius)
    size = 2 * radius + 1
    # вага за відстанню однакова для всіх пікселів, тому рахуємо її один раз
    space = np.zeros((size, size))
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            space[dy + radius, dx + radius] = np.exp(-(dy * dy + dx * dx) / (2.0 * sigma_space ** 2))
    range_denominator = 2.0 * sigma_range ** 2
    result = np.zeros_like(arr)
    for i in range(height):
        for j in range(width):
            window = padded[i:i + size, j:j + size]
            # вага за схожістю яскравості
            weights = space * np.exp(-((window - arr[i, j]) ** 2) / range_denominator)
            result[i, j] = np.sum(weights * window) / np.sum(weights)
    return result


def anisotropic_diffusion(image, iterations, kappa, gamma=0.2):
    """Анізотропна дифузія Переона-Маліка (1990): ітераційне згладжування, що зупиняється на краях.

    I_new = I + gamma * сума по 4 сусідах c(різниця) * різниця, c(g) = 1 / (1 + (g / kappa)^2).
    Де різниця яскравостей велика (край), провідність c близька до 0 і яскравість не розпливається.
    gamma <= 0,25 для стійкості.
    """
    arr = check_image(image)
    if not isinstance(iterations, int) or iterations < 0:
        raise ValueError("iterations має бути цілим >= 0")
    if kappa <= 0:
        raise ValueError("kappa має бути додатним")
    if not 0.0 < gamma <= 0.25:
        raise ValueError("gamma має бути в (0; 0,25]")
    current = arr.copy()
    for _ in range(iterations):
        padded = np.pad(current, 1, mode="edge")
        flow = np.zeros_like(current)
        # різниці з північним, південним, західним і східним сусідом
        for diff in (padded[:-2, 1:-1] - current, padded[2:, 1:-1] - current,
                     padded[1:-1, :-2] - current, padded[1:-1, 2:] - current):
            conductance = 1.0 / (1.0 + (diff / kappa) ** 2)
            flow = flow + conductance * diff
        current = current + gamma * flow
    return current

"""Перетворення Фур'є, написане вручну (через матрицю ДПФ), і частотний фільтр Вінера."""
import numpy as np

from src.common import check_image, pad_image
from src.retouch import estimate_noise_sigma


def dft_matrix(size, inverse=False):
    """Матриця одновимірного ДПФ: елемент (j, k) = exp(-2 pi i j k / size) (для оберненого знак +)."""
    index = np.arange(size)
    sign = 1.0 if inverse else -1.0
    return np.exp(sign * 2j * np.pi * np.outer(index, index) / size)


def dft2(image):
    """Двовимірне ДПФ: F = W_h * f * W_w (ДПФ рядків і стовпців по черзі)."""
    arr = np.asarray(image, dtype=np.float64)
    return dft_matrix(arr.shape[0]) @ arr @ dft_matrix(arr.shape[1])


def idft2(spectrum):
    """Обернене двовимірне ДПФ (дійсна частина, ділення на кількість пікселів)."""
    height, width = spectrum.shape
    full = dft_matrix(height, True) @ spectrum @ dft_matrix(width, True)
    return full.real / (height * width)


def spectral_wiener(image, strength=1.0, pad=16):
    """Адаптивний частотний фільтр типу Вінера.

    Рівень шуму sigma оцінюємо за зображенням. Білий шум додає потужність sigma^2 * N до кожного
    коефіцієнта ДПФ (N - кількість пікселів), тому кожен коефіцієнт F множимо на підсилення

        G = max(|F|^2 - strength * sigma^2 * N, 0) / |F|^2

    Сильні (структурні) частоти лишаються, слабші за рівень шуму - вилучаються.
    Перед ДПФ зображення доповнюється дзеркально на pad пікселів, щоб не було артефактів на краях.
    """
    arr = check_image(image)
    if strength <= 0:
        raise ValueError("strength має бути додатним")
    padded = pad_image(arr, max(0, pad))
    sigma = estimate_noise_sigma(padded)
    spectrum = dft2(padded)
    power = np.abs(spectrum) ** 2
    noise_power = strength * sigma ** 2 * padded.size
    gain = np.maximum(power - noise_power, 0.0) / np.maximum(power, 1e-12)
    filtered = idft2(spectrum * gain)
    offset = max(0, pad)
    return filtered[offset:offset + arr.shape[0], offset:offset + arr.shape[1]]

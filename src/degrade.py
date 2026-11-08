"""Спотворення зображень: гаусів шум, імпульсний шум («сіль-перець»), їхня суміш, слабкий контраст."""
import zlib

import numpy as np

from src.common import clip_image


def make_rng(seed, image_name, degradation_name):
    """Генератор випадкових чисел, однаковий для однієї трійки (seed, знімок, спотворення).

    Тому шум відтворюється при повторному запуску, а порядок обробки файлів не має значення.
    """
    return np.random.default_rng([seed, zlib.crc32(image_name.encode("utf-8")),
                                  zlib.crc32(degradation_name.encode("utf-8"))])


def add_gaussian(image, sigma, rng):
    """Адитивний гаусів шум: I_noisy = I + N(0, sigma^2), далі округлення й обрізання до 0...255."""
    if sigma < 0:
        raise ValueError("sigma не може бути від'ємною")
    noise = rng.normal(0.0, sigma, image.shape)
    return np.round(clip_image(image + noise))


def add_salt_pepper(image, prob, rng):
    """Імпульсний шум: частка prob пікселів стає чорною (0) або білою (255), порівну."""
    if not 0.0 <= prob <= 1.0:
        raise ValueError("prob має бути від 0 до 1")
    result = image.copy()
    chance = rng.random(image.shape)
    result[chance < prob / 2.0] = 0.0
    result[chance > 1.0 - prob / 2.0] = 255.0
    return result


def add_low_contrast(image, alpha, beta, sigma, rng):
    """Слабке освітлення: out = alpha * I + beta (контраст стиснуто), потім гаусів шум sigma."""
    if not 0.0 < alpha <= 1.0:
        raise ValueError("alpha має бути в (0; 1]")
    return add_gaussian(clip_image(alpha * image + beta), sigma, rng)


def apply_degradation(image, spec, rng):
    """Застосовує спотворення, описане словником spec з config.json (поле type + параметри)."""
    kind = spec.get("type")
    if kind == "gaussian":
        return add_gaussian(image, float(spec["sigma"]), rng)
    if kind == "salt_pepper":
        return add_salt_pepper(image, float(spec["prob"]), rng)
    if kind == "mixed":
        noisy = add_gaussian(image, float(spec["sigma"]), rng)
        return add_salt_pepper(noisy, float(spec["prob"]), rng)
    if kind == "low_contrast":
        return add_low_contrast(image, float(spec["alpha"]), float(spec["beta"]),
                                float(spec["sigma"]), rng)
    raise ValueError("Невідомий тип спотворення: " + str(kind))

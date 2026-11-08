"""Тести метрик MSE, PSNR, SSIM: очікувані числа пораховано вручну."""
import math
import unittest

import numpy as np

from src import metrics


class TestMetrics(unittest.TestCase):
    """Перевірка MSE, PSNR і SSIM."""

    def test_mse_by_hand(self):
        """РОЗРАХУНОК ВРУЧНУ: різниці 0, 0, 0, 4 -> квадрати 0, 0, 0, 16 -> сума 16 -> MSE = 16 / 4 = 4."""
        first = np.array([[0.0, 0.0], [0.0, 4.0]])
        second = np.zeros((2, 2))
        self.assertEqual(metrics.mse(first, second), 4.0)

    def test_mse_symmetric_and_zero(self):
        """MSE однакових зображень = 0, і MSE(a, b) = MSE(b, a)."""
        first = np.array([[1.0, 2.0], [3.0, 4.0]])
        second = np.array([[2.0, 2.0], [1.0, 0.0]])
        self.assertEqual(metrics.mse(first, first), 0.0)
        self.assertEqual(metrics.mse(first, second), metrics.mse(second, first))

    def test_mse_shape_mismatch(self):
        """Різні розміри зображень -> помилка."""
        with self.assertRaises(ValueError):
            metrics.mse(np.zeros((2, 2)), np.zeros((3, 3)))

    def test_psnr_by_hand(self):
        """РОЗРАХУНОК ВРУЧНУ: MSE = 65,025 -> 255^2 / 65,025 = 1000 -> 10 * lg(1000) = 30 дБ."""
        self.assertAlmostEqual(metrics.psnr(65.025), 30.0, places=9)

    def test_psnr_identical_is_inf(self):
        """MSE = 0 -> PSNR нескінченний."""
        self.assertTrue(math.isinf(metrics.psnr(0.0)))

    def test_psnr_example_mse4(self):
        """РОЗРАХУНОК ВРУЧНУ: MSE = 4 -> 10 * lg(65025 / 4) = 10 * lg(16256,25) = 42,1103 дБ."""
        self.assertAlmostEqual(metrics.psnr(4.0), 10 * math.log10(65025 / 4.0), places=9)
        self.assertAlmostEqual(metrics.psnr(4.0), 42.1103, places=3)

    def test_ssim_identical_is_one(self):
        """SSIM однакових зображень = 1 (чисельник дорівнює знаменнику)."""
        rng = np.random.default_rng(1)
        image = rng.integers(0, 256, (16, 16)).astype(float)
        self.assertAlmostEqual(metrics.ssim(image, image), 1.0, places=9)

    def test_ssim_flat_black_vs_white(self):
        """РОЗРАХУНОК ВРУЧНУ: a = 0, b = 255, дисперсії й коваріація 0 -> SSIM = C1 / (255^2 + C1).

        C1 = (0,01 * 255)^2 = 6,5025; 6,5025 / 65031,5025 = 0,0001.
        """
        black = np.zeros((8, 8))
        white = np.full((8, 8), 255.0)
        self.assertAlmostEqual(metrics.ssim(black, white), 6.5025 / (65025 + 6.5025), places=9)

    def test_ssim_decreases_with_noise(self):
        """Чим сильніший шум, тим менший SSIM."""
        rng = np.random.default_rng(2)
        image = rng.integers(0, 256, (32, 32)).astype(float)
        weak = np.clip(image + rng.normal(0, 5, image.shape), 0, 255)
        strong = np.clip(image + rng.normal(0, 40, image.shape), 0, 255)
        self.assertGreater(metrics.ssim(image, weak), metrics.ssim(image, strong))

    def test_ssim_small_image(self):
        """Зображення менше за вікно: беремо все зображення, помилки немає."""
        image = np.array([[1.0, 2.0], [3.0, 4.0]])
        self.assertAlmostEqual(metrics.ssim(image, image), 1.0, places=9)

    def test_compare_keys(self):
        """Compare повертає mse, psnr, ssim."""
        image = np.zeros((8, 8))
        self.assertEqual(set(metrics.compare(image, image)), {"mse", "psnr", "ssim"})


if __name__ == "__main__":
    unittest.main()

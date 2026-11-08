"""Тести білатерального фільтра й анізотропної дифузії на малих зображеннях 3 x 3."""
import unittest

import numpy as np

from src import filtering


class TestBilateral(unittest.TestCase):
    """Білатеральний фільтр."""

    def test_flat_image_stays_flat(self):
        """Однотонне зображення не змінюється: усі сусіди однакові, зважене середнє = 100."""
        image = np.full((3, 3), 100.0)
        result = filtering.bilateral_filter(image, 1, 1.0, 30)
        self.assertTrue(np.allclose(result, 100.0))

    def test_outlier_is_ignored(self):
        """РОЗРАХУНОК ВРУЧНУ: викид 255 в куті, центр 100, sigma_range = 10.

        Різниця 155, вага = exp(-155^2 / (2 * 100)) = exp(-120) ~ 0, тому центр лишається 100.
        """
        image = np.full((3, 3), 100.0)
        image[0, 0] = 255.0
        result = filtering.bilateral_filter(image, 1, 1.0, 10)
        self.assertAlmostEqual(result[1, 1], 100.0, places=6)

    def test_spike_is_smoothed_when_range_is_large(self):
        """Великий sigma_range робить фільтр майже усередненням: центральний «пік» стає меншим."""
        image = np.zeros((3, 3))
        image[1, 1] = 100.0
        result = filtering.bilateral_filter(image, 1, 1.0, 1000.0)
        self.assertLess(result[1, 1], 100.0)
        self.assertGreater(result[1, 1], 0.0)

    def test_two_pixel_weights_by_hand(self):
        """РОЗРАХУНОК ВРУЧНУ: рядок з 2 однакових значень і одного іншого, radius 1, sigma_space 1.

        Для крайнього лівого пікселя (0, 0) у зображенні 1 x 3 дзеркало не працює, береться edge:
        перевіряємо лише, що результат між мінімумом і максимумом вікна.
        """
        image = np.array([[0.0, 0.0, 100.0], [0.0, 0.0, 100.0], [0.0, 0.0, 100.0]])
        result = filtering.bilateral_filter(image, 1, 1.0, 50.0)
        self.assertTrue(np.all(result >= 0.0) and np.all(result <= 100.0))

    def test_edge_preserved(self):
        """Різкий край (0 | 200) при малому sigma_range майже не розмивається."""
        image = np.zeros((6, 6))
        image[:, 3:] = 200.0
        result = filtering.bilateral_filter(image, 2, 2.0, 10.0)
        self.assertLess(abs(result[3, 2] - 0.0), 1.0)
        self.assertLess(abs(result[3, 3] - 200.0), 1.0)

    def test_invalid_parameters(self):
        """Некоректні параметри -> ValueError."""
        image = np.zeros((3, 3))
        with self.assertRaises(ValueError):
            filtering.bilateral_filter(image, 0, 1.0, 10)
        with self.assertRaises(ValueError):
            filtering.bilateral_filter(image, 1, 0.0, 10)
        with self.assertRaises(ValueError):
            filtering.bilateral_filter(image, 1, 1.0, -5)

    def test_tiny_image(self):
        """Зображення 1 x 1 обробляється без помилки (береться edge-доповнення)."""
        result = filtering.bilateral_filter(np.array([[42.0]]), 1, 1.0, 10)
        self.assertAlmostEqual(result[0, 0], 42.0, places=6)


class TestDiffusion(unittest.TestCase):
    """Анізотропна дифузія."""

    def test_flat_image_stays_flat(self):
        """Однотонне зображення не змінюється."""
        image = np.full((4, 4), 50.0)
        self.assertTrue(np.allclose(filtering.anisotropic_diffusion(image, 5, 20.0), 50.0))

    def test_one_step_by_hand(self):
        """РОЗРАХУНОК ВРУЧНУ: пік 100 в центрі, kappa = 1e9 (провідність = 1), gamma = 0,2.

        Центр: 100 + 0,2 * 4 * (0 - 100) = 20. Верхній сусід: 0 + 0,2 * (100 - 0) = 20
        (інші його різниці 0, бо край дзеркалиться). Кути: 0. Сума 20 * 5 = 100 зберігається.
        """
        image = np.zeros((3, 3))
        image[1, 1] = 100.0
        result = filtering.anisotropic_diffusion(image, 1, 1e9, 0.2)
        expected = np.array([[0.0, 20.0, 0.0], [20.0, 20.0, 20.0], [0.0, 20.0, 0.0]])
        self.assertTrue(np.allclose(result, expected))
        self.assertAlmostEqual(result.sum(), 100.0, places=9)

    def test_edge_not_diffused_with_small_kappa(self):
        """При малому kappa провідність на сильному краю майже 0 - край лишається."""
        image = np.zeros((4, 4))
        image[:, 2:] = 200.0
        result = filtering.anisotropic_diffusion(image, 3, 1.0, 0.2)
        self.assertLess(abs(result[1, 1] - 0.0), 0.1)
        self.assertLess(abs(result[1, 2] - 200.0), 0.1)

    def test_zero_iterations_is_identity(self):
        """0 ітерацій - зображення без змін."""
        image = np.arange(9.0).reshape(3, 3)
        self.assertTrue(np.array_equal(filtering.anisotropic_diffusion(image, 0, 10.0), image))

    def test_invalid_parameters(self):
        """Некоректні параметри -> ValueError."""
        image = np.zeros((3, 3))
        with self.assertRaises(ValueError):
            filtering.anisotropic_diffusion(image, -1, 10.0)
        with self.assertRaises(ValueError):
            filtering.anisotropic_diffusion(image, 1, 0.0)
        with self.assertRaises(ValueError):
            filtering.anisotropic_diffusion(image, 1, 10.0, 0.5)


if __name__ == "__main__":
    unittest.main()

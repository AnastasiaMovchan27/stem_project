"""Тести ретушування: імпульсне відновлення, оцінка шуму, нерізке маскування."""
import unittest

import numpy as np

from src import retouch


class TestInpaint(unittest.TestCase):
    """Усунення імпульсів."""

    def test_salt_in_center(self):
        """РОЗРАХУНОК ВРУЧНУ: усі пікселі 50, у центрі 255; сусідів 8 штук по 50 -> середнє 50."""
        image = np.full((3, 3), 50.0)
        image[1, 1] = 255.0
        self.assertEqual(retouch.impulse_inpaint(image, 3)[1, 1], 50.0)

    def test_neighbours_that_are_impulses_are_skipped(self):
        """РОЗРАХУНОК ВРУЧНУ: центр 255, сусіди: 255 (угорі), 0 (ліворуч), решта 6 штук по 10.

        Незіпсовані сусіди - шість значень 10; середнє = 10.
        """
        image = np.array([[10.0, 255.0, 10.0], [0.0, 255.0, 10.0], [10.0, 10.0, 10.0]])
        result = retouch.impulse_inpaint(image, 3)
        self.assertTrue(np.allclose(result, 10.0))

    def test_clean_pixels_unchanged(self):
        """Піксель, що не є 0 або 255, не змінюється."""
        image = np.array([[10.0, 20.0, 30.0], [40.0, 50.0, 60.0], [70.0, 80.0, 90.0]])
        self.assertTrue(np.array_equal(retouch.impulse_inpaint(image, 3), image))

    def test_window_grows(self):
        """Якщо всі сусіди 3 x 3 зіпсовані, вікно збільшується до 5 x 5.

        РОЗРАХУНОК ВРУЧНУ: 5 x 5, усі 255, окрім кутів, де 100: центр бере лише їх (4 штуки по 100) -> 100.
        """
        image = np.full((5, 5), 255.0)
        for i, j in ((0, 0), (0, 4), (4, 0), (4, 4)):
            image[i, j] = 100.0
        self.assertAlmostEqual(retouch.impulse_inpaint(image, 5)[2, 2], 100.0)

    def test_nothing_to_use_keeps_value(self):
        """Якщо в межах max_window немає жодного чистого пікселя, значення лишається."""
        image = np.full((3, 3), 255.0)
        self.assertTrue(np.array_equal(retouch.impulse_inpaint(image, 3), image))

    def test_invalid_window(self):
        """max_window парне або < 3 -> ValueError."""
        with self.assertRaises(ValueError):
            retouch.impulse_inpaint(np.zeros((3, 3)), 4)
        with self.assertRaises(ValueError):
            retouch.impulse_inpaint(np.zeros((3, 3)), 1)


class TestNoiseAndSharpen(unittest.TestCase):
    """Оцінка шуму, розмиття, нерізке маскування."""

    def test_noise_estimate_flat_and_plane(self):
        """Однотонне зображення й похила площина дають 0 (маска Immerkaer прибирає лінійні зміни)."""
        flat = np.full((8, 8), 40.0)
        plane = np.add.outer(np.arange(8.0), 2 * np.arange(8.0))
        self.assertAlmostEqual(retouch.estimate_noise_sigma(flat), 0.0)
        self.assertAlmostEqual(retouch.estimate_noise_sigma(plane), 0.0)

    def test_noise_estimate_close_to_sigma(self):
        """Для гаусового шуму sigma = 10 на гладкому тлі оцінка близька до 10."""
        rng = np.random.default_rng(5)
        image = np.full((128, 128), 100.0) + rng.normal(0, 10, (128, 128))
        self.assertAlmostEqual(retouch.estimate_noise_sigma(image), 10.0, delta=0.7)

    def test_noise_estimate_small_image(self):
        """Зображення менше 3 x 3 -> 0."""
        self.assertEqual(retouch.estimate_noise_sigma(np.ones((2, 2))), 0.0)

    def test_gaussian_kernel_sum_and_symmetry(self):
        """Сума коефіцієнтів = 1, маска симетрична, центр найбільший."""
        kernel = retouch.gaussian_kernel(1.0)
        self.assertAlmostEqual(kernel.sum(), 1.0)
        self.assertTrue(np.allclose(kernel, kernel.T))
        self.assertEqual(kernel.argmax(), kernel.size // 2)

    def test_blur_flat_and_spreads_impulse(self):
        """Розмиття однотонного не змінює; піковий піксель розпливається, а сума зберігається."""
        flat = np.full((9, 9), 30.0)
        self.assertTrue(np.allclose(retouch.gaussian_blur(flat, 1.0), 30.0))
        spike = np.zeros((15, 15))
        spike[7, 7] = 100.0
        blurred = retouch.gaussian_blur(spike, 1.0)
        self.assertLess(blurred[7, 7], 100.0)
        self.assertAlmostEqual(blurred.sum(), 100.0, places=6)

    def test_unsharp_identity_and_flat(self):
        """Amount = 0 і однотонне зображення не змінюються."""
        rng = np.random.default_rng(6)
        image = rng.integers(0, 256, (8, 8)).astype(float)
        self.assertTrue(np.allclose(retouch.unsharp_mask(image, 0.0, 1.0), image))
        flat = np.full((8, 8), 9.0)
        self.assertTrue(np.allclose(retouch.unsharp_mask(flat, 1.0, 1.0), 9.0))

    def test_unsharp_increases_edge_contrast(self):
        """На краю 0 | 200 нерізке маскування робить перепад більшим."""
        image = np.zeros((12, 12))
        image[:, 6:] = 200.0
        sharp = retouch.unsharp_mask(image, 1.0, 1.0)
        self.assertGreater(sharp[6, 6] - sharp[6, 5], image[6, 6] - image[6, 5] - 1e-9)
        self.assertGreater(sharp[6, 6], 200.0)

    def test_unsharp_noise_threshold_blocks_weak_detail(self):
        """Дуже великий noise_factor вважає всі деталі шумом: результат = вхід."""
        rng = np.random.default_rng(7)
        image = rng.integers(0, 256, (12, 12)).astype(float)
        out = retouch.unsharp_mask(image, 1.0, 1.0, 0.0, 1e6)
        self.assertTrue(np.allclose(out, image))

    def test_unsharp_invalid(self):
        """Від'ємне amount або sigma <= 0 -> ValueError."""
        with self.assertRaises(ValueError):
            retouch.unsharp_mask(np.zeros((4, 4)), -1.0, 1.0)
        with self.assertRaises(ValueError):
            retouch.unsharp_mask(np.zeros((4, 4)), 1.0, 0.0)


if __name__ == "__main__":
    unittest.main()

"""Тести спотворень: відтворюваність (seed), частка зіпсованих пікселів, діапазон значень."""
import unittest

import numpy as np

from src import degrade


class TestDegrade(unittest.TestCase):
    """Перевірка шумів."""

    def setUp(self):
        self.image = np.full((64, 64), 100.0)

    def test_same_seed_same_noise(self):
        """Однаковий seed, знімок і спотворення дають однаковий шум."""
        first = degrade.add_gaussian(self.image, 10, degrade.make_rng(1, "a", "g"))
        second = degrade.add_gaussian(self.image, 10, degrade.make_rng(1, "a", "g"))
        self.assertTrue(np.array_equal(first, second))

    def test_different_seed_different_noise(self):
        """Інший seed дає інший шум."""
        first = degrade.add_gaussian(self.image, 10, degrade.make_rng(1, "a", "g"))
        second = degrade.add_gaussian(self.image, 10, degrade.make_rng(2, "a", "g"))
        self.assertFalse(np.array_equal(first, second))

    def test_gaussian_statistics(self):
        """Середнє шуму близьке до 0, відхилення близьке до sigma (64 x 64 = 4096 значень)."""
        noisy = degrade.add_gaussian(self.image, 10, degrade.make_rng(3, "a", "g"))
        self.assertAlmostEqual(float(np.mean(noisy - 100)), 0.0, delta=1.0)
        self.assertAlmostEqual(float(np.std(noisy - 100)), 10.0, delta=1.0)

    def test_gaussian_range_and_integers(self):
        """Значення цілі й у діапазоні 0...255."""
        noisy = degrade.add_gaussian(self.image, 200, degrade.make_rng(4, "a", "g"))
        self.assertTrue(noisy.min() >= 0 and noisy.max() <= 255)
        self.assertTrue(np.array_equal(noisy, np.round(noisy)))

    def test_zero_sigma_keeps_image(self):
        """Sigma = 0 не змінює зображення."""
        noisy = degrade.add_gaussian(self.image, 0, degrade.make_rng(5, "a", "g"))
        self.assertTrue(np.array_equal(noisy, self.image))

    def test_salt_pepper_values_and_share(self):
        """Змінені пікселі лише 0 або 255; їх близько prob = 20 % (допуск 3 %)."""
        noisy = degrade.add_salt_pepper(self.image, 0.2, degrade.make_rng(6, "a", "s"))
        changed = noisy != 100
        self.assertTrue(set(np.unique(noisy[changed])) <= {0.0, 255.0})
        self.assertAlmostEqual(float(changed.mean()), 0.2, delta=0.03)

    def test_salt_pepper_zero_prob(self):
        """Prob = 0 не змінює зображення."""
        noisy = degrade.add_salt_pepper(self.image, 0.0, degrade.make_rng(7, "a", "s"))
        self.assertTrue(np.array_equal(noisy, self.image))

    def test_invalid_parameters(self):
        """Некоректні параметри -> ValueError."""
        rng = degrade.make_rng(1, "a", "b")
        with self.assertRaises(ValueError):
            degrade.add_gaussian(self.image, -1, rng)
        with self.assertRaises(ValueError):
            degrade.add_salt_pepper(self.image, 1.5, rng)
        with self.assertRaises(ValueError):
            degrade.add_low_contrast(self.image, 0, 10, 0, rng)

    def test_low_contrast_by_hand(self):
        """РОЗРАХУНОК ВРУЧНУ: alpha = 0,5, beta = 40, sigma = 0: 100 -> 0,5 * 100 + 40 = 90."""
        out = degrade.add_low_contrast(self.image, 0.5, 40, 0, degrade.make_rng(1, "a", "b"))
        self.assertTrue(np.all(out == 90))

    def test_apply_degradation_types(self):
        """apply_degradation розуміє всі типи з конфігурації й відхиляє невідомі."""
        rng = degrade.make_rng(1, "a", "b")
        specs = [{"type": "gaussian", "sigma": 5}, {"type": "salt_pepper", "prob": 0.1},
                 {"type": "mixed", "sigma": 5, "prob": 0.1},
                 {"type": "low_contrast", "alpha": 0.5, "beta": 40, "sigma": 5}]
        for spec in specs:
            self.assertEqual(degrade.apply_degradation(self.image, spec, rng).shape, (64, 64))
        with self.assertRaises(ValueError):
            degrade.apply_degradation(self.image, {"type": "blur"}, rng)


if __name__ == "__main__":
    unittest.main()

"""Тести гістограмних методів: вирівнювання, CLAHE, розтягування контрасту."""
import unittest

import numpy as np

from src import histogram


class TestHistogram(unittest.TestCase):
    """Гістограмна корекція."""

    def test_histogram_counts(self):
        """Гістограма: два пікселі 10 і два 20 -> hist[10] = 2, hist[20] = 2, сума 4."""
        hist = histogram.histogram(np.array([[10.0, 10.0], [20.0, 20.0]]))
        self.assertEqual(hist[10], 2)
        self.assertEqual(hist[20], 2)
        self.assertEqual(hist.sum(), 4)

    def test_equalize_by_hand(self):
        """РОЗРАХУНОК ВРУЧНУ: рівні 10, 20, 30, 40 по одному разу.

        cdf = 1, 2, 3, 4; cdf_min = 1; N = 4; new = (cdf - 1) / (4 - 1) * 255 = 0, 85, 170, 255.
        """
        image = np.array([[10.0, 20.0], [30.0, 40.0]])
        expected = np.array([[0.0, 85.0], [170.0, 255.0]])
        self.assertTrue(np.array_equal(histogram.equalize_histogram(image), expected))

    def test_equalize_flat_image(self):
        """Однотонне зображення лишається без змін (немає з чого вирівнювати)."""
        image = np.full((3, 3), 77.0)
        self.assertTrue(np.array_equal(histogram.equalize_histogram(image), image))

    def test_equalize_keeps_order(self):
        """Вирівнювання не змінює порядок яскравостей: світліший піксель лишається світлішим."""
        rng = np.random.default_rng(1)
        image = rng.integers(0, 100, (8, 8)).astype(float)
        result = histogram.equalize_histogram(image)
        order = np.argsort(image.ravel(), kind="stable")
        self.assertTrue(np.all(np.diff(result.ravel()[order]) >= 0))

    def test_tile_table_without_clip(self):
        """РОЗРАХУНОК ВРУЧНУ: рівні 10, 20, 30, 40, без обмеження: cdf / 4 * 255 = 63,75; 127,5; 191,25; 255."""
        levels = np.array([[10, 20], [30, 40]])
        table = histogram.tile_table(levels, 256.0)
        self.assertAlmostEqual(table[10], 63.75)
        self.assertAlmostEqual(table[20], 127.5)
        self.assertAlmostEqual(table[30], 191.25)
        self.assertAlmostEqual(table[40], 255.0)

    def test_tile_table_clip_limits_slope(self):
        """З обмеженням гістограми таблиця стає ближчою до тотожного відображення (менше підсилення)."""
        levels = np.array([[100, 100], [100, 101]])
        free = histogram.tile_table(levels, 256.0)
        clipped = histogram.tile_table(levels, 1.0)
        self.assertLess(clipped[101] - clipped[99], free[101] - free[99])

    def test_clahe_single_tile_by_hand(self):
        """Одна плитка без обмеження збігається з таблицею плитки: 10 -> 63,75, 40 -> 255."""
        image = np.array([[10.0, 20.0], [30.0, 40.0]])
        result = histogram.clahe(image, tiles=1, clip_limit=256.0)
        self.assertAlmostEqual(result[0, 0], 63.75)
        self.assertAlmostEqual(result[1, 1], 255.0)

    def test_clahe_range_threshold_skips_contrasty_image(self):
        """Якщо динамічний діапазон >= порога, зображення лишається без змін."""
        rng = np.random.default_rng(3)
        image = rng.integers(0, 256, (16, 16)).astype(float)
        result = histogram.clahe(image, tiles=2, clip_limit=2.0, range_threshold=50)
        self.assertTrue(np.array_equal(result, image))

    def test_clahe_shape_and_range(self):
        """CLAHE зберігає розмір і діапазон 0...255 (також для зображення менше за кількість плиток)."""
        image = np.random.default_rng(4).integers(0, 256, (5, 7)).astype(float)
        result = histogram.clahe(image, tiles=8, clip_limit=2.0)
        self.assertEqual(result.shape, (5, 7))
        self.assertTrue(result.min() >= 0 and result.max() <= 255.0 + 1e-9)

    def test_clahe_invalid(self):
        """Некоректні параметри -> ValueError."""
        with self.assertRaises(ValueError):
            histogram.clahe(np.zeros((4, 4)), tiles=0)
        with self.assertRaises(ValueError):
            histogram.clahe(np.zeros((4, 4)), clip_limit=0.5)

    def test_stretch_by_hand(self):
        """РОЗРАХУНОК ВРУЧНУ: рівні 50 і 100; 0 % -> 50, 100 % -> 100; (50 - 50) * 255 / 50 = 0, 100 -> 255."""
        image = np.array([[50.0, 100.0], [50.0, 100.0]])
        result = histogram.contrast_stretch(image)
        self.assertTrue(np.array_equal(result, np.array([[0.0, 255.0], [0.0, 255.0]])))

    def test_stretch_threshold_and_flat(self):
        """Динамічний діапазон 50 >= порога 40 -> без змін; однотонне зображення лишається."""
        image = np.array([[50.0, 100.0], [50.0, 100.0]])
        self.assertTrue(np.array_equal(histogram.contrast_stretch(image, range_threshold=40), image))
        flat = np.full((3, 3), 9.0)
        self.assertTrue(np.array_equal(histogram.contrast_stretch(flat), flat))

    def test_stretch_invalid(self):
        """Некоректні перцентилі -> ValueError."""
        with self.assertRaises(ValueError):
            histogram.contrast_stretch(np.zeros((2, 2)), 50.0, 10.0)

    def test_percentile_level_edges(self):
        """0 % дає найтемніший рівень на знімку, 100 % - найсвітліший."""
        levels = np.array([[50, 100], [50, 100]])
        self.assertEqual(histogram.percentile_level(levels, 0.0, False), 50.0)
        self.assertEqual(histogram.percentile_level(levels, 100.0, True), 100.0)


if __name__ == "__main__":
    unittest.main()

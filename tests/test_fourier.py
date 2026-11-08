"""Тести ДПФ, написаного вручну, і частотного фільтра."""
import unittest

import numpy as np

from src import fourier


class TestFourier(unittest.TestCase):
    """ДПФ та фільтр Вінера."""

    def test_dft_matrix_small(self):
        """РОЗРАХУНОК ВРУЧНУ: для N = 2 матриця [[1, 1], [1, -1]] (exp(-i pi) = -1)."""
        matrix = fourier.dft_matrix(2)
        self.assertTrue(np.allclose(matrix, np.array([[1, 1], [1, -1]])))

    def test_dft_matches_numpy(self):
        """Наше ДПФ збігається з numpy.fft.fft2 (для перевірки)."""
        image = np.random.default_rng(1).integers(0, 256, (6, 8)).astype(float)
        self.assertTrue(np.allclose(fourier.dft2(image), np.fft.fft2(image)))

    def test_inverse_restores_image(self):
        """idft2(dft2(f)) = f."""
        image = np.random.default_rng(2).integers(0, 256, (5, 7)).astype(float)
        self.assertTrue(np.allclose(fourier.idft2(fourier.dft2(image)), image))

    def test_dc_component_is_sum(self):
        """РОЗРАХУНОК ВРУЧНУ: F(0, 0) = сума всіх пікселів: 1 + 2 + 3 + 4 = 10."""
        spectrum = fourier.dft2(np.array([[1.0, 2.0], [3.0, 4.0]]))
        self.assertAlmostEqual(spectrum[0, 0].real, 10.0)

    def test_wiener_flat_image_unchanged(self):
        """Однотонне зображення: шуму 0, підсилення 1 на всіх ненульових частотах - без змін."""
        flat = np.full((16, 16), 80.0)
        self.assertTrue(np.allclose(fourier.spectral_wiener(flat, 1.0, 4), 80.0, atol=1e-6))

    def test_wiener_reduces_noise(self):
        """На гладкому зображенні з гаусовим шумом фільтр зменшує похибку."""
        rng = np.random.default_rng(3)
        yy, xx = np.mgrid[0:32, 0:32]
        clean = 100 + 60 * np.sin(xx / 8.0)
        noisy = clean + rng.normal(0, 15, clean.shape)
        result = fourier.spectral_wiener(noisy, 1.0, 8)
        self.assertLess(np.mean((result - clean) ** 2), np.mean((noisy - clean) ** 2))

    def test_wiener_shape_and_invalid(self):
        """Розмір зберігається; strength <= 0 -> ValueError."""
        image = np.random.default_rng(4).integers(0, 256, (10, 12)).astype(float)
        self.assertEqual(fourier.spectral_wiener(image, 1.0, 4).shape, (10, 12))
        with self.assertRaises(ValueError):
            fourier.spectral_wiener(image, 0.0)


if __name__ == "__main__":
    unittest.main()

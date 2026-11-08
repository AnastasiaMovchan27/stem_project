"""Тести читання, підготовки й збереження зображень, зокрема крайніх випадків (порожній файл тощо)."""
import os
import tempfile
import unittest

import numpy as np
from PIL import Image

from src import image_io


class TestImageIO(unittest.TestCase):
    """Перевірка image_io."""

    def setUp(self):
        self.folder = tempfile.mkdtemp()

    def path(self, name):
        return os.path.join(self.folder, name)

    def test_to_gray_by_hand(self):
        """РОЗРАХУНОК ВРУЧНУ: червоний (255, 0, 0) -> 0,299 * 255 = 76,245; білий -> 255."""
        rgb = np.array([[[255.0, 0.0, 0.0], [255.0, 255.0, 255.0]]])
        gray = image_io.to_gray(rgb)
        self.assertAlmostEqual(gray[0, 0], 76.245, places=6)
        self.assertAlmostEqual(gray[0, 1], 255.0, places=6)

    def test_save_and_load_roundtrip(self):
        """Збережене сіре зображення читається без змін."""
        image = np.array([[0.0, 50.0], [200.0, 255.0]])
        image_io.save_image(image, self.path("a.png"))
        self.assertTrue(np.array_equal(image_io.load_image(self.path("a.png")), image))

    def test_load_rgb_and_rgba(self):
        """RGB і RGBA читаються як сірі; прозорість ігнорується."""
        Image.new("RGB", (4, 4), (255, 0, 0)).save(self.path("rgb.png"))
        Image.new("RGBA", (4, 4), (255, 0, 0, 10)).save(self.path("rgba.png"))
        for name in ("rgb.png", "rgba.png"):
            loaded = image_io.load_image(self.path(name))
            self.assertEqual(loaded.shape, (4, 4))
            self.assertAlmostEqual(loaded[0, 0], 76.245, delta=0.01)

    def test_load_palette_and_16bit(self):
        """Палітрові й 16-бітні зображення читаються без помилки в діапазоні 0...255."""
        Image.new("P", (4, 4), 3).save(self.path("p.png"))
        data = np.full((4, 4), 65535, dtype=np.uint16)
        Image.fromarray(data).save(self.path("deep.png"))
        self.assertEqual(image_io.load_image(self.path("p.png")).shape, (4, 4))
        self.assertAlmostEqual(image_io.load_image(self.path("deep.png"))[0, 0], 255.0, delta=0.01)

    def test_missing_empty_and_corrupt_files(self):
        """Немає файла, порожній файл і не зображення -> None, а не аварія."""
        open(self.path("empty.png"), "w").close()
        with open(self.path("bad.png"), "w") as file:
            file.write("це не зображення")
        self.assertIsNone(image_io.load_image(self.path("nothing.png")))
        self.assertIsNone(image_io.load_image(self.path("empty.png")))
        self.assertIsNone(image_io.load_image(self.path("bad.png")))

    def test_square_resize_shape_and_crop(self):
        """Зображення 4 x 8 -> центральний квадрат 4 x 4 -> розмір 2 x 2; однотонне лишається однотонним."""
        image = np.full((4, 8), 77.0)
        small = image_io.square_resize(image, 2)
        self.assertEqual(small.shape, (2, 2))
        self.assertTrue(np.all(np.abs(small - 77.0) < 1.0))

    def test_square_resize_takes_center(self):
        """Із зображення з лівою світлою й правою темною смугою центр дає суміш обох."""
        image = np.zeros((4, 12))
        image[:, :4] = 255.0
        left_edge = image_io.square_resize(image[:, :4], 2)
        self.assertTrue(np.all(left_edge > 250))
        center = image_io.square_resize(image, 2)
        self.assertTrue(np.all(center < 5))

    def test_list_images_filters_and_sorts(self):
        """list_images повертає лише зображення, відсортовані; для неіснуючої папки порожній список."""
        for name in ("b.png", "a.jpg", "notes.txt"):
            open(self.path(name), "w").close()
        names = [os.path.basename(p) for p in image_io.list_images(self.folder)]
        self.assertEqual(names, ["a.jpg", "b.png"])
        self.assertEqual(image_io.list_images(self.path("none")), [])


if __name__ == "__main__":
    unittest.main()

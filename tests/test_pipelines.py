"""Тести стадій, пайплайнів і їхньої валідації."""
import json
import unittest

import numpy as np

from src import pipelines, stages


class TestStages(unittest.TestCase):
    """run_stage і категорії."""

    def setUp(self):
        with open("config.json", encoding="utf-8") as file:
            self.config = json.load(file)
        self.image = np.random.default_rng(1).integers(0, 256, (16, 16)).astype(float)

    def test_every_stage_runs(self):
        """Кожна стадія з довідника CATEGORIES працює з параметрами з config.json й зберігає розмір."""
        for name in stages.CATEGORIES:
            if name == "equalize":
                params = {}
            else:
                params = self.config["stages"][name]
            self.assertEqual(stages.run_stage(name, self.image, params).shape, (16, 16), name)

    def test_unknown_stage(self):
        """Невідома назва -> ValueError."""
        with self.assertRaises(ValueError):
            stages.run_stage("blur3000", self.image, {})

    def test_stage_matches_function(self):
        """Equalize через run_stage дає те саме, що виклик функції (рівні 10, 20, 30, 40 -> 0, 85, 170, 255)."""
        image = np.array([[10.0, 20.0], [30.0, 40.0]])
        result = stages.run_stage("equalize", image, {})
        self.assertTrue(np.array_equal(result, np.array([[0.0, 85.0], [170.0, 255.0]])))


class TestPipelines(unittest.TestCase):
    """Валідація пайплайнів і виконання ланцюжка."""

    def setUp(self):
        with open("config.json", encoding="utf-8") as file:
            self.config = json.load(file)

    def test_config_pipelines_are_valid_and_different(self):
        """Обидва пайплайни з конфігурації: >= 3 стадії, >= 3 категорії, набори категорій різні."""
        sets = []
        for stage_names in self.config["pipelines"].values():
            categories = pipelines.validate_pipeline(stage_names)
            self.assertGreaterEqual(len(stage_names), 3)
            self.assertGreaterEqual(len(categories), 3)
            sets.append(categories)
        self.assertNotEqual(sets[0], sets[1])

    def test_too_few_stages(self):
        """Дві стадії -> помилка."""
        with self.assertRaises(ValueError):
            pipelines.validate_pipeline(["bilateral", "clahe"])

    def test_too_few_categories(self):
        """Три стадії лише з двох категорій (дві фільтрації й гістограма) -> помилка."""
        with self.assertRaises(ValueError):
            pipelines.validate_pipeline(["bilateral", "diffusion", "clahe"])

    def test_unknown_stage_in_pipeline(self):
        """Невідома стадія -> помилка."""
        with self.assertRaises(ValueError):
            pipelines.validate_pipeline(["bilateral", "clahe", "magic"])

    def test_run_chain_outputs(self):
        """Ланцюжок повертає результат кожної стадії; значення в діапазоні 0...255."""
        image = np.random.default_rng(2).integers(0, 256, (16, 16)).astype(float)
        names = self.config["pipelines"]["pipeline2"]
        outputs = pipelines.run_chain(image, names, self.config["stages"])
        self.assertEqual(len(outputs), len(names))
        for output in outputs:
            self.assertTrue(output.min() >= 0 and output.max() <= 255)

    def test_pipeline_improves_impulse_noise(self):
        """Пайплайн 2 суттєво зменшує імпульсний шум (64 x 64, 10 % імпульсів: PSNR зростає більш ніж на 20 дБ)."""
        from src import degrade, metrics
        yy, xx = np.mgrid[0:64, 0:64]
        clean = 60 + 2 * xx + yy + 10 * np.sin(xx / 6.0)
        noisy = degrade.add_salt_pepper(clean, 0.1, degrade.make_rng(1, "t", "s"))
        out = pipelines.run_chain(noisy, self.config["pipelines"]["pipeline2"], self.config["stages"])[-1]
        before = metrics.psnr(metrics.mse(clean, noisy))
        after = metrics.psnr(metrics.mse(clean, out))
        self.assertGreater(after, before + 20)


if __name__ == "__main__":
    unittest.main()

"""Наскрізний тест усього потоку prepare -> degrade -> run -> compare/analyze/check/plots на малій вибірці."""
import json
import os
import tempfile
import unittest

import numpy as np
from PIL import Image

import main


class TestMain(unittest.TestCase):
    """Команди main.py на тимчасових даних."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        original = os.path.join(self.root, "original")
        os.makedirs(original)
        for index in range(4):
            yy, xx = np.mgrid[0:48, 0:64]
            data = (80 + 2 * xx + index * 10 + 20 * np.sin(yy / 5.0)).clip(0, 255).astype(np.uint8)
            Image.fromarray(data).save(os.path.join(original, "img%d.png" % index))
        open(os.path.join(original, "empty.png"), "w").close()  # порожній файл: має бути пропущений
        with open("config.json", encoding="utf-8") as file:
            config = json.load(file)
        config["image_size"] = 32
        config["workers"] = 1
        config["tuning"]["step"] = 3
        config["save_intermediate_for"] = ["img1"]
        config["paths"] = {"original": original, "prepared": os.path.join(self.root, "prepared"),
                           "degraded": os.path.join(self.root, "degraded"),
                           "results": os.path.join(self.root, "results")}
        self.config_path = os.path.join(self.root, "config.json")
        with open(self.config_path, "w", encoding="utf-8") as file:
            json.dump(config, file)
        self.config = config

    def run_main(self, *args):
        return main.main(["--config", self.config_path] + list(args))

    def test_full_flow(self):
        """Усі команди працюють послідовно й створюють очікувані файли."""
        self.assertEqual(self.run_main("prepare"), 0)
        self.assertEqual(len(os.listdir(self.config["paths"]["prepared"])), 4)
        self.assertEqual(self.run_main("degrade"), 0)
        self.assertEqual(len(os.listdir(self.config["paths"]["degraded"])), 4 * 6)
        self.assertEqual(self.run_main("run", "all"), 0)
        results = self.config["paths"]["results"]
        for pipeline in ("pipeline1", "pipeline2"):
            self.assertTrue(os.path.isfile(os.path.join(results, pipeline + "_metrics.csv")))
        self.assertEqual(self.run_main("compare"), 0)
        self.assertEqual(self.run_main("analyze"), 0)
        self.assertEqual(self.run_main("check"), 0)
        self.assertEqual(self.run_main("plots"), 0)
        self.assertTrue(os.path.isfile(os.path.join(results, "figures", "examples_img1.png")))

    def test_reproducible(self):
        """Двічі виконана команда degrade дає ті самі файли (фіксований seed)."""
        self.run_main("prepare")
        self.run_main("degrade")
        path = os.path.join(self.config["paths"]["degraded"], "img0__gauss_15.png")
        with open(path, "rb") as file:
            first = file.read()
        self.run_main("degrade")
        with open(path, "rb") as file:
            self.assertEqual(first, file.read())

    def test_missing_config(self):
        """Немає файла конфігурації -> зрозуміла помилка (SystemExit), а не трасування."""
        with self.assertRaises(SystemExit):
            main.main(["--config", os.path.join(self.root, "nope.json"), "prepare"])

    def test_bad_pipeline_in_config(self):
        """Пайплайн з двох стадій у конфігурації відхиляється."""
        self.config["pipelines"]["bad"] = ["bilateral", "clahe"]
        with open(self.config_path, "w", encoding="utf-8") as file:
            json.dump(self.config, file)
        with self.assertRaises(SystemExit):
            self.run_main("prepare")

    def test_run_without_degrade(self):
        """Run до degrade не падає: повідомляє про відсутність даних."""
        self.run_main("prepare")
        self.assertEqual(self.run_main("run", "pipeline1"), 0)

    def test_unknown_pipeline_and_no_command(self):
        """Невідомий пайплайн не падає; без команди друкується довідка й код 1."""
        self.assertEqual(self.run_main("run", "pipeline9"), 0)
        self.assertEqual(main.main(["--config", self.config_path]), 1)

    def test_metrics_and_stage_commands(self):
        """Команди metrics і stage працюють на файлах."""
        self.run_main("prepare")
        prepared = os.path.join(self.config["paths"]["prepared"], "img0.png")
        out = os.path.join(self.root, "out.png")
        self.assertEqual(self.run_main("stage", "bilateral", prepared, out, "--reference", prepared), 0)
        self.assertTrue(os.path.isfile(out))
        self.assertEqual(self.run_main("metrics", prepared, out), 0)
        self.assertEqual(self.run_main("stage", "nope", prepared, out), 0)


if __name__ == "__main__":
    unittest.main()

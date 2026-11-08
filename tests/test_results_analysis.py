"""Тести запису/читання результатів, аналізу, парного порівняння й перевірки сценаріїв."""
import os
import tempfile
import unittest

import pandas as pd

from src import analysis, checks, comparison, results_io


class TestResultsIO(unittest.TestCase):
    """CSV і JSON."""

    def test_csv_roundtrip(self):
        """Числа читаються як числа, порожня клітинка - як None, текст лишається текстом."""
        path = os.path.join(tempfile.mkdtemp(), "a", "t.csv")
        results_io.write_csv(path, [{"a": "x", "b": 1.5, "c": ""}], ["a", "b", "c"])
        row = results_io.read_csv(path)[0]
        self.assertEqual(row["a"], "x")
        self.assertEqual(row["b"], 1.5)
        self.assertIsNone(row["c"])

    def test_json_roundtrip(self):
        """JSON з українським текстом записується й читається без змін."""
        path = os.path.join(tempfile.mkdtemp(), "t.json")
        results_io.write_json(path, {"назва": [1, 2]})
        self.assertEqual(results_io.read_json(path), {"назва": [1, 2]})


def make_table():
    """Маленька таблиця метрик: 3 зображення, 2 пайплайни, 1 спотворення."""
    rows = []
    for name, p1, p2 in (("a", 20.0, 21.0), ("b", 22.0, 24.0), ("c", 24.0, 27.0)):
        for pipeline, value in (("pipeline1", p1), ("pipeline2", p2)):
            rows.append({"pipeline": pipeline, "image": name, "degradation": "g",
                         "psnr_noisy": 18.0, "psnr": value, "ssim_noisy": 0.5, "ssim": 0.6,
                         "psnr_stage1": value - 1.0, "psnr_stage2": value, "psnr_stage3": value,
                         "psnr_stage4": None, "seconds": 0.1,
                         "gain_psnr": value - 18.0, "gain_ssim": 0.1})
    return pd.DataFrame(rows)


class TestAnalysis(unittest.TestCase):
    """Таблиці аналізу."""

    def test_by_condition_by_hand(self):
        """РОЗРАХУНОК ВРУЧНУ: пайплайн 1: PSNR 20, 22, 24 -> середнє 22; приріст 22 - 18 = 4."""
        summary = analysis.by_condition(make_table())
        row = summary[summary["pipeline"] == "pipeline1"].iloc[0]
        self.assertAlmostEqual(row["psnr"], 22.0)
        self.assertAlmostEqual(row["gain_psnr"], 4.0)
        self.assertEqual(row["n"], 3)

    def test_ablation_by_hand(self):
        """РОЗРАХУНОК ВРУЧНУ: пайплайн 1, середнє psnr = 22: stage1 = 21 -> 21 - 18 = 3; stage2 = 22 -> +1."""
        table = analysis.ablation(make_table())
        row = table[table["pipeline"] == "pipeline1"].iloc[0]
        self.assertAlmostEqual(row["stage1"], 3.0)
        self.assertAlmostEqual(row["stage2"], 1.0)
        self.assertAlmostEqual(row["stage3"], 0.0)
        self.assertNotIn("stage4", table.columns)

    def test_stability(self):
        """Приріст PSNR пайплайна 1: 2, 4, 6 -> мінімум 2, стандартне відхилення 2, втрат немає."""
        table = analysis.stability(make_table())
        row = table[table["pipeline"] == "pipeline1"].iloc[0]
        self.assertAlmostEqual(row["min_gain"], 2.0)
        self.assertAlmostEqual(row["std_gain"], 2.0)
        self.assertEqual(row["share_worse"], 0.0)


class TestComparison(unittest.TestCase):
    """Парне порівняння."""

    def test_paired_by_hand(self):
        """РОЗРАХУНОК ВРУЧНУ: різниці (пайплайн 2 - пайплайн 1): 1, 2, 3 -> середнє 2, s = 1, n = 3.

        Півширина інтервалу = 1,96 * 1 / sqrt(3) = 1,1316; інтервал (0,8684; 3,1316); P2 кращий у 100 %.
        """
        result = comparison.paired_comparison(make_table(), "pipeline1", "pipeline2").iloc[0]
        self.assertAlmostEqual(result["mean_diff_psnr"], 2.0)
        self.assertAlmostEqual(result["ci_low"], 2.0 - 1.96 / 3 ** 0.5)
        self.assertAlmostEqual(result["ci_high"], 2.0 + 1.96 / 3 ** 0.5)
        self.assertEqual(result["share_second_better"], 1.0)

    def test_too_few_images(self):
        """Менше двох спільних зображень - рядка немає."""
        table = make_table().iloc[:2]
        self.assertTrue(comparison.paired_comparison(table, "pipeline1", "pipeline2").empty)


class TestChecks(unittest.TestCase):
    """Сценарії перевірки."""

    def test_gain_scenarios(self):
        """Приріст PSNR пайплайна 1: 2, 4, 6 дБ. Для min_gain = 3 частка = 2/3: при пороз 0,6 OK, при 0,7 НЕ ОК."""
        config = {"scenarios": [
            {"id": 1, "kind": "gain", "pipeline": "pipeline1", "degradation": "g", "min_gain": 3.0, "min_share": 0.6},
            {"id": 2, "kind": "gain", "pipeline": "pipeline1", "degradation": "g", "min_gain": 3.0, "min_share": 0.7},
            {"id": 3, "kind": "mean_ssim_gain", "pipeline": "pipeline2", "degradation": "g", "min_gain": 0.05},
            {"id": 4, "kind": "gain", "pipeline": "pipeline1", "degradation": "nothing", "min_gain": 0,
             "min_share": 0}]}
        rows = checks.run_scenarios(config, make_table())
        self.assertAlmostEqual(rows[0]["value"], 2 / 3)
        self.assertEqual([row["ok"] for row in rows], [True, False, True, False])

    def test_unknown_kind(self):
        """Невідомий вид сценарію -> ValueError."""
        config = {"scenarios": [{"id": 1, "kind": "magic", "pipeline": "pipeline1", "degradation": "g"}]}
        with self.assertRaises(ValueError):
            checks.run_scenarios(config, make_table())


if __name__ == "__main__":
    unittest.main()

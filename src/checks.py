"""Перевірка коректності: сценарії з config.json (розділ scenarios) з очікуваними результатами."""


def run_scenarios(config, table):
    """Виконує сценарії й повертає рядки: id, опис, виміряне значення, поріг, ok.

    kind = "gain": частка зображень, де приріст PSNR не менший за min_gain (дБ), має бути >= min_share.
    kind = "mean_ssim_gain": середній приріст SSIM має бути >= min_gain.
    """
    rows = []
    for scenario in config["scenarios"]:
        part = table[(table["pipeline"] == scenario["pipeline"])
                     & (table["degradation"] == scenario["degradation"])]
        if len(part) == 0:
            rows.append({"id": scenario["id"], "pipeline": scenario["pipeline"],
                         "degradation": scenario["degradation"], "kind": scenario["kind"],
                         "value": None, "threshold": None, "ok": False})
            continue
        if scenario["kind"] == "gain":
            value = float((part["gain_psnr"] >= scenario["min_gain"]).mean())
            threshold = scenario["min_share"]
        elif scenario["kind"] == "mean_ssim_gain":
            value = float(part["gain_ssim"].mean())
            threshold = scenario["min_gain"]
        else:
            raise ValueError("Невідомий вид сценарію: " + str(scenario["kind"]))
        rows.append({"id": scenario["id"], "pipeline": scenario["pipeline"],
                     "degradation": scenario["degradation"], "kind": scenario["kind"],
                     "value": value, "threshold": threshold, "ok": value >= threshold})
    return rows

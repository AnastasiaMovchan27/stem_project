"""Запис і читання таблиць результатів у CSV та підсумків у JSON."""
import csv
import json
import os


def write_csv(path, rows, fields):
    """Записує список словників у CSV-файл із заголовком fields (папку створює, якщо її немає)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_csv(path):
    """Читає CSV у список словників; числа перетворює на float, порожні клітинки лишає None."""
    rows = []
    with open(path, "r", newline="", encoding="utf-8") as file:
        for raw in csv.DictReader(file):
            row = {}
            for key, value in raw.items():
                if value == "" or value is None:
                    row[key] = None
                    continue
                try:
                    row[key] = float(value)
                except ValueError:
                    row[key] = value
            rows.append(row)
    return rows


def write_json(path, data):
    """Записує словник у JSON-файл."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def read_json(path):
    """Читає JSON-файл у словник."""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

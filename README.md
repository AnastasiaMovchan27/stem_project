# STEM-проєкт: аналіз та обробка зображень класичними методами

Студентка: Мовчан Анастасія, група ІПЗ-22, спеціальність 121 «Інженерія програмного забезпечення»,
КНУ імені Тараса Шевченка (кафедра програмних систем і технологій). Варіант 2 (два пайплайни).

Програма вручну (без ШІ та готових реалізацій алгоритмів) обробляє зображення двома пайплайнами,
зашумлює їх шістьма способами й порівнює результат метриками MSE, PSNR, SSIM.

* **pipeline1 (P1):** білатеральний фільтр → CLAHE → нерізке маскування (фільтрація, гістограмна корекція, ретушування).
* **pipeline2 (P2):** усунення імпульсів → частотний фільтр Вінера → анізотропна дифузія → розтягування контрасту
  (ретушування, перетворення Фур'є, фільтрація, яскравість/контраст).

## Встановлення (macOS / Linux, Python 3.9+)
```bash
cd stem_project
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск (усі команди з папки проєкту)
```bash
python main.py prepare          # data/original -> data/prepared (сірий квадрат 128 x 128)
python main.py degrade          # data/prepared -> data/degraded (6 спотворень кожного зображення) + метрики спотворень
python main.py run all          # обидва пайплайни: results/pipeline1_metrics.csv, results/pipeline2_metrics.csv
python main.py compare          # середні метрики та парне порівняння -> results/tables
python main.py analyze          # внесок стадій і стабільність -> results/tables
python main.py check            # перевірка сценаріїв з config.json
python main.py plots            # графіки -> results/figures
```
Швидка перевірка, що не затирає основні результати: `python main.py --results results_demo run all --limit 5`. Одна стадія на одному файлі:
`python main.py stage bilateral data/prepared/my_photo.png out.png --reference data/prepared/my_photo.png`.
Метрики двох файлів: `python main.py metrics a.png b.png`. Підбір параметрів: `python main.py tune pipeline1`.
Інший файл конфігурації: `python main.py --config інший.json run all`.

Повний експеримент (124 зображення × 6 умов × 2 пайплайни) займає близько 2–3 хвилин на двох ядрах.

## Тести
```bash
python -m unittest discover -s tests -t .        # або: python -m pytest -q
```

## Структура
```
main.py                     точка входу (команди)
config.json                 усі параметри (пояснення: config.json.пояснення.md)
src/                        image_io, degrade, metrics, filtering, histogram, retouch, fourier,
                            stages, pipelines, results_io, tuning, analysis, comparison, checks, plots
tests/                      автотести (по одному файлу на модуль)
data/original/              вихідні зображення (123 з відкритих наборів + my_photo.jpg); джерела: data/SOURCES.md
data/prepared, data/degraded  створюються командами prepare і degrade
results/                    таблиці метрик (CSV), таблиці аналізу (results/tables), графіки (results/figures)
docs/                       ТЗ, шпаргалка до захисту, звіт Zvit_STEM.docx
META-USAGE.md               декларація використання генеративного ШІ (вимога завдання)
```

## Потік даних
```
data/original --prepare--> data/prepared --degrade--> data/degraded (744 файли)
   --run--> results/pipelineN_metrics.csv (+ results/pipelineN/*.png для my_photo)
   --compare / analyze / check / plots--> results/tables/*.csv, results/figures/*.png
```

## Відтворюваність
Шум створюється з фіксованого seed (config.json, поле seed) окремо для кожної трійки (seed, зображення,
спотворення), тому результат однаковий при кожному запуску й не залежить від порядку обробки.

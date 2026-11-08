# STEM-проєкт: аналіз та обробка зображень

Студентка: Мовчан Анастасія, група ІПЗ-22

Програма обробляє зображення двома пайплайнами, написаними вручну, зашумлює їх шістьма способами й порівнює результат метриками MSE, PSNR, SSIM.

* **pipeline1:** білатеральний фільтр → CLAHE → нерізке маскування.
* **pipeline2:** усунення імпульсів → частотний фільтр Вінера → анізотропна дифузія → розтягування контрасту.

## Встановлення
```bash
pip3 install numpy pandas matplotlib Pillow
```

## Запуск
```bash
python3 main.py prepare     # data/original -> data/prepared (сірий квадрат 128 x 128)
python3 main.py degrade     # data/prepared -> data/degraded (6 спотворень кожного зображення)
python3 main.py run all     # обидва пайплайни -> results/pipelineN_metrics.csv (2-3 хвилини)
python3 main.py compare     # середні метрики та порівняння пайплайнів -> results/tables
python3 main.py analyze     # внесок стадій і стабільність -> results/tables
python3 main.py check       # перевірка сценаріїв з config.json
python3 main.py plots       # графіки -> results/figures
```
Усі параметри задаються в `config.json` (пояснення: `config.json.пояснення.md`).
Шум відтворюється: він створюється з фіксованого seed.

## Тести
```bash
python3 -m unittest discover -s tests -t .
```

## Структура
```
main.py            точка входу (команди)
config.json        усі параметри
src/               модулі: введення-виведення, спотворення, метрики, методи, пайплайни, аналіз
tests/             автотести
data/original/     105 вихідних зображень (відкриті набори + my_photo.jpg); джерела: data/SOURCES.md
results/           таблиці метрик (CSV), таблиці аналізу, графіки
docs/              ТЗ та матеріали до захисту
META-USAGE.md      декларація використання генеративного ШІ
```
```

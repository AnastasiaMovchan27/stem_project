# Пояснення до config.json

Усі параметри експерименту зібрано в `config.json`; код лише читає їх (`main.load_config`), тому експеримент
можна змінити без правки Python. JSON не допускає коментарів, тому пояснення тут. Помилка в комі між
елементами — найчастіша причина повідомлення «Не вдалося прочитати файл конфігурації».

| Ключ | Значення | Що це | Де використовується |
|---|---|---|---|
| `seed` | 2026 | початкове число генератора випадкових чисел | `degrade.make_rng` |
| `image_size` | 128 | сторона зображення після підготовки (пікселів) | `main.command_prepare`, `image_io.square_resize` |
| `workers` | 2 | кількість процесів у команді `run` | `main.command_run` |
| `paths` | original, prepared, degraded, results | папки даних і результатів | усі команди |
| `degradations` | 6 умов | назва → тип і параметри спотворення | `main.command_degrade`, `degrade.apply_degradation` |
| `metrics` | ssim_window 8, ssim_step 4 | вікно й крок SSIM | `metrics.ssim` |
| `stages` | параметри 7 методів | назва стадії → параметри | `stages.run_stage` |
| `pipelines` | pipeline1, pipeline2 | назва → список стадій | `main.command_run`, `pipelines.run_chain` |
| `tuning` | step 20, sweeps, conditions | контрольні зображення (кожне 20-те) і перебір параметрів | `tuning.py`, `analysis.load_metrics` |
| `save_intermediate_for` | ["my_photo"] | для яких зображень зберігати картинки кожної стадії | `main.command_run`, `plots` |
| `scenarios` | 8 сценаріїв | порогові значення для перевірки коректності | `main.command_check`, `checks.run_scenarios` |

## Спотворення
* `gauss_15`, `gauss_30`: гаусів шум, sigma = 15 і 30.
* `sp_5`, `sp_20`: імпульсний шум «сіль-перець», 5 % і 20 % пікселів (половина білі, половина чорні).
* `mixed`: гаусів шум sigma = 15 і 5 % імпульсів.
* `lowcontrast`: out = 0,5 · I + 40 (контраст удвічі менший) і шум sigma = 10.
Нове спотворення наявного типу додається лише в цей файл, наприклад `"sp_10": {"type": "salt_pepper", "prob": 0.1}`
(потім `python main.py degrade` і `python main.py run all`).

## Параметри методів (`stages`)
* `bilateral`: radius 3 (вікно 7×7), sigma_space 1,5, sigma_range 60 (найчутливіший параметр).
* `clahe`: tiles 8 (сітка 8×8), clip_limit 2,0, range_threshold 120 (застосовується лише до зображень зі стисненим діапазоном).
* `unsharp`: amount 0,4, sigma 1,5, threshold 0, noise_factor 3 (деталі менші за 3 · σ шуму не підсилюються).
* `inpaint`: max_window 7 (найбільше вікно пошуку чистих сусідів).
* `wiener`: strength 0,5 (множник рівня шуму), pad 16 (дзеркальне доповнення країв).
* `diffusion`: iterations 3, kappa 10, gamma 0,2.
* `stretch`: low/high_percentile 0 і 100, range_threshold 150.

## Пайплайни
Це списки назв стадій, що виконуються по порядку. Щоб поміняти порядок або додати стадію, достатньо змінити список
(назва має збігатися з гілкою в `stages.run_stage`). Програма перевіряє, що пайплайн має щонайменше 3 стадії
з щонайменше 3 різних категорій.

## Сценарії перевірки (`scenarios`)
* `"kind": "gain"`: частка зображень, у яких приріст PSNR (після пайплайна відносно спотвореного) не менший
  за `min_gain` дБ, має бути не менша за `min_share`.
* `"kind": "mean_ssim_gain"`: середній приріст SSIM не менший за `min_gain`.
Запуск: `python main.py check`.

## Зміни, які можуть попросити на захисті
1. Змінити силу шуму (`"sigma": 20`) і показати результат після `degrade` та `run`.
2. Додати нове спотворення (див. вище).
3. Змінити параметр стадії (`"bilateral": {"sigma_range": 25}`) і порівняти PSNR.
4. Додати пайплайн (`"pipeline3": ["inpaint", "bilateral", "clahe"]`).
5. Змінити `seed` і показати, що шум інший.

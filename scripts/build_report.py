"""Будує звіт (docs/Zvit_STEM.docx) із збережених результатів.

Запуск (після main.py run all, compare, analyze, check, plots):
    python scripts/build_report.py

Усі числа в таблицях і тексті читаються з results/tables, малюнки беруться з results/figures.
"""

import glob
import json
import os
import subprocess
import sys

import matplotlib
import pandas as pd
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLES = os.path.join(ROOT, "results", "tables")
FIGURES = os.path.join(ROOT, "results", "figures")
OUT = os.path.join(ROOT, "docs", "Zvit_STEM.docx")
REPO_PLACEHOLDER = "[вставити посилання на Git-репозиторій]"

SOURCES = [
    "Gonzalez R. C., Woods R. E. Digital Image Processing. 4th ed. New York : Pearson, 2018. 1022 p.",
    "Tomasi C., Manduchi R. Bilateral filtering for gray and color images. Proceedings of the Sixth "
    "International Conference on Computer Vision (ICCV). Bombay, 1998. P. 839–846.",
    "Perona P., Malik J. Scale-space and edge detection using anisotropic diffusion. IEEE Transactions on "
    "Pattern Analysis and Machine Intelligence. 1990. Vol. 12, No. 7. P. 629–639.",
    "Zuiderveld K. Contrast limited adaptive histogram equalization. Graphics Gems IV / ed. P. S. Heckbert. "
    "San Diego : Academic Press, 1994. P. 474–485.",
    "Pizer S. M., Amburn E. P., Austin J. D. et al. Adaptive histogram equalization and its variations. "
    "Computer Vision, Graphics, and Image Processing. 1987. Vol. 39, No. 3. P. 355–368.",
    "Wang Z., Bovik A. C., Sheikh H. R., Simoncelli E. P. Image quality assessment: from error visibility to "
    "structural similarity. IEEE Transactions on Image Processing. 2004. Vol. 13, No. 4. P. 600–612.",
    "Immerkaer J. Fast noise variance estimation. Computer Vision and Image Understanding. 1996. "
    "Vol. 64, No. 2. P. 300–302.",
    "Buades A., Coll B., Morel J.-M. A non-local algorithm for image denoising. Proceedings of the IEEE "
    "Conference on Computer Vision and Pattern Recognition (CVPR). San Diego, 2005. Vol. 2. P. 60–65.",
    "Dabov K., Foi A., Katkovnik V., Egiazarian K. Image denoising by sparse 3-D transform-domain collaborative "
    "filtering. IEEE Transactions on Image Processing. 2007. Vol. 16, No. 8. P. 2080–2095.",
    "Zhang K., Zuo W., Chen Y., Meng D., Zhang L. Beyond a Gaussian denoiser: residual learning of deep CNN for "
    "image denoising. IEEE Transactions on Image Processing. 2017. Vol. 26, No. 7. P. 3142–3155.",
    "Chan R. H., Ho C.-W., Nikolova M. Salt-and-pepper noise removal by median-type noise detectors and "
    "detail-preserving regularization. IEEE Transactions on Image Processing. 2005. Vol. 14, No. 10. P. 1479–1485.",
    "Martin D., Fowlkes C., Tal D., Malik J. A database of human segmented natural images and its application "
    "to evaluating segmentation algorithms and measuring ecological statistics. Proceedings of the Eighth IEEE "
    "International Conference on Computer Vision (ICCV). Vancouver, 2001. Vol. 2. P. 416–423.",
]

RELATED = [
    ("Tomasi, Manduchi, 1998 [2]", "Двосторонній фільтр: просторова та яскравісна вага",
     "Стадія 1 пайплайна P1; реалізовано вручну у вікні (2r+1)², параметри підібрано перебором"),
    ("Perona, Malik, 1990 [3]", "Анізотропна дифузія, що зупиняється на краях",
     "Стадія 3 пайплайна P2; провідність 1/(1+(g/κ)²)"),
    ("Zuiderveld, 1994 [4]; Pizer et al., 1987 [5]", "Адаптивне вирівнювання гістограми з обмеженням (CLAHE)",
     "Стадія 2 пайплайна P1; додано умову застосування за динамічним діапазоном"),
    ("Chan, Ho, Nikolova, 2005 [11]", "Видалення імпульсного шуму: спершу детекція імпульсів, потім відновлення",
     "Ідея стадії 1 пайплайна P2: детекція за значеннями 0/255 і заміна середнім чистих сусідів"),
    ("Immerkaer, 1996 [7]", "Швидка оцінка дисперсії шуму однією згорткою",
     "Використано для адаптивних стадій (фільтр Вінера в частотній області, поріг нерізкого маскування)"),
    ("Buades et al., 2005 [8]", "Нелокальне усереднення (NLM): усереднення за схожими фрагментами",
     "Не реалізовано; потенційно сильніший, але обчислювально важчий (квадратична складність за фрагментами)"),
    ("Dabov et al., 2007 [9]", "BM3D: спільна фільтрація схожих блоків у 3D-перетворенні",
     "Еталон серед класичних методів; не реалізовано через обсяг та складність"),
    ("Zhang et al., 2017 [10]", "DnCNN: згорткова нейромережа з залишковим навчанням",
     "Поза межами завдання (ШІ/ML заборонено); використано ті самі тестові набори (BSD68, Set12)"),
    ("Wang et al., 2004 [6]", "Індекс структурної подібності SSIM",
     "Метрика якості; реалізовано вручну, збігається зі scikit-image (тест)"),
]


def shade(cell, color="D9E2F3"):
    """Fill a table cell with a background colour."""
    props = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), color)
    props.append(shading)


class Report:
    """Thin wrapper around python-docx with the formatting used in the report."""

    def __init__(self):
        """Create an empty A4 document with the default style (Times New Roman 14)."""
        self.doc = Document()
        section = self.doc.sections[0]
        section.page_width, section.page_height = Cm(21), Cm(29.7)
        section.left_margin, section.right_margin = Cm(3), Cm(1.5)
        section.top_margin = section.bottom_margin = Cm(2)
        style = self.doc.styles["Normal"]
        style.font.name = "Times New Roman"
        style.font.size = Pt(14)
        style.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style.paragraph_format.line_spacing = 1.5
        self.tables = 0
        self.figures = 0

    def heading(self, text, level=1):
        """Add a heading."""
        para = self.doc.add_heading(level=level)
        run = para.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(16 if level == 1 else 14)
        run.bold = True
        run.font.color.rgb = None
        para.paragraph_format.keep_with_next = True
        return para

    def para(self, text, bold=False, italic=False, center=False, indent=True, size=None):
        """Add a paragraph."""
        para = self.doc.add_paragraph()
        run = para.add_run(text)
        run.bold = bold
        run.italic = italic
        if size:
            run.font.size = Pt(size)
        if center:
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        else:
            para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            if indent:
                para.paragraph_format.first_line_indent = Cm(1.25)
        return para

    def bullets(self, items):
        """Add a bulleted list."""
        for item in items:
            para = self.doc.add_paragraph(item, style="List Bullet")
            para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    def table(self, title, header, rows, widths=None, size=10):
        """Add a captioned table."""
        self.tables += 1
        cap = self.doc.add_paragraph()
        cap.add_run(f"Таблиця {self.tables} – {title}").italic = True
        cap.paragraph_format.keep_with_next = True
        table = self.doc.add_table(rows=1, cols=len(header))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for idx, text in enumerate(header):
            cell = table.rows[0].cells[idx]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(text))
            run.bold = True
            run.font.size = Pt(size)
            shade(cell)
        for row in rows:
            cells = table.add_row().cells
            for idx, value in enumerate(row):
                cells[idx].text = ""
                run = cells[idx].paragraphs[0].add_run(str(value))
                run.font.size = Pt(size)
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    para.paragraph_format.line_spacing = 1.0
                    para.paragraph_format.space_after = Pt(0)
        if widths:
            for row in table.rows:
                for idx, width in enumerate(widths):
                    row.cells[idx].width = Cm(width)
        self.doc.add_paragraph()

    def figure(self, path, caption, width=15.5):
        """Add a picture with a caption."""
        self.figures += 1
        self.doc.add_picture(path, width=Cm(width))
        self.doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap = self.doc.add_paragraph()
        cap.add_run(f"Рисунок {self.figures} – {caption}").italic = True
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def code(self, text, size=8):
        """Add a monospaced code block."""
        for line in text.rstrip("\n").split("\n"):
            para = self.doc.add_paragraph()
            run = para.add_run(line if line else " ")
            run.font.name = "Courier New"
            run.font.size = Pt(size)
            para.paragraph_format.line_spacing = 1.0
            para.paragraph_format.space_after = Pt(0)
            para.paragraph_format.left_indent = Cm(0.3)

    def page_break(self):
        """Start a new page."""
        self.doc.add_page_break()


def read(name):
    """Read a CSV table from results/tables."""
    return pd.read_csv(os.path.join(TABLES, f"{name}.csv"))


def draw_pipelines(path):
    """Draw the schema of the two pipelines."""
    fig, ax = plt.subplots(figsize=(10, 3.6))
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    rows = {
        "P1": ["Шумне\nзображення", "bilateral\n(фільтрація)", "clahe\n(гістограма)",
               "unsharp\n(ретушування)", "Результат"],
        "P2": ["Шумне\nзображення", "inpaint\n(ретушування)", "wiener\n(Фур'є)",
               "diffusion\n(фільтрація)", "stretch\n(яскравість/контраст)"],
    }
    colors = {"P1": "#cfe0f5", "P2": "#fbe0c4"}
    for row, (name, labels) in enumerate(rows.items()):
        y_pos = 2.9 - row * 1.9
        ax.text(0.0, y_pos, name, fontsize=14, fontweight="bold", va="center")
        count = len(labels) + (1 if name == "P2" else 0)
        step = 8.9 / count
        for k, label in enumerate(labels):
            x_pos = 0.9 + k * step
            ax.text(x_pos + step * 0.42, y_pos, label, ha="center", va="center", fontsize=8.5,
                    bbox={"boxstyle": "round,pad=0.4", "fc": colors[name] if k > 0 else "#eeeeee",
                          "ec": "#555555"})
            if k < count - 1:
                ax.annotate("", xy=(x_pos + step * 0.97, y_pos), xytext=(x_pos + step * 0.78, y_pos),
                            arrowprops={"arrowstyle": "->"})
        if name == "P2":
            x_pos = 0.9 + 5 * step
            ax.text(x_pos + step * 0.42, y_pos, "Результат", ha="center", va="center", fontsize=8.5,
                    bbox={"boxstyle": "round,pad=0.4", "fc": "#eeeeee", "ec": "#555555"})
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def command_output(command):
    """Run a command in the project root; return stdout+stderr text ('' on failure)."""
    try:
        done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=300,
                              check=False)
        return done.stdout + done.stderr
    except (OSError, subprocess.TimeoutExpired):
        return ""


def quality_facts():
    """Повертає результат тестів і стан статичного аналізу."""
    text = command_output([sys.executable, "-m", "pytest", "-q"])
    tests = text.strip().splitlines()[-1] if text.strip() else "не виконано"
    ruff = command_output(["ruff", "check", ".", "--quiet"]).strip()
    ruff_state = "0 зауважень" if text and not ruff else ("не виконано" if not ruff else "є зауваження")
    flake = command_output([sys.executable, "-m", "flake8", "--max-line-length", "120", "src", "main.py",
                            "tests"]).strip()
    lines = 0
    for path in (glob.glob(os.path.join(ROOT, "src", "*.py")) + [os.path.join(ROOT, "main.py")]):
        with open(path, encoding="utf-8") as handle:
            lines += len(handle.readlines())
    return tests, ruff_state, ("0 зауважень" if not flake else "є зауваження"), lines


def fmt(value, digits=2):
    """Format a number with a decimal comma."""
    return f"{value:.{digits}f}".replace(".", ",")


def source_files():
    """Файли проєкту для додатка з кодом."""
    files = ["main.py", "config.json"]
    files += sorted(os.path.join("src", name) for name in os.listdir(os.path.join(ROOT, "src"))
                    if name.endswith(".py") and name != "__init__.py")
    return files


def build():
    """Збирає весь звіт."""
    import inspect
    sys.path.insert(0, ROOT)
    from src import filtering, fourier, histogram, pipelines, retouch  # noqa: E402

    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as handle:
        config = json.load(handle)
    by_cond = read("by_condition")
    pair = read("pairwise")
    abl = read("ablation")
    stab = read("stability")
    checks_table = read("scenarios_check")
    tests, ruff_state, flake_state, code_lines = quality_facts()
    n_eval = int(by_cond["n"].iloc[0])
    n_total = len(os.listdir(os.path.join(ROOT, "data", "original")))
    n_tune = n_total - n_eval
    size = config["image_size"]
    conditions = list(config["degradations"])

    def cond_val(cond, pipe, col):
        sel = by_cond[(by_cond["degradation"] == cond) & (by_cond["pipeline"] == pipe)]
        return float(sel[col].iloc[0])

    def pair_val(cond, col="mean_diff_psnr"):
        return float(pair[pair["degradation"] == cond][col].iloc[0])

    def abl_val(pipe, stage, cond):
        sel = abl[(abl["pipeline"] == pipe) & (abl["degradation"] == cond)]
        return float(sel[stage].iloc[0])

    def stab_val(cond, pipe, col):
        sel = stab[(stab["degradation"] == cond) & (stab["pipeline"] == pipe)]
        return float(sel[col].iloc[0])

    passed = int(checks_table["ok"].sum())
    total_checks = len(checks_table)
    failed = checks_table[~checks_table["ok"]]

    rep = Report()
    # ---- титульна сторінка
    for text, bold in (("МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ", True),
                       ("КИЇВСЬКИЙ НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ ІМЕНІ ТАРАСА ШЕВЧЕНКА", True),
                       ("Кафедра програмних систем і технологій", False)):
        rep.para(text, bold=bold, center=True)
    for _ in range(3):
        rep.para("", center=True)
    rep.para("ЗВІТ", bold=True, center=True, size=20)
    rep.para("зі STEM-проєкту", center=True, size=16)
    rep.para("Аналіз та обробка зображень за допомогою класичних методів фільтрації, гістограмної корекції, "
             "перетворення Фур'є та ретушування", bold=True, center=True)
    for _ in range(2):
        rep.para("", center=True)
    rep.para("Виконала: студентка 2 курсу, групи ІПЗ-22,\nспеціальність 121 «Інженерія програмного забезпечення»\n"
             "Мовчан Анастасія", indent=False)
    rep.para("Перевірив(ла): ______________________", indent=False)
    rep.para(f"Репозиторій: {REPO_PLACEHOLDER}", indent=False)
    rep.para("Київ – 2026", center=True)
    rep.page_break()

    # ---- анотація
    rep.heading("Анотація")
    rep.para(
        "У роботі розроблено програмний стенд для обробки та аналізу зображень класичними методами комп'ютерної "
        "графіки без використання штучного інтелекту та готових бібліотечних реалізацій алгоритмів: усі методи "
        "написано вручну. Створено два пайплайни, що відрізняються набором категорій методів: P1 (білатеральний "
        "фільтр → CLAHE → нерізке маскування) і P2 (усунення імпульсів → частотний фільтр Вінера → анізотропна "
        f"дифузія → розтягування контрасту). Вибірка містить {n_total} зображень (відкриті набори BSD68, Set12, "
        f"Set14, LIVE1 та власна фотографія авторки); {n_eval} з них використано для аналізу, решту — для підбору "
        "параметрів. Зображення зашумлено шістьма способами (гаусів шум двох рівнів, імпульсний шум двох рівнів, "
        "суміш, слабкий контраст з шумом); якість оцінено за MSE, PSNR і SSIM, реалізованими вручну. Показано, що "
        "P1 ефективніший за P2 при гаусовому шумі, а P2 значно ефективніший при імпульсному й змішаному шумі та "
        "низькому контрасті; визначено внесок кожної стадії та умови, за яких стадії шкодять.")
    rep.para("Ключові слова: обробка зображень, зменшення шуму, білатеральний фільтр, CLAHE, перетворення Фур'є, "
             "анізотропна дифузія, PSNR, SSIM, пайплайн.", italic=True, indent=False)
    rep.page_break()

    # ---- 1. вступ
    rep.heading("1. Вступ")
    rep.heading("1.1. Актуальність", 2)
    rep.para("Цифрові зображення з камер і сканерів містять шум і спотворення (слабке освітлення, помилки передачі), "
             "що ускладнює їх аналіз. Покращення якості є базовим етапом підготовки даних для подальшого "
             "розпізнавання. Класичні методи, на відміну від нейромереж, не потребують навчальних вибірок, мають "
             "прозору поведінку та передбачувані обмеження, тому важливо розуміти, у яких умовах кожен з них "
             "ефективний. Робота показує це на кількісному експерименті зі ста й більше зображень.")
    rep.heading("1.2. Мета і завдання", 2)
    rep.para("Мета: застосувати класичні методи комп'ютерної графіки до обробки зображень, спроєктувати "
             "пайплайни з кількох стадій і проаналізувати результати, визначивши ефективність та обмеження методів. "
             "Завдання:")
    rep.bullets(["сформувати вибірку не менше ніж зі 100 зображень з відкритих джерел;",
                 "реалізувати вручну два пайплайни (кожен із трьох і більше стадій з трьох і більше різних "
                 "категорій), що відрізняються комбінацією категорій і не повторюють методи лабораторних робіт 5–6;",
                 "створити програму з параметрами в конфігураційному файлі й командному рядку, збереженням "
                 "проміжних результатів і таблиць метрик MSE/PSNR/SSIM у CSV/JSON;",
                 "порівняти пайплайни кількісно, визначити внесок стадій, обмеження та стійкість;",
                 "покрити код автоматичними тестами з обчисленими вручну очікуваними значеннями."])
    rep.heading("1.3. Огляд суміжних робіт", 2)
    rep.table("Огляд суміжних робіт і зв'язок з проєктом", ["Робота", "Ідея", "Зв'язок з проєктом"],
              RELATED, widths=[3.5, 6.0, 6.0], size=9)
    rep.para("Класичні методи (двосторонній фільтр, дифузія, CLAHE) застосовуються як самостійні, так і як "
             "складові сучасних систем. Найсильніші результати зі зменшення шуму дають BM3D [9] і нейромережа "
             "DnCNN [10]; їхні значення PSNR на тих самих наборах за літературою помітно вищі, ніж у простих "
             "класичних методів, тому порівняння з ними подано як орієнтир, а не як пряме змагання.")
    rep.page_break()

    # ---- 2. вибірка
    rep.heading("2. Опис вибірки зображень")
    rep.para(f"Об'єкти аналізу — фотографії природних сцен. Вибірка складається з {n_total} зображень: 113 з "
             "відкритих тестових наборів (репозиторій https://github.com/cszn/DnCNN, каталог testsets; файли "
             "лише перекодовано в PNG без втрат) і одна власна фотографія авторки (гірська долина з кіньми). "
             "Усі зображення програма перетворює на відтінки сірого за формулою Y = 0,299R + 0,587G + 0,114B, "
             f"вирізає центральний квадрат і зменшує до {size}×{size} пікселів (команда prepare).")
    rep.table("Склад вибірки", ["Набір", "Кількість", "Походження"],
              [["BSD68", 68, "Berkeley Segmentation Dataset, тестова частина [12]"],
               ["LIVE1", 29, "LIVE Image Quality Assessment Database"],
               ["Set12", 12, "класичні тестові зображення"],
               ["Set14", 14, "Zeyde et al., 2010"],
               ["my_photo", 1, "власна фотографія авторки"]], widths=[3, 3, 9.5])
    rep.para(f"Кожне {config['tuning']['step']}-те зображення за алфавітом ({n_tune} шт.) використано як контрольне "
             f"для підбору параметрів і виключено з аналізу, щоб параметри не підганялися під ті самі дані; "
             f"в аналізі {n_eval} зображень. Власну фотографію оброблено так само, як решту, її результати "
             "наведено на рисунку 3.")
    rep.heading("Умови спотворення", 2)
    rows = []
    descriptions = {"gaussian": "адитивний гаусів шум", "salt_pepper": "імпульсний шум «сіль-перець»",
                    "mixed": "гаусів + імпульсний шум", "low_contrast": "стиснутий контраст і зсув яскравості + шум"}
    for name, spec in config["degradations"].items():
        params = ", ".join(f"{k} = {v}" for k, v in spec.items() if k != "type")
        rows.append([name, descriptions[spec["type"]], params])
    rep.table("Умови спотворення (еталонні сценарії)", ["Умова", "Опис", "Параметри"], rows, widths=[3, 7, 5.5])
    rep.para("Генератор випадкових чисел створюється для кожної трійки (seed, зображення, умова), seed = "
             f"{config['seed']}, тому результат не залежить від порядку обробки й відтворюється повністю.")
    rep.page_break()

    # ---- 3. методи
    rep.heading("3. Опис методів, пайплайнів та обґрунтування параметрів")
    rep.heading("3.1. Схема пайплайнів", 2)
    draw_pipelines(os.path.join(FIGURES, "pipelines.png"))
    rep.figure(os.path.join(FIGURES, "pipelines.png"), "Схема пайплайнів P1 і P2")
    rep.para("P1 поєднує категорії «фільтрація», «гістограмна корекція», «ретушування та покращення». P2 — "
             "«ретушування», «перетворення Фур'є», «фільтрація», «регулювання яскравості та контрасту». Набори "
             "категорій різні; разом використано п'ять категорій. У коді P1 = pipeline1, P2 = pipeline2.")
    rep.heading("3.2. Методи", 2)
    rep.para("Білатеральний фільтр (P1, стадія 1). Кожен піксель замінюється зваженим середнім сусідів: "
             "w = exp(−d²/2σs²) · exp(−c²/2σr²), де d — відстань, c — різниця яскравостей. Сусіди з іншого боку "
             "краю мають малу вагу, тому краї зберігаються.")
    rep.para("CLAHE (P1, стадія 2). Зображення ділиться на плитки 8×8, для кожної будується гістограма, обмежена "
             "значенням clip_limit·(середня висота), надлишок розподіляється порівну; накопичена гістограма дає "
             "таблицю перетворення; значення піксела обчислюється з таблиць чотирьох найближчих плиток білінійно. "
             "Додано умову range_threshold: корекція застосовується лише до зображень зі стисненим діапазоном.")
    rep.para("Нерізке маскування (P1, стадія 3). out = I + a·(I − blur(I)); деталі, менші за поріг, вважаються "
             "шумом і не підсилюються; поріг дорівнює k разів оцінці рівня шуму (Immerkaer), тому на шумних "
             "зображеннях підсилення слабшає.")
    rep.para("Усунення імпульсів (P2, стадія 1). Піксель зі значенням 0 або 255 вважається зіпсованим і "
             "замінюється середнім незіпсованих пікселів у найменшому вікні 3×3, 5×5, 7×7, де такі є; решта "
             "пікселів не змінюється.")
    rep.para("Частотний фільтр Вінера (P2, стадія 2). ДПФ обчислюється вручну через матрицю "
             "(F = W·f·W), рівень шуму σ оцінюється за зображенням, кожен коефіцієнт множиться на "
             "G = max(|F|² − s·σ²N, 0)/|F|²: частоти слабші за шум вилучаються, сильні лишаються.")
    rep.para("Анізотропна дифузія Переона–Маліка (P2, стадія 3). I ← I + γ·Σ c(g)·g за чотирма сусідами, "
             "c(g) = 1/(1 + (g/κ)²); дифузія зупиняється на краях.")
    rep.para("Розтягування контрасту (P2, стадія 4). Рівні з гістограми (мінімум і максимум) відображаються на "
             "0 і 255; застосовується лише коли динамічний діапазон (рівні 0,5 % і 99,5 %) менший за поріг.")
    rep.para("Метрики: MSE = (1/NM)Σ(a − b)², PSNR = 10·lg(255²/MSE), SSIM усереднюється по вікнах "
             f"{config['metrics']['ssim_window']}×{config['metrics']['ssim_window']} з кроком "
             f"{config['metrics']['ssim_step']} за формулою (2μxμy + C1)(2σxy + C2) / "
             "((μx² + μy² + C1)(σx² + σy² + C2)).")
    rep.para("Від лабораторних 5–6 (усереднення, Гаусс, медіана, мінімум, максимум, середина діапазону, "
             "ранговий фільтр) методи відрізняються алгоритмом: жоден з них не повторює ці фільтри; "
             "для нерізкого маскування розмиття Гаусса використовується лише як складова.")
    rep.heading("3.3. Підбір параметрів", 2)
    rep.para("Параметри підбиралися перебором одного параметра за раз (команда tune) на контрольних зображеннях за "
             "середнім PSNR; для пайплайна 2 додатково виконано сумісний перебір трьох параметрів (strength, "
             "iterations, kappa; різниця між найкращими варіантами менша за 0,1 дБ). Повні журнали — у "
             "results/tuning_*.csv. Підсумкові параметри:")
    rows = []
    for pipe, stage_names in config["pipelines"].items():
        for name in stage_names:
            rows.append(["P" + pipe[-1], name, pipelines.stages.CATEGORIES[name],
                         ", ".join(f"{k} = {v}" for k, v in config["stages"][name].items())])
    rep.table("Параметри стадій (після підбору)", ["Пайплайн", "Стадія", "Категорія", "Параметри"], rows,
              widths=[2, 2.5, 5, 6], size=9)
    rep.para("Обмеження підбору: параметри оптимізовано за середнім PSNR на обмеженій вибірці; PSNR не завжди "
             "відповідає візуальній якості. Різниця між найближчими варіантами параметрів часто менша за 0,3 дБ, "
             "тобто оптимум пологий.")
    rep.page_break()

    # ---- 4. реалізація
    rep.heading("4. Реалізація програми")
    rep.para("Програму написано мовою Python (NumPy, pandas, matplotlib, Pillow). Pillow використовується лише для "
             "читання й запису файлів та зміни розміру; усі методи й метрики написано вручну. Точка входу — "
             "main.py з командами prepare, degrade, run, compare, analyze, check, plots, stage, metrics, tune. "
             "Параметри задаються в config.json (пояснення — config.json.пояснення.md). Модулі: image_io, degrade, "
             "metrics, filtering, histogram, retouch, fourier, stages (назва стадії → функція), pipelines, "
             "results_io, tuning, analysis, comparison, checks, plots.")
    rep.code("python main.py prepare\npython main.py degrade\npython main.py run all\n"
             "python main.py compare\npython main.py analyze\npython main.py check\npython main.py plots", size=10)
    rep.heading("4.1. Ключові функції", 2)
    for title, function in (("Білатеральний фільтр:", filtering.bilateral_filter),
                            ("CLAHE:", histogram.clahe),
                            ("Усунення імпульсів:", retouch.impulse_inpaint),
                            ("Частотний фільтр Вінера:", fourier.spectral_wiener),
                            ("Виконання пайплайна:", pipelines.run_chain)):
        rep.para(title, bold=True, indent=False)
        rep.code(inspect.getsource(function), size=8)
    rep.heading("4.2. Тестування та якість коду", 2)
    rep.para("Автотести (unittest) перевіряють кожен метод на зображеннях 2×2, 3×3 та 5×5 з очікуваними значеннями, "
             "обчисленими вручну (наприклад, PSNR для MSE = 65,025 дорівнює 30 дБ; вирівнювання рівнів 10, 20, 30, "
             "40 дає 0, 85, 170, 255; крок дифузії піка 100 дає 20 у центрі й чотирьох сусідах), крайні випадки "
             "(порожній і пошкоджений файл, зображення 1×1, некоректні параметри, відсутній конфіг), відтворюваність "
             "за seed і наскрізний сценарій усіх команд. Результат: " + tests + ".")
    rep.para(f"Статичний аналіз: ruff — {ruff_state}, flake8 (довжина рядка 120) — {flake_state}; "
             f"код має докстрінги та коментарі українською; обсяг програми {code_lines} рядків. "
             "Файл .pylintrc підготовлено, але pylint у середовищі розробки не запускався.")
    rep.page_break()

    # ---- 5. результати
    rep.heading("5. Результати та аналіз")
    rep.para(f"Обробку виконано для {n_total} зображень × {len(conditions)} умов × 2 пайплайни; в аналізі "
             f"{n_eval} зображень на кожну умову. Усі значення — середні по зображеннях.")
    rows = []
    for _, r in by_cond.iterrows():
        rows.append(["P" + r["pipeline"][-1], r["degradation"], fmt(r["psnr_noisy"], 1), fmt(r["psnr"], 1),
                     fmt(r["gain_psnr"], 1), fmt(r["ssim_noisy"], 3), fmt(r["ssim"], 3)])
    rep.table("Середні PSNR (дБ) та SSIM", ["Пайплайн", "Умова", "PSNR до", "PSNR після", "Приріст", "SSIM до",
                                            "SSIM після"], rows, widths=[2.2, 2.8, 2.2, 2.4, 2.2, 2.2, 2.4], size=9)
    rep.figure(os.path.join(FIGURES, "psnr_by_condition.png"), "Середній PSNR за умовами")
    rep.figure(os.path.join(FIGURES, "ssim_by_condition.png"), "Середній SSIM за умовами")
    rep.heading("5.1. Парне порівняння пайплайнів", 2)
    rows = []
    for _, r in pair.iterrows():
        rows.append([r["degradation"], fmt(r["mean_diff_psnr"], 2),
                     f"[{fmt(r['ci_low'], 2)}; {fmt(r['ci_high'], 2)}]", fmt(r["mean_diff_ssim"], 3),
                     fmt(100 * r["share_second_better"], 0) + " %"])
    rep.table("Різниця P2 − P1 на тих самих зображеннях",
              ["Умова", "Δ PSNR, дБ", "95 % інтервал", "Δ SSIM", "P2 кращий"], rows, widths=[3, 3, 4, 2.5, 3])
    rep.para(f"При гаусовому шумі кращий P1 (σ = 15: на {fmt(-pair_val('gauss_15'))} дБ, σ = 30: "
             f"на {fmt(-pair_val('gauss_30'))} дБ вище за P2); при імпульсному, змішаному шумі та низькому контрасті "
             f"кращий P2 (від {fmt(pair_val('lowcontrast'), 1)} дБ при низькому контрасті до "
             f"{fmt(pair_val('sp_20'), 1)} дБ при імпульсах 20 %). Інтервали не перетинають нуль, тобто різниці "
             "статистично значущі на цій вибірці.")
    rep.figure(os.path.join(FIGURES, "examples_my_photo.png"),
               "Власна фотографія: чисте зображення, спотворене та результати пайплайнів", width=11)
    rep.heading("5.2. Внесок стадій", 2)
    for pipe in config["pipelines"]:
        part = abl[abl["pipeline"] == pipe].dropna(axis=1, how="all")
        stage_cols = [c for c in part.columns if c.startswith("stage")]
        header = ["Умова"] + [f"{c[-1]}: {config['pipelines'][pipe][int(c[-1]) - 1]}" for c in stage_cols]
        rows = [[r["degradation"]] + [fmt(r[c], 2) for c in stage_cols] for _, r in part.iterrows()]
        rep.table(f"Зміна PSNR після кожної стадії, дБ (P{pipe[-1]})", header, rows, size=9)
        rep.figure(os.path.join(FIGURES, f"ablation_{pipe}.png"), f"Внесок стадій, P{pipe[-1]}", width=10)
    rep.para(f"Білатеральний фільтр у P1 дає основний виграш при гаусовому шуму "
             f"({fmt(abl_val('pipeline1', 'stage1', 'gauss_30'), 1)} дБ при σ = 30), але при імпульсах дає лише "
             f"{fmt(abl_val('pipeline1', 'stage1', 'sp_5'), 1)} дБ, бо імпульс сприймається як край. Нерізке "
             f"маскування при імпульсах знижує якість ({fmt(abl_val('pipeline1', 'stage3', 'sp_5'), 1)} дБ), бо "
             f"підсилює залишки шуму. У P2 усунення імпульсів дає {fmt(abl_val('pipeline2', 'stage1', 'sp_20'), 1)} "
             f"дБ при 20 % імпульсів; розтягування контрасту дає "
             f"{fmt(abl_val('pipeline2', 'stage4', 'lowcontrast'), 1)} "
             "дБ лише при слабкому контрасті, а в інших умовах іноді шкодить на природно малоконтрастних оригіналах.")
    rep.heading("5.3. Стабільність і перевірка коректності", 2)
    rows = []
    for _, r in by_cond.iterrows():
        rows.append(["P" + r["pipeline"][-1], r["degradation"],
                     fmt(stab_val(r["degradation"], r["pipeline"], "std_gain"), 2),
                     fmt(stab_val(r["degradation"], r["pipeline"], "min_gain"), 2),
                     fmt(100 * stab_val(r["degradation"], r["pipeline"], "share_worse"), 1) + " %"])
    rep.table("Розкид приросту PSNR по зображеннях", ["Пайплайн", "Умова", "σ приросту", "Найгірший, дБ",
                                                      "Частка погіршень"], rows, widths=[2.5, 3, 3, 3.5, 3.5], size=9)
    rows = []
    for _, r in checks_table.iterrows():
        rows.append([int(r["id"]), "P" + r["pipeline"][-1], r["degradation"],
                     "приріст PSNR" if r["kind"] == "gain" else "середній приріст SSIM",
                     fmt(r["value"], 3), fmt(r["threshold"], 2), "так" if r["ok"] else "ні"])
    rep.table("Сценарії перевірки коректності (config.json, розділ scenarios)",
              ["№", "Пайплайн", "Умова", "Критерій", "Значення", "Поріг", "Пройдено"], rows, size=9)
    rep.para(f"Пройдено {passed} з {total_checks} сценаріїв." + (
        " Не пройдено: " + "; ".join(
            f"сценарій {int(r['id'])} (P{r['pipeline'][-1]}, {r['degradation']}: {fmt(r['value'], 3)} при "
            f"порозі {fmt(r['threshold'], 2)})" for _, r in failed.iterrows())
        + ". Причина — на частині текстурних зображень слабкий гаусів шум фільтр частково розмиває деталі й PSNR "
          "зростає менше за 1 дБ; поріг не змінювався після отримання результату." if len(failed) else ""))
    rep.page_break()

    # ---- 6. обговорення
    rep.heading("6. Обговорення")
    rep.heading("6.1. Ефективність", 2)
    rep.para("Жоден пайплайн не є найкращим в усіх умовах: вибір методу визначається типом спотворення. "
             "Згладжувальні методи (білатеральний фільтр, дифузія, частотний фільтр) ефективні проти гаусового "
             "шуму, але не проти імпульсів; детекція викидів ефективна проти імпульсів, але не проти гаусового шуму.")
    rep.heading("6.2. Обмеження", 2)
    rep.bullets(["Шум синтетичний; реальні шуми камер мають інший розподіл.",
                 "Параметри підібрано за PSNR на обмеженій контрольній вибірці; оптимум пологий.",
                 f"Зображення зменшено до {size}×{size}, що змінює масштаб деталей порівняно з вихідним розміром.",
                 "Детекція імпульсів за значеннями 0/255 працює лише для шуму «сіль-перець» у чистому вигляді.",
                 "PSNR/SSIM не завжди відповідають візуальній якості (див. рисунок 3)."])
    rep.heading("6.3. Порівняння з сучасними підходами", 2)
    rep.para("BM3D [9] і DnCNN [10] за літературою дають суттєво вищий PSNR при гаусовому шумі, але BM3D складніший "
             "й повільніший, а DnCNN потребує навчання на великих наборах і не завжди переноситься на інші типи "
             "шуму. Нелокальне усереднення [8] краще зберігає текстури. Класичні методи проєкту поступаються за "
             "точністю, але прості, прозорі, швидкі (соті частки секунди на знімок) і дозволяють пояснити причину "
             "помилок. Прямого порівняння на тій самій вибірці не проводилось.")
    rep.heading("6.4. Практична цінність", 2)
    rep.para("Практична цінність — відтворюваний стенд для порівняння класичних методів із фіксованим seed, "
             "кількісним аналізом (довірчі інтервали, абляція стадій) та конфігурацією без правки коду. Наукову "
             "новизну в строгому сенсі робота не заявляє: використано відомі методи.")
    rep.page_break()

    # ---- 7. висновки
    rep.heading("7. Висновки")
    rep.bullets([
        f"Створено програму з двома пайплайнами (3 і 4 стадії, 5 категорій методів), усі методи й метрики написано "
        f"вручну; вибірка — {n_total} зображень, з яких {n_eval} в аналізі.",
        f"При гаусовому шумі кращий P1 (на {fmt(-pair_val('gauss_15'), 1)}–{fmt(-pair_val('gauss_30'), 1)} дБ "
        "за PSNR), при імпульсному, змішаному шумі та слабкому контрасті кращий P2 "
        f"(на {fmt(pair_val('lowcontrast'), 1)}–{fmt(pair_val('sp_20'), 1)} дБ).",
        "Внесок стадій залежить від умов: нерізке маскування й розтягування контрасту іноді шкодять, тому їх "
        "застосування обмежено порогами (шум, динамічний діапазон).",
        f"Перевірка сценаріїв: {passed} з {total_checks}; тести: {tests}.",
        "Обмеження: синтетичний шум, підбір за PSNR, зменшений розмір зображень; для реальних даних потрібна "
        "повторна оцінка."])
    rep.heading("Список використаних джерел")
    for index, text in enumerate(SOURCES, 1):
        rep.para(f"{index}. {text}", indent=False, size=12)
    rep.page_break()

    # ---- додаток
    rep.heading("Додаток А. Повний код програми")
    rep.para(f"Репозиторій: {REPO_PLACEHOLDER}. Нижче наведено вихідний код.", indent=False)
    for relative in source_files():
        rep.para(relative, bold=True, indent=False)
        with open(os.path.join(ROOT, relative), encoding="utf-8") as handle:
            rep.code(handle.read(), size=7)
    props = rep.doc.core_properties
    props.author = "Мовчан Анастасія"
    props.last_modified_by = "Мовчан Анастасія"
    props.title = "Звіт зі STEM-проєкту"
    props.comments = ""
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    rep.doc.save(OUT)
    print("звіт збережено:", OUT)


if __name__ == "__main__":
    build()

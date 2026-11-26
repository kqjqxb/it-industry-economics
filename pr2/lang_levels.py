"""Дослідження рівнів мов програмування C# та Java (порівняно з TypeScript).

Одна й та сама функціональність (модуль розрахунку вільних слотів) реалізована трьома
мовами; результати перевірено на однакових сценаріях (lang_levels/run_all.sh).
Розмір кожної реалізації вимірюється cloc без тестового драйвера.

Рівень мови за C. Jones: level = 320 / (SLOC на 1 функціональну точку), де 320 –
кількість операторів базового асемблера на одну функціональну точку.

Запуск: python lang_levels.py <шлях до репозиторію Visitera>
"""
import json
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
SOURCES = {
    "TypeScript": [f"src/lib/availability/{n}" for n in ("intervals.ts", "zoned.ts", "slots.ts")],
    "Java": ["java/Interval.java", "java/Intervals.java", "java/Zoned.java", "java/Slots.java"],
    "C#": ["csharp/Intervals.cs", "csharp/Zoned.cs", "csharp/Slots.cs"],
}
ASSEMBLY_SLOC_PER_FP = 320
# QSM Function Point Languages Table v5.0: середнє та медіана SLOC на функціональну точку.
QSM = {"Java": (53, 53), "C#": (54, 59), "JavaScript": (47, 53), "C++": (50, 53),
       "C": (97, 99), "SQL": (21, 21), "HTML": (34, 40)}
REFERENCE = "Java"


def measure(files: list[str], cwd: Path) -> dict:
    out = subprocess.run(["cloc", "--json", "--quiet", *files], cwd=cwd,
                         capture_output=True, text=True, check=True)
    total = json.loads(out.stdout)["SUM"]
    return {key: total[key] for key in ("nFiles", "blank", "comment", "code")}


def comma(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")


def main() -> None:
    visitera = Path(sys.argv[1]).expanduser().resolve()
    sizes = {lang: measure(files, visitera if lang == "TypeScript" else ROOT / "lang_levels")
             for lang, files in SOURCES.items()}
    # Функціональний розмір модуля оцінюємо через еталонну мову з найбільшою вибіркою QSM.
    function_points = sizes[REFERENCE]["code"] / QSM[REFERENCE][0]

    rows = []
    for lang, size in sizes.items():
        gearing = size["code"] / function_points
        rows.append({
            "language": lang,
            **size,
            "ratio_to_ts": size["code"] / sizes["TypeScript"]["code"],
            "sloc_per_fp": gearing,
            "level": ASSEMBLY_SLOC_PER_FP / gearing,
        })
    reference = [{"language": lang, "avg": avg, "median": median,
                  "level": ASSEMBLY_SLOC_PER_FP / avg} for lang, (avg, median) in QSM.items()]
    (RESULTS / "lang_levels.json").write_text(json.dumps(
        {"function_points": function_points, "measured": rows, "qsm": reference},
        ensure_ascii=False, indent=2))

    lines = [f"Функціональний розмір модуля: {sizes[REFERENCE]['code']} / {QSM[REFERENCE][0]} = "
             f"{comma(function_points)} FP", ""]
    for row in rows:
        lines.append(f"{row['language']:10} код {row['code']:4}  коментарі {row['comment']:3}  "
                     f"відносно TS {comma(row['ratio_to_ts'])}  "
                     f"SLOC/FP {comma(row['sloc_per_fp'], 1):>5}  "
                     f"рівень {comma(row['level'], 1)}")
    lines.append("")
    for row in reference:
        lines.append(f"QSM {row['language']:10} SLOC/FP {row['avg']:3} "
                     f"(медіана {row['median']:3})  "
                     f"рівень {comma(row['level'], 1)}")
    text = "\n".join(lines)
    (RESULTS / "lang_levels.txt").write_text(text + "\n")
    print(text)

    fig, axis = plt.subplots(figsize=(8, 3.6))
    names = [row["language"] for row in rows]
    code = [row["code"] for row in rows]
    comments = [row["comment"] for row in rows]
    axis.bar(names, code, color="#4c72b0", label="Рядки коду")
    axis.bar(names, comments, bottom=code, color="#c4cfe0", label="Коментарі")
    for i, row in enumerate(rows):
        axis.annotate(f"{row['code']} ({comma(row['ratio_to_ts'])}×)", (i, row["code"] / 2),
                      ha="center", color="white", fontsize=10)
    axis.set_ylabel("Кількість рядків")
    axis.legend(loc="upper left")
    axis.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS / "lang_levels.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    main()

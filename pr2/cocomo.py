"""Економічні розрахунки за базовою моделлю COCOMO на основі виміряного LOC.

Effort = a * KLOC^b (людино-місяці), Cost = Effort * salary (грн),
Schedule = c * Effort^d (місяці). Коефіцієнти – таблиця 3 методички.

Запуск (після measure_loc.py): python cocomo.py
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

RESULTS = Path(__file__).parent / "results"

PROJECT_TYPES = {
    "Органічний": (2.4, 1.05, 2.5, 0.38),
    "Напіврозділений": (3.0, 1.12, 2.5, 0.35),
    "Вбудований": (3.6, 1.20, 2.5, 0.32),
}
CHOSEN_TYPE = "Напіврозділений"

# Медіанні зарплати розробників в Україні, червень 2026, $ на місяць «чистими» (DOU, літо 2026).
SALARY_USD = {"Middle": 2500, "Усі розробники": 3500, "Senior": 4500}
BASE_LEVEL = "Middle"
USD_RATE = 45.272  # офіційний курс НБУ на 26.11.2026, грн за 1 $


def cocomo(kloc: float, a: float, b: float, c: float, d: float) -> tuple[float, float]:
    effort = a * kloc ** b
    return effort, c * effort ** d


def comma(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")


def estimate(kloc: float, project_type: str, salary_uah: float) -> dict:
    effort, schedule = cocomo(kloc, *PROJECT_TYPES[project_type])
    return {
        "type": project_type,
        "kloc": kloc,
        "effort_pm": effort,
        "schedule_m": schedule,
        "team": effort / schedule,
        "productivity_loc_pm": kloc * 1000 / effort,
        "cost_uah": effort * salary_uah,
        "cost_per_loc_uah": effort * salary_uah / (kloc * 1000),
    }


def plot_curves(sizes: dict[str, float]) -> None:
    kloc = [x / 2 for x in range(1, 161)]
    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.2))
    for name, coef in PROJECT_TYPES.items():
        efforts = [cocomo(k, *coef)[0] for k in kloc]
        left.plot(kloc, efforts, label=name)
        right.plot(kloc, [cocomo(k, *coef)[1] for k in kloc], label=name)
    for label, size in sizes.items():
        effort, schedule = cocomo(size, *PROJECT_TYPES[CHOSEN_TYPE])
        left.scatter([size], [effort], color="black", zorder=3)
        left.annotate(label, (size, effort), textcoords="offset points", xytext=(6, -12),
                      fontsize=8)
        right.scatter([size], [schedule], color="black", zorder=3)
    left.set(xlabel="Розмір, KLOC", ylabel="Трудомісткість, людино-місяців", title="Зусилля")
    right.set(xlabel="Розмір, KLOC", ylabel="Тривалість, місяців", title="Час на розробку")
    for axis in (left, right):
        axis.grid(alpha=0.3)
        axis.legend()
        axis.xaxis.set_major_formatter(FuncFormatter(lambda v, _: comma(v, 0)))
        axis.yaxis.set_major_formatter(
            FuncFormatter(lambda v, _: comma(v, 0 if v == int(v) else 1)))
    fig.tight_layout()
    fig.savefig(RESULTS / "cocomo_curves.png", dpi=200)
    plt.close(fig)


def plot_structure(summary: dict) -> None:
    categories = summary["categories"]
    order = ["product", "tests", "tools", "generated", "config"]
    labels = [categories[k]["title"] for k in order]
    values = [categories[k]["total"]["code"] for k in order]
    fig, axis = plt.subplots(figsize=(9, 3.6))
    bars = axis.barh(labels[::-1], values[::-1], color="#4c72b0")
    axis.bar_label(bars, labels=[comma(v, 0) for v in values[::-1]], padding=4)
    axis.set_xlabel("Рядки коду (без коментарів і порожніх рядків)")
    axis.xaxis.set_major_formatter(FuncFormatter(lambda v, _: comma(v, 0)))
    axis.set_xlim(0, max(values) * 1.15)
    axis.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS / "loc_structure.png", dpi=200)
    plt.close(fig)


def main() -> None:
    summary = json.loads((RESULTS / "loc_summary.json").read_text())
    code = {key: value["total"]["code"] for key, value in summary["categories"].items()}
    sizes = {
        "Поставлений код": (code["product"] + code["config"]) / 1000,
        "Увесь власний код":
            (code["product"] + code["config"] + code["tests"] + code["tools"]) / 1000,
    }
    salary_uah = {level: usd * USD_RATE for level, usd in SALARY_USD.items()}
    base_salary = salary_uah[BASE_LEVEL]

    report = {
        "sizes_kloc": sizes,
        "salary_uah": salary_uah,
        "by_type": [estimate(sizes["Поставлений код"], t, base_salary) for t in PROJECT_TYPES],
        "by_size": [estimate(size, CHOSEN_TYPE, base_salary) for size in sizes.values()],
        "by_salary": {level: estimate(sizes["Поставлений код"], CHOSEN_TYPE, value)["cost_uah"]
                      for level, value in salary_uah.items()},
    }
    (RESULTS / "cocomo.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))

    lines = [f"Розмір: поставлений код {comma(sizes['Поставлений код'], 3)} KLOC, "
             f"увесь власний код {comma(sizes['Увесь власний код'], 3)} KLOC",
             f"Зарплата {BASE_LEVEL}: {SALARY_USD[BASE_LEVEL]} $ x {comma(USD_RATE, 3)} = "
             f"{comma(base_salary)} грн/міс", ""]
    for row in report["by_type"] + report["by_size"]:
        lines.append(
            f"{row['type']:16} {comma(row['kloc'], 3):>7} KLOC  "
            f"Effort {comma(row['effort_pm']):>7} л.-міс  "
            f"Schedule {comma(row['schedule_m']):>6} міс  команда {comma(row['team'], 1):>5}  "
            f"Cost {comma(row['cost_uah']):>15} грн")
    lines.append("")
    for level, cost in report["by_salary"].items():
        lines.append(f"Вартість ({CHOSEN_TYPE.lower()}, {level}): {comma(cost)} грн")
    text = "\n".join(lines)
    (RESULTS / "cocomo.txt").write_text(text + "\n")
    print(text)

    plot_curves(sizes)
    plot_structure(summary)


if __name__ == "__main__":
    main()

"""Оцінка зусиль і вартості «нового» проєкту методом аналогій.

Атрибути (без розміру, зусиль і мови) нормуються до [0; 1] методом мінімакс, відстані до
нового проєкту рахуються евклідовою і манхеттенською метриками. Аналоги беруться серед
проєктів тієї самої або близької мови (TypeScript/JavaScript), оцінка – середнє, медіана,
зважене середнє і середнє з коригуванням за розміром зусиль трьох найближчих проєктів.

Запуск: python analogy.py (після collect.py)
"""
import csv
import json
import math
import statistics
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from projects import NEW_PROJECT

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
PR2 = ROOT.parent / "pr2" / "results"

ATTRIBUTES = {
    "duration_months": "Тривалість, міс",
    "developers": "Розробників",
    "commits": "Комітів",
    "tags": "Релізів",
}
CLOSE_LANGUAGES = {"TypeScript", "JavaScript", "JSX"}
K = 3


def comma(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")


def load() -> list[dict]:
    with open(RESULTS / "database_raw.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for key in (*ATTRIBUTES, "size_loc", "effort_pm"):
            row[key] = float(row[key])
    return rows


def normalise(rows: list[dict], log: bool) -> None:
    """Мінімакс до [0; 1]; з log – після логарифмування ln(1 + x), що стискає довгий хвіст."""
    for key in ATTRIBUTES:
        values = [math.log1p(r[key]) if log else r[key] for r in rows]
        low, high = min(values), max(values)
        for r, v in zip(rows, values):
            r[f"n_{key}"] = (v - low) / (high - low) if high > low else 0.0


def distances(rows: list[dict], new: dict) -> None:
    for r in rows:
        diffs = [r[f"n_{k}"] - new[f"n_{k}"] for k in ATTRIBUTES]
        r["euclid"] = sum(d * d for d in diffs) ** 0.5
        r["manhattan"] = sum(abs(d) for d in diffs)


def predict(target: dict, pool: list[dict], metric: str, k: int, statistic: str) -> float:
    """Зусилля цільового проєкту за k найближчими проєктами пулу близької мови."""
    distances(pool, target)
    close = [r for r in pool if r is not target and r["language"] in CLOSE_LANGUAGES]
    neighbours = sorted(close, key=lambda r: r[metric])[:k]
    return estimate(neighbours, target)[statistic]


def calibrate(rows: list[dict]) -> list[dict]:
    """Перевірка «залиш одного» на проєктах бази мовою TypeScript/JavaScript."""
    results = []
    known = [r for r in rows if r["project"] != NEW_PROJECT]
    targets = [r for r in known if r["language"] in CLOSE_LANGUAGES]
    for log in (False, True):
        normalise(rows, log)
        for metric in ("euclid", "manhattan"):
            for k in (1, 2, 3):
                for statistic in STATISTICS:
                    errors = [abs(predict(t, known, metric, k, statistic) - t["effort_pm"])
                              / t["effort_pm"] for t in targets]
                    results.append({"log": log, "metric": metric, "k": k, "statistic": statistic,
                                    "mmre": statistics.mean(errors),
                                    "pred25": sum(e <= 0.25 for e in errors) / len(errors),
                                    "mdmre": statistics.median(errors)})
    return sorted(results, key=lambda r: r["mmre"])


STATISTICS = ("Середнє", "Медіана", "Зважене за 1/d", "З коригуванням за розміром")


def estimate(neighbours: list[dict], new: dict) -> dict:
    efforts = [n["effort_pm"] for n in neighbours]
    weights = [1 / max(n["euclid"], 1e-9) for n in neighbours]
    adjusted = [new["size_loc"] / n["size_loc"] * n["effort_pm"] for n in neighbours]
    return {
        "Середнє": statistics.mean(efforts),
        "Медіана": statistics.median(efforts),
        "Зважене за 1/d": sum(w * e for w, e in zip(weights, efforts)) / sum(weights),
        "З коригуванням за розміром": statistics.mean(adjusted),
    }


def write_xlsx(rows: list[dict], nearest: set, nearest_any: set) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Database"
    header = ["Проєкт", "GitHub URL", *ATTRIBUTES.values(), "Мова", "Size, LOC", "Effort, р.-міс",
              "d евклід", "d манхеттен"]
    ws.append(header)
    green = PatternFill("solid", fgColor="C6EFCE")
    yellow = PatternFill("solid", fgColor="FFEB9C")
    orange = PatternFill("solid", fgColor="F8CBAD")
    for r in rows:
        ws.append([r["project"], r["url"], *[r[k] for k in ATTRIBUTES], r["language"],
                   r["size_loc"],
                   r["effort_pm"] if r["project"] != NEW_PROJECT else "?",
                   round(r["euclid"], 4), round(r["manhattan"], 4)])
        fill = (orange if r["project"] == NEW_PROJECT else green if r["project"] in nearest
                else yellow if r["project"] in nearest_any else None)
        if fill:
            for cell in ws[ws.max_row]:
                cell.fill = fill
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for col, width in zip("ABCDEFGHIJK", (24, 62, 12, 12, 10, 10, 12, 11, 12, 11, 12)):
        ws.column_dimensions[col].width = width
    ws.append([])
    ws.append(["Помаранчевий – новий проєкт; зелений – три найближчі аналоги мовою "
               "TypeScript/JavaScript; "
               "жовтий – найближчі проєкти іншими мовами, відкинуті через мову."])
    wb.save(RESULTS / "database.xlsx")


def plot(rows: list[dict], nearest: set, nearest_any: set, metric: str) -> None:
    others = sorted((r for r in rows if r["project"] != NEW_PROJECT), key=lambda r: r[metric])
    colors = ["#2ca02c" if r["project"] in nearest else "#e6b800" if r["project"] in nearest_any
              else "#9aa9c4" for r in others]
    fig, axis = plt.subplots(figsize=(9, 5.4))
    axis.barh([f"{r['project']} ({r['language']})" for r in others][::-1],
              [r[metric] for r in others][::-1], color=colors[::-1])
    name = "Манхеттенська" if metric == "manhattan" else "Евклідова"
    axis.set_xlabel(f"{name} відстань до нового проєкту (нормовані атрибути)")
    axis.xaxis.set_major_formatter(FuncFormatter(lambda v, _: comma(v)))
    axis.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS / "distances.png", dpi=200)
    plt.close(fig)


def main() -> None:
    rows = load()
    calibration = calibrate(rows)
    # Завдання вимагає трьох найближчих проєктів: найкраща конфігурація серед k = 3.
    best = next(c for c in calibration if c["k"] == K)
    normalise(rows, best["log"])
    new = next(r for r in rows if r["project"] == NEW_PROJECT)
    distances(rows, new)
    metric = best["metric"]
    others = [r for r in rows if r is not new]
    by_metric = sorted(others, key=lambda r: r[metric])
    nearest_any = by_metric[:K]
    nearest = [r for r in by_metric if r["language"] in CLOSE_LANGUAGES][:K]
    other_metric = "euclid" if metric == "manhattan" else "manhattan"
    nearest_other = sorted((r for r in others if r["language"] in CLOSE_LANGUAGES),
                           key=lambda r: r[other_metric])[:K]

    estimates = estimate(nearest, new)
    estimates_any = estimate(nearest_any, new)
    actual = new["effort_pm"]
    salary = json.loads((PR2 / "cocomo.json").read_text())["salary_uah"]["Middle"]
    chosen = estimates[best["statistic"]]
    economics = {
        "effort_pm": chosen,
        "cost_uah": chosen * salary,
        "actual_cost_uah": actual * salary,
        "duration_months": statistics.mean(n["duration_months"] for n in nearest),
        "team": statistics.mean(n["developers"] for n in nearest),
        "productivity_loc_pm": new["size_loc"] / chosen,
        "salary_uah": salary,
        "mre": abs(chosen - actual) / actual,
    }
    summary = {
        "new": new, "attributes": ATTRIBUTES, "rows": rows, "best": best,
        "calibration": calibration, "metric": metric,
        "nearest": [n["project"] for n in nearest],
        "nearest_any": [n["project"] for n in nearest_any],
        "nearest_other_metric": [n["project"] for n in nearest_other],
        "estimates": estimates, "estimates_any": estimates_any, "actual": actual,
        "economics": economics,
    }
    (RESULTS / "analogy.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    with open(RESULTS / "database.csv", "w", newline="", encoding="utf-8") as f:
        fields = ["project", "url", *ATTRIBUTES, "language", "size_loc", "effort_pm", "euclid",
                  "manhattan"]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    lines = [f"Новий проєкт: {NEW_PROJECT}, фактичні зусилля {actual:g} р.-міс", ""]
    for r in by_metric:
        mark = "*" if r in nearest else "+" if r in nearest_any else " "
        lines.append(f"{mark} {r['project']:24} {r['language']:12} d_E {comma(r['euclid'], 4)}  "
                     f"d_M {comma(r['manhattan'], 4)}  effort {r['effort_pm']:g}")
    lines += ["", f"Калібрування: {best}",
              f"Найближчі (TS/JS): {summary['nearest']}; за іншою метрикою: "
              f"{summary['nearest_other_metric']}; без урахування мови: {summary['nearest_any']}"]
    for name, value in estimates.items():
        lines.append(f"{name:28} {comma(value)} р.-міс  (похибка "
                     f"{comma(abs(value - actual) / actual * 100, 1)} %)")
    lines.append(f"Без урахування мови, середнє: {comma(estimates_any['Середнє'])} р.-міс")
    lines.append(f"Вартість: {comma(economics['cost_uah'], 0)} грн, тривалість "
                 f"{comma(economics['duration_months'], 1)} міс, "
                 f"команда {comma(economics['team'], 1)}")
    text = "\n".join(lines)
    (RESULTS / "analogy.txt").write_text(text + "\n")
    print(text)
    write_xlsx(rows, {n["project"] for n in nearest}, {n["project"] for n in nearest_any})
    plot(rows, {n["project"] for n in nearest}, {n["project"] for n in nearest_any}, metric)


if __name__ == "__main__":
    main()

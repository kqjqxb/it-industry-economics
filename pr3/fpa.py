"""Аналіз функціональних точок застосунку Visitera та економічні характеристики.

Складність функцій визначається за матрицями методички (таблиці 4–7), далі UFP, VAF за 14
характеристиками системи, AFP і оцінка розміру в рядках коду SLOC = AFP * LM. Розмір у SLOC
переводиться в трудомісткість, вартість і тривалість за моделлю COCOMO (як у ПР2) і
порівнюється з фактично виміряним розміром.

Запуск: python fpa.py (потрібні результати ../pr2/results)
"""
import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt

from fpa_data import EIF, GSC, ILF, TRANSACTIONS

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
PR2 = ROOT.parent / "pr2" / "results"

LEVELS = ("Низький", "Середній", "Високий")
WEIGHTS = {"ILF": (7, 10, 15), "EIF": (5, 7, 10), "EI": (3, 4, 6), "EO": (4, 5, 7), "EQ": (3, 4, 6)}
SERVICE_COLUMNS = {"id", "created_at", "updated_at"}
EQ_INPUT_DET = 2

# Множники мов LM, SLOC на одну функціональну точку (QSM v5.0; TypeScript – емпірично з ПР2).
LANGUAGE_MULTIPLIERS = {"JavaScript (QSM)": 47, "Java (QSM)": 53, "C# (QSM)": 54}
SEMIDETACHED = (3.0, 1.12, 2.5, 0.35)


def level(row: int, col: int) -> str:
    """Рівень за індексами рядка й стовпця матриці складності 3×3 (однакова форма для всіх)."""
    matrix = ((0, 0, 1), (0, 1, 2), (1, 2, 2))
    return LEVELS[matrix[row][col]]


def data_function_level(ret: int, det: int) -> str:
    return level(0 if ret == 1 else 1 if ret <= 5 else 2, 0 if det <= 19 else 1 if det <= 50 else 2)


def transaction_level(kind: str, ftr: int, det: int) -> str:
    if kind == "EQ":
        # Більший з рівнів входу (як EI, критерій вибірки + дія = 2 DET) і виходу (як EO).
        both = (transaction_level("EI", ftr, EQ_INPUT_DET), transaction_level("EO", ftr, det))
        return max(both, key=LEVELS.index)
    if kind == "EI":
        return level(0 if ftr <= 1 else 1 if ftr == 2 else 2,
                     0 if det <= 4 else 1 if det <= 15 else 2)
    return level(0 if ftr <= 1 else 1 if ftr <= 3 else 2, 0 if det <= 5 else 1 if det <= 19 else 2)


def data_functions(files: dict, kind: str) -> list[dict]:
    rows = []
    for name, (description, tables) in files.items():
        columns = {c for cols in tables.values() for c in cols if c not in SERVICE_COLUMNS}
        lvl = data_function_level(len(tables), len(columns))
        rows.append({"name": name, "type": kind, "description": description, "ret": len(tables),
                     "ret_names": list(tables), "det": len(columns), "level": lvl,
                     "ufp": WEIGHTS[kind][LEVELS.index(lvl)]})
    return rows


def transactions() -> list[dict]:
    rows = []
    for name, kind, fields, ftr in TRANSACTIONS:
        det = len(fields) + 1  # плюс дія/повідомлення
        lvl = transaction_level(kind, len(ftr), det)
        rows.append({"name": name, "type": kind, "fields": fields, "det": det, "ftr": len(ftr),
                     "ftr_names": ftr, "level": lvl, "ufp": WEIGHTS[kind][LEVELS.index(lvl)]})
    return rows


def cocomo(kloc: float) -> tuple[float, float]:
    a, b, c, d = SEMIDETACHED
    effort = a * kloc ** b
    return effort, c * effort ** d


def comma(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")


def plot(summary: dict, gsc: list) -> None:
    kinds = list(WEIGHTS)
    fig, axis = plt.subplots(figsize=(8, 3.8))
    bottom = [0] * len(kinds)
    for lvl, color in zip(LEVELS, ("#9ecae1", "#4292c6", "#08519c")):
        values = [summary["matrix"][k][lvl]["ufp"] for k in kinds]
        axis.bar(kinds, values, bottom=bottom, color=color, label=lvl)
        bottom = [b + v for b, v in zip(bottom, values)]
    for i, total in enumerate(bottom):
        axis.annotate(str(total), (i, total), ha="center", va="bottom", xytext=(0, 3),
                      textcoords="offset points")
    axis.set_ylabel("Нескориговані функціональні точки")
    axis.set_ylim(0, max(bottom) * 1.15)
    axis.legend(title="Складність")
    axis.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS / "ufp_structure.png", dpi=200)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(8, 4.6))
    names = [f"{i}. {name}" for i, (name, _, _) in enumerate(gsc, 1)][::-1]
    axis.barh(names, [score for _, score, _ in gsc][::-1], color="#4c72b0")
    axis.set_xlim(0, 5)
    axis.set_xlabel("Ступінь впливу (0–5)")
    axis.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS / "gsc.png", dpi=200)
    plt.close(fig)


def plot_boundary() -> None:
    """Межа застосунку: користувачі, внутрішні та зовнішні логічні файли."""
    fig, axis = plt.subplots(figsize=(10, 5.6))
    axis.set_xlim(0, 100)
    axis.set_ylim(0, 60)
    axis.axis("off")

    def box(x, y, w, h, text, face, edge="#333333", style="-", size=9):
        axis.add_patch(plt.Rectangle((x, y), w, h, facecolor=face, edgecolor=edge, linestyle=style,
                                     linewidth=1.2))
        axis.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, wrap=True)

    def arrow(x1, y1, x2, y2):
        axis.annotate("", (x2, y2), (x1, y1), arrowprops={"arrowstyle": "<->", "color": "#555555"})

    box(22, 2, 54, 56, "", "#f7f7f7", style="--")
    axis.text(49, 55.5, "Межа застосунку Visitera", ha="center", fontsize=11, weight="bold")
    names = list(ILF)
    for i, name in enumerate(names):
        col, row = i % 3, i // 3
        box(25 + col * 17, 38 - row * 13, 15, 9, name.replace(" ", "\n", 1), "#c6dbef", size=8)
    box(2, 38, 14, 9, "Клієнт\n(телефон)", "#fde0c5")
    box(2, 12, 14, 9, "Майстер\n(адмінпанель)", "#fde0c5")
    for i, name in enumerate(EIF):
        box(83, 38 - i * 18, 15, 10, name.replace(" (", "\n(").replace("поясів ", "поясів\n"),
            "#d9f0d3", size=8)
    box(83, 2, 15, 8, "Поштовий\nсервіс", "#eeeeee", size=8)
    arrow(16, 42.5, 25, 42.5)
    arrow(16, 16.5, 25, 16.5)
    arrow(76, 43, 83, 43)
    arrow(76, 25, 83, 25)
    arrow(76, 6, 83, 6)
    axis.text(20.5, 45, "EI / EO / EQ", ha="center", fontsize=8)
    axis.text(20.5, 19, "EI / EO / EQ", ha="center", fontsize=8)
    axis.text(79.5, 8, "EO", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(RESULTS / "boundary.png", dpi=200)
    plt.close(fig)


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    rows = data_functions(ILF, "ILF") + data_functions(EIF, "EIF") + transactions()

    matrix = {k: {lvl: {"count": 0, "ufp": 0} for lvl in LEVELS} for k in WEIGHTS}
    for row in rows:
        cell = matrix[row["type"]][row["level"]]
        cell["count"] += 1
        cell["ufp"] += row["ufp"]
    ufp = sum(row["ufp"] for row in rows)
    tdi = sum(score for _, score, _ in GSC)
    vaf = tdi * 0.01 + 0.65
    afp = ufp * vaf

    pr2_loc = json.loads((PR2 / "loc_summary.json").read_text())["categories"]
    measured = pr2_loc["product"]["total"]["code"] + pr2_loc["config"]["total"]["code"]
    pr2_cocomo = json.loads((PR2 / "cocomo.json").read_text())
    salary = pr2_cocomo["salary_uah"]["Middle"]
    ts_gearing = next(r["sloc_per_fp"] for r in json.loads((PR2 / "lang_levels.json").read_text())
                      ["measured"] if r["language"] == "TypeScript")
    multipliers = {**LANGUAGE_MULTIPLIERS, "TypeScript (ПР2)": round(ts_gearing, 1)}

    estimates = []
    for language, lm in multipliers.items():
        sloc = afp * lm
        effort, schedule = cocomo(sloc / 1000)
        estimates.append({"language": language, "lm": lm, "sloc": sloc, "effort_pm": effort,
                          "schedule_m": schedule, "cost_uah": effort * salary,
                          "vs_measured": sloc / measured})
    measured_effort, measured_schedule = cocomo(measured / 1000)
    measured_cost = measured_effort * salary

    summary = {
        "counts": dict(Counter(row["type"] for row in rows)),
        "matrix": matrix, "ufp": ufp, "tdi": tdi, "vaf": vaf, "afp": afp,
        "measured_sloc": measured, "actual_gearing": measured / afp,
        "estimates": estimates,
        "measured_cocomo": {"effort_pm": measured_effort, "schedule_m": measured_schedule,
                            "cost_uah": measured_cost},
        "cost_per_fp_uah": measured_cost / afp,
        "fp_per_pm": afp / measured_effort,
        "salary_uah": salary,
    }
    (RESULTS / "functions.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    (RESULTS / "fpa_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    lines = [f"Функцій: {summary['counts']}"]
    for kind in WEIGHTS:
        cells = "  ".join(f"{lvl} {matrix[kind][lvl]['count']:2} ({matrix[kind][lvl]['ufp']:3})"
                          for lvl in LEVELS)
        lines.append(f"{kind:4} {cells}")
    lines += [f"UFP = {ufp}", f"TDI = {tdi}, VAF = {comma(vaf)}", f"AFP = {comma(afp)}",
              f"Виміряний розмір: {measured} SLOC, фактичний LM = {comma(measured / afp, 1)}", ""]
    for e in estimates:
        lines.append(f"{e['language']:18} LM {comma(e['lm'], 1):>5}  "
                     f"SLOC {comma(e['sloc'], 0):>7}  "
                     f"Effort {comma(e['effort_pm']):>7}  Schedule {comma(e['schedule_m']):>6}  "
                     f"Cost {comma(e['cost_uah'], 0):>12} грн  "
                     f"({comma(e['vs_measured'] * 100, 1)} %)")
    lines.append("Вартість однієї функціональної точки: "
                 f"{comma(summary['cost_per_fp_uah'], 0)} грн, "
                 f"продуктивність {comma(summary['fp_per_pm'])} FP на людино-місяць")
    text = "\n".join(lines)
    (RESULTS / "fpa.txt").write_text(text + "\n")
    print(text)
    plot(summary, GSC)
    plot_boundary()


if __name__ == "__main__":
    main()

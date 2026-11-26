"""Оцінка трудомісткості Visitera моделями COCOMO: базовою, проміжною, COCOMO II (Early Design
і Post-Architecture), дослідження впливу розміру і порівняння моделей для проєкту з високою
новизною.

PM = a · SIZE^b · EAF (COCOMO 81), TM = c · PM^d, SS = PM / TM, P = SIZE / PM;
COCOMO II: PM = A · SIZE^E · ΠEM, E = B + 0,01 · ΣSF, TM = C · PM^F, F = D + 0,2 · (E − B).

Запуск: python cocomo_models.py (потрібні результати ../pr2/results)
"""
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

import cocomo_data as cd

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
PR2 = ROOT.parent / "pr2" / "results"


def comma(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")


def indicators(kloc: float, pm: float, tm: float, salary: float) -> dict:
    return {"pm": pm, "tm": tm, "ss": pm / tm, "p": kloc * 1000 / pm, "cost": pm * salary}


def basic(kloc: float, mode: str, salary: float) -> dict:
    a, b, c, d = cd.BASIC[mode]
    pm = a * kloc ** b
    return indicators(kloc, pm, c * pm ** d, salary)


def intermediate(kloc: float, mode: str, eaf: float, salary: float) -> dict:
    a, b = cd.INTERMEDIATE[mode]
    _, _, c, d = cd.BASIC[mode]
    pm = a * kloc ** b * eaf
    return indicators(kloc, pm, c * pm ** d, salary)


def product(values) -> float:
    return math.prod(values)


def cocomo2(kloc: float, sf_sum: float, ems: list[float], sced: float, salary: float) -> dict:
    """SCED% = 100: графік номінальний, тому TM рахується від PM без множника SCED."""
    e = cd.B + 0.01 * sf_sum
    pm = cd.A * kloc ** e * product(ems)
    pm_ns = pm / sced
    f = cd.D + 0.2 * (e - cd.B)
    tm = cd.C * pm_ns ** f
    return {**indicators(kloc, pm, tm, salary), "e": e, "f": f, "eaf": product(ems)}


def ratings(table: dict, chosen: dict, levels: tuple) -> list[dict]:
    rows = []
    for key, (title, values) in table.items():
        index, why = chosen[key]
        rows.append({"key": key, "title": title, "level": levels[index], "value": values[index],
                     "why": why})
    return rows


def plot_sizes(sweep: list[dict]) -> None:
    sizes = [r["kloc"] for r in sweep]
    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.2))
    for key, label in (("early", "COCOMO II, Early Design"),
                       ("post", "COCOMO II, Post-Architecture"),
                       ("intermediate", "Проміжна COCOMO"), ("basic", "Базова COCOMO")):
        left.plot(sizes, [r[key]["pm"] for r in sweep], marker="o", label=label)
        right.plot(sizes, [r[key]["tm"] for r in sweep], marker="o", label=label)
    left.set(xlabel="SIZE, KSLOC", ylabel="PM, людино-місяців", title="Трудомісткість")
    right.set(xlabel="SIZE, KSLOC", ylabel="TM, місяців", title="Час розробки")
    for axis in (left, right):
        axis.grid(alpha=0.3)
        axis.legend(fontsize=8)
        axis.xaxis.set_major_formatter(FuncFormatter(lambda v, _: comma(v, 0)))
        axis.yaxis.set_major_formatter(
            FuncFormatter(lambda v, _: comma(v, 0 if v == int(v) else 1)))
    fig.tight_layout()
    fig.savefig(RESULTS / "size_influence.png", dpi=200)
    plt.close(fig)


def plot_models(rows: list[dict]) -> None:
    fig, axis = plt.subplots(figsize=(9, 3.8))
    names = [r["model"] for r in rows][::-1]
    bars = axis.barh(names, [r["pm"] for r in rows][::-1], color="#4c72b0")
    axis.bar_label(bars, labels=[f"{comma(r['pm'], 1)} л.-міс, {comma(r['tm'], 1)} міс"
                                 for r in rows][::-1], padding=4, fontsize=8)
    axis.set_xlabel("PM, людино-місяців")
    axis.set_xlim(0, max(r["pm"] for r in rows) * 1.45)
    axis.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS / "models_novelty.png", dpi=200)
    plt.close(fig)


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    pr2 = json.loads((PR2 / "cocomo.json").read_text())
    kloc = pr2["sizes_kloc"]["Поставлений код"]
    salary = pr2["salary_uah"]["Middle"]

    # 1. Базова і проміжна моделі.
    basic_rows = {mode: basic(kloc, mode, salary) for mode in cd.BASIC}
    cost_drivers = ratings(cd.COST_DRIVERS, cd.COST_DRIVER_RATINGS, cd.LEVELS)
    eaf = product(r["value"] for r in cost_drivers)
    inter = intermediate(kloc, cd.MODE, eaf, salary)

    # 2. COCOMO II.
    scale = ratings(cd.SCALE_FACTORS, cd.SCALE_RATINGS, cd.SF_LEVELS)
    sf_sum = sum(r["value"] for r in scale)
    early = ratings(cd.EARLY, cd.EARLY_RATINGS, cd.LEVELS_II)
    post = ratings(cd.POST, cd.POST_RATINGS, cd.SF_LEVELS)
    early_sced = next(r["value"] for r in early if r["key"] == "SCED")
    post_sced = next(r["value"] for r in post if r["key"] == "SCED")
    early_res = cocomo2(kloc, sf_sum, [r["value"] for r in early], early_sced, salary)
    post_res = cocomo2(kloc, sf_sum, [r["value"] for r in post], post_sced, salary)

    # 3. Вплив розміру.
    sweep = [{"kloc": s,
              "basic": basic(s, cd.MODE, salary),
              "intermediate": intermediate(s, cd.MODE, eaf, salary),
              "early": cocomo2(s, sf_sum, [r["value"] for r in early], early_sced, salary),
              "post": cocomo2(s, sf_sum, [r["value"] for r in post], post_sced, salary)}
             for s in cd.SIZES_KSLOC]

    # 4. Номінальна складність, висока новизна: усі множники номінальні, PREC – Very Low,
    # для COCOMO 81 – вбудований режим (нові для команди задачі й обмеження).
    nominal_sf = sum(values[2] for _, values in cd.SCALE_FACTORS.values())
    novelty_sf = nominal_sf - cd.SCALE_FACTORS["PREC"][1][2] + cd.SCALE_FACTORS["PREC"][1][0]
    size = cd.NOVELTY_SIZE_KSLOC
    novelty = [
        {"model": "Базова, вбудований", **basic(size, "Вбудований", salary)},
        {"model": "Проміжна, вбудований (EAF = 1)",
         **intermediate(size, "Вбудований", 1.0, salary)},
        {"model": "Базова, напівнезалежний", **basic(size, "Напівнезалежний", salary)},
        {"model": "Проміжна, напівнезалежний (EAF = 1)",
         **intermediate(size, "Напівнезалежний", 1.0, salary)},
        {"model": "COCOMO II, Early Design", **cocomo2(size, novelty_sf, [1.0] * 7, 1.0, salary)},
        {"model": "COCOMO II, Post-Architecture",
         **cocomo2(size, novelty_sf, [1.0] * 17, 1.0, salary)},
    ]

    summary = {
        "kloc": kloc, "salary": salary, "basic": basic_rows, "cost_drivers": cost_drivers,
        "eaf": eaf, "intermediate": inter, "scale": scale, "sf_sum": sf_sum, "early": early,
        "post": post, "early_result": early_res, "post_result": post_res, "sweep": sweep,
        "novelty": novelty, "novelty_sf": novelty_sf, "nominal_sf": nominal_sf,
    }
    (RESULTS / "cocomo_models.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    lines = [f"SIZE = {comma(kloc, 3)} KSLOC, зарплата {comma(salary)} грн/міс", ""]
    for mode, r in basic_rows.items():
        lines.append(f"Базова, {mode:16} PM {comma(r['pm']):>7}  TM {comma(r['tm']):>6}")
    lines.append(f"Проміжна, {cd.MODE}: EAF {comma(eaf, 4)}  PM {comma(inter['pm'])}  "
                 f"TM {comma(inter['tm'])}")
    lines.append(f"COCOMO II: ΣSF {comma(sf_sum)}  E {comma(early_res['e'], 4)}")
    for name, r in (("Early Design", early_res), ("Post-Architecture", post_res)):
        lines.append(f"  {name:18} EAF {comma(r['eaf'], 4)}  PM {comma(r['pm'])}  "
                     f"TM {comma(r['tm'])}  "
                     f"SS {comma(r['ss'], 1)}  Cost {comma(r['cost'], 0)} грн")
    lines.append("")
    for r in novelty:
        lines.append(f"{r['model']:38} PM {comma(r['pm']):>7}  TM {comma(r['tm']):>6}")
    text = "\n".join(lines)
    (RESULTS / "cocomo_models.txt").write_text(text + "\n")
    print(text)
    plot_sizes(sweep)
    plot_models(novelty)


if __name__ == "__main__":
    main()

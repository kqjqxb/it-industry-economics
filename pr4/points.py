"""Feature points, Object points і Use-case points (два методи) для Visitera та їхній
економічний вплив у порівнянні з оцінками за LOC (ПР2) і функціональними точками (ПР3).

Запуск: python points.py (потрібні результати ../pr2/results і ../pr3/results, Graphviz)
"""
import json
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

import points_data as d

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
PR2 = ROOT.parent / "pr2" / "results"
PR3 = ROOT.parent / "pr3" / "results"
SEMIDETACHED = (3.0, 1.12, 2.5, 0.35)


def comma(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")


def cocomo(kloc: float) -> tuple[float, float]:
    a, b, c, e = SEMIDETACHED
    effort = a * kloc ** b
    return effort, c * effort ** e


# ------------------------------------------------------------------ Feature points
def feature_points(counts: dict, vaf: float) -> dict:
    counts = {**counts, "ALG": len(d.ALGORITHMS)}
    parts = {k: counts[k] * w for k, w in d.FEATURE_WEIGHTS.items()}
    unadjusted = sum(parts.values())
    return {"counts": counts, "parts": parts, "unadjusted": unadjusted, "vaf": vaf,
            "adjusted": unadjusted * vaf}


# ------------------------------------------------------------------ Object points
def screen_level(views: int, tables: int) -> int:
    row = 0 if views < 3 else 1 if views <= 7 else 2
    col = 0 if tables < 4 else 1 if tables < 8 else 2
    return ((0, 0, 1), (0, 1, 2), (1, 2, 2))[row][col]


def report_level(sections: int, tables: int) -> int:
    row = 0 if sections <= 1 else 1 if sections <= 3 else 2
    col = 0 if tables < 4 else 1 if tables < 8 else 2
    return ((0, 0, 1), (0, 1, 2), (1, 2, 2))[row][col]


def object_points() -> dict:
    names = ("простий", "середній", "складний")
    screens = [{"name": n, "views": v, "tables": t, "level": names[screen_level(v, t)],
                "op": d.SCREEN_WEIGHTS[screen_level(v, t)]} for n, v, t in d.SCREENS]
    reports = [{"name": n, "sections": s, "tables": t, "level": names[report_level(s, t)],
                "op": d.REPORT_WEIGHTS[report_level(s, t)]} for n, s, t in d.REPORTS]
    components = [{"name": n, "description": desc, "op": d.COMPONENT_WEIGHT}
                  for n, desc in d.COMPONENTS]
    total = sum(x["op"] for x in screens + reports + components)
    new = total * (100 - d.REUSE_PERCENT) / 100
    prod = d.PROD[d.PROD_LEVEL]
    sensitivity = {level: new / value for level, value in d.PROD.items()}
    return {"screens": screens, "reports": reports, "components": components, "op": total,
            "reuse": d.REUSE_PERCENT, "op_new": new, "prod": prod, "effort_pm": new / prod,
            "by_prod": sensitivity}


# ------------------------------------------------------------------ Use-case points
def use_case_level(transactions: int) -> str:
    return "простий" if transactions <= 3 else "середній" if transactions <= 7 else "складний"


def use_case_points(counts: dict, vaf: float) -> dict:
    uaw = sum(w for _, _, w, _ in d.ACTORS)
    cases = []
    for name, actor, steps, functions in d.USE_CASES:
        level = use_case_level(len(steps))
        cases.append({"name": name, "actor": actor, "steps": steps, "transactions": len(steps),
                      "level": level, "weight": d.USE_CASE_WEIGHTS[level], "functions": functions})
    uucw = sum(c["weight"] for c in cases)
    uucp = uaw + uucw
    tfactor = sum(w * v for _, w, v in d.TECHNICAL)
    efactor = sum(w * v for _, w, v in d.ENVIRONMENTAL)
    tcf = 0.6 + 0.01 * tfactor
    ef = 1.4 - 0.03 * efactor
    ucp = uucp * tcf * ef
    hours = ucp * d.HOURS_PER_UCP

    # Метод 2: функції, виділені за діаграмами варіантів використання і діяльності.
    found = {k: sum(c["functions"].get(k, 0) for c in cases) for k in ("EI", "EO", "EQ")}
    found.update({"ILF": counts["ILF"], "EIF": counts["EIF"]})
    parts = {k: found[k] * w for k, w in d.AVERAGE_FP_WEIGHTS.items()}
    ufp2 = sum(parts.values())
    return {
        "uaw": uaw, "cases": cases, "uucw": uucw, "uucp": uucp, "tfactor": tfactor, "tcf": tcf,
        "efactor": efactor, "ef": ef, "ucp": ucp, "hours": hours,
        "effort_pm": hours / d.HOURS_PER_MONTH,
        "method2": {"counts": found, "parts": parts, "ufp": ufp2, "vaf": vaf, "afp": ufp2 * vaf},
    }


# ------------------------------------------------------------------ діаграми
def dot(source: str, png: Path) -> None:
    subprocess.run(["dot", "-Tpng", "-Gdpi=200", "-o", str(png)],
                   input=source, text=True, check=True)


def use_case_diagram(cases: list) -> None:
    lines = ['digraph G { rankdir=LR; graph [fontname="Helvetica", nodesep=0.12, ranksep=1.1];',
             'node [fontname="Helvetica", fontsize=11]; edge [arrowhead=none, color="#555555"];',
             'subgraph cluster_sys { label="Visitera"; fontsize=14; style=rounded;',
             'color="#777777";',
             'node [shape=ellipse, style=filled, fillcolor="#e8f0fb"];']
    lines += [f'uc{i} [label="{c["name"]}"];' for i, c in enumerate(cases)]
    lines.append("}")
    actor_ids = {}
    for i, (name, _, _, _) in enumerate(d.ACTORS):
        actor_ids[name] = f"a{i}"
        fill = "#fde0c5" if i < 2 else "#d9f0d3"
        lines.append(f'a{i} [label="{name}", shape=box, style="rounded,filled", '
                     f'fillcolor="{fill}"];')
    for i, c in enumerate(cases):
        lines.append(f'{actor_ids[c["actor"]]} -> uc{i};')
    lines.append('a2 -> uc4; a3 -> uc4;')
    lines.append("}")
    dot("\n".join(lines), RESULTS / "use_cases.png")


def activity_diagram() -> None:
    """Діяльність «Записатися на послугу» з позначенням функцій FPA."""
    source = """digraph A { graph [fontname="Helvetica", nodesep=0.3, ranksep=0.28];
node [fontname="Helvetica", fontsize=11, shape=box, style="rounded,filled", fillcolor="#e8f0fb"];
edge [color="#555555", fontname="Helvetica", fontsize=10];
start [shape=circle, label="", width=0.25, fillcolor="black"];
end [shape=doublecircle, label="", width=0.2, fillcolor="black"];
s1 [label="Відкрити сторінку майстра\\n[EQ: публічна сторінка]"];
s2 [label="Обрати послугу і дату"];
s3 [label="Розрахувати вільні слоти\\n[EO: слоти; ILF: розклад, записи, послуги]"];
s4 [label="Обрати час, ввести ім'я, телефон, e-mail"];
d1 [shape=diamond, label="Дані\\nкоректні?", fillcolor="#fff2cc"];
s5 [label="Створити запис\\n[EI: онлайн-запис; ILF: записи, клієнти]"];
d2 [shape=diamond, label="Час ще\\nвільний?", fillcolor="#fff2cc"];
s6 [label="Поставити листи в чергу\\n[ILF: сповіщення]"];
s7 [label="Показати підтвердження"];
s8 [label="Надіслати лист клієнту і майстру\\n[EO: листи]", fillcolor="#d9f0d3"];
start -> s1 -> s2 -> s3 -> s4 -> d1;
d1:w -> s4:w [label=" ні"]; d1 -> s5 [label=" так"];
s5 -> d2; d2 -> s3 [label=" ні"]; d2 -> s6 [label=" так"];
s6 -> s7 -> end; s6 -> s8 [style=dashed];
}"""
    dot(source, RESULTS / "activity_booking.png")


def plot_methods(rows: list) -> None:
    fig, axis = plt.subplots(figsize=(9, 3.9))
    names = [r["method"] for r in rows][::-1]
    values = [r["effort_pm"] for r in rows][::-1]
    bars = axis.barh(names, values, color="#4c72b0")
    axis.bar_label(bars, labels=[comma(v, 1) for v in values], padding=4)
    axis.set_xlabel("Трудомісткість, людино-місяців")
    axis.set_xlim(0, max(values) * 1.15)
    axis.xaxis.set_major_formatter(FuncFormatter(lambda v, _: comma(v, 0)))
    axis.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS / "methods_effort.png", dpi=200)
    plt.close(fig)


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    fpa = json.loads((PR3 / "fpa_summary.json").read_text())
    pr2 = json.loads((PR2 / "cocomo.json").read_text())
    counts, vaf, gearing = fpa["counts"], fpa["vaf"], fpa["actual_gearing"]
    salary = pr2["salary_uah"]["Middle"]

    fep = feature_points(counts, vaf)
    op = object_points()
    ucp = use_case_points(counts, vaf)

    def by_size(method: str, size: float, unit: str) -> dict:
        effort, schedule = cocomo(size * gearing / 1000)
        return {"method": method, "size": size, "unit": unit, "effort_pm": effort,
                "schedule_m": schedule, "cost_uah": effort * salary}

    loc = pr2["by_type"][1]
    rows = [
        {"method": "LOC + COCOMO (ПР2)", "size": loc["kloc"] * 1000, "unit": "SLOC",
         "effort_pm": loc["effort_pm"], "schedule_m": loc["schedule_m"],
         "cost_uah": loc["cost_uah"]},
        by_size("Function points (ПР3)", fpa["afp"], "AFP"),
        by_size("Feature points", fep["adjusted"], "AFeP"),
        by_size("Use-case points, метод 2", ucp["method2"]["afp"], "AFP"),
        {"method": "Use-case points, метод 1", "size": ucp["ucp"], "unit": "UCP",
         "effort_pm": ucp["effort_pm"], "schedule_m": None, "cost_uah": ucp["effort_pm"] * salary},
        {"method": "Object points", "size": op["op_new"], "unit": "NOP",
         "effort_pm": op["effort_pm"], "schedule_m": None, "cost_uah": op["effort_pm"] * salary},
    ]
    summary = {"feature": fep, "object": op, "use_case": ucp, "comparison": rows,
               "gearing": gearing, "salary_uah": salary,
               "algorithms": [{"name": n, "where": w, "what": x} for n, w, x in d.ALGORITHMS]}
    (RESULTS / "points.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    lines = [f"Feature points: UFeP = {fep['unadjusted']}, AFeP = {comma(fep['adjusted'])} "
             f"(алгоритмів {len(d.ALGORITHMS)})",
             f"Object points: OP = {op['op']}, OPnew = {comma(op['op_new'])}, "
             f"E = {comma(op['effort_pm'])} л.-міс (PROD = {op['prod']})",
             f"Use-case points: UAW = {ucp['uaw']}, UUCW = {ucp['uucw']}, UUCP = {ucp['uucp']}, "
             f"TCF = {comma(ucp['tcf'], 3)}, EF = {comma(ucp['ef'], 3)}, "
             f"UCP = {comma(ucp['ucp'])}, "
             f"{comma(ucp['hours'], 0)} год = {comma(ucp['effort_pm'])} л.-міс",
             f"Метод 2: {ucp['method2']['counts']} UFP = {ucp['method2']['ufp']}, "
             f"AFP = {comma(ucp['method2']['afp'])}", ""]
    for r in rows:
        lines.append(f"{r['method']:26} {comma(r['size'], 1):>9} {r['unit']:5} "
                     f"Effort {comma(r['effort_pm']):>7}  Cost {comma(r['cost_uah'], 0):>12} грн")
    text = "\n".join(lines)
    (RESULTS / "points.txt").write_text(text + "\n")
    print(text)

    use_case_diagram(ucp["cases"])
    activity_diagram()
    plot_methods(rows)


if __name__ == "__main__":
    main()

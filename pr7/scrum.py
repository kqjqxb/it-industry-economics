"""Економічні показники Product Backlog Visitera, оціненого методом Bucket System.

Швидкість команди: V = розробники · дні спринту · фокус-фактор (SP за спринт).
Вартість SP = місячний фонд оплати праці / (розробники · робочі дні місяця · фокус-фактор).

Запуск: python scrum.py (потрібні результати ../pr2/results)
"""
import csv
import json
import math
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

import backlog as b

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
PR2 = ROOT.parent / "pr2" / "results"
EPIC_ORDER = ("E1", "E2", "E3", "E4", "E5", "E6", "E7")


def comma(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")


def scenario(total_sp: int, epic_sp: dict, developers: int, focus: float, salary: float) -> dict:
    velocity = developers * b.SPRINT_DAYS * focus
    sprints = math.ceil(total_sp / velocity)
    payroll = developers * salary
    cost_per_sp = payroll / (developers * b.WORKING_DAYS_PER_MONTH * focus)
    # Реліз за епіками у порядку пріоритету: накопичені SP, номер спринту завершення, вартість.
    releases, done = [], 0
    for epic in EPIC_ORDER:
        done += epic_sp[epic]
        releases.append({"epic": epic, "cumulative_sp": done, "sprint": math.ceil(done / velocity),
                         "cost": done * cost_per_sp})
    return {"developers": developers, "focus": focus, "velocity": velocity, "sprints": sprints,
            "weeks": sprints * b.SPRINT_DAYS / 5, "months": sprints * b.SPRINT_DAYS
            / b.WORKING_DAYS_PER_MONTH, "payroll": payroll, "cost_per_sp": cost_per_sp,
            "cost": total_sp * cost_per_sp, "cost_per_sprint": velocity * cost_per_sp,
            "releases": releases}


def plot_epics(epic_sp: dict, cost_per_sp: float) -> None:
    labels = [f"{e}. {b.EPICS[e]}" for e in EPIC_ORDER][::-1]
    values = [epic_sp[e] for e in EPIC_ORDER][::-1]
    fig, axis = plt.subplots(figsize=(9, 3.8))
    bars = axis.barh(labels, values, color="#4c72b0")
    labels_text = [f"{v} SP · {comma(v * cost_per_sp / 1000, 0)} тис. грн" for v in values]
    axis.bar_label(bars, labels=labels_text, padding=4, fontsize=8)
    axis.set_xlabel("Story points")
    axis.set_xlim(0, max(values) * 1.6)
    axis.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS / "epics.png", dpi=200)
    plt.close(fig)


def plot_burndown(total_sp: int, scenarios: dict) -> None:
    fig, axis = plt.subplots(figsize=(9, 4))
    for name, s in scenarios.items():
        xs = list(range(s["sprints"] + 1))
        axis.plot(xs, [max(total_sp - s["velocity"] * x, 0) for x in xs], marker="o", markersize=3,
                  label=f"{name} (V = {comma(s['velocity'], 0)} SP)")
    axis.set_xlabel("Спринт (2 тижні)")
    axis.set_ylabel("Залишок беклогу, SP")
    axis.grid(alpha=0.3)
    axis.legend()
    fig.tight_layout()
    fig.savefig(RESULTS / "burndown.png", dpi=200)
    plt.close(fig)


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    salary = json.loads((PR2 / "cocomo.json").read_text())["salary_uah"]["Middle"]
    assert all(sp in b.BUCKETS for *_, sp, _ in b.STORIES), "історія поза кошиками"
    total = sum(sp for *_, sp, _ in b.STORIES)
    epic_sp = {e: sum(sp for _, ep, _, sp, _ in b.STORIES if ep == e) for e in EPIC_ORDER}
    buckets = Counter(sp for *_, sp, _ in b.STORIES)
    scenarios = {name: scenario(total, epic_sp, p["developers"], p["focus"], salary)
                 for name, p in b.SCENARIOS.items()}

    summary = {"total_sp": total, "stories": len(b.STORIES), "epic_sp": epic_sp,
               "buckets": {str(k): buckets.get(k, 0) for k in b.BUCKETS}, "salary": salary,
               "scenarios": scenarios}
    (RESULTS / "scrum.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    with open(RESULTS / "product_backlog.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "epic", "priority", "story", "sp", "reason"])
        for sid, epic, story, sp, why in b.STORIES:
            writer.writerow([sid, epic, b.EPIC_PRIORITY[epic], story, sp, why])

    solo = scenarios["Команда з однієї особи"]
    lines = [f"Історій {len(b.STORIES)}, разом {total} SP; кошики {dict(buckets)}",
             "SP за епіками: " + ", ".join(f"{e} {epic_sp[e]}" for e in EPIC_ORDER), ""]
    for name, s in scenarios.items():
        lines.append(f"{name}: V {comma(s['velocity'], 1)} SP/спринт, {s['sprints']} спринтів "
                     f"({comma(s['months'], 1)} міс), {comma(s['cost_per_sp'], 0)} грн/SP, "
                     f"разом {comma(s['cost'], 0)} грн")
    text = "\n".join(lines)
    (RESULTS / "scrum.txt").write_text(text + "\n")
    print(text)
    plot_epics(epic_sp, solo["cost_per_sp"])
    plot_burndown(total, scenarios)


if __name__ == "__main__":
    main()

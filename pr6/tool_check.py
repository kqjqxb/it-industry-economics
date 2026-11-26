"""Звірка детальної оцінки COCOMO II з онлайн-калькулятором COCOMO II (R. Madachy, той самий
інструмент, що й на сайті USC CSSE) і знімок сторінки з результатом.

Запуск: python tool_check.py <каталог для збереженої сторінки>
"""
import html
import json
import re
import subprocess
import sys
from pathlib import Path

import cocomo_data as cd

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
URL = "https://softwarecost.org/tools/COCOMO/"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FORM_LEVELS = ("Very_Low", "Low", "Nominal", "High", "Very_High", "Extra_High")
FORM_KEYS = {"AEXP": "apex"}  # у формі калькулятора AEXP називається APEX


def request(kloc: float, scale: dict, post: dict, salary: float) -> str:
    fields = {"startCOCOMO": "1", "MonteCarlo": "MonteCarlo_Off", "AutoCalculate": "Off",
              "size_type": "SLOC", "new_size": str(round(kloc * 1000)),
              "software_labor_cost_per_PM": str(round(salary)), "software_maintenance": "Off",
              "submit2": "Calculate"}
    fields.update({k.lower(): FORM_LEVELS[i] for k, (i, _) in scale.items()})
    fields.update({FORM_KEYS.get(k, k.lower()): FORM_LEVELS[i] for k, (i, _) in post.items()})
    args = [arg for k, v in fields.items() for arg in ("--data-urlencode", f"{k}={v}")]
    return subprocess.run(["curl", "-s", "-m", "60", "-X", "POST", URL, *args],
                          capture_output=True, text=True, errors="replace", check=True).stdout


def parse(page: str) -> dict:
    text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page)))
    return {"pm": float(re.search(r"Effort = ([\d.]+)", text).group(1)),
            "tm": float(re.search(r"Schedule = ([\d.]+)", text).group(1)),
            "eaf": float(re.search(r"\(EAF\) = ([\d.]+)", text).group(1))}


def main() -> None:
    out = Path(sys.argv[1]).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    summary = json.loads((RESULTS / "cocomo_models.json").read_text())
    nominal = {k: (2, "") for k in cd.SCALE_FACTORS}
    novelty_scale = {**nominal, "PREC": (0, "")}
    nominal_post = {k: (2, "") for k in cd.POST}
    cases = {
        "visitera": (summary["kloc"], cd.SCALE_RATINGS, cd.POST_RATINGS),
        "novelty": (cd.NOVELTY_SIZE_KSLOC, novelty_scale, nominal_post),
    }
    results = {}
    for name, (kloc, scale, post) in cases.items():
        page = request(kloc, scale, post, summary["salary"])
        results[name] = parse(page)
        (out / f"{name}.html").write_text(page.replace("<head>", f'<head><base href="{URL}">', 1),
                                          encoding="utf-8")
    # Окремо: значення RUSE = Low у калькуляторі (за інших номінальних параметрів).
    base = parse(request(100, nominal, nominal_post, 0))["pm"]
    ruse = parse(request(100, nominal, {**nominal_post, "RUSE": (1, "")}, 0))["pm"]
    results["ruse_low_in_tool"] = round(ruse / base, 3)
    (RESULTS / "tool_check.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(results)

    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--window-size=1100,1190", f"--screenshot={RESULTS / 'tool_visitera.png'}",
                    (out / "visitera.html").as_uri()], check=True, capture_output=True)


if __name__ == "__main__":
    main()

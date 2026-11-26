"""Збір бази проєктів для оцінки за аналогією з публічних репозиторіїв GitHub.

Для кожного репозиторію (клон без вмісту історії, лише останній стан файлів):
- атрибути: тривалість розробки (місяці), кількість розробників, кількість комітів, кількість
  релізів (тегів);
- розмір: рядки коду (cloc, без порожніх рядків, коментарів, залежностей і збірок);
- мова: мова з найбільшою кількістю рядків коду серед мов програмування;
- зусилля: активні розробнико-місяці – кількість пар (розробник, календарний місяць), у яких
  розробник зробив хоча б один коміт.
Коміти ботів (dependabot, renovate тощо) не враховуються; записи одного автора з різними іменами
чи адресами (наприклад, особиста пошта і службова адреса GitHub) об'єднуються.

Запуск: python collect.py <каталог для клонів>
"""
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from projects import PROJECTS

RESULTS = Path(__file__).parent / "results"
BOT_MARKERS = ("[bot]", "dependabot", "renovate", "github-actions", "weblate", "crowdin",
               "allcontributors", "semantic-release", "greenkeeper", "snyk")
NON_CODE = ("JSON", "Markdown", "YAML", "XML", "SVG", "Text", "CSV", "TOML", "INI", "diff",
            "reStructuredText", "AsciiDoc", "Properties", "Dockerfile", "make", "Bourne Shell")
EXCLUDE_DIRS = ("node_modules,vendor,dist,build,.next,public,static,assets,locales,lang,i18n,"
                "migrations,generated")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=True).stdout


def clone(url: str, target: Path) -> None:
    if not target.exists():
        subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", url, str(target)],
                       check=True)


def identity_tokens(name: str, email: str) -> set[str]:
    """Ознаки, за якими різні записи автора належать одній людині."""
    email = email.lower()
    local = email.split("@")[0]
    tokens = {email, "".join(name.lower().split())}
    if email.endswith("@users.noreply.github.com"):
        tokens.add(local.split("+")[-1])  # логін GitHub
    else:
        tokens.add(local)
    return {t for t in tokens if len(t) > 2}


def merge_authors(authors: set[tuple[str, str]]) -> dict[tuple[str, str], int]:
    """Об'єднує записи (ім'я, e-mail) зі спільними ознаками в одного розробника."""
    parent = {a: a for a in authors}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    owner: dict[str, tuple[str, str]] = {}
    for author in sorted(authors):
        for token in identity_tokens(*author):
            if token in owner:
                parent[find(author)] = find(owner[token])
            else:
                owner[token] = author
    roots = sorted({find(a) for a in authors})
    return {a: roots.index(find(a)) for a in authors}


def history(repo: Path) -> dict:
    log = git(repo, "log", "--no-merges", "--format=%aN%x09%aE%x09%at")
    raw = []
    for line in log.splitlines():
        name, email, stamp = line.split("\t")
        who = f"{name} {email}".lower()
        if any(marker in who for marker in BOT_MARKERS):
            continue
        raw.append((name, email, int(stamp)))
    person = merge_authors({(n, e) for n, e, _ in raw})
    commits = [(person[(n, e)], t) for n, e, t in raw]
    times = sorted(t for _, t in commits)
    months = {(a, datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m")) for a, t in commits}
    return {
        "commits": len(commits),
        "developers": len({a for a, _ in commits}),
        "duration_months": round((times[-1] - times[0]) / 86400 / 30.44, 1),
        "tags": len(git(repo, "tag").split()),
        "effort_pm": len(months),
        "first": datetime.fromtimestamp(times[0], timezone.utc).strftime("%Y-%m-%d"),
        "last": datetime.fromtimestamp(times[-1], timezone.utc).strftime("%Y-%m-%d"),
    }


def size(repo: Path) -> tuple[int, str, dict]:
    out = subprocess.run(["cloc", "--json", "--quiet", f"--exclude-dir={EXCLUDE_DIRS}",
                          "--exclude-ext=min.js,min.css,map", str(repo)],
                         capture_output=True, text=True, check=True, timeout=300).stdout
    data = json.loads(out)
    langs = {k: v["code"] for k, v in data.items()
             if k not in ("header", "SUM") and k not in NON_CODE}
    main_lang = max(langs, key=langs.get)
    return sum(langs.values()), main_lang, langs


def main() -> None:
    clones = Path(sys.argv[1]).expanduser().resolve()
    clones.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    rows = []
    for key, url, description in PROJECTS:
        target = clones / url.rstrip("/").split("/")[-2] / url.rstrip("/").split("/")[-1]
        target.parent.mkdir(exist_ok=True)
        clone(url, target)
        h = history(target)
        loc, lang, langs = size(target)
        rows.append({"project": key, "url": url, "description": description, **h,
                     "language": lang, "size_loc": loc,
                     "languages": ", ".join(f"{k} {v}" for k, v in
                                            sorted(langs.items(), key=lambda kv: -kv[1])[:3])})
        print(f"{key:24} {lang:12} LOC {loc:7}  months {h['duration_months']:5}  "
              f"devs {h['developers']:3}  commits {h['commits']:5}  tags {h['tags']:3}  "
              f"effort {h['effort_pm']:4}")
    with open(RESULTS / "database_raw.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()

"""Вимірювання розміру програмного продукту метрикою LOC.

Файли репозиторію (лише ті, що під контролем git) розкладаються на категорії,
кожна категорія вимірюється утилітою cloc, а продуктовий код додатково –
утилітою scc для перехресної перевірки.

Запуск: python measure_loc.py <шлях до репозиторію Visitera>
"""
import json
import subprocess
import sys
import tempfile
from fnmatch import fnmatch
from pathlib import Path

RESULTS = Path(__file__).parent / "results"

# Порядок важливий: файл потрапляє до першої категорії, шаблон якої збігся.
CATEGORIES = [
    ("generated", "Згенерований код (типи БД)", ["src/lib/supabase/database.types.ts"]),
    ("tests", "Автоматичні тести", ["*.test.ts", "*.test.tsx", "e2e/*", "playwright.config.ts",
                                     "vitest.config.mts", "vitest.db.config.mts"]),
    ("tools", "Службові скрипти та демо-дані", ["scripts/*", "supabase/seed.sql"]),
    ("config", "Конфігурація збирання",
     ["next.config.ts", "postcss.config.mjs", "eslint.config.mjs"]),
    ("product", "Продуктовий код", ["src/*.ts", "src/*.tsx", "src/*.css", "emails/*.tsx",
                                     "supabase/migrations/*.sql", "supabase/templates/*.html"]),
]
TOTAL_KEYS = ("nFiles", "blank", "comment", "code")


def git_files(repo: Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(repo), "ls-files"],
                         capture_output=True, text=True, check=True)
    return out.stdout.split()


def classify(files: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {key: [] for key, _, _ in CATEGORIES}
    groups["excluded"] = []
    for name in files:
        for key, _, patterns in CATEGORIES:
            if any(fnmatch(name, pattern) for pattern in patterns):
                groups[key].append(name)
                break
        else:
            groups["excluded"].append(name)
    return groups


def cloc(repo: Path, files: list[str]) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as listing:
        listing.write("\n".join(str(repo / name) for name in files))
    out = subprocess.run(["cloc", "--json", "--quiet", f"--list-file={listing.name}"],
                         capture_output=True, text=True, check=True)
    Path(listing.name).unlink()
    data = json.loads(out.stdout)
    data.pop("header", None)
    return data


def cloc_text(repo: Path, files: list[str]) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as listing:
        listing.write("\n".join(str(repo / name) for name in files))
    out = subprocess.run(["cloc", "--quiet", "--hide-rate", f"--list-file={listing.name}"],
                         capture_output=True, text=True, check=True)
    Path(listing.name).unlink()
    return out.stdout.replace(str(repo) + "/", "")


def scc_text(repo: Path, files: list[str]) -> str:
    out = subprocess.run(["scc", "--no-cocomo", "--no-size", *files],
                         cwd=repo, capture_output=True, text=True, check=True)
    return out.stdout


def main() -> None:
    repo = Path(sys.argv[1]).expanduser().resolve()
    RESULTS.mkdir(exist_ok=True)
    groups = classify(git_files(repo))

    summary = {"categories": {}, "excluded_files": len(groups["excluded"])}
    for key, title, _ in CATEGORIES:
        stats = cloc(repo, groups[key])
        summary["categories"][key] = {
            "title": title,
            "languages": {lang: {k: v[k] for k in TOTAL_KEYS}
                          for lang, v in stats.items() if lang != "SUM"},
            "total": {k: stats["SUM"][k] for k in TOTAL_KEYS},
        }

    # Окремо – компоненти інтерфейсу на основі shadcn/ui (згенеровані й доопрацьовані).
    ui_files = [f for f in groups["product"] if f.startswith("src/components/ui/")]
    summary["ui_components"] = cloc(repo, ui_files)["SUM"]["code"]

    (RESULTS / "loc_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    (RESULTS / "cloc_product.txt").write_text(cloc_text(repo, groups["product"]))
    (RESULTS / "cloc_all_own.txt").write_text(
        cloc_text(repo, [f for key, _, _ in CATEGORIES if key != "generated" for f in groups[key]]))
    (RESULTS / "scc_product.txt").write_text(scc_text(repo, groups["product"]))

    for key, title, _ in CATEGORIES:
        total = summary["categories"][key]["total"]
        print(f"{title:32} файлів {total['nFiles']:4}  коду {total['code']:6}  "
              f"коментарів {total['comment']:5}  порожніх {total['blank']:5}")
    print("Не вимірювались (документація, ресурси, lock-файли):",
          summary["excluded_files"], "файлів")
    print("З них компоненти src/components/ui:", summary["ui_components"], "рядків коду")


if __name__ == "__main__":
    main()

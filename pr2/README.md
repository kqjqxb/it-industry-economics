# Практична робота №2. Метрики розміру. Метрика Lines of Code

Об'єкт вимірювання – власний вебзастосунок Visitera (Next.js + TypeScript, PostgreSQL у Supabase).

| Файл | Призначення |
|------|-------------|
| `measure_loc.py` | Розкладає файли репозиторію Visitera на категорії, вимірює кожну cloc, продуктовий код – ще й scc |
| `cocomo.py` | Трудомісткість, вартість і тривалість за базовою моделлю COCOMO для трьох типів проєктів, графіки |
| `lang_levels.py` | Вимірювання трьох еквівалентних реалізацій модуля і розрахунок рівнів мов |
| `lang_levels/run_all.sh` | Збирає й запускає реалізації TypeScript, Java і C#, перевіряє збіг результатів |
| `lang_levels/scenarios.txt` | Спільні тестові сценарії (зокрема переходи на літній і зимовий час) |
| `lang_levels/ts/main.ts` | Тестовий драйвер для оригінального модуля Visitera (`src/lib/availability`, закритий репозиторій – підключається під час запуску) |
| `lang_levels/java/`, `lang_levels/csharp/` | Той самий модуль на Java і C# |
| `results/` | Виміри cloc/scc, результати COCOMO, рівні мов, графіки |
| `ІП-33_Ломакін_ПР2.pdf` | Звіт |

## Запуск

Потрібні cloc і scc (`brew install cloc scc`), Python з matplotlib, для `run_all.sh` – Node.js з TypeScript, JDK і .NET SDK.

```
python measure_loc.py <шлях до репозиторію Visitera>
python cocomo.py
lang_levels/run_all.sh <шлях до репозиторію Visitera>
python lang_levels.py <шлях до репозиторію Visitera>
```

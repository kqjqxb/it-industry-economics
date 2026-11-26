#!/bin/sh
# Збирає і запускає три реалізації розрахунку слотів (TypeScript, Java, C#) на спільних
# сценаріях і перевіряє, що результати збігаються рядок у рядок.
# Оригінальний модуль TypeScript береться з репозиторію Visitera (src/lib/availability).
# Запуск: run_all.sh <шлях до репозиторію Visitera>
# Потрібні: Node.js + TypeScript (змінна TSC, за замовчуванням tsc), JDK, .NET SDK.
set -e
VISITERA=$(cd "$1" && pwd)
cd "$(dirname "$0")"
BUILD=${BUILD:-$(mktemp -d)}
OUT=../results
TSC=${TSC:-tsc}

mkdir -p "$BUILD/ts-src"
cp "$VISITERA"/src/lib/availability/intervals.ts "$VISITERA"/src/lib/availability/zoned.ts \
  "$VISITERA"/src/lib/availability/slots.ts ts/main.ts "$BUILD/ts-src/"

"$TSC" --outDir "$BUILD/ts" --module commonjs --target es2022 --strict --skipLibCheck \
  --types node ${TS_TYPE_ROOTS:+--typeRoots "$TS_TYPE_ROOTS"} "$BUILD/ts-src/main.ts"
node "$BUILD/ts/main.js" scenarios.txt > "$OUT/slots_ts.txt"

javac -d "$BUILD/java" java/*.java
java -cp "$BUILD/java" Main scenarios.txt > "$OUT/slots_java.txt"

dotnet build csharp -c Release --nologo -v quiet --artifacts-path "$BUILD/cs" > /dev/null
dotnet "$BUILD/cs/bin/Availability/release/Availability.dll" scenarios.txt > "$OUT/slots_csharp.txt"

diff "$OUT/slots_ts.txt" "$OUT/slots_java.txt"
diff "$OUT/slots_ts.txt" "$OUT/slots_csharp.txt"
echo "Результати трьох реалізацій збігаються:"
grep -v '^ ' "$OUT/slots_ts.txt"

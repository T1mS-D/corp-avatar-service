#!/usr/bin/env bash
# Пример полного цикла: загрузить фото → дождаться → скачать результат.
# Использование: ./scripts/demo_request.sh photo.jpg corporate
set -euo pipefail
PHOTO="${1:?Укажите путь к фото}"
STYLE="${2:-corporate}"
HOST="${HOST:-http://localhost:8000}"
KEY="${API_KEY:?Задайте API_KEY в переменных окружения (значение из .env)}"

JOB=$(curl -sf -X POST "$HOST/api/v1/avatars/upload" \
  -H "X-API-Key: $KEY" -F "file=@${PHOTO}" -F "style=${STYLE}" | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "Задание создано: $JOB"

for i in $(seq 1 60); do
  STATUS=$(curl -sf "$HOST/api/v1/avatars/$JOB" -H "X-API-Key: $KEY")
  STATE=$(echo "$STATUS" | python3 -c "import sys,json;print(json.load(sys.stdin)['status'])")
  echo "  [$i] статус: $STATE"
  [[ "$STATE" != "queued" && "$STATE" != "processing" ]] && break
  sleep 2
done

echo "$STATUS" | python3 -m json.tool
if [[ "$STATE" == "done" ]]; then
  OUT="avatar_${JOB}.png"
  curl -sf "$HOST/api/v1/avatars/$JOB/image" -H "X-API-Key: $KEY" -o "$OUT"
  echo "Готово: $OUT"
fi

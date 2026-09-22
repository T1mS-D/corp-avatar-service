# API

Базовый путь: `/api/v1`. Авторизация: заголовок `X-API-Key: <значение из .env>` (кроме `/health`).
Интерактивная документация: `http://<host>:8000/docs` (Swagger UI, там же можно отправить файл через форму).

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/health` | Проверка живости (без авторизации), для docker healthcheck |
| GET | `/api/v1/styles` | Список доступных стилей (`id`, `title`, `description`) |
| POST | `/api/v1/avatars` | Создать задание. JSON: `image_base64`, `style`, `employee_ref?`, `seed?` → `202` + задание |
| POST | `/api/v1/avatars/upload` | То же самое, но `multipart/form-data` (`file`, `style`, `employee_ref`) — удобно для curl/Swagger |
| GET | `/api/v1/avatars` | Список заданий (`?employee_ref=...&limit=...`) |
| GET | `/api/v1/avatars/{id}` | Статус и метрики одного задания |
| GET | `/api/v1/avatars/{id}/image` | Готовый PNG (только когда `status = done`; `409` иначе) |
| DELETE | `/api/v1/avatars/{id}` | Удалить задание и файлы (фото — персональные данные) |

## Статусы задания

`queued → processing → done | rejected | failed`

- `rejected` — исходное фото не подходит (нет лица, несколько лиц, размыто, сильный поворот
  головы, лицо слишком мелкое). Текст причины — в поле `error`, читаем и годится для показа
  в 1С без перевода.
- `failed` — фото было пригодно, генерация прошла, но результат не прошёл проверку сохранности
  лица (ArcFace-сходство ниже порога после всех попыток), либо внутренняя ошибка обработки.
- `done` — есть PNG и `metrics.similarity ≥ metrics.threshold`.

## Пример: curl

```bash
# список стилей
curl -s http://localhost:8000/api/v1/styles -H "X-API-Key: $API_KEY" | jq

# создать задание (multipart — не нужно вручную кодировать base64)
JOB=$(curl -s -X POST http://localhost:8000/api/v1/avatars/upload \
  -H "X-API-Key: $API_KEY" -F "file=@photo.jpg" -F "style=corporate" | jq -r .id)

# опрос статуса
curl -s http://localhost:8000/api/v1/avatars/$JOB -H "X-API-Key: $API_KEY" | jq

# скачать результат
curl -s http://localhost:8000/api/v1/avatars/$JOB/image -H "X-API-Key: $API_KEY" -o avatar.png
```

## Метрики в ответе

```json
{
  "input_face_px": 178, "input_det_score": 0.837, "input_yaw": 0.6, "input_sharpness": 183.1,
  "face_found": true, "similarity": 0.9913, "threshold": 0.55, "passed": true,
  "backend": "classic", "seconds": 2.4
}
```

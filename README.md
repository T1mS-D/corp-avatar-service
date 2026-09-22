# Corporate Avatar Service

Сервис автоматической генерации корпоративных аватаров сотрудников по фото:
светлый/фирменный фон, деловая одежда, лицо не искажается. Опционально — мульт-аватар.
Работает как отдельный HTTP-сервис и интегрируется с **1С:УНФ** через расширение
(`onec/extension`).

Статус: **Спринт 1** — рабочий сквозной сервис (API + очередь + воркер + PostgreSQL +
2 бэкенда обработки + интеграция с 1С), см. «Известные ограничения» ниже.

## Структура репозитория

```
app/
  main.py            — FastAPI приложение (health, роуты)
  worker.py           — воркер очереди (poll PostgreSQL, запускает пайплайн)
  config.py            — настройки (pydantic-settings, из .env)
  db.py, models.py, schemas.py — SQLAlchemy 2.x модель + Pydantic-схемы API
  storage.py, security.py     — файлы на диске, авторизация по X-API-Key
  api/routes.py        — REST-эндпоинты (см. docs/api.md)
  pipeline/
    base.py            — интерфейс AvatarPipeline + PipelineResult
    classic.py         — CPU-бэкенд: кадрирование + замена фона (без генеративных моделей)
    diffusion.py        — GPU-бэкенд: + замена одежды (SD inpainting) + IP-Adapter FaceID + мульт-стиль
    faces.py            — InsightFace: детекция, поза, ArcFace-эмбеддинг
    segmentation.py      — rembg/u2net: маска человека, композит с фоном
    background.py        — генерация фонов (градиент / цвет бренда / шаблон из assets)
    verify.py            — проверки входа (лицо есть/одно/чёткое/анфас) и выхода (сходство лиц)
    preprocess.py        — EXIF, кадрирование «голова+плечи»
    styles.py            — реестр стилей (добавление стиля = запись в словаре)
tests/                — pytest: API, очередь/воркер (без моделей, быстро),
                        e2e и diffusion-логика на реальных/подменённых моделях (RUN_SLOW=1)
onec/extension/        — исходники расширения 1С:УНФ (BSL) + отдельный README с шагами подключения
assets/backgrounds/    — сюда кладутся фирменные PNG-подложки по имени стиля (опционально)
docs/                  — architecture.md, api.md, models.md
scripts/               — demo_request.sh (полный цикл через curl), wait_for_db.sh
Dockerfile, docker-compose.yml, docker-compose.gpu.yml, .env.example
```

Подробности архитектуры и почему так — `docs/architecture.md`. Формат API — `docs/api.md`.
Список используемых open-source моделей и лицензионные оговорки — `docs/models.md`.

## Как запустить

### Вариант A — демо-режим без GPU (быстрее всего, 5 минут)

Работает сразу «из коробки»: заменяет фон на фирменный, лицо не трогает. Замена одежды и
мульт-аватар в этом режиме недоступны (для этого нужен GPU-бэкенд, вариант Б).

```bash
git clone <repo_url> && cd corp-avatar
cp .env.example .env
# откройте .env и задайте свои POSTGRES_PASSWORD и API_KEY (openssl rand -hex 32)
docker compose up -d --build
curl http://localhost:8000/health          # {"status":"ok","backend":"classic"}
open http://localhost:8000/docs            # Swagger UI — можно сразу отправить фото
```

Полный цикл через curl:

```bash
export API_KEY=<значение из .env>
./scripts/demo_request.sh path/to/photo.jpg corporate
```

### Вариант Б — с заменой одежды и мульт-аватаром (нужен GPU NVIDIA)

```bash
cp .env.example .env
# в .env: PIPELINE_BACKEND=diffusion
# первый запуск воркера скачает веса SD 1.5 + IP-Adapter (~7 ГБ) — см. docs/models.md
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

Требуется установленный `nvidia-container-toolkit` на хосте.

### Локально без Docker (для разработки)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install cython numpy==1.26.4 && pip install --no-build-isolation insightface==0.7.3
pip install -r requirements-core.txt          # или requirements.txt для diffusion-бэкенда
# нужен локальный PostgreSQL с БД/пользователем из .env
uvicorn app.main:app --reload &
python -m app.worker &
```

### Тесты

```bash
pip install -r requirements-core.txt
pytest -q                          # быстрые тесты API и очереди (без моделей), ~1 сек
RUN_SLOW=1 pytest -q               # + сквозные тесты на реальных InsightFace/rembg (скачает веса)
```

## Интеграция с 1С:УНФ

Расширение (BSL-исходники + пошаговая инструкция для Конфигуратора) — в `onec/extension/README.md`.
Коротко: расширение добавляет общий модуль с HTTP-клиентом к этому сервису
(`ИнтернетСоединение`/`HTTPЗапрос`, без внешних компонент) и кнопку «Создать корпоративный
аватар» в карточке сотрудника, которая отправляет фото, дожидается генерации и сохраняет
готовый аватар как присоединённый файл.

## Известные ограничения спринта 1 (честно, для приоритизации спринта 2)

- Лицензия весов InsightFace `buffalo_l` — non-commercial research; для продакшена нужно решение
  по лицензированию/замене весов (подробнее — `docs/models.md`).
- Нет очереди повторной обработки «руками» из 1С при `failed`/`rejected` — сейчас это отдельный
  новый запрос; UI для ретрая — в бэклог.
- Нет админки/дашборда статистики по всем сотрудникам — только REST и таблица в PostgreSQL.
- `classic`-бэкенд не меняет одежду (только фон) — это ограничение отсутствия GPU в демо-режиме,
  не пайплайна; на GPU (`diffusion`) одежда заменяется.
- Диффузионный бэкенд визуально не тестировался на реальном GPU в рамках этой сессии (нет GPU в
  окружении разработки) — логика (маска, сохранение головы побайтно, ретраи) покрыта тестами с
  подменённой моделью (`tests/test_diffusion_logic.py`); рекомендуется прогнать вручную на первом
  же доступном GPU перед демо спринта.
- Аутентификация — общий статический ключ на сервис; ролевая модель/токены на пользователя — вне
  рамок спринта 1.

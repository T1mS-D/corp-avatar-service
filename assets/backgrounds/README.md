# Фирменные фоны (опционально)

Эта папка пуста по умолчанию — фон генерируется программно (градиент из цветов
`BRAND_PRIMARY_COLOR` / `BRAND_SECONDARY_COLOR`, см. `.env`), см. `app/pipeline/background.py`.

## Как подключить готовый фон вместо градиента

Положите сюда квадратное изображение (рекомендуется ≥ 1024×1024, PNG или JPG),
назвав его **точно как id стиля**:

```
assets/backgrounds/corporate.png   → для стиля "corporate"
assets/backgrounds/brand.png       → для стиля "brand"
assets/backgrounds/cartoon.png     → для стиля "cartoon"
```

Если файл существует — сервис использует его вместо программного градиента.
Если файла нет — ничего делать не нужно, всё работает и без него.

Список стилей и их id — в `app/pipeline/styles.py`.

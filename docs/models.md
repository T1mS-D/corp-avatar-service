# Используемые модели (все open source)

| Задача | Модель | Репозиторий | Лицензия весов |
|---|---|---|---|
| Детекция лица, ключевые точки, поза, ArcFace-эмбеддинг | InsightFace `buffalo_l` | github.com/deepinsight/insightface | некоммерческое использование (research); для продакшена уточнить лицензию у DeepInsight или обучить/использовать альтернативный набор весов |
| Сегментация человека (маска для замены фона) | u2net_human_seg (rembg) | github.com/danielgatis/rembg | Apache-2.0 |
| Замена одежды (inpainting) | Stable Diffusion 1.5 Inpainting | huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting | CreativeML Open RAIL-M |
| Сохранение идентичности при генерации | IP-Adapter FaceID | huggingface.co/h94/IP-Adapter-FaceID | Apache-2.0 |
| Мульт-стиль (img2img) | Stable Diffusion 1.5 + опционально LoRA | тот же репозиторий SD 1.5 | CreativeML Open RAIL-M |

Веса скачиваются автоматически при первом запуске воркера (`insightface`/`rembg` — с GitHub,
`diffusers`/`transformers` — с Hugging Face Hub) и кэшируются в томе `/models`, чтобы не
скачивать их при каждом перезапуске контейнера.

**Важно перед продакшен-использованием**: лицензия весов `buffalo_l` у InsightFace помечена как
non-commercial research — для коммерческого использования нужно либо получить отдельное
разрешение, либо переобучить/заменить веса детекции и распознавания лица на модель с
коммерчески чистой лицензией (например, веса, обученные только на CASIA-WebFace/MS1M с явным
разрешением, или полностью самостоятельно обученная ArcFace-модель). Это отмечено как открытый
риск проекта, см. `README.md → Известные ограничения`.

# Один образ для API и воркера (команда задаётся в docker-compose).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    INSIGHTFACE_HOME=/models/insightface \
    U2NET_HOME=/models/u2net \
    HF_HOME=/models/hf \
    STORAGE_DIR=/data

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# insightface собирает Cython-расширение: ему нужны numpy и cython до сборки
RUN pip install cython numpy==1.26.4 setuptools wheel \
    && pip install --no-build-isolation insightface==0.7.3

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app ./app
COPY assets ./assets

RUN mkdir -p /data /models && useradd -m appuser && chown -R appuser /data /models /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fs http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

#!/usr/bin/env bash
# Утилита для CI/локального запуска: ждём готовность Postgres перед стартом API/воркера.
set -e
until pg_isready -h "${POSTGRES_HOST:-localhost}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-avatar}" >/dev/null 2>&1; do
  echo "Ожидание PostgreSQL..."; sleep 1
done

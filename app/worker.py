"""Воркер: забирает задания из PostgreSQL (SELECT ... FOR UPDATE SKIP LOCKED) и запускает пайплайн.
Запуск: python -m app.worker   (можно поднять несколько воркеров — задания не пересекутся)."""
import logging
import signal
import time
from datetime import timedelta

from sqlalchemy import select

from app import storage
from app.config import get_settings
from app.db import init_db, session_scope
from app.models import AvatarJob, JobStatus, utcnow
from app.pipeline import get_pipeline
from app.pipeline.errors import RejectedError

log = logging.getLogger("worker")
_stop = False


def _handle_stop(*_):
    global _stop
    _stop = True


def requeue_stuck(timeout_s: int) -> int:
    """Задания, зависшие в processing (упал воркер), возвращаем в очередь."""
    limit = utcnow() - timedelta(seconds=timeout_s)
    with session_scope() as db:
        stuck = db.scalars(
            select(AvatarJob).where(AvatarJob.status == JobStatus.processing, AvatarJob.started_at < limit)
        ).all()
        for j in stuck:
            j.status = JobStatus.queued if j.attempts < get_settings().max_attempts else JobStatus.failed
            if j.status == JobStatus.failed:
                j.error = "Превышено время обработки"
                j.finished_at = utcnow()
        return len(stuck)


def claim_job() -> str | None:
    """Атомарно берём одно задание. Возвращаем id (объект не тащим между сессиями)."""
    with session_scope() as db:
        job = db.scalars(
            select(AvatarJob)
            .where(AvatarJob.status == JobStatus.queued)
            .order_by(AvatarJob.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        ).first()
        if not job:
            return None
        job.status = JobStatus.processing
        job.started_at = utcnow()
        job.attempts += 1
        return job.id


def process(job_id: str, pipeline) -> None:
    with session_scope() as db:
        job = db.get(AvatarJob, job_id)
        input_path, style, seed = job.input_path, job.style, job.seed
    try:
        result = pipeline.run(input_path, style, seed)
        out_path = storage.output_path(job_id)
        result.image.save(out_path, format="PNG")
        status, error = (JobStatus.done, None) if result.passed else (JobStatus.failed, result.message)
        metrics, out = result.metrics, out_path
    except RejectedError as e:
        status, error, metrics, out = JobStatus.rejected, str(e), None, None
    except Exception as e:  # noqa: BLE001 — любая ошибка модели не должна ронять воркер
        log.exception("Ошибка обработки %s", job_id)
        status, error, metrics, out = JobStatus.failed, f"{type(e).__name__}: {e}", None, None

    with session_scope() as db:
        job = db.get(AvatarJob, job_id)
        job.status, job.error, job.metrics, job.output_path = status, error, metrics, out
        job.finished_at = utcnow()
    log.info("Задание %s → %s %s", job_id, status.value, metrics or error)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    s = get_settings()
    init_db()
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)
    pipeline = get_pipeline(s)
    log.info("Воркер запущен, backend=%s", pipeline.name)
    last_gc = 0.0
    while not _stop:
        if time.time() - last_gc > 60:
            n = requeue_stuck(s.job_timeout_seconds)
            if n:
                log.warning("Возвращено в очередь зависших заданий: %d", n)
            last_gc = time.time()
        job_id = claim_job()
        if job_id is None:
            time.sleep(s.worker_poll_seconds)
            continue
        process(job_id, pipeline)
    log.info("Воркер остановлен")


if __name__ == "__main__":
    main()

"""ORM-модели."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(str, enum.Enum):
    queued = "queued"          # принято, ждёт воркера
    processing = "processing"  # воркер работает
    done = "done"              # аватар готов, проверки пройдены
    rejected = "rejected"      # исходное фото не подходит (нет лица, много лиц, размыто...)
    failed = "failed"          # ошибка или не прошла проверка сохранности лица


class AvatarJob(Base):
    """Задание на генерацию аватара. Одновременно очередь для воркера и история для 1С."""

    __tablename__ = "avatar_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_ref: Mapped[str | None] = mapped_column(String(64), index=True)  # GUID сотрудника в 1С
    style: Mapped[str] = mapped_column(String(32), default="corporate")
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus, name="job_status"), default=JobStatus.queued)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    seed: Mapped[int | None] = mapped_column(Integer)
    input_path: Mapped[str] = mapped_column(String(512))
    output_path: Mapped[str | None] = mapped_column(String(512))
    metrics: Mapped[dict | None] = mapped_column(JSON)   # similarity, sharpness, yaw, backend, время...
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_jobs_status_created", "status", "created_at"),)

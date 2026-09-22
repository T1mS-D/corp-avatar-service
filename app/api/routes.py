from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session
import io

from app import storage
from app.config import get_settings
from app.db import get_db
from app.models import AvatarJob, JobStatus
from app.pipeline.styles import STYLES
from app.schemas import AvatarCreate, AvatarOut, StyleOut
from app.security import require_api_key

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])


def _validate_image(data: bytes) -> None:
    limit = get_settings().max_upload_mb * 1024 * 1024
    if len(data) > limit:
        raise HTTPException(413, f"Файл больше {get_settings().max_upload_mb} МБ")
    try:
        Image.open(io.BytesIO(data)).verify()
    except (UnidentifiedImageError, OSError) as e:
        raise HTTPException(400, "Файл не является изображением (JPEG/PNG)") from e


def _create_job(db: Session, data: bytes, style: str, employee_ref: str | None, seed: int | None) -> AvatarJob:
    if style not in STYLES:
        raise HTTPException(400, f"Неизвестный стиль '{style}'. Доступные: {', '.join(STYLES)}")
    _validate_image(data)
    job = AvatarJob(style=style, employee_ref=employee_ref, seed=seed, input_path="")
    db.add(job)
    db.flush()  # получаем id
    job.input_path = storage.save_input(job.id, data)
    db.commit()
    return job


@router.get("/styles", response_model=list[StyleOut])
def list_styles():
    return [StyleOut(id=s.id, title=s.title, description=s.description) for s in STYLES.values()]


@router.post("/avatars", response_model=AvatarOut, status_code=202)
def create_avatar(body: AvatarCreate, db: Session = Depends(get_db)):
    """Основной метод для 1С: JSON + base64."""
    try:
        data = storage.decode_b64(body.image_base64)
    except Exception:
        raise HTTPException(400, "Некорректный base64")
    return _create_job(db, data, body.style, body.employee_ref, body.seed)


@router.post("/avatars/upload", response_model=AvatarOut, status_code=202)
def create_avatar_upload(
    file: UploadFile = File(...),
    style: str = Form("corporate"),
    employee_ref: str | None = Form(None),
    seed: int | None = Form(None),
    db: Session = Depends(get_db),
):
    """Удобно для Swagger (/docs) и curl."""
    return _create_job(db, file.file.read(), style, employee_ref, seed)


@router.get("/avatars", response_model=list[AvatarOut])
def list_avatars(employee_ref: str | None = None, limit: int = Query(20, le=100), db: Session = Depends(get_db)):
    q = select(AvatarJob).order_by(AvatarJob.created_at.desc()).limit(limit)
    if employee_ref:
        q = q.where(AvatarJob.employee_ref == employee_ref)
    return db.scalars(q).all()


def _get_or_404(db: Session, job_id: str) -> AvatarJob:
    job = db.get(AvatarJob, job_id)
    if not job:
        raise HTTPException(404, "Задание не найдено")
    return job


@router.get("/avatars/{job_id}", response_model=AvatarOut)
def get_avatar(job_id: str, db: Session = Depends(get_db)):
    return _get_or_404(db, job_id)


@router.get("/avatars/{job_id}/image")
def get_avatar_image(job_id: str, db: Session = Depends(get_db)):
    """Готовый PNG. Отдаём и для failed (если файл есть) — чтобы можно было посмотреть, что не так."""
    job = _get_or_404(db, job_id)
    if not job.output_path:
        raise HTTPException(409, f"Результата нет (статус: {job.status.value})")
    return FileResponse(job.output_path, media_type="image/png", filename=f"avatar_{job.id}.png")


@router.delete("/avatars/{job_id}", status_code=204)
def delete_avatar(job_id: str, db: Session = Depends(get_db)):
    """Удаление задания и файлов (персональные данные — фото сотрудников)."""
    job = _get_or_404(db, job_id)
    storage.delete_files(job.input_path, job.output_path)
    db.delete(job)
    db.commit()

"""Pydantic-схемы API."""
import base64
import binascii
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import JobStatus


class AvatarCreate(BaseModel):
    """Запрос из 1С: фото в base64 (удобно для HTTPСоединение 1С)."""

    image_base64: str = Field(..., description="Фото сотрудника, JPEG/PNG в base64")
    style: str = Field("corporate", description="corporate | brand | cartoon")
    employee_ref: str | None = Field(None, max_length=64, description="GUID сотрудника из 1С")
    seed: int | None = None

    @field_validator("image_base64")
    @classmethod
    def _valid_b64(cls, v: str) -> str:
        if "," in v[:64]:  # data:image/jpeg;base64,....
            v = v.split(",", 1)[1]
        try:
            base64.b64decode(v, validate=False)
        except (binascii.Error, ValueError) as e:
            raise ValueError("image_base64 не является корректным base64") from e
        return v


class AvatarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_ref: str | None
    style: str
    status: JobStatus
    attempts: int
    metrics: dict | None = None
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class StyleOut(BaseModel):
    id: str
    title: str
    description: str

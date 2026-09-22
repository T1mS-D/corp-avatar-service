"""Файловое хранилище (том /data в Docker)."""
import base64
from pathlib import Path

from app.config import get_settings


def _root() -> Path:
    r = get_settings().storage_dir
    (r / "inputs").mkdir(parents=True, exist_ok=True)
    (r / "outputs").mkdir(parents=True, exist_ok=True)
    return r


def save_input(job_id: str, data: bytes) -> str:
    p = _root() / "inputs" / f"{job_id}.bin"
    p.write_bytes(data)
    return str(p)


def output_path(job_id: str) -> str:
    return str(_root() / "outputs" / f"{job_id}.png")


def decode_b64(s: str) -> bytes:
    return base64.b64decode(s)


def delete_files(*paths: str | None) -> None:
    for p in paths:
        if p:
            Path(p).unlink(missing_ok=True)

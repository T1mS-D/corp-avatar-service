"""Проверка очереди и жизненного цикла задания на подменённом пайплайне (без моделей)."""
import pytest
from PIL import Image

from app import worker
from app.models import AvatarJob, JobStatus
from app.db import SessionLocal
from app.pipeline.base import AvatarPipeline, PipelineResult
from app.pipeline.errors import RejectedError


@pytest.fixture(autouse=True)
def clean_queue():
    """Изоляция: чистая очередь перед каждым тестом."""
    with SessionLocal() as db:
        db.query(AvatarJob).delete()
        db.commit()


class FakePipeline(AvatarPipeline):
    name = "fake"

    def __init__(self, mode="ok"):
        self.mode = mode

    def run(self, image_path, style_id, seed=None):
        if self.mode == "reject":
            raise RejectedError("нет лица")
        if self.mode == "boom":
            raise RuntimeError("cuda oom")
        ok = self.mode == "ok"
        return PipelineResult(Image.new("RGB", (64, 64), "white"), {"similarity": 0.9 if ok else 0.1},
                              passed=ok, message=None if ok else "Не пройдена проверка сохранности лица")


def _run_one(client, b64, mode):
    job = client.post("/api/v1/avatars", json={"image_base64": b64}).json()
    jid = worker.claim_job()
    assert jid == job["id"]
    worker.process(jid, FakePipeline(mode))
    with SessionLocal() as db:
        return db.get(AvatarJob, jid)


def test_done(client, portrait_b64):
    j = _run_one(client, portrait_b64, "ok")
    assert j.status == JobStatus.done and j.output_path and j.attempts == 1
    r = client.get(f"/api/v1/avatars/{j.id}/image")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"


def test_rejected(client, portrait_b64):
    j = _run_one(client, portrait_b64, "reject")
    assert j.status == JobStatus.rejected and "лица" in j.error


def test_failed_identity(client, portrait_b64):
    j = _run_one(client, portrait_b64, "low_sim")
    assert j.status == JobStatus.failed and "сохранности лица" in j.error and j.output_path


def test_exception_does_not_crash_worker(client, portrait_b64):
    j = _run_one(client, portrait_b64, "boom")
    assert j.status == JobStatus.failed and "RuntimeError" in j.error


def test_queue_empty():
    while worker.claim_job():
        pass
    assert worker.claim_job() is None

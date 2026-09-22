import base64
import io
import os
import tempfile

# Переменные окружения нужно выставить ДО импорта app.*
_tmp = tempfile.mkdtemp(prefix="avatar-test-")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_tmp}/test.db")
os.environ["STORAGE_DIR"] = _tmp
os.environ["API_KEY"] = "test-key"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    init_db()
    with TestClient(app) as c:
        c.headers.update({"X-API-Key": "test-key"})
        yield c


@pytest.fixture(scope="session")
def portrait_bytes() -> bytes:
    """Портрет для тестов: astronaut из scikit-image (общественное достояние NASA), увеличенный до 1024px."""
    from skimage import data

    img = Image.fromarray(data.astronaut()).resize((1024, 1024), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=95)
    return buf.getvalue()


@pytest.fixture()
def portrait_b64(portrait_bytes) -> str:
    return base64.b64encode(portrait_bytes).decode()

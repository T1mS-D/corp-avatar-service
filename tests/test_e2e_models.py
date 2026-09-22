"""Сквозной тест на реальных моделях (InsightFace + rembg, CPU). Скачивает ~350 МБ весов.
Запуск: RUN_SLOW=1 pytest tests/test_e2e_models.py -s"""
import os

import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("RUN_SLOW"), reason="нужны веса моделей; RUN_SLOW=1")


@pytest.mark.parametrize("style", ["corporate", "brand"])
def test_classic_pipeline(portrait_bytes, tmp_path, style):
    from app.config import get_settings
    from app.pipeline.classic import ClassicPipeline

    p = tmp_path / "in.jpg"
    p.write_bytes(portrait_bytes)
    res = ClassicPipeline(get_settings()).run(str(p), style)
    assert res.passed, res.metrics
    assert res.metrics["similarity"] > 0.8
    assert res.image.size == (get_settings().output_size,) * 2


def test_reject_no_face(tmp_path):
    from PIL import Image
    from app.config import get_settings
    from app.pipeline.classic import ClassicPipeline
    from app.pipeline.errors import RejectedError

    p = tmp_path / "blank.jpg"
    Image.new("RGB", (800, 800), (120, 130, 140)).save(p)
    with pytest.raises(RejectedError):
        ClassicPipeline(get_settings()).run(str(p), "corporate")

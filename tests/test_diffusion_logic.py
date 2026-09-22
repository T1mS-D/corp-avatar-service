"""Проверка логики diffusion-бэкенда БЕЗ GPU и без весов: torch и SD-пайплайн подменены заглушками.
Проверяем: маска одежды не заходит на голову, вне маски пиксели == оригиналу, ретраи, метрики.
Реальную генерацию нужно смотреть глазами на GPU (см. docs/)."""
import os
import sys
import types
from contextlib import contextmanager

import numpy as np
import pytest
from PIL import Image

pytestmark = pytest.mark.skipif(not os.environ.get("RUN_SLOW"), reason="нужны веса InsightFace/rembg; RUN_SLOW=1")


def _fake_torch():
    m = types.ModuleType("torch")

    class _G:
        def manual_seed(self, s):
            self.seed = s
            return self

    class _T:  # минимальный «тензор»
        def __init__(self, a): self.a = np.asarray(a)
        def unsqueeze(self, _): return _T(self.a[None])
        def to(self, **_): return self
    m.Generator = lambda device="cpu": _G()
    m.float16 = m.float32 = "f"
    m.cuda = types.SimpleNamespace(is_available=lambda: False)
    m.from_numpy = lambda a: _T(a)
    m.stack = lambda l, dim=0: _T(np.stack([x.a for x in l]))
    m.zeros_like = lambda t: _T(np.zeros_like(t.a))
    m.cat = lambda l: _T(np.concatenate([x.a for x in l]))
    @contextmanager
    def inference_mode():
        yield
    m.inference_mode = inference_mode
    return m


class _FakeSD:
    """Вместо генерации закрашивает маску оранжевым и запоминает вызовы."""
    calls = []

    def __call__(self, **kw):
        _FakeSD.calls.append(kw)
        mask = np.asarray(kw["mask_image"]) > 127
        arr = np.asarray(kw["image"]).copy()
        arr[mask] = (20, 30, 80)  # «тёмно-синий пиджак»
        return types.SimpleNamespace(images=[Image.fromarray(arr)])


def test_photo_flow_keeps_head_pixels(monkeypatch, portrait_bytes, tmp_path):
    monkeypatch.setitem(sys.modules, "torch", _fake_torch())
    from app.config import get_settings
    from app.pipeline.diffusion import DiffusionPipeline

    s = get_settings()
    pipe = DiffusionPipeline(s)
    monkeypatch.setattr(pipe, "_get_inpaint", lambda: _FakeSD())
    p = tmp_path / "in.jpg"
    p.write_bytes(portrait_bytes)

    _FakeSD.calls.clear()
    res = pipe.run(str(p), "corporate", seed=7)
    assert res.passed, res.metrics
    assert res.metrics["backend"] == "diffusion" and res.metrics["attempts_used"] == 1
    call = _FakeSD.calls[0]
    mask = np.asarray(call["mask_image"]) > 127
    # маска не пустая и не начинается выше шеи: верхняя треть кадра (голова) не тронута
    assert mask.sum() > 1000
    h = mask.shape[0]
    assert mask[: h // 3].sum() == 0
    # вне маски результат идентичен подложке (голова сохранена побайтно, с учётом финального ресайза)
    out = np.asarray(res.image.resize(call["image"].size))
    base = np.asarray(call["image"])
    # (допуск — из-за двойного ресайза 512→OUTPUT_SIZE→512 в самом тесте, не из-за пайплайна)
    diff = np.abs(out[: h // 3].astype(int) - base[: h // 3].astype(int))
    assert diff.mean() < 1.0 and diff.max() <= 12
    # а в зоне одежды — «пиджак»
    assert (out[mask][:, 2] > out[mask][:, 0]).mean() > 0.8

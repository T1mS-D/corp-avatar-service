"""Генерация фонов: градиент / цвет бренда / пользовательский шаблон из assets/backgrounds."""
from pathlib import Path

import numpy as np
from PIL import Image

ASSETS = Path(__file__).resolve().parents[2] / "assets" / "backgrounds"


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _vertical_gradient(size: int, top: tuple, bottom: tuple, vignette: float = 0.0) -> Image.Image:
    t = np.linspace(0, 1, size, dtype=np.float32)[:, None, None]
    top_a, bot_a = np.array(top, np.float32), np.array(bottom, np.float32)
    grad = top_a * (1 - t) + bot_a * t                    # (H,1,3)
    arr = np.repeat(grad, size, axis=1)                   # (H,W,3)
    if vignette > 0:
        yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
        r = np.sqrt(((xx - size / 2) / (size / 2)) ** 2 + ((yy - size / 2) / (size / 2)) ** 2)
        arr = arr * (1 - vignette * np.clip(r - 0.4, 0, 1)[..., None])
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def make_background(kind: str, size: int, primary: str, secondary: str, style_id: str | None = None) -> Image.Image:
    """Если в assets/backgrounds лежит <style_id>.png|jpg — используем его как фирменный шаблон."""
    if style_id:
        for ext in ("png", "jpg", "jpeg"):
            p = ASSETS / f"{style_id}.{ext}"
            if p.exists():
                return Image.open(p).convert("RGB").resize((size, size), Image.LANCZOS)
    p_rgb, s_rgb = _hex(primary), _hex(secondary)
    if kind == "brand":
        lighter = tuple(int(c + (255 - c) * 0.25) for c in p_rgb)
        return _vertical_gradient(size, lighter, p_rgb, vignette=0.25)
    # gradient: светлый, от secondary к белому-серому
    return _vertical_gradient(size, (250, 251, 253), s_rgb, vignette=0.05)

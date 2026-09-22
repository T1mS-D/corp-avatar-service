"""Маска человека (rembg / u2net_human_seg)."""
import threading

import cv2
import numpy as np
from PIL import Image

_session = None
_lock = threading.Lock()


def _get_session():
    global _session
    with _lock:
        if _session is None:
            from rembg import new_session

            _session = new_session("u2net_human_seg")
        return _session


def person_mask(img: Image.Image) -> np.ndarray:
    """Возвращает float32 маску [0..1] размера изображения (1 — человек)."""
    from rembg import remove

    m = remove(img.convert("RGB"), session=_get_session(), only_mask=True)
    arr = np.asarray(m, dtype=np.float32) / 255.0
    # подчищаем шум: лёгкое сжатие и сглаживание края, чтобы не оставалось светлого ореола от старого фона
    arr = cv2.erode(arr, np.ones((3, 3), np.uint8), iterations=1)
    arr = cv2.GaussianBlur(arr, (0, 0), 1.2)
    return np.clip(arr, 0, 1)


def composite(fg: Image.Image, bg: Image.Image, mask: np.ndarray) -> Image.Image:
    f = np.asarray(fg.convert("RGB"), dtype=np.float32)
    b = np.asarray(bg.convert("RGB"), dtype=np.float32)
    m = mask[..., None]
    return Image.fromarray(np.clip(f * m + b * (1 - m), 0, 255).astype(np.uint8), "RGB")

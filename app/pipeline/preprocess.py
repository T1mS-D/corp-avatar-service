"""Подготовка данных: загрузка, EXIF-поворот, кадрирование «голова + плечи» в квадрат."""
import cv2
import numpy as np
from PIL import Image, ImageOps

from app.pipeline.faces import FaceInfo

MAX_SIDE = 1600


def load_image(path: str) -> Image.Image:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    if max(img.size) > MAX_SIDE:
        img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    return img


def crop_head_shoulders(img: Image.Image, face: FaceInfo, out_size: int) -> Image.Image:
    """Квадрат ~3 высоты лица: запас над головой и плечи. За границей кадра дополняем краевыми пикселями (зеркало создаёт «призрак» головы)."""
    fh = face.face_height
    side = 3.0 * fh
    cx = face.center[0]
    top = face.bbox[1] - 0.75 * fh
    left = cx - side / 2

    arr = np.asarray(img)
    h, w = arr.shape[:2]
    pad_l = int(max(0, -left))
    pad_t = int(max(0, -top))
    pad_r = int(max(0, left + side - w))
    pad_b = int(max(0, top + side - h))
    if any((pad_l, pad_t, pad_r, pad_b)):
        arr = cv2.copyMakeBorder(arr, pad_t, pad_b, pad_l, pad_r, cv2.BORDER_REPLICATE)
    x0, y0 = int(round(left + pad_l)), int(round(top + pad_t))
    s = int(round(side))
    crop = arr[y0 : y0 + s, x0 : x0 + s]
    return Image.fromarray(crop).resize((out_size, out_size), Image.LANCZOS)

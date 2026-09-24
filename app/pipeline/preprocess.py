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
    """Квадрат ~3 высоты лица: запас над головой и плечи. За границей кадра дополняем краевыми
    пикселями (зеркало создаёт «призрак» головы) — но не более чем на разумный запас: если лицо
    само по себе занимает большую часть кадра (плотный студийный портрет), запрошенный кроп
    может оказаться КРУПНЕЕ самого изображения, и тогда почти весь результат будет состоять из
    повторяющегося фона у края фото, а не из лица. Поэтому сторона кропа никогда не превышает
    фактические размеры изображения.

    "Запас" (side минус высота лица) делится пропорционально между "над головой" и "под
    подбородком" в той же пропорции, что и в исходном незаклампленном варианте (0.75fh к 1.25fh,
    т.е. 3/8 к 5/8). Раньше подбородок был жёстко привязан к фиксированной доле стороны, а
    макушка — к отступу от неё независимо: при урезанной стороне это могло съесть весь запас
    в пользу подбородка и обрезать волосы сверху. Пропорциональное деление гарантирует, что
    ОБЕ границы (макушка и подбородок) остаются внутри кадра одновременно, каким бы ни был side.

    Все координаты переводятся в int СРАЗУ (а не в конце через отдельные round()), иначе
    смешение int()-усечения для отступов и round() для итоговой позиции может дать рассинхрон
    в 1px и отрицательный индекс среза (Python трактует arr[-1:N] как ПУСТОЙ срез, а не "с начала")."""
    fh = face.face_height
    arr = np.asarray(img)
    h, w = arr.shape[:2]

    HEADROOM_SHARE = 0.75 / 3.0  # доля запаса, отдаваемая под "над головой" (остальное — под подбородок)

    side = int(round(min(3.0 * fh, w, h)))
    slack = max(0.0, side - fh)  # свободное место сверх высоты лица (может быть 0 при очень плотном кадре)
    headroom = slack * HEADROOM_SHARE

    cx = face.center[0]
    top = int(round(face.bbox[1] - headroom))
    left = int(round(cx - side / 2))

    pad_l = max(0, -left)
    pad_t = max(0, -top)
    pad_r = max(0, left + side - w)
    pad_b = max(0, top + side - h)
    if any((pad_l, pad_t, pad_r, pad_b)):
        arr = cv2.copyMakeBorder(arr, pad_t, pad_b, pad_l, pad_r, cv2.BORDER_REPLICATE)
    x0, y0 = left + pad_l, top + pad_t
    crop = arr[y0 : y0 + side, x0 : x0 + side]
    return Image.fromarray(crop).resize((out_size, out_size), Image.LANCZOS)
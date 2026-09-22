"""Проверки: пригодность входного фото и сохранность лица в результате."""
import cv2
import numpy as np

from app.config import Settings
from app.pipeline.errors import RejectedError
from app.pipeline.faces import FaceAnalyzer, FaceInfo, cosine


def sharpness(rgb: np.ndarray, bbox: tuple | None = None) -> float:
    """Дисперсия лапласиана (чем выше, тем резче). Считаем по области лица, если она известна."""
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    if bbox is not None:
        x1, y1, x2, y2 = [int(max(0, v)) for v in bbox]
        crop = g[y1:y2, x1:x2]
        if crop.size > 0:
            g = cv2.resize(crop, (160, 160))
    return float(cv2.Laplacian(g, cv2.CV_64F).var())


def check_input(rgb: np.ndarray, s: Settings) -> tuple[FaceInfo, dict]:
    """Возвращает главное лицо и метрики. Если фото не подходит — RejectedError с понятным текстом."""
    faces = FaceAnalyzer.get().analyze(rgb)
    if not faces:
        raise RejectedError("На фото не найдено лицо. Загрузите портретное фото анфас.")
    main = faces[0]
    if len(faces) > 1:
        a = lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])
        if a(faces[1]) / a(main) > 0.35:
            raise RejectedError("На фото несколько лиц. Нужен портрет одного сотрудника.")
    if main.det_score < 0.6:
        raise RejectedError("Лицо распознано с низкой уверенностью (плохое освещение/ракурс).")
    if main.face_width < s.min_face_px:
        raise RejectedError(f"Лицо слишком маленькое ({int(main.face_width)}px, нужно ≥ {s.min_face_px}px).")
    if main.yaw is not None and abs(main.yaw) > s.max_yaw_deg:
        raise RejectedError(f"Голова сильно повёрнута ({main.yaw:.0f}°). Нужен ракурс анфас.")
    sharp = sharpness(rgb, main.bbox)
    if sharp < s.min_sharpness:
        raise RejectedError("Фото размыто. Загрузите более чёткое изображение.")
    metrics = {
        "input_face_px": int(main.face_width),
        "input_det_score": round(main.det_score, 3),
        "input_yaw": None if main.yaw is None else round(main.yaw, 1),
        "input_sharpness": round(sharp, 1),
    }
    return main, metrics


def check_output(src: FaceInfo, out_rgb: np.ndarray, threshold: float) -> dict:
    """Сравнивает эмбеддинг лица исходника и результата (ArcFace, косинусное сходство)."""
    faces = FaceAnalyzer.get().analyze(out_rgb)
    if not faces:
        return {"face_found": False, "similarity": 0.0, "passed": False, "threshold": threshold}
    sim = cosine(src.embedding, faces[0].embedding)
    return {
        "face_found": True,
        "similarity": round(sim, 4),
        "threshold": threshold,
        "passed": bool(sim >= threshold),
        "output_faces": len(faces),
    }

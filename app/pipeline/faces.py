"""Детекция лица, эмбеддинги (ArcFace), поза — на базе InsightFace (buffalo_l)."""
import os
import threading
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class FaceInfo:
    bbox: tuple[float, float, float, float]
    det_score: float
    embedding: np.ndarray          # L2-нормированный ArcFace, 512
    yaw: float | None
    pitch: float | None
    chin_y: float                  # y нижней точки подбородка
    face_height: float
    face_width: float
    center: tuple[float, float]


class FaceAnalyzer:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        from insightface.app import FaceAnalysis

        root = os.environ.get("INSIGHTFACE_HOME", os.path.expanduser("~/.insightface"))
        # onnxruntime выберет CUDA, если она доступна, иначе CPU
        self.app = FaceAnalysis(
            name="buffalo_l",
            root=root,
            allowed_modules=["detection", "recognition", "landmark_2d_106", "landmark_3d_68"],
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        self.app.prepare(ctx_id=0, det_size=(640, 640))

    @classmethod
    def get(cls) -> "FaceAnalyzer":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def analyze(self, rgb: np.ndarray) -> list[FaceInfo]:
        """rgb: HxWx3 uint8. Возвращает лица, отсортированные по площади (крупные первыми)."""
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        faces = self.app.get(bgr)
        out: list[FaceInfo] = []
        for f in faces:
            x1, y1, x2, y2 = [float(v) for v in f.bbox]
            lm = getattr(f, "landmark_2d_106", None)
            # точки 0..32 — контур лица, 16 — подбородок
            chin_y = float(lm[0:33, 1].max()) if lm is not None else y2
            pose = getattr(f, "pose", None)
            pitch, yaw = (float(pose[0]), float(pose[1])) if pose is not None else (None, None)
            out.append(
                FaceInfo(
                    bbox=(x1, y1, x2, y2),
                    det_score=float(f.det_score),
                    embedding=np.asarray(f.normed_embedding, dtype=np.float32),
                    yaw=yaw,
                    pitch=pitch,
                    chin_y=chin_y,
                    face_height=chin_y - y1,
                    face_width=x2 - x1,
                    center=((x1 + x2) / 2, (y1 + y2) / 2),
                )
            )
        out.sort(key=lambda i: (i.bbox[2] - i.bbox[0]) * (i.bbox[3] - i.bbox[1]), reverse=True)
        return out


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

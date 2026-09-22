"""CPU-пайплайн без генеративных моделей: кадрирование + сегментация + замена фона.
Одежду не меняет (это делает diffusion-бэкенд). Нужен для быстрого демо, тестов и как fallback."""
import time

import numpy as np

from app.config import Settings
from app.pipeline import verify
from app.pipeline.background import make_background
from app.pipeline.base import AvatarPipeline, PipelineResult
from app.pipeline.faces import FaceAnalyzer
from app.pipeline.preprocess import crop_head_shoulders, load_image
from app.pipeline.segmentation import composite, person_mask
from app.pipeline.styles import get_style


class ClassicPipeline(AvatarPipeline):
    name = "classic"

    def __init__(self, settings: Settings):
        self.s = settings

    def run(self, image_path: str, style_id: str, seed: int | None = None) -> PipelineResult:
        t0 = time.time()
        style = get_style(style_id)
        if style.kind == "cartoon":
            raise ValueError("Мульт-стиль доступен только при PIPELINE_BACKEND=diffusion")

        img = load_image(image_path)
        face, m_in = verify.check_input(np.asarray(img), self.s)
        crop = crop_head_shoulders(img, face, self.s.output_size)

        mask = person_mask(crop)
        bg = make_background(style.background, self.s.output_size, self.s.brand_primary_color,
                             self.s.brand_secondary_color, style.id)
        out = composite(crop, bg, mask)

        m_out = verify.check_output(face, np.asarray(out), self.s.face_sim_threshold)
        metrics = {**m_in, **m_out, "backend": self.name, "seconds": round(time.time() - t0, 2)}
        return PipelineResult(
            image=out, metrics=metrics, passed=m_out["passed"],
            message=None if m_out["passed"] else "Не пройдена проверка сохранности лица",
        )

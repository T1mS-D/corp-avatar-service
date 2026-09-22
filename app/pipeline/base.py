from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from PIL import Image


@dataclass
class PipelineResult:
    image: Image.Image
    metrics: dict = field(default_factory=dict)
    passed: bool = True          # прошла ли проверка сохранности лица
    message: str | None = None   # причина, если passed == False


class AvatarPipeline(ABC):
    name: str = "base"

    @abstractmethod
    def run(self, image_path: str, style_id: str, seed: int | None = None) -> PipelineResult:
        """Полный цикл: проверка входа → кадрирование → генерация → проверка выхода."""

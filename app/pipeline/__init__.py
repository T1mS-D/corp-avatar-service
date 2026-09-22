from app.config import Settings, get_settings
from app.pipeline.base import AvatarPipeline


def get_pipeline(settings: Settings | None = None) -> AvatarPipeline:
    """Фабрика: выбирает бэкенд по PIPELINE_BACKEND."""
    s = settings or get_settings()
    if s.pipeline_backend == "diffusion":
        from app.pipeline.diffusion import DiffusionPipeline

        return DiffusionPipeline(s)
    from app.pipeline.classic import ClassicPipeline

    return ClassicPipeline(s)

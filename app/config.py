"""Настройки приложения. Все значения приходят из переменных окружения / .env."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # БД
    postgres_user: str = "avatar"
    postgres_password: str = "avatar"
    postgres_db: str = "avatar_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None  # если задан — имеет приоритет (тесты: sqlite)

    # API
    api_key: str = "dev-key"
    max_upload_mb: int = 10
    storage_dir: Path = Path("./data")

    # Пайплайн
    pipeline_backend: str = Field("classic", pattern="^(classic|diffusion)$")
    worker_poll_seconds: float = 2.0
    job_timeout_seconds: int = 600
    max_attempts: int = 3
    output_size: int = 768

    # Бренд
    brand_primary_color: str = "#0B5FA5"
    brand_secondary_color: str = "#E8F1FA"
    brand_name: str = "Acme"

    # Проверки
    face_sim_threshold: float = 0.55
    face_sim_threshold_cartoon: float = 0.30
    min_face_px: int = 110
    max_yaw_deg: float = 40.0
    min_sharpness: float = 40.0

    # Diffusion
    sd_inpaint_model: str = "stable-diffusion-v1-5/stable-diffusion-inpainting"
    sd_img2img_model: str = "stable-diffusion-v1-5/stable-diffusion-v1-5"
    ip_adapter_repo: str = "h94/IP-Adapter-FaceID"
    ip_adapter_weight: str = "ip-adapter-faceid_sd15.bin"
    ip_adapter_scale: float = 0.7
    cartoon_lora_path: str = ""
    diffusion_size: int = 512
    diffusion_steps: int = 30
    cpu_offload: bool = True
    neck_offset_ratio: float = 0.25  # где начинается зона замены одежды (доля высоты лица ниже подбородка)

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

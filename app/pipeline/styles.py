"""Пресеты стилей. Чтобы добавить стиль — добавьте запись в STYLES (и, при желании, фон в assets/backgrounds/<id>.png)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Style:
    id: str
    title: str
    description: str
    kind: str            # "photo" — реалистичный аватар, "cartoon" — мульт-аватар
    background: str      # "gradient" | "brand"
    prompt: str = ""
    negative_prompt: str = ""


_NEG_PHOTO = (
    "deformed, blurry, low quality, extra fingers, bad anatomy, logo, text, watermark, "
    "t-shirt, hoodie, casual clothes, nsfw"
)

STYLES: dict[str, Style] = {
    "corporate": Style(
        id="corporate",
        title="Корпоративный (светлый фон)",
        description="Деловая одежда, светлый градиентный фон.",
        kind="photo",
        background="gradient",
        prompt=(
            "professional corporate headshot, wearing a dark navy business suit jacket, "
            "white collared shirt, formal, neat, studio lighting, high detail"
        ),
        negative_prompt=_NEG_PHOTO,
    ),
    "brand": Style(
        id="brand",
        title="Фирменный цвет",
        description="Деловая одежда, фон цвета бренда.",
        kind="photo",
        background="brand",
        prompt=(
            "professional corporate headshot, wearing a charcoal business suit jacket, "
            "white shirt, formal, neat, studio lighting, high detail"
        ),
        negative_prompt=_NEG_PHOTO,
    ),
    "cartoon": Style(
        id="cartoon",
        title="Мульт-аватар",
        description="Стилизация под 3D-мультфильм, фон бренда.",
        kind="cartoon",
        background="brand",
        prompt=(
            "3d pixar style cartoon portrait of a person, business attire, smooth skin, "
            "big expressive eyes, vibrant colors, soft studio lighting, clean background"
        ),
        negative_prompt="realistic photo, blurry, deformed, low quality, text, watermark, nsfw",
    ),
}


def get_style(style_id: str) -> Style:
    try:
        return STYLES[style_id]
    except KeyError as e:
        raise ValueError(f"Неизвестный стиль '{style_id}'. Доступные: {', '.join(STYLES)}") from e

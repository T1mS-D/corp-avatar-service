import hmac

from fastapi import Header, HTTPException, status

from app.config import get_settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Простая авторизация сервис-сервис: 1С передаёт X-API-Key."""
    expected = get_settings().api_key
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный или отсутствующий X-API-Key")

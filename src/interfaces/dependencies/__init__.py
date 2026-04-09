from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from src.infra.config.database import get_db
from src.infra.config.settings import get_settings, Settings


def get_current_settings() -> Settings:
    return get_settings()


def verify_support_key(
    x_support_key: str = Header(None, alias="X-SUPPORT-KEY"),
    settings: Settings = Depends(get_current_settings),
):
    """Dependency: verifica la clave de soporte en el header."""
    if not x_support_key or x_support_key != settings.SUPPORT_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

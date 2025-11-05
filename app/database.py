"""Compatibility shim for legacy imports.

Use from app.core.database import engine, SessionLocal, Base, get_db.
"""
from app.core.database import engine, SessionLocal, Base, get_db  # noqa: F401

def get_database_url() -> str:
    from app.core.config import settings as _settings
    return _settings.database_url

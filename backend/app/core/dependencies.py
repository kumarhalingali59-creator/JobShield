from collections.abc import Generator

from app.core.database import SessionLocal


def get_db() -> Generator:
    if SessionLocal is None:
        raise RuntimeError("Database is not configured")

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def commit_or_raise(db: Session) -> None:
    """Commit a transaction and safely translate database failures to HTTP errors."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The submission conflicts with an existing database record.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database transaction failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The database operation failed.",
        ) from exc

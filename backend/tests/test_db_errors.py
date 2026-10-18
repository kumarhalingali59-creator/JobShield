from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.db_errors import commit_or_raise


def test_commit_or_raise_commits_successfully():
    db = MagicMock()

    commit_or_raise(db)

    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_commit_or_raise_rolls_back_integrity_error():
    db = MagicMock()
    db.commit.side_effect = IntegrityError(
        "INSERT", {}, Exception("duplicate")
    )

    with pytest.raises(HTTPException) as exc_info:
        commit_or_raise(db)

    assert exc_info.value.status_code == 409
    db.rollback.assert_called_once()


def test_commit_or_raise_rolls_back_database_error():
    db = MagicMock()
    db.commit.side_effect = SQLAlchemyError("database unavailable")

    with pytest.raises(HTTPException) as exc_info:
        commit_or_raise(db)

    assert exc_info.value.status_code == 500
    db.rollback.assert_called_once()

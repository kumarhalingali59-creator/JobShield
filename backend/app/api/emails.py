
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.db_errors import commit_or_raise
from app.models.email import Email
from app.schemas.email import (
    EmailCreate,
    EmailResponse,
    PublicEmailListResponse,
    PublicEmailResponse,
)

router = APIRouter(
    prefix="/api/emails",
    tags=["Emails"],
)

@router.post(
    "",
    response_model=PublicEmailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_email(
    email_data: EmailCreate,
    db: Session = Depends(get_db),
):
    existing_email = (
        db.query(Email)
        .filter(Email.email_address == email_data.email_address)
        .first()
    )

    if existing_email is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address already exists.",
        )

    email = Email(
        email_address=email_data.email_address,
        description=email_data.description,
    )

    db.add(email)
    commit_or_raise(db)
    db.refresh(email)

    return email


@router.get(
    "",
    response_model=PublicEmailListResponse,
)
def list_emails(
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Email)

    if search and search.strip():
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            Email.email_address.ilike(search_pattern)
        )

    total = query.count()

    emails = (
        query
        .order_by(Email.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return PublicEmailListResponse(
        items=emails,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{email_id}",
    response_model=PublicEmailResponse,
)
def get_email(
    email_id: int,
    db: Session = Depends(get_db),
):
    email = db.get(Email, email_id)

    if email is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email address not found.",
        )

    return email

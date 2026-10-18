from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.db_errors import commit_or_raise
from app.models.phone_number import PhoneNumber
from app.schemas.phone_number import (
    PhoneNumberCreate,
    PhoneNumberListResponse,
    PhoneNumberResponse,
)


router = APIRouter(
    prefix="/api/phone-numbers",
    tags=["Phone Numbers"],
)


@router.post(
    "",
    response_model=PhoneNumberResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_phone_number(
    phone_data: PhoneNumberCreate,
    db: Session = Depends(get_db),
):
    existing_phone = (
        db.query(PhoneNumber)
        .filter(PhoneNumber.phone_number == phone_data.phone_number)
        .first()
    )

    if existing_phone is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number already exists.",
        )

    phone_number = PhoneNumber(
        phone_number=phone_data.phone_number,
        country_code=phone_data.country_code,
        description=phone_data.description,
    )

    db.add(phone_number)
    commit_or_raise(db)
    db.refresh(phone_number)

    return phone_number


@router.get(
    "",
    response_model=PhoneNumberListResponse,
)
def list_phone_numbers(
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(PhoneNumber)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            PhoneNumber.phone_number.ilike(search_pattern)
        )

    total = query.count()

    phone_numbers = (
        query
        .order_by(PhoneNumber.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return PhoneNumberListResponse(
        items=phone_numbers,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{phone_number_id}",
    response_model=PhoneNumberResponse,
)
def get_phone_number(
    phone_number_id: int,
    db: Session = Depends(get_db),
):
    phone_number = db.get(PhoneNumber, phone_number_id)

    if phone_number is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found.",
        )

    return phone_number
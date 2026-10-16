from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.recruiter import Recruiter
from app.schemas.recruiter import (
    RecruiterCreate,
    RecruiterListResponse,
    RecruiterResponse,
)


router = APIRouter(
    prefix="/api/recruiters",
    tags=["Recruiters"],
)


@router.post(
    "",
    response_model=RecruiterResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_recruiter(
    recruiter_data: RecruiterCreate,
    db: Session = Depends(get_db),
):
    recruiter = Recruiter(
        name=recruiter_data.name,
        email=recruiter_data.email,
        phone=recruiter_data.phone,
        company_name=recruiter_data.company_name,
        profile_url=recruiter_data.profile_url,
        description=recruiter_data.description,
    )

    db.add(recruiter)
    db.commit()
    db.refresh(recruiter)

    return recruiter


@router.get(
    "",
    response_model=RecruiterListResponse,
)
def list_recruiters(
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Recruiter)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Recruiter.name.ilike(search_pattern),
                Recruiter.email.ilike(search_pattern),
                Recruiter.phone.ilike(search_pattern),
                Recruiter.company_name.ilike(search_pattern),
            )
        )

    total = query.count()

    recruiters = (
        query
        .order_by(Recruiter.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return RecruiterListResponse(
        items=recruiters,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{recruiter_id}",
    response_model=RecruiterResponse,
)
def get_recruiter(
    recruiter_id: int,
    db: Session = Depends(get_db),
):
    recruiter = db.get(Recruiter, recruiter_id)

    if recruiter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recruiter not found.",
        )

    return recruiter
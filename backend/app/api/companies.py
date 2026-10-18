
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.db_errors import commit_or_raise
from app.models.company import Company
from app.schemas.company import (
    CompanyCreate,
    CompanyListResponse,
    CompanyResponse,
)


router = APIRouter(
    prefix="/api/companies",
    tags=["Companies"],
)


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_company(
    company_data: CompanyCreate,
    db: Session = Depends(get_db),
):
    company = Company(
        name=company_data.name,
        legal_name=company_data.legal_name,
        description=company_data.description,
        website=company_data.website,
    )

    db.add(company)
    commit_or_raise(db)
    db.refresh(company)

    return company


@router.get(
    "",
    response_model=CompanyListResponse,
)
def list_companies(
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Company)

    if search:
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                    or_(
                        Company.name.ilike(search_pattern),
                        Company.legal_name.ilike(search_pattern),
                    )
           )


    total = query.count()

    companies = (
        query
        .order_by(Company.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return CompanyListResponse(
        items=companies,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
):
    company = db.get(Company, company_id)

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found.",
        )

    return company
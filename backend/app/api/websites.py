from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.db_errors import commit_or_raise
from app.models.website import Website
from app.schemas.website import (
    WebsiteCreate,
    WebsiteListResponse,
    WebsiteResponse,
)


router = APIRouter(
    prefix="/api/websites",
    tags=["Websites"],
)


@router.post(
    "",
    response_model=WebsiteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_website(
    website_data: WebsiteCreate,
    db: Session = Depends(get_db),
):
    existing_website = (
        db.query(Website)
        .filter(Website.website_url == website_data.website_url)
        .first()
    )

    if existing_website is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Website URL already exists.",
        )

    website = Website(
        website_url=website_data.website_url,
        domain=website_data.domain,
        description=website_data.description,
    )

    db.add(website)
    commit_or_raise(db)
    db.refresh(website)

    return website


@router.get(
    "",
    response_model=WebsiteListResponse,
)
def list_websites(
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Website)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            Website.website_url.ilike(search_pattern)
        )

    total = query.count()

    websites = (
        query
        .order_by(Website.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return WebsiteListResponse(
        items=websites,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{website_id}",
    response_model=WebsiteResponse,
)
def get_website(
    website_id: int,
    db: Session = Depends(get_db),
):
    website = db.get(Website, website_id)

    if website is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found.",
        )

    return website
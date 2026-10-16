from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.job import Job
from app.schemas.job import (
    JobCreate,
    JobListResponse,
    JobResponse,
)


router = APIRouter(
    prefix="/api/jobs",
    tags=["Jobs"],
)


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job(
    job_data: JobCreate,
    db: Session = Depends(get_db),
):
    existing_job = (
        db.query(Job)
        .filter(Job.job_url == job_data.job_url)
        .first()
    )

    if existing_job is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job URL already exists.",
        )

    job = Job(
        job_url=job_data.job_url,
        title=job_data.title,
        company_name=job_data.company_name,
        description=job_data.description,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


@router.get(
    "",
    response_model=JobListResponse,
)
def list_jobs(
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Job)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            Job.job_url.ilike(search_pattern)
        )

    total = query.count()

    jobs = (
        query
        .order_by(Job.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return JobListResponse(
        items=jobs,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
):
    job = db.get(Job, job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    return job
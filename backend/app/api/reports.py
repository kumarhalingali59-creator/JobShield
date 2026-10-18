
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.auth_dependencies import get_current_user
from app.models.report import Report
from app.models.user import User
from app.schemas.report import (
    ReportCreate,
    ReportListResponse,
    ReportResponse,
)
from app.services.report_risk_integration import assess_report

router = APIRouter(
    prefix="/api/reports",
    tags=["Reports"],
)


@router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_report(
    report_data: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report_type = report_data.report_type.strip().lower()
    target_value = report_data.target_value.strip()
    description = report_data.description.strip()

    if not report_type or not target_value or not description:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Report fields cannot be blank.",
        )

    report = Report(
        user_id=current_user.id,
        report_type=report_type,
        target_value=target_value,
        description=description,
    )

    try:
        db.add(report)
        db.flush()

        # User reports are allegations, not verified proof.
        assess_report(db, report)

        db.commit()
        db.refresh(report)

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The report could not be saved.",
        ) from exc

    return report


@router.get(
    "/mine",
    response_model=ReportListResponse,
)
def list_my_reports(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Authenticated users can see only reports they submitted.
    # Their own reports may be pending, approved, or rejected.
    query = db.query(Report).filter(
        Report.user_id == current_user.id
    )

    total = query.count()

    reports = (
        query
        .order_by(Report.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return ReportListResponse(
        items=reports,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "",
    response_model=ReportListResponse,
)
def list_reports(
    search: str | None = Query(default=None, max_length=1000),
    report_type: str | None = Query(default=None, max_length=50),
    report_status: str | None = Query(
        default=None,
        alias="status",
        max_length=30,
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    # Only approved reports may appear in public search results.
    query = db.query(Report).filter(Report.status == "approved")

    if search and search.strip():
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            Report.target_value.ilike(search_pattern)
            | Report.description.ilike(search_pattern)
        )

    if report_type and report_type.strip():
        query = query.filter(
            Report.report_type.ilike(report_type.strip())
        )

    # This filter cannot expose pending or rejected reports.
    if report_status and report_status.strip():
        query = query.filter(
            Report.status.ilike(report_status.strip())
        )

    total = query.count()

    reports = (
        query
        .order_by(Report.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return ReportListResponse(
        items=reports,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
):
    report = db.get(Report, report_id)

    if report is None or report.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    return report

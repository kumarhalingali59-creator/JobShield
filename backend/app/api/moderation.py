from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.core.admin_dependencies import require_admin
from app.core.dependencies import get_db
from app.core.db_errors import commit_or_raise
from app.models.company import Company
from app.models.email import Email
from app.models.evidence import Evidence
from app.models.phone_number import PhoneNumber
from app.models.report import Report
from app.models.report_moderation_log import ReportModerationLog
from app.models.recruiter import Recruiter
from app.models.user import User


router = APIRouter(
    prefix="/api/admin/moderation",
    tags=["Admin Moderation"],
    dependencies=[Depends(require_admin)],
)


ModeratedCategory = Literal[
    "companies",
    "recruiters",
    "emails",
    "phone_numbers",
]

MODERATED_MODELS = {
    "companies": Company,
    "recruiters": Recruiter,
    "emails": Email,
    "phone_numbers": PhoneNumber,
}


class ModerationAction(BaseModel):
    status: Literal["approved", "rejected"]


class ReportModerationAction(BaseModel):
    status: Literal["approved", "rejected", "needs_evidence"]
    notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def validate_notes(self):
        if self.notes is not None:
            self.notes = self.notes.strip() or None

        if self.status == "needs_evidence" and not self.notes:
            raise ValueError(
                "Notes explaining the requested evidence are required."
            )

        if self.status == "rejected" and not self.notes:
            raise ValueError("Notes explaining the rejection are required.")

        return self


@router.get("/pending/{category}")
def list_pending_submissions(
    category: ModeratedCategory,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    model = MODERATED_MODELS[category]

    query = db.query(model).filter(
        model.moderation_status == "pending"
    )

    total = query.count()
    items = (
        query.order_by(model.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "category": category,
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/{category}/{record_id}")
def moderate_submission(
    category: ModeratedCategory,
    record_id: int,
    action: ModerationAction,
    db: Session = Depends(get_db),
):
    model = MODERATED_MODELS[category]

    record = (
        db.query(model)
        .filter(model.id == record_id)
        .with_for_update()
        .first()
    )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found.",
        )

    if record.moderation_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending submissions can be moderated.",
        )

    record.moderation_status = action.status
    commit_or_raise(db)
    db.refresh(record)

    return {
        "message": f"Submission {action.status}.",
        "category": category,
        "id": record.id,
        "moderation_status": record.moderation_status,
    }


@router.get("/reports/pending")
def list_pending_reports(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List pending reports and safe evidence metadata for admin review."""
    query = db.query(Report).filter(Report.status == "pending")

    total = query.count()
    reports = (
        query.order_by(Report.created_at.asc(), Report.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []

    for report in reports:
        evidence_items = (
            db.query(Evidence)
            .filter(Evidence.report_id == report.id)
            .order_by(Evidence.created_at.desc())
            .all()
        )

        items.append(
            {
                "id": report.id,
                "user_id": report.user_id,
                "report_type": report.report_type,
                "target_value": report.target_value,
                "description": report.description,
                "status": report.status,
                "created_at": report.created_at,
                "updated_at": report.updated_at,
                "evidence": [
                    {
                        "id": evidence.id,
                        "file_name": evidence.file_name,
                        "content_type": evidence.content_type,
                        "file_size": evidence.file_size,
                        "description": evidence.description,
                        "created_at": evidence.created_at,
                    }
                    for evidence in evidence_items
                ],
            }
        )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/reports/{report_id}/decision")
def moderate_report(
    report_id: int,
    action: ReportModerationAction,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Approve, reject, or request more evidence for a pending report."""
    report = (
        db.query(Report)
        .filter(Report.id == report_id)
        .with_for_update()
        .first()
    )

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    if report.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending reports can be moderated.",
        )

    report.status = action.status

    log = ReportModerationLog(
        report_id=report.id,
        actor_user_id=current_admin.id,
        actor_type="admin",
        action=action.status,
        notes=action.notes,
    )
    db.add(log)

    commit_or_raise(db)
    db.refresh(report)
    db.refresh(log)

    return {
        "message": f"Report marked as {report.status}.",
        "report_id": report.id,
        "status": report.status,
        "moderation_log_id": log.id,
        "created_at": log.created_at,
    }


@router.get("/reports/{report_id}/history")
def get_report_moderation_history(
    report_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Return the private moderation audit trail for an existing report."""
    report = db.get(Report, report_id)

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    query = db.query(ReportModerationLog).filter(
        ReportModerationLog.report_id == report_id
    )

    total = query.count()
    logs = (
        query.order_by(
            ReportModerationLog.created_at.desc(),
            ReportModerationLog.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "report_id": report_id,
        "items": [
            {
                "id": log.id,
                "actor_user_id": log.actor_user_id,
                "actor_type": log.actor_type,
                "action": log.action,
                "notes": log.notes,
                "created_at": log.created_at,
            }
            for log in logs
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }

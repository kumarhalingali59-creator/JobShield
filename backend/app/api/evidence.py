from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.core.dependencies import get_db
from app.core.storage import get_storage_client
from app.models.evidence import Evidence
from app.models.report import Report
from app.models.user import User
from app.schemas.evidence import EvidenceListResponse, EvidenceResponse
from app.services.evidence_storage import (
    BUCKET_NAME,
    SIGNED_URL_TTL_SECONDS,
    create_evidence_signed_url,
    upload_evidence_file,
)

router = APIRouter(prefix="/api/evidence", tags=["Evidence"])


def get_owned_report(
    report_id: int,
    user_id: int,
    db: Session,
) -> Report:
    """Return a report only when it belongs to the authenticated user."""
    report = db.get(Report, report_id)

    # Use the same response for missing and unowned reports.
    if report is None or report.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    return report


def get_owned_evidence(
    evidence_id: int,
    user_id: int,
    db: Session,
) -> Evidence:
    """Return evidence only when its parent report belongs to the user."""
    evidence = db.get(Evidence, evidence_id)

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found.",
        )

    get_owned_report(evidence.report_id, user_id, db)
    return evidence


@router.post(
    "/upload",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_evidence(
    report_id: int = Form(..., gt=0),
    file: UploadFile = File(...),
    description: str | None = Form(default=None, max_length=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_report(report_id, current_user.id, db)

    # Upload only after verifying report ownership.
    uploaded = upload_evidence_file(report_id, file)

    evidence = Evidence(
        report_id=report_id,
        file_name=uploaded["file_name"],
        storage_path=uploaded["storage_path"],
        content_type=uploaded["content_type"],
        file_size=uploaded["file_size"],
        description=(
            description.strip()
            if description and description.strip()
            else None
        ),
    )

    db.add(evidence)

    try:
        db.commit()
        db.refresh(evidence)

    except IntegrityError as exc:
        db.rollback()

        try:
            get_storage_client().storage.from_(BUCKET_NAME).remove(
                [uploaded["storage_path"]]
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evidence metadata conflicts with an existing record.",
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()

        try:
            get_storage_client().storage.from_(BUCKET_NAME).remove(
                [uploaded["storage_path"]]
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save evidence metadata.",
        ) from exc

    return evidence


@router.get("", response_model=EvidenceListResponse)
def list_evidence(
    report_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only return evidence attached to reports owned by this user.
    query = (
        select(Evidence)
        .join(Report, Evidence.report_id == Report.id)
        .where(Report.user_id == current_user.id)
    )

    if report_id is not None:
        # Return 404 rather than revealing whether another user's
        # report exists.
        get_owned_report(report_id, current_user.id, db)
        query = query.where(Evidence.report_id == report_id)

    total_query = select(func.count()).select_from(
        query.subquery()
    )
    total = db.scalar(total_query) or 0

    items = db.scalars(
        query.order_by(Evidence.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return EvidenceListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_owned_evidence(
        evidence_id,
        current_user.id,
        db,
    )


@router.get("/{evidence_id}/download")
def download_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate temporary download access for evidence owned by the user."""
    evidence = get_owned_evidence(
        evidence_id,
        current_user.id,
        db,
    )

    signed_url = create_evidence_signed_url(
    evidence.storage_path,
    report_id=evidence.report_id,
)

    return {
        "download_url": signed_url,
        "expires_in": SIGNED_URL_TTL_SECONDS,
    }

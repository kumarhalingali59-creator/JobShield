
import logging
from pathlib import PurePosixPath
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from supabase import Client

from app.core.storage import get_storage_client


logger = logging.getLogger(__name__)

BUCKET_NAME = "jobshield-evidence"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
SIGNED_URL_TTL_SECONDS = 60

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
}


def _is_utf8_text(content: bytes) -> bool:
    """Return whether content is valid UTF-8 text."""
    try:
        content.decode("utf-8-sig")
        return True
    except UnicodeDecodeError:
        return False


def validate_file_content(content: bytes, content_type: str) -> None:
    """Validate basic file signatures against the declared MIME type."""
    signatures = {
        "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
        "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": lambda data: (
            len(data) >= 12
            and data.startswith(b"RIFF")
            and data[8:12] == b"WEBP"
        ),
        "application/pdf": lambda data: data.startswith(b"%PDF-"),
        "text/plain": lambda data: (
            b"\x00" not in data and _is_utf8_text(data)
        ),
    }

    checker = signatures.get(content_type)

    if checker is None or not checker(content):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File contents do not match the supported file type.",
        )


def upload_evidence_file(
    report_id: int,
    file: UploadFile,
    *,
    client: Client | None = None,
) -> dict:
    if report_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid report ID.",
        )

    original_name = PurePosixPath(
        (file.filename or "").replace("\\", "/")
    ).name

    if not original_name or original_name in {".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid file name is required.",
        )

    content_type = (file.content_type or "").lower().strip()

    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Unsupported file type. Upload a JPG, PNG, "
                "WEBP, PDF, or TXT file."
            ),
        )

    content = file.file.read(MAX_FILE_SIZE + 1)

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File size must not exceed 5 MB.",
        )

    # Validate bytes before sending anything to Supabase.
    validate_file_content(content, content_type)

    storage_path = (
        f"{report_id}/{uuid4().hex}"
        f"{ALLOWED_CONTENT_TYPES[content_type]}"
    )

    storage_client = client or get_storage_client()

    try:
        storage_client.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=content,
            file_options={
                "content-type": content_type,
                "upsert": "false",
            },
        )
    except Exception as exc:
        # Avoid printing potentially sensitive response bodies or headers.
        logger.exception("Evidence upload to storage failed.")

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Evidence could not be uploaded to private storage.",
        ) from exc

    return {
        "file_name": original_name,
        "storage_path": storage_path,
        "content_type": content_type,
        "file_size": len(content),
    }


def create_evidence_signed_url(
    storage_path: str,
    *,
    report_id: int,
    client: Client | None = None,
) -> str:
    """Create a short-lived URL for evidence inside its report folder."""
    path = PurePosixPath(storage_path) if storage_path else None

    if (
        path is None
        or storage_path.startswith("/")
        or "\\" in storage_path
        or path.as_posix() != storage_path
        or len(path.parts) != 2
        or path.parts[0] != str(report_id)
        or any(part in {".", ".."} for part in path.parts)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid evidence storage path.",
        )

    storage_client = client or get_storage_client()

    try:
        result = storage_client.storage.from_(BUCKET_NAME).create_signed_url(
            storage_path,
            SIGNED_URL_TTL_SECONDS,
        )
    except Exception as exc:
        logger.exception("Creating an evidence signed URL failed.")

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not create temporary evidence access.",
        ) from exc

    signed_url = result.get("signedURL") or result.get("signedUrl")

    if not signed_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Storage did not return a temporary access URL.",
        )

    return signed_url

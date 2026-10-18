
import pytest
from fastapi import HTTPException

from app.services.evidence_storage import (
    MAX_FILE_SIZE,
    validate_file_content,
    upload_evidence_file,
    create_evidence_signed_url,
)


@pytest.mark.parametrize(
    "content_type,content",
    [
        ("image/jpeg", b"\xff\xd8\xff" + b"\x00" * 12),
        ("image/png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 12),
        ("image/webp", b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP"),
        ("application/pdf", b"%PDF-1.7\n"),
        ("text/plain", b"This is a UTF-8 text file.\n"),
        ("text/plain", b"\xef\xbb\xbfUTF-8 text with BOM"),
    ],
)
def test_accepts_supported_file_signatures(content_type, content):
    validate_file_content(content, content_type)


@pytest.mark.parametrize(
    "content_type,content",
    [
        ("image/jpeg", b"not a JPEG"),
        ("image/png", b"not a PNG"),
        ("image/webp", b"not a WEBP"),
        ("application/pdf", b"not a PDF"),
        ("text/plain", b"\x00binary\x00content"),
        ("text/plain", b"\xff\xfe\xfa"),
    ],
)
def test_rejects_invalid_file_contents(content_type, content):
    with pytest.raises(HTTPException) as exc_info:
        validate_file_content(content, content_type)

    assert exc_info.value.status_code == 415


def test_rejects_unsupported_content_type():
    with pytest.raises(HTTPException) as exc_info:
        validate_file_content(b"some content", "application/octet-stream")

    assert exc_info.value.status_code == 415


def test_rejects_empty_upload_before_storage():
    from unittest.mock import Mock
    from fastapi import UploadFile
    from io import BytesIO

    file = UploadFile(
        filename="evidence.txt",
        file=BytesIO(b""),
        headers={"content-type": "text/plain"},
    )
    client = Mock()

    with pytest.raises(HTTPException) as exc_info:
        upload_evidence_file(1, file, client=client)

    assert exc_info.value.status_code == 400
    client.storage.from_.assert_not_called()


def test_rejects_oversized_upload_before_storage():
    from unittest.mock import Mock
    from fastapi import UploadFile
    from io import BytesIO

    content = b"A" * (MAX_FILE_SIZE + 1)
    file = UploadFile(
        filename="evidence.txt",
        file=BytesIO(content),
        headers={"content-type": "text/plain"},
    )
    client = Mock()

    with pytest.raises(HTTPException) as exc_info:
        upload_evidence_file(1, file, client=client)

    assert exc_info.value.status_code == 413
    client.storage.from_.assert_not_called()


def test_rejects_mismatched_mime_type_before_storage():
    from unittest.mock import Mock
    from fastapi import UploadFile
    from io import BytesIO

    file = UploadFile(
        filename="evidence.png",
        file=BytesIO(b"this is not a PNG"),
        headers={"content-type": "image/png"},
    )
    client = Mock()

    with pytest.raises(HTTPException) as exc_info:
        upload_evidence_file(1, file, client=client)

    assert exc_info.value.status_code == 415
    client.storage.from_.assert_not_called()

from unittest.mock import Mock


@pytest.mark.parametrize(
    "storage_path",
    [
        "",
        "/12/evidence.pdf",
        "13/evidence.pdf",
        "12/../evidence.pdf",
        "12\\evidence.pdf",
        "12/evidence/extra.pdf",
        "../12/evidence.pdf",
    ],
)
def test_rejects_invalid_signed_url_paths_before_storage(storage_path):
    client = Mock()

    with pytest.raises(HTTPException) as exc_info:
        create_evidence_signed_url(
            storage_path,
            report_id=12,
            client=client,
        )

    assert exc_info.value.status_code == 400
    client.storage.from_.assert_not_called()

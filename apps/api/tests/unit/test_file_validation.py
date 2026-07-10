"""File validation unit tests."""

import pytest

from eaw.domain.common.errors import ValidationAppError
from eaw.infrastructure.storage.file_validation import (
    extract_text_preview,
    validate_upload,
)


def test_validate_txt_ok() -> None:
    data = b"Hello knowledge base"
    v = validate_upload(
        filename="notes.txt",
        content_type="text/plain",
        data=data,
        max_bytes=1024 * 1024,
    )
    assert v.extension == ".txt"
    assert v.size_bytes == len(data)
    assert len(v.checksum_sha256) == 64


def test_reject_exe() -> None:
    with pytest.raises(ValidationAppError):
        validate_upload(
            filename="virus.exe",
            content_type="application/octet-stream",
            data=b"MZ",
            max_bytes=1024,
        )


def test_reject_oversized() -> None:
    with pytest.raises(ValidationAppError):
        validate_upload(
            filename="big.txt",
            content_type="text/plain",
            data=b"x" * 100,
            max_bytes=10,
        )


def test_pdf_magic() -> None:
    with pytest.raises(ValidationAppError):
        validate_upload(
            filename="fake.pdf",
            content_type="application/pdf",
            data=b"not a pdf",
            max_bytes=1024,
        )


def test_preview_txt() -> None:
    text = extract_text_preview(b"Line one\nLine two", ".txt")
    assert text and "Line one" in text

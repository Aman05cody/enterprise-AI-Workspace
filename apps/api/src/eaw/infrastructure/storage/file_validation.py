"""Upload validation helpers."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from eaw.domain.common.errors import ValidationAppError

# Extension → allowed content-types (loose match)
ALLOWED_TYPES: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
    ".txt": {"text/plain", "application/octet-stream"},
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
    ".csv": {"text/csv", "text/plain", "application/csv", "application/octet-stream"},
    ".pptx": {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/octet-stream",
    },
}

MAGIC_PREFIXES: list[tuple[bytes, str]] = [
    (b"%PDF", ".pdf"),
    (b"PK\x03\x04", ".zip_office"),  # docx/pptx are zip
]


@dataclass
class ValidatedFile:
    filename: str
    extension: str
    content_type: str
    size_bytes: int
    checksum_sha256: str
    data: bytes


def _normalize_filename(name: str) -> str:
    base = name.replace("\\", "/").split("/")[-1].strip()
    base = re.sub(r"[^\w.\- ()\[\]]+", "_", base)
    if not base or base in {".", ".."}:
        raise ValidationAppError("Invalid filename")
    return base[:500]


def validate_upload(
    *,
    filename: str,
    content_type: str | None,
    data: bytes,
    max_bytes: int,
) -> ValidatedFile:
    if not data:
        raise ValidationAppError("Empty file")
    if len(data) > max_bytes:
        mb = max_bytes // (1024 * 1024)
        raise ValidationAppError(f"File exceeds maximum size of {mb} MB")

    safe_name = _normalize_filename(filename)
    ext = "." + safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    if ext not in ALLOWED_TYPES:
        raise ValidationAppError(
            f"Unsupported file type '{ext}'. Allowed: PDF, DOCX, TXT, MD, CSV, PPTX"
        )

    ctype = (content_type or "application/octet-stream").split(";")[0].strip().lower()
    allowed = ALLOWED_TYPES[ext]
    if ctype not in allowed and ctype != "application/octet-stream":
        # soft check — some browsers send wrong MIME; magic helps for PDF
        if not data.startswith(b"%PDF") and ext == ".pdf":
            raise ValidationAppError("Content type does not match PDF")
        if ext not in {".txt", ".md", ".csv", ".docx", ".pptx"}:
            raise ValidationAppError(f"Unexpected content type: {ctype}")

    if ext == ".pdf" and not data.startswith(b"%PDF"):
        raise ValidationAppError("File content is not a valid PDF")

    if ext in {".docx", ".pptx"} and not data.startswith(b"PK"):
        raise ValidationAppError(f"File content is not a valid {ext[1:].upper()} archive")

    checksum = hashlib.sha256(data).hexdigest()
    return ValidatedFile(
        filename=safe_name,
        extension=ext,
        content_type=ctype if ctype in allowed else next(iter(ALLOWED_TYPES[ext])),
        size_bytes=len(data),
        checksum_sha256=checksum,
        data=data,
    )


def extract_text_preview(data: bytes, extension: str, *, max_chars: int = 4000) -> str | None:
    """Best-effort text extraction for preview (Phase 3)."""
    try:
        if extension in {".txt", ".md", ".csv"}:
            text = data.decode("utf-8", errors="replace")
            return text[:max_chars]
        if extension == ".pdf":
            try:
                from pypdf import PdfReader
                import io

                reader = PdfReader(io.BytesIO(data))
                parts: list[str] = []
                for page in reader.pages[:5]:
                    parts.append(page.extract_text() or "")
                    if sum(len(p) for p in parts) >= max_chars:
                        break
                text = "\n".join(parts).strip()
                return text[:max_chars] if text else None
            except Exception:  # noqa: BLE001
                return None
        if extension == ".docx":
            try:
                import io
                from docx import Document

                doc = Document(io.BytesIO(data))
                text = "\n".join(p.text for p in doc.paragraphs if p.text)
                return text[:max_chars] if text else None
            except Exception:  # noqa: BLE001
                return None
        if extension == ".pptx":
            try:
                import io
                from pptx import Presentation

                prs = Presentation(io.BytesIO(data))
                parts = []
                for slide in prs.slides[:10]:
                    for shape in slide.shapes:
                        if hasattr(shape, "text") and shape.text:
                            parts.append(shape.text)
                text = "\n".join(parts)
                return text[:max_chars] if text else None
            except Exception:  # noqa: BLE001
                return None
    except Exception:  # noqa: BLE001
        return None
    return None

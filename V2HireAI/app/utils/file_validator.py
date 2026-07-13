"""
File validation utilities.

Validates uploaded files for size, extension, and MIME type.
Raises typed exceptions that map to clean HTTP responses.
"""
import hashlib
import os
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings
from app.core.exceptions import FileSizeExceededError, InvalidFileTypeError

# Allowed MIME types keyed by file extension
_ALLOWED_MIME_TYPES: dict[str, list[str]] = {
    "pdf": ["application/pdf"],
    "docx": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",  # Some systems report DOCX as zip
    ],
}


def validate_file_extension(filename: str) -> str:
    """
    Validate file has an allowed extension.

    Returns:
        The lowercased extension (without dot).

    Raises:
        InvalidFileTypeError: if extension is not in the allowed list.
    """
    ext = Path(filename).suffix.lstrip(".").lower()
    if ext not in settings.allowed_extensions:
        raise InvalidFileTypeError(
            message=(
                f"File extension '.{ext}' is not allowed. "
                f"Allowed: {settings.allowed_extensions}"
            ),
            details={"filename": filename, "extension": ext},
        )
    return ext


def validate_file_size(file_size_bytes: int) -> None:
    """
    Validate file size does not exceed the configured maximum.

    Raises:
        FileSizeExceededError: if file is too large.
    """
    if file_size_bytes > settings.max_file_size_bytes:
        raise FileSizeExceededError(
            message=(
                f"File size {file_size_bytes / (1024*1024):.1f} MB exceeds "
                f"the maximum allowed {settings.max_file_size_mb} MB."
            ),
            details={
                "file_size_mb": round(file_size_bytes / (1024 * 1024), 2),
                "max_size_mb": settings.max_file_size_mb,
            },
        )


def validate_mime_type(file_path: Path, extension: str) -> None:
    """
    Validate file MIME type matches the declared extension.

    Uses python-magic for reliable MIME detection.
    Falls back silently if magic is unavailable (e.g., test environments).

    Raises:
        InvalidFileTypeError: if MIME type does not match extension.
    """
    try:
        import magic  # type: ignore[import-untyped]
        detected_mime = magic.from_file(str(file_path), mime=True)
        allowed_mimes = _ALLOWED_MIME_TYPES.get(extension, [])
        if detected_mime not in allowed_mimes:
            raise InvalidFileTypeError(
                message=(
                    f"File MIME type '{detected_mime}' does not match "
                    f"the declared extension '.{extension}'."
                ),
                details={
                    "detected_mime": detected_mime,
                    "allowed_mimes": allowed_mimes,
                    "extension": extension,
                },
            )
    except ImportError:
        # python-magic not available — skip MIME check
        pass


def compute_sha256(file_path: Path) -> str:
    """
    Compute SHA-256 hash of a file for duplicate detection.

    Returns:
        Hex-encoded SHA-256 digest string (64 chars).
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

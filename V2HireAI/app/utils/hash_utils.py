"""
Hash utilities for file deduplication.
"""
import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    """
    Compute the SHA-256 hex digest of a file.

    Reads in 64 KB chunks to handle large files without loading
    the entire file into memory.

    Returns:
        64-character lowercase hex string.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 hex digest of an in-memory bytes object."""
    return hashlib.sha256(data).hexdigest()

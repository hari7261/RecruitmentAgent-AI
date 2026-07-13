"""
Structured logging configuration.

Sets up rotating file + console handlers with a consistent format.
Log level and output directory are driven by Settings.
"""
import logging
import logging.handlers
from pathlib import Path

from app.core.config import settings

_LOG_DIR = Path.home() / ".resume_ats" / "logs"  # Outside project — stops watchfiles reload spam
_LOG_FILE = _LOG_DIR / "ats.log"
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB per file
_BACKUP_COUNT = 5


def configure_logging() -> None:
    """Configure root logger with rotating file + console handlers."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Rotating File Handler ────────────────────────────────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        filename=_LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    # ── Console Handler ──────────────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # ── Root Logger ──────────────────────────────────────────────────────────
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers on reload (e.g. uvicorn --reload)
    if not root_logger.handlers:
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "multipart", "PIL", "easyocr", "watchfiles"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger (call after configure_logging())."""
    return logging.getLogger(name)

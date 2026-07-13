"""
Soft Delete mixin for SQLAlchemy models.

Adds a `deleted_at` DateTime column. Queries must filter out
`deleted_at IS NOT NULL` rows. The BaseRepository will provide
`soft_delete()` and override `get_all()` to exclude soft-deleted rows.

Does NOT use SQLAlchemy `soft_delete` plugin — pure mixin approach
for maximum control and MySQL compatibility.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class SoftDeleteMixin:
    """Mixin adding soft-delete support to an ORM model."""

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

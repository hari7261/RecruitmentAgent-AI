"""
Generic async repository base.

Uses SQLAlchemy 2.0 select() style (no legacy Query API).
Type-safe via Generic[ModelT].
"""
import logging
from datetime import datetime, timezone
from typing import Any, Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select, update, delete as sa_delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.exceptions import ValidationError
from app.database.base import Base
from app.database.mixins import SoftDeleteMixin

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Provides async CRUD operations for any SQLAlchemy ORM model.

    Usage:
        class MyRepo(BaseRepository[MyModel]):
            def __init__(self, session): super().__init__(MyModel, session)
    """

    def __init__(self, model: Type[ModelT], session: AsyncSession) -> None:
        self._model = model
        self._session = session

    def _apply_tenant_filter(
        self,
        stmt: Select,
        tenant_id: Optional[str] = None,
        *,
        allow_unscoped: bool = False,
    ) -> Select:
        """
        If the model has a tenant_id column, filter by it.
        H1 Fix: For tenant-scoped models, tenant_id should be explicitly provided.
        """
        if hasattr(self._model, "tenant_id"):
            if tenant_id is None:
                if allow_unscoped:
                    return stmt
                raise ValidationError(
                    message=f"Tenant scope is required for {self._model.__name__} queries",
                    details={"model": self._model.__name__},
                )
            stmt = stmt.where(self._model.tenant_id == tenant_id)
        return stmt

    def _apply_deleted_filter(self, stmt: Select) -> Select:
        """Exclude soft-deleted rows if the model supports soft delete."""
        if issubclass(self._model, SoftDeleteMixin):
            stmt = stmt.where(self._model.deleted_at.is_(None))
        return stmt

    async def create(self, obj: ModelT) -> ModelT:
        """Persist a new model instance."""
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def get(
        self,
        record_id: Any,
        tenant_id: Optional[str] = None,
        *,
        allow_unscoped: bool = False,
    ) -> Optional[ModelT]:
        """Fetch a single record by primary key, optionally scoped to tenant."""
        stmt = select(self._model).where(self._model.id == record_id)
        stmt = self._apply_tenant_filter(stmt, tenant_id, allow_unscoped=allow_unscoped)
        stmt = self._apply_deleted_filter(stmt)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        tenant_id: Optional[str] = None,
        allow_unscoped: bool = False,
    ) -> Sequence[ModelT]:
        """Fetch all records with optional pagination and tenant filter."""
        stmt = select(self._model)
        stmt = self._apply_tenant_filter(stmt, tenant_id, allow_unscoped=allow_unscoped)
        stmt = self._apply_deleted_filter(stmt)
        result = await self._session.execute(stmt.offset(offset).limit(limit))
        return result.scalars().all()

    async def update(self, obj: ModelT) -> ModelT:
        """Merge and flush changes to an existing model instance."""
        merged = await self._session.merge(obj)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def delete(self, obj: ModelT) -> None:
        """Delete a model instance (hard delete)."""
        await self._session.delete(obj)
        await self._session.flush()

    async def soft_delete(self, record_id: Any, tenant_id: Optional[str] = None) -> Optional[ModelT]:
        """Soft-delete by setting deleted_at timestamp. L1 Fix: Use UTC timezone."""
        if not issubclass(self._model, SoftDeleteMixin):
            raise TypeError(f"Model {self._model.__name__} does not support soft delete")

        obj = await self.get(record_id, tenant_id)
        if not obj:
            return None

        obj.deleted_at = datetime.now(timezone.utc)
        await self._session.flush()
        return obj

    async def count(self, tenant_id: Optional[str] = None, *, allow_unscoped: bool = False) -> int:
        """Return total row count for the model's table, optionally filtered by tenant."""
        stmt = select(func.count()).select_from(self._model)
        stmt = self._apply_tenant_filter(stmt, tenant_id, allow_unscoped=allow_unscoped)
        stmt = self._apply_deleted_filter(stmt)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def exists(
        self,
        record_id: Any,
        tenant_id: Optional[str] = None,
        *,
        allow_unscoped: bool = False,
    ) -> bool:
        """Check if a record exists by primary key."""
        obj = await self.get(record_id, tenant_id, allow_unscoped=allow_unscoped)
        return obj is not None

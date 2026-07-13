"""
URL slug generation utilities.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def generate_slug(text: str, max_length: int = 60) -> str:
    """
    Generate a URL-safe slug from a text string.

    - Lowercase
    - Replace spaces/special chars with hyphens
    - Remove consecutive hyphens
    - Trim to max_length
    """
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug or "item"


async def ensure_unique_slug(
    session,
    model_class,
    base_slug: str,
    tenant_id: Optional[str] = None,
    max_attempts: int = 100,
) -> str:
    """
    Ensure a slug is unique within a tenant scope.

    Appends -1, -2, etc. if the slug already exists.
    """
    from sqlalchemy import select

    slug = base_slug
    for i in range(1, max_attempts + 1):
        stmt = select(model_class).where(model_class.slug == slug)
        if hasattr(model_class, "tenant_id") and tenant_id:
            stmt = stmt.where(model_class.tenant_id == tenant_id)
        result = await session.execute(stmt)
        if not result.scalar_one_or_none():
            return slug
        slug = f"{base_slug}-{i}"

    raise ValueError(f"Could not generate unique slug for '{base_slug}' after {max_attempts} attempts")

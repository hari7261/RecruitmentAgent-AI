"""
SQLAlchemy DeclarativeBase.

Importing this module (not the engine) ensures models are isolated
from connection details — makes PostgreSQL migration trivial.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass

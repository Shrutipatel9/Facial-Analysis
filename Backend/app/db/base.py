"""Declarative base for all SQLAlchemy models.

Every model in app/models/ must inherit from Base so that Alembic's
autogenerate (wired to Base.metadata in alembic/env.py) can see it.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

"""Base class shared by all SQLAlchemy database models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """All database tables inherit from this class."""

    pass

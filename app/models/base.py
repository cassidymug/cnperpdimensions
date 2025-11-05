from datetime import datetime, date
from typing import Any, Dict
from decimal import Decimal
import enum
from sqlalchemy import Column, DateTime, func
from sqlalchemy.ext.declarative import declared_attr
from app.core.database import Base


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps"""
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class BaseModel(Base, TimestampMixin):
    """Base model with common functionality"""
    __abstract__ = True

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name"""
        return cls.__name__.lower() + "s"

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        data: Dict[str, Any] = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Normalize JSON-unsafe types
            if isinstance(value, enum.Enum):
                value = value.value
            elif isinstance(value, Decimal):
                # Convert to float for JSON friendliness
                value = float(value)
            elif isinstance(value, (datetime, date)):
                value = value.isoformat()

            data[column.name] = value

        return data

    def update(self, **kwargs) -> None:
        """Update model attributes"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value) 
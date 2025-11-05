"""Custom SQLAlchemy types for cross-database compatibility."""

from typing import List, Any, Optional
from sqlalchemy import types, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Dialect
import json


class StringArray(types.TypeDecorator):
    """
    Hybrid type that uses PostgreSQL ARRAY for PostgreSQL databases
    and JSON-encoded TEXT for other databases (like SQLite).
    
    This provides optimal storage for PostgreSQL while maintaining
    compatibility with other database systems.
    """
    
    impl = Text
    cache_ok = True
    
    def load_dialect_impl(self, dialect: Dialect) -> types.TypeEngine:
        """Choose the appropriate storage type based on database dialect."""
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(postgresql.ARRAY(Text))
        else:
            return dialect.type_descriptor(Text)
    
    def process_bind_param(self, value: Optional[List[str]], dialect: Dialect) -> Any:
        """Convert Python list to database representation."""
        if value is None:
            return None
            
        # Ensure we have a list
        if not isinstance(value, (list, tuple)):
            value = [str(value)] if value else []
        
        if dialect.name == 'postgresql':
            # PostgreSQL can handle the list directly
            return list(value)
        else:
            # Other databases: store as JSON string
            return json.dumps(list(value))
    
    def process_result_value(self, value: Any, dialect: Dialect) -> Optional[List[str]]:
        """Convert database representation back to Python list."""
        if value is None:
            return None
            
        if dialect.name == 'postgresql':
            # PostgreSQL returns the list directly
            return list(value) if value else []
        else:
            # Other databases: parse JSON string
            if not value:
                return []
            try:
                result = json.loads(value)
                return list(result) if isinstance(result, (list, tuple)) else []
            except (json.JSONDecodeError, TypeError):
                return []


class JSONList(types.TypeDecorator):
    """
    Generic list type that stores as JSON TEXT.
    Useful for lists that might contain non-string data.
    """
    
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value: Optional[List[Any]], dialect: Dialect) -> Optional[str]:
        """Convert Python list to JSON string."""
        if value is None:
            return None
        if not isinstance(value, (list, tuple)):
            value = [value] if value else []
        return json.dumps(list(value))
    
    def process_result_value(self, value: Optional[str], dialect: Dialect) -> Optional[List[Any]]:
        """Convert JSON string back to Python list."""
        if not value:
            return []
        try:
            result = json.loads(value)
            return list(result) if isinstance(result, (list, tuple)) else []
        except (json.JSONDecodeError, TypeError):
            return []
"""
Security module - ALL AUTHENTICATION DISABLED FOR DEVELOPMENT
"""
from datetime import datetime, timedelta
from typing import Any, Optional, Union, Dict, List
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

# Create password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# Dummy constants for development
SECRET_KEY = "dummy-key-for-development"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class DummyUser:
    """Dummy user class for development without authentication"""
    def __init__(self):
        self.id = "dev-user-id"
        self.username = "developer"
        self.email = "dev@localhost"
        self.role = "superadmin"
        self.branch_id = "default-branch"
        self.is_active = True

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Always return True for development"""
    return True

def get_password_hash(password: str) -> str:
    """Return dummy hash for development"""
    return "dummy-hash-for-development"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Return dummy token for development"""
    return "dummy-token-for-development"

def verify_token(token: str) -> Optional[dict]:
    """Always return valid token data for development"""
    return {"sub": "developer", "role": "superadmin"}

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> DummyUser:
    """Always return dummy user for development"""
    return DummyUser()

def get_current_active_user(current_user: DummyUser = Depends(get_current_user)) -> DummyUser:
    """Always return dummy user for development"""
    return DummyUser()

def require_roles(*roles) -> Any:
    """No-op decorator for development"""
    def decorator(func):
        return func
    return decorator

def require_any(*roles) -> Any:
    """No-op decorator for development"""
    def decorator(func):
        return func
    return decorator

def forbid_roles(*roles) -> Any:
    """No-op decorator for development"""
    def decorator(func):
        return func
    return decorator

def enforce_branch_scope(user: DummyUser, target_branch_id: str = None) -> bool:
    """Always return True for development"""
    return True

def check_branch_access(user: DummyUser, branch_id: str) -> bool:
    """Always return True for development"""
    return True

def require_permission(permission: str) -> Any:
    """No-op decorator for development"""
    def decorator(func):
        return func
    return decorator

def require_permission_or_roles(permission: str, *roles) -> Any:
    """No-op decorator for development"""
    def decorator(func):
        return func
    return decorator

def has_permission(user: DummyUser, permission: str) -> bool:
    """Always return True for development"""
    return True

def has_role(user: DummyUser, role: str) -> bool:
    """Always return True for development"""
    return True

def normalize_role(role: str) -> str:
    """Return role as-is for development"""
    return role.lower()

def expand_roles(roles: List[str]) -> List[str]:
    """Return roles as-is for development"""
    return roles

def check_permission() -> bool:
    """Always return True for development"""
    return True

def apply_branch_scope(query, model_class, user=None):
    """Return query unchanged for development"""
    return query

# Constants for role checking (all allowed in development)
ALLOWED_EVERYTHING = ["superadmin", "admin", "administrator", "developer", "user", "staff", "manager", "accountant"]
UNIVERSAL_ROLES = ["super_admin", "admin", "accountant"]

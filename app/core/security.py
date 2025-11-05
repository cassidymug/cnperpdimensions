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
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

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
    """Create a real JWT token for development"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """Always return valid token data for development"""
    return {"sub": "developer", "role": "superadmin"}

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Get current user from JWT token"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # For now, return a simple user object with the ID from the token
    # In production, you would fetch the user from the database
    from app.models.user import User
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return user
    finally:
        db.close()

def get_current_active_user(current_user = Depends(get_current_user)):
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

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

def log_user_action(user, action: str, details: str = None):
    """No-op function for development"""
    pass

def require_branch_match(*args, **kwargs):
    """No-op decorator for development"""
    def decorator(func):
        return func
    return decorator

def require_roles(*roles) -> Any:
    """No-op decorator for development"""
    def decorator(func):
        return func
    return decorator

# Constants for role checking (all allowed in development)
ALLOWED_EVERYTHING = ["superadmin", "admin", "administrator", "developer", "user", "staff", "manager", "accountant"]
UNIVERSAL_ROLES = ["super_admin", "admin", "accountant"]
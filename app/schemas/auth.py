from pydantic import BaseModel, ConfigDict
from datetime import datetime


class UserLogin(BaseModel):
    """User login request schema"""
    username: str
    password: str
    # Optional branch selectors from the login screen
    branch_id: str | None = None
    branch_code: str | None = None


class Token(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str
    user_id: str
    username: str
    role: str
    branch_id: str | None = None
    branch_code: str | None = None
    branch_name: str | None = None


class UserCreate(BaseModel):
    """User creation schema"""
    username: str
    password: str
    role: str = "staff"
    branch_id: str = None
    email: str = None
    first_name: str = None
    last_name: str = None
    phone: str = None
    address: str = None
    notes: str = None


class UserResponse(BaseModel):
    """User response schema with extended fields for frontend user management UI"""
    id: str
    username: str
    role: str
    branch_id: str | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    active: bool | None = None
    last_login: datetime | None = None
    created_at: datetime | None = None
    address: str | None = None
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """User update schema"""
    email: str = None
    first_name: str = None
    last_name: str = None
    phone: str = None
    role: str = None
    branch_id: str = None
    active: bool = None
    address: str = None
    notes: str = None 
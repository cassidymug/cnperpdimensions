from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str = "staff"
    branch_id: Optional[str] = None
    active: bool = True


class UserCreate(UserBase):
    """User creation schema"""
    password: str


class UserUpdate(BaseModel):
    """User update schema"""
    username: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    branch_id: Optional[str] = None
    active: Optional[bool] = None
    password: Optional[str] = None


class User(UserBase):
    """User schema for authentication"""
    id: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    login_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    """User response schema"""
    id: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    login_count: int = 0

    model_config = ConfigDict(from_attributes=True)
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.branch import Branch
from app.core.security import get_password_hash
from .registry import register

# Sample demo users removed - users are created via seed_all.py
# This file is kept for backwards compatibility but does not create additional sample users
DEMO = [
    # Sample users removed - add users via the application interface
]

@register("demo_users")
def seed_demo_users(db: Session):
    """
    Demo users seeding disabled.
    Users are created via the main seed_all.py script.
    Add additional users via the application interface.
    """
    # No demo users to seed
    pass

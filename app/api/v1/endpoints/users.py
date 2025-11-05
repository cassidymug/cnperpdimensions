from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, func
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime

from app.core.database import get_db
from app.core.security import require_any, get_password_hash, verify_password
from app.models.user import User
from app.models.branch import Branch
from app.models.role import Role
from app.schemas.auth import UserCreate, UserResponse, UserUpdate
from app.core.security import log_user_action
from pydantic import BaseModel
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)
router = APIRouter()

# Define role hierarchy and branch access rules
GLOBAL_ROLES = {"super_admin", "admin", "accountant"}  # Can access any branch
BRANCH_SPECIFIC_ROLES = {"manager", "cashier", "staff"}  # Must be assigned to specific branches

class UserDetailResponse(BaseModel):
    id: str
    username: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    role: str
    branch_id: Optional[str]
    branch_name: Optional[str]
    branch_code: Optional[str]
    active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    last_login: Optional[datetime]
    login_count: Optional[int]
    notes: Optional[str]

class BranchAssignmentRequest(BaseModel):
    branch_id: str

class UserCreateRequest(BaseModel):
    username: str
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    role: str
    branch_id: Optional[str] = None
    notes: Optional[str] = None

class UserUpdateRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    role: Optional[str] = None
    branch_id: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None


@router.get("/", response_model=List[UserResponse])
async def get_users(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    role: Optional[str] = Query(None, description="Filter by role"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    branch_id: Optional[str] = Query(None, description="Filter by branch id"),
    search: Optional[str] = Query(None, description="Search username, email, first/last name")
):
    """Get users with filtering & pagination and branch access rules."""
    query = db.query(User)

    # Filter by active status
    if active is not None:
        query = query.filter(User.active == active)
    else:
        query = query.filter(User.active == True)

    if role:
        query = query.filter(func.lower(User.role) == role.lower())
    if branch_id:
        query = query.filter(User.branch_id == branch_id)
    if search:
        like = f"%{search.lower()}%"
        query = query.filter(or_(
            func.lower(User.username).like(like),
            func.lower(User.email).like(like),
            func.lower(User.first_name).like(like),
            func.lower(User.last_name).like(like)
        ))

    total = query.count()
    users = query.offset(skip).limit(limit).all()

    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            branch_id=user.branch_id,
            active=user.active,
            created_at=user.created_at,
            last_login=user.last_login
        ) for user in users
    ]


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(user_id: str, db: Session = Depends(get_db)):
    """Get a specific user by ID with full details"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserDetailResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        address=user.address,
        role=user.role,
        branch_id=user.branch_id,
        branch_name=user.branch.name if user.branch else None,
        branch_code=user.branch.code if user.branch else None,
        active=user.active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
        login_count=user.login_count,
        notes=user.notes
    )


@router.post("/", response_model=UserResponse)
async def create_user(user_data: UserCreateRequest, db: Session = Depends(get_db)):
    """Create a new user with proper branch assignment validation"""

    # Validate role and branch assignment rules
    if user_data.role in BRANCH_SPECIFIC_ROLES:
        if not user_data.branch_id:
            raise HTTPException(
                status_code=400,
                detail=f"Users with role '{user_data.role}' must be assigned to a specific branch"
            )

        # Verify branch exists and is active
        branch = db.query(Branch).filter(
            Branch.id == user_data.branch_id,
            Branch.active == True
        ).first()
        if not branch:
            raise HTTPException(status_code=400, detail="Invalid or inactive branch")

    elif user_data.role in GLOBAL_ROLES:
        # Global roles don't require branch assignment (but can have one)
        if user_data.branch_id:
            branch = db.query(Branch).filter(Branch.id == user_data.branch_id).first()
            if not branch:
                raise HTTPException(status_code=400, detail="Invalid branch")
    else:
        raise HTTPException(status_code=400, detail=f"Invalid role: {user_data.role}")

    # Check for existing username/email
    existing_user = db.query(User).filter(
        (User.username == user_data.username) |
        (User.email == user_data.email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username or email already exists"
        )

    # Create new user
    try:
        new_user = User(
            id=str(uuid4()),
            username=user_data.username,
            email=user_data.email,
            password_digest=get_password_hash(user_data.password),
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            address=user_data.address,
            role=user_data.role,
            branch_id=user_data.branch_id,
            active=True,
            notes=user_data.notes,
            password_changed_at=datetime.utcnow()
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return UserResponse(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            role=new_user.role,
            branch_id=new_user.branch_id,
            active=new_user.active,
            created_at=new_user.created_at,
            last_login=new_user.last_login
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Username or email already exists"
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update user information with branch assignment validation"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields if provided
    update_data = user_data.dict(exclude_unset=True)

    # Handle password update
    if 'password' in update_data:
        update_data['password_digest'] = get_password_hash(update_data.pop('password'))
        update_data['password_changed_at'] = datetime.utcnow()

    # Validate role and branch changes
    new_role = update_data.get('role', user.role)
    new_branch_id = update_data.get('branch_id', user.branch_id)

    if new_role in BRANCH_SPECIFIC_ROLES and not new_branch_id:
        raise HTTPException(
            status_code=400,
            detail=f"Users with role '{new_role}' must be assigned to a specific branch"
        )

    # Update user
    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(user)

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            branch_id=user.branch_id,
            active=user.active,
            created_at=user.created_at,
            last_login=user.last_login
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or email already exists")


@router.post("/{user_id}/assign-branch")
async def assign_user_to_branch(
    user_id: str,
    assignment: BranchAssignmentRequest,
    db: Session = Depends(get_db)
):
    """Assign or reassign a user to a branch"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify branch exists
    branch = db.query(Branch).filter(
        Branch.id == assignment.branch_id,
        Branch.active == True
    ).first()
    if not branch:
        raise HTTPException(status_code=400, detail="Invalid or inactive branch")

    # Check role compatibility
    if user.role in BRANCH_SPECIFIC_ROLES:
        user.branch_id = assignment.branch_id
    elif user.role in GLOBAL_ROLES:
        # Global users can have a default branch but aren't restricted to it
        user.branch_id = assignment.branch_id
    else:
        raise HTTPException(status_code=400, detail="Invalid user role for branch assignment")

    user.updated_at = datetime.utcnow()
    db.commit()

    return {
        "message": f"User {user.username} successfully assigned to branch {branch.name}",
        "user_id": user.id,
        "branch_id": branch.id,
        "branch_name": branch.name
    }


@router.post("/{user_id}/toggle-status")
async def toggle_user_status(user_id: str, db: Session = Depends(get_db)):
    """Activate or deactivate a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.active = not user.active
    user.updated_at = datetime.utcnow()
    db.commit()

    status_text = "activated" if user.active else "deactivated"
    return {
        "message": f"User {user.username} has been {status_text}",
        "user_id": user.id,
        "active": user.active
    }


@router.get("/branch/{branch_id}/users", response_model=List[UserResponse])
async def get_branch_users(branch_id: str, db: Session = Depends(get_db)):
    """Get all users who can access a specific branch"""
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Get branch-specific users
    branch_users = db.query(User).filter(
        User.branch_id == branch_id,
        User.active == True
    ).all()

    # Get global users (they can access this branch too)
    global_users = db.query(User).filter(
        User.role.in_(GLOBAL_ROLES),
        User.active == True
    ).all()

    # Combine and deduplicate
    all_users = []
    user_ids = set()

    for user in branch_users + global_users:
        if user.id not in user_ids:
            all_users.append(UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role,
                branch_id=user.branch_id,
                active=user.active,
                created_at=user.created_at,
                last_login=user.last_login
            ))
            user_ids.add(user.id)

    return all_users


@router.get("/roles/summary")
async def get_roles_summary(db: Session = Depends(get_db)):
    """Get summary of user roles and their branch access rules"""
    return {
        "global_roles": {
            "roles": list(GLOBAL_ROLES),
            "description": "Can access any branch",
            "branch_required": False
        },
        "branch_specific_roles": {
            "roles": list(BRANCH_SPECIFIC_ROLES),
            "description": "Must be assigned to a specific branch",
            "branch_required": True
        }
    }


@router.get("/roles/summary")
async def get_roles_summary(db: Session = Depends(get_db)):
    """Get summary of user roles and their branch access rules"""
    return {
        "global_roles": {
            "roles": list(GLOBAL_ROLES),
            "description": "Can access any branch",
            "branch_required": False
        },
        "branch_specific_roles": {
            "roles": list(BRANCH_SPECIFIC_ROLES),
            "description": "Must be assigned to a specific branch",
            "branch_required": True
        }
    }

    # Attach pagination metadata via response headers using a FastAPI workaround (return list but set headers in dependency) - simpler: we cannot set here w/out Response; we'll include in custom header if response object passed.
    # For now: client can read X-Total-Count via middleware configured globally (optional). TODO: refactor signature to include Response if needed.
    # We'll try import Response elegantly.
    from fastapi import Response
    # Provide header with total count.
    Response(headers={"X-Total-Count": str(total)} )
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    # Allow managers as well as accountant/admin/super_admin
    # current_user parameter removed for development),
    request: Request = None
):
    """Create a new user (enforces unique username & email)."""
    from app.core.security import get_password_hash

    # Uniqueness checks
    if db.query(User).filter(func.lower(User.username) == user_data.username.lower()).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if user_data.email and db.query(User).filter(func.lower(User.email) == user_data.email.lower()).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        password_digest=hashed_password,
        role=user_data.role,
        branch_id=user_data.branch_id,
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        address=user_data.address,
        notes=user_data.notes,
        active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    try:
        log_user_action(db, None, action="create", module="users", resource_type="user", resource_id=new_user.id, details={"username": new_user.username}, request=request)
    except Exception:
        pass

    return new_user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    # current_user parameter removed for development),
    request: Request = None
):
    """Update a user (email uniqueness enforced)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_update.dict(exclude_unset=True)

    # Enforce unique email if updating
    if update_data.get("email"):
        email_l = update_data["email"].lower()
        existing = db.query(User).filter(func.lower(User.email) == email_l, User.id != user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")

    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)

    try:
        log_user_action(db, None, action="update", module="users", resource_type="user", resource_id=user.id, details=list(update_data.keys()), request=request)
    except Exception:
        pass

    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    # current_user parameter removed for development),
    request: Request = None
):
    """Soft delete a user (set active False)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.active:
        return {"message": "User already inactive"}

    user.active = False
    db.commit()
    try:
        log_user_action(db, None, action="deactivate", module="users", resource_type="user", resource_id=user.id, details=None, request=request)
    except Exception:
        pass
    return {"message": "User deactivated"}


@router.post("/{user_id}/change-password")
async def change_password(
    user_id: str,
    password_data: dict,
    db: Session = Depends(get_db),
    # current_user parameter removed for development)
):
    """Change user password"""
    from app.core.security import get_password_hash

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if "new_password" not in password_data:
        raise HTTPException(status_code=400, detail="New password is required")

    # Hash the new password
    hashed_password = get_password_hash(password_data["new_password"])
    user.password_digest = hashed_password

    db.commit()
    db.refresh(user)

    try:
        log_user_action(db, None, action="change_password", module="users", resource_type="user", resource_id=user.id, details=None)
    except Exception:
        pass
    return {"message": "Password changed successfully"}



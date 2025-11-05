from datetime import timedelta, datetime
import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, SECRET_KEY, ALGORITHM
from jose import jwt, JWTError
from fastapi import Header
from app.models.user import User
from app.models.branch import Branch
from app.models.role import UserAuditLog
from app.models.app_setting import AppSetting
from app.schemas.auth import Token, UserLogin
from pydantic import BaseModel

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)
# from app.core.security import get_current_user  # Removed for development

router = APIRouter()

# Development-friendly expiry helper
def _compute_expiry(db: Session, default_minutes: int = 480) -> timedelta:
    """Return appropriate token lifetime.
    If debug mode or env flags set, extend dramatically to effectively suspend timeouts during development.
    DEV_LONG_SESSION=1 => 30 days
    DEV_DISABLE_TIMEOUT=1 => 5 years
    """
    long_session = False
    ultra = False
    try:
        app_settings = AppSetting.get_instance(db)
        if getattr(app_settings, 'debug_mode', False):
            long_session = True
    except Exception:
        pass
    if os.getenv('DEV_LONG_SESSION', '0') == '1':
        long_session = True
    if os.getenv('DEV_DISABLE_TIMEOUT', '0') == '1':
        long_session = True
        ultra = True
    if ultra:
        return timedelta(days=365*5)  # ~5 years
    if long_session:
        return timedelta(days=30)
    return timedelta(minutes=default_minutes)

class BranchSwitchRequest(BaseModel):
    branch_id: str | None = None

@router.get('/login-branches')
def public_login_branches(db: Session = Depends(get_db)):
    """Public endpoint (no auth) to list active branches for the login page.
    Returns minimal fields to avoid exposing sensitive data."""
    branches = db.query(Branch).filter(Branch.active == True).all()
    return [
        {
            'id': str(b.id),
            'code': b.code,
            'name': b.name,
            'active': b.active
        } for b in branches
    ]

@router.get('/login-branches/health')
def public_login_branches_health(db: Session = Depends(get_db)):
    """Health probe for branch listing and auth preconditions."""
    try:
        branches = db.query(Branch).all()
        active = [b for b in branches if b.active]
        return {
            'total': len(branches),
            'active': len(active),
            'sample': [{ 'id': str(b.id), 'code': b.code, 'active': b.active } for b in active[:5]],
            'ok': len(active) > 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Branch health error: {e}")

UNIVERSAL_ROLES = {"super_admin","admin","accountant"}
BRANCH_SPECIFIC_ROLES = {"manager", "cashier", "staff"}

@router.post('/login-json', response_model=Token)
async def login_json(user_login: UserLogin, db: Session = Depends(get_db)):
    """Enhanced login endpoint with branch-specific authentication.
    Accepts optional `branch_code` or `branch_id` from the login page.
    """
    # 1) Find user by username and ensure active
    user = db.query(User).filter(User.username == user_login.username, User.active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    # 2) Validate password (note: in dev, verify_password is permissive by design)
    if not verify_password(user_login.password, user.password_digest or ""):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    # Helper to resolve a branch from provided inputs
    def resolve_branch():
        if getattr(user_login, 'branch_id', None):
            return db.query(Branch).filter(Branch.id == user_login.branch_id, Branch.active == True).first()
        if getattr(user_login, 'branch_code', None):
            return db.query(Branch).filter(Branch.code == user_login.branch_code, Branch.active == True).first()
        return None

    login_branch = None

    # 3) Branch rules based on role
    if user.role in BRANCH_SPECIFIC_ROLES:
        # Must have an assigned branch
        if not user.branch_id:
            raise HTTPException(status_code=400, detail=f"User with role '{user.role}' must be assigned to a branch before login")
        user_branch = db.query(Branch).filter(Branch.id == user.branch_id, Branch.active == True).first()
        if not user_branch:
            raise HTTPException(status_code=400, detail="Your assigned branch is inactive. Contact administrator.")
        # If a branch was selected, it must match the assigned branch
        selected = resolve_branch()
        if selected and selected.id != user.branch_id:
            raise HTTPException(status_code=403, detail=f"You can only log into your assigned branch: {user_branch.name}")
        login_branch = user_branch
    elif user.role in UNIVERSAL_ROLES:
        # Can log into any active branch (or none)
        selected = resolve_branch()
        if selected is not None:
            login_branch = selected
        else:
            # If user has a default branch, use it; else first active branch if any
            if user.branch_id:
                login_branch = db.query(Branch).filter(Branch.id == user.branch_id).first()
            if not login_branch:
                login_branch = db.query(Branch).filter(Branch.active == True).first()
    else:
        raise HTTPException(status_code=400, detail=f"Invalid user role: {user.role}")

    # 4) Update login stats
    user.last_login = datetime.utcnow()
    user.login_count = (user.login_count or 0) + 1
    db.commit()

    # 5) Issue token with role and branch context
    access_token_expires = _compute_expiry(db)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "branch_id": str(login_branch.id) if login_branch else None,
            "role": user.role
        },
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "username": user.username,
        "role": user.role,
        "branch_id": str(login_branch.id) if login_branch else None,
        "branch_code": login_branch.code if login_branch else None,
        "branch_name": login_branch.name if login_branch else None,
        "can_switch_branches": user.role in UNIVERSAL_ROLES
    }

@router.post('/switch-branch', response_model=Token)
async def switch_branch(payload: BranchSwitchRequest, db: Session = Depends(get_db)):
    """Switch active branch context with role-based validation."""
    # For development, get a user from token if available, otherwise use admin user
    user = db.query(User).filter(User.role.in_(['super_admin','admin'])).first() or db.query(User).first()
    if not user:
        raise HTTPException(status_code=400, detail="No user available for branch switch")

    # Check if user can switch branches
    if user.role in BRANCH_SPECIFIC_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"Users with role '{user.role}' cannot switch branches. They are restricted to their assigned branch."
        )

    target_branch = None
    if payload.branch_id:
        target_branch = db.query(Branch).filter(
            Branch.id == payload.branch_id,
            Branch.active == True
        ).first()
        if not target_branch:
            raise HTTPException(status_code=404, detail="Branch not found or inactive")

    branch_id_for_token = str(payload.branch_id) if payload.branch_id else None

    # Create new token with branch context
    access_token_expires = _compute_expiry(db)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "branch_id": branch_id_for_token,
            "role": user.role
        },
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "username": user.username,
        "role": user.role,
        "branch_id": branch_id_for_token,
        "branch_code": target_branch.code if target_branch else None,
        "branch_name": target_branch.name if target_branch else None,
        "can_switch_branches": user.role in UNIVERSAL_ROLES
    }

@router.post('/refresh', response_model=Token)
async def refresh_access_token(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    """Issue a new access token extending the current session if current token valid & unexpired.
    Preserves the branch context embedded in the existing token, if present.
    """
    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    raw = authorization.split(' ', 1)[1].strip()
    try:
        payload = jwt.decode(raw, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get('sub')
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Confirm user still active
    user = db.query(User).filter(User.id == sub, User.active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User inactive or not found")

    # Preserve branch context from the token if possible, else fallback to user's default
    branch_from_token = payload.get('branch_id') if isinstance(payload, dict) else None
    branch = None
    if branch_from_token:
        branch = db.query(Branch).filter(Branch.id == branch_from_token).first()
    if not branch and user.branch_id:
        branch = db.query(Branch).filter(Branch.id == user.branch_id).first()

    access_token_expires = _compute_expiry(db)
    access_token = create_access_token(
        data={"sub": str(user.id), "branch_id": str(branch.id) if branch else None},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "username": user.username,
        "role": user.role,
        "branch_id": str(branch.id) if branch else None,
        "branch_code": branch.code if branch else None,
        "branch_name": branch.name if branch else None
    }


@router.post("/logout")
@router.get("/logout")
async def logout(db: Session = Depends(get_db)):
    """
    Logout endpoint - clears session server-side if needed
    Frontend should clear localStorage
    """
    # In a stateless JWT system, logout is primarily handled client-side
    # This endpoint exists to provide a proper HTTP endpoint for logout
    # and can be extended for token blacklisting if needed
    return {
        "status": "success",
        "message": "Logged out successfully"
    }

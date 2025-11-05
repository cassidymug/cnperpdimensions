from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.branch import Branch
from app.schemas.branch import Branch as BranchSchema

router = APIRouter()

@router.get("/", response_model=List[BranchSchema])
def read_branches(db: Session = Depends(get_db)):
    """
    Retrieve all branches.
    """
    branches = db.query(Branch).all()
    return branches

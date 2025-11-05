from __future__ import annotations

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.branch import Branch


class BranchLookupCache:
    """Simple in-memory cache for branch metadata.

    Keeps a small dictionary of branch id -> {"id", "name", "code"} that is refreshed
    periodically. Defaults to a 5 minute time-to-live which is a reasonable compromise for
    low-churn branch records while keeping responses consistent across the app.
    """

    _instance: Optional["BranchLookupCache"] = None
    _instance_lock: Lock = Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, ttl_seconds: int = 300):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._ttl = timedelta(seconds=ttl_seconds)
        self._cache: Dict[str, Dict[str, Optional[str]]] = {}
        self._expires_at: Optional[datetime] = None
        self._cache_lock: Lock = Lock()

    def get_branch(self, branch_id: Optional[str], session: Optional[Session] = None) -> Optional[Dict[str, Optional[str]]]:
        if not branch_id:
            return None

        with self._cache_lock:
            if self._is_expired():
                self._refresh_locked(session)

            if branch_id in self._cache:
                return self._cache[branch_id]

        # Cache miss after potential refresh – perform targeted fetch and store
        self._refresh_single(branch_id, session)
        with self._cache_lock:
            return self._cache.get(branch_id)

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _is_expired(self) -> bool:
        if not self._expires_at:
            return True
        return datetime.utcnow() >= self._expires_at

    def _refresh_locked(self, session: Optional[Session] = None) -> None:
        db = session or SessionLocal()
        try:
            records = db.query(Branch.id, Branch.name, Branch.code).all()
            self._cache = {
                record.id: {"id": record.id, "name": record.name, "code": record.code}
                for record in records
            }
            self._expires_at = datetime.utcnow() + self._ttl
        finally:
            if session is None:
                db.close()

    def _refresh_single(self, branch_id: str, session: Optional[Session] = None) -> None:
        db = session or SessionLocal()
        try:
            record = db.query(Branch.id, Branch.name, Branch.code).filter(Branch.id == branch_id).first()
            if not record:
                return
            with self._cache_lock:
                self._cache[branch_id] = {"id": record.id, "name": record.name, "code": record.code}
        finally:
            if session is None:
                db.close()


branch_cache = BranchLookupCache()

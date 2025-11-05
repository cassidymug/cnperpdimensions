from fastapi import APIRouter

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()


@router.get("/")
async def get_notifications():
    """Get notifications"""
    return {"message": "Notifications endpoint - to be implemented"}


@router.get("/unread")
async def get_unread_notifications():
    """Get unread notifications"""
    return {"message": "Unread notifications endpoint - to be implemented"}


@router.post("/mark-read")
async def mark_notification_read():
    """Mark notification as read"""
    return {"message": "Mark notification read endpoint - to be implemented"} 
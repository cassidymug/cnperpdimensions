import uuid
from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Notification(BaseModel):
    """System notification model"""
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    message = Column(String)
    kind = Column(Integer)
    data = Column(Text)
    read = Column(Boolean, default=False)
    # Additional fields for better notification management
    title = Column(String)
    notification_type = Column(String, default="info")  # info, warning, error, success
    priority = Column(String, default="normal")  # low, normal, high, urgent
    category = Column(String)  # system, sales, inventory, accounting, etc.
    action_url = Column(String)
    expires_at = Column(DateTime)
    created_by = Column(ForeignKey("users.id"))
    branch_id = Column(ForeignKey("branches.id"))

    # Relationships
    notification_users = relationship("NotificationUser", back_populates="notification")
    created_by_user = relationship("User")
    branch = relationship("Branch")


class NotificationUser(BaseModel):
    """Notification user association model"""
    __tablename__ = "notification_users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    notification_id = Column(ForeignKey("notifications.id"), nullable=False)
    user_id = Column(ForeignKey("users.id"), nullable=False)
    read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    # Additional fields for better user notification tracking
    dismissed = Column(Boolean, default=False)
    dismissed_at = Column(DateTime)
    action_taken = Column(String)  # clicked, dismissed, ignored
    action_taken_at = Column(DateTime)

    # Relationships
    notification = relationship("Notification", back_populates="notification_users")
    user = relationship("User", back_populates="notification_users") 
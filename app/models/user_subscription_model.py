from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import CHAR
from app.database import Base
import uuid


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subs_id = Column(String(255), ForeignKey("subscriptions.subs_id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(64), nullable=False, default="active")
    feature_entitlements = Column(JSON, nullable=True)  # JSON blob of features/limits for this user
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    usage_metadata = Column(JSON, nullable=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

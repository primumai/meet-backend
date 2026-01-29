from sqlalchemy import Column, String, DateTime, Integer, JSON
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import CHAR
from app.database import Base
import uuid


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(1024), nullable=True)
    subs_id = Column(String(255), unique=True, nullable=False, index=True)
    price = Column(String(64), nullable=False)
    duration_days = Column(Integer, nullable=False)  # Number of days the subscription runs
    feature_entitlements = Column(JSON, nullable=True)  # JSON blob of features/limits
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

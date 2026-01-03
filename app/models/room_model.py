from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from app.database import Base
import uuid


class Room(Base):
    __tablename__ = "rooms"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    room_id = Column(String(255), unique=True, nullable=False, index=True)  # VideoSDK room ID
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    permissions = Column(JSON, nullable=False)  # Store permissions as JSON object
    maximum_participants = Column(Integer, nullable=False, default=10)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship with User
    user = relationship("User", backref="rooms")


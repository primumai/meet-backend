from datetime import datetime, timedelta
from app.database import Base
from sqlalchemy import Column, String, DateTime, ForeignKey
import uuid

class ResetPassword(Base):
    __tablename__ = "reset_passwords"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(100), nullable=False, index=True)
    reset_token = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

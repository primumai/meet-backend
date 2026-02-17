from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import CHAR
from app.database import Base
import uuid

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(CHAR(36), ForeignKey('users.id'), nullable=False, index=True)
    subscription_id = Column(CHAR(36), ForeignKey('subscriptions.id'), nullable=True, index=True)
    invoice_id = Column(String(255), nullable=True, index=True)
    transaction_id = Column(String(255), nullable=True, index=True)
    amount = Column(String(64), nullable=False)
    currency = Column(String(10), default='USD')
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

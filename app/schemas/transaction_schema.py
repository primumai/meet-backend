from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class TransactionResponseSchema(BaseModel):
    """Schema for transaction response"""
    id: str
    user_id: str
    subscription_id: Optional[str] = None
    invoice_id: Optional[str] = None
    transaction_id: Optional[str] = None
    amount: str
    currency: str = "USD"
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TransactionListResponse(BaseModel):
    """Schema for list of transactions"""
    transactions: list[TransactionResponseSchema]
    total: int

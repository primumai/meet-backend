from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class ResetPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class ResetPasswordResponse(BaseModel):
    message: str
    # reset_token: Optional[str] = None

class ResetPasswordInDB(BaseModel):
    email: str
    reset_token: str
    expires_at: datetime
    user_id: str
    
    class Config:
        from_attributes = True

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional

class UserUpdateSchema(BaseModel):
    """Schema for updating user profile"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    current_password: Optional[str] = Field(None, min_length=6)
    new_password: Optional[str] = Field(None, min_length=6)
    is_active: Optional[bool] = None

    @validator('new_password')
    def check_current_password_if_new_password(cls, v, values):
        if v is not None and 'current_password' not in values:
            raise ValueError('Current password is required to set a new password')
        return v

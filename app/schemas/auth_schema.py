from pydantic import BaseModel, EmailStr, Field
from typing import Literal
from datetime import datetime


class UserSignupSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str


class TokenResponseSchema(BaseModel):
    access_token: str
    token_type: Literal["signup", "login"]
    user_id: str  # UUID as string
    role: str


class UserResponseSchema(BaseModel):
    """Schema for user response"""
    id: str
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


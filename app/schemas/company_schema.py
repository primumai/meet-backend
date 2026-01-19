from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class CreateCompanySchema(BaseModel):
    """Schema for creating a company"""
    company_name: str = Field(..., min_length=1, max_length=255, description="Company name")
    email: Optional[EmailStr] = Field(None, description="Company email address")
    contact: Optional[str] = Field(None, max_length=255, description="Company contact information")
    location: Optional[str] = Field(None, max_length=255, description="Company location")


class CompanyResponseSchema(BaseModel):
    """Schema for company response"""
    id: str
    company_name: str
    email: Optional[str]
    contact: Optional[str]
    location: Optional[str]
    apikey: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

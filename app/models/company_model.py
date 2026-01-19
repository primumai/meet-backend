from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import CHAR
from app.database import Base
import uuid


class Company(Base):
    __tablename__ = "companies"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    company_name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    contact = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    apikey = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

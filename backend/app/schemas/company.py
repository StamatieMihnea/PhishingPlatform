from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl


class CompanyBase(BaseModel):
    """Base company schema."""
    name: str = Field(..., min_length=1, max_length=255)
    domain: str = Field(..., min_length=1, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)


class CompanyCreate(CompanyBase):
    """Company creation schema."""
    pass


class CompanyUpdate(BaseModel):
    """Company update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    domain: Optional[str] = Field(None, min_length=1, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class CompanyResponse(BaseModel):
    """Company response schema."""
    id: UUID
    name: str
    domain: str
    logo_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CompanyListResponse(BaseModel):
    """Company list response schema."""
    companies: List[CompanyResponse]
    total: int


class CompanyStats(BaseModel):
    """Company statistics schema."""
    company_id: UUID
    company_name: str
    total_users: int
    total_campaigns: int
    total_emails_sent: int
    total_emails_opened: int
    total_links_clicked: int
    total_credentials_submitted: int
    click_rate: float
    submission_rate: float

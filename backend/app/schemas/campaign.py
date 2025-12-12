from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.campaign import CampaignStatus


class CampaignBase(BaseModel):
    """Base campaign schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    template_id: Optional[UUID] = None


class CampaignCreate(CampaignBase):
    """Campaign creation schema."""
    target_user_ids: List[UUID] = Field(default_factory=list)


class CampaignUpdate(BaseModel):
    """Campaign update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    template_id: Optional[UUID] = None


class CampaignResponse(BaseModel):
    """Campaign response schema."""
    id: UUID
    company_id: UUID
    created_by: UUID
    name: str
    description: Optional[str] = None
    template_id: Optional[UUID] = None
    phishing_url: Optional[str] = None
    status: CampaignStatus
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CampaignListResponse(BaseModel):
    """Campaign list response schema."""
    campaigns: List[CampaignResponse]
    total: int


class CampaignScheduleRequest(BaseModel):
    """Campaign schedule request schema."""
    scheduled_at: datetime


class CampaignStats(BaseModel):
    """Campaign statistics schema."""
    campaign_id: UUID
    campaign_name: str
    status: CampaignStatus
    total_targets: int
    emails_sent: int
    emails_opened: int
    links_clicked: int
    credentials_submitted: int
    open_rate: float
    click_rate: float
    submission_rate: float

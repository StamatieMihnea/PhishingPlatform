from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class CampaignTargetCreate(BaseModel):
    """Campaign target creation schema."""
    user_id: UUID


class CampaignTargetResponse(BaseModel):
    """Campaign target response schema."""
    id: UUID
    campaign_id: UUID
    user_id: UUID
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    email_sent: bool
    email_sent_at: Optional[datetime] = None
    email_opened: bool
    email_opened_at: Optional[datetime] = None
    link_clicked: bool
    link_clicked_at: Optional[datetime] = None
    credentials_submitted: bool
    submitted_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class CampaignTargetListResponse(BaseModel):
    """Campaign target list response schema."""
    targets: List[CampaignTargetResponse]
    total: int

from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.campaign import CampaignStatus
from app.models.security_recommendation import Priority


class DashboardCampaign(BaseModel):
    """Dashboard campaign info for users."""
    id: UUID
    name: str
    description: Optional[str] = None
    status: CampaignStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class DashboardResult(BaseModel):
    """User's phishing test result."""
    campaign_id: UUID
    campaign_name: str
    email_sent_at: Optional[datetime] = None
    email_opened: bool
    email_opened_at: Optional[datetime] = None
    link_clicked: bool
    link_clicked_at: Optional[datetime] = None
    credentials_submitted: bool
    submitted_at: Optional[datetime] = None
    was_phished: bool


class DashboardRecommendation(BaseModel):
    """Security recommendation for user."""
    id: UUID
    title: str
    description: str
    category: str
    priority: Priority


class DashboardStats(BaseModel):
    """User dashboard statistics."""
    total_campaigns: int
    campaigns_passed: int
    campaigns_failed: int
    success_rate: float


class TrainingMaterial(BaseModel):
    """Training material for security awareness."""
    id: UUID
    title: str
    description: str
    content_url: Optional[str] = None
    category: str
    completed: bool = False


class TrainingCompleteRequest(BaseModel):
    """Training completion request."""
    training_id: UUID

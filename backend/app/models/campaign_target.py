import uuid
import secrets
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_tracking_token():
    """Generate a secure tracking token."""
    return secrets.token_urlsafe(32)


class CampaignTarget(Base):
    """Campaign target for tracking phishing interactions."""
    
    __tablename__ = "campaign_targets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    tracking_token = Column(String(64), unique=True, default=generate_tracking_token, nullable=False, index=True)
    
    email_sent = Column(Boolean, default=False, nullable=False)
    email_sent_at = Column(DateTime, nullable=True)
    email_opened = Column(Boolean, default=False, nullable=False)
    email_opened_at = Column(DateTime, nullable=True)
    link_clicked = Column(Boolean, default=False, nullable=False)
    link_clicked_at = Column(DateTime, nullable=True)
    credentials_submitted = Column(Boolean, default=False, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    campaign = relationship("Campaign", back_populates="targets")
    user = relationship("User", back_populates="campaign_targets")
    email_tasks = relationship("EmailTask", back_populates="campaign_target", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<CampaignTarget(id={self.id}, campaign_id={self.campaign_id}, user_id={self.user_id})>"

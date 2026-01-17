import uuid
import secrets
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

# We don't need generate_tracking_token here as we only read/update existing tokens
# But we keep the import if needed for structure matching

class CampaignTarget(Base):
    """Campaign target for tracking phishing interactions. Simplified model without relationships."""
    
    __tablename__ = "campaign_targets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    tracking_token = Column(String(64), unique=True, nullable=False, index=True)
    
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
    
    def __repr__(self):
        return f"<CampaignTarget(id={self.id}, tracking_token={self.tracking_token})>"

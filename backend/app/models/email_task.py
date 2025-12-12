import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class EmailTaskStatus(str, enum.Enum):
    """Email task status enum."""
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    SENT = "SENT"
    FAILED = "FAILED"


class EmailTask(Base):
    """Email task for queue processing."""
    
    __tablename__ = "email_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_target_id = Column(UUID(as_uuid=True), ForeignKey("campaign_targets.id"), nullable=False, index=True)
    status = Column(Enum(EmailTaskStatus), nullable=False, default=EmailTaskStatus.PENDING)
    scheduled_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    campaign_target = relationship("CampaignTarget", back_populates="email_tasks")
    
    def __repr__(self):
        return f"<EmailTask(id={self.id}, status={self.status}, attempts={self.attempts})>"

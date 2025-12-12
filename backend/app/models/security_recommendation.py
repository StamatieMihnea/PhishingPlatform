import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Priority(str, enum.Enum):
    """Priority level for recommendations."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SecurityRecommendation(Base):
    """Security recommendation for users."""
    
    __tablename__ = "security_recommendations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)  # passwords, links, attachments
    priority = Column(Enum(Priority), nullable=False, default=Priority.MEDIUM)
    trigger_condition = Column(String(100), nullable=True)  # What action triggers this recommendation
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<SecurityRecommendation(id={self.id}, title={self.title}, priority={self.priority})>"

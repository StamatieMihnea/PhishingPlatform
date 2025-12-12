import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class DifficultyLevel(str, enum.Enum):
    """Difficulty level for detecting phishing."""
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class EmailTemplate(Base):
    """Email template for phishing campaigns."""
    
    __tablename__ = "email_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True)  # NULL = global template
    name = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=False)
    difficulty = Column(Enum(DifficultyLevel), nullable=False, default=DifficultyLevel.MEDIUM)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    company = relationship("Company", back_populates="email_templates")
    campaigns = relationship("Campaign", back_populates="template")
    
    def __repr__(self):
        return f"<EmailTemplate(id={self.id}, name={self.name}, difficulty={self.difficulty})>"

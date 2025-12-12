from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.email_template import DifficultyLevel


class EmailTemplateBase(BaseModel):
    """Base email template schema."""
    name: str = Field(..., min_length=1, max_length=255)
    subject: str = Field(..., min_length=1, max_length=500)
    body_html: str = Field(..., min_length=1)
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    category: Optional[str] = Field(None, max_length=100)


class EmailTemplateCreate(EmailTemplateBase):
    """Email template creation schema."""
    pass


class EmailTemplateUpdate(BaseModel):
    """Email template update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    subject: Optional[str] = Field(None, min_length=1, max_length=500)
    body_html: Optional[str] = Field(None, min_length=1)
    difficulty: Optional[DifficultyLevel] = None
    category: Optional[str] = Field(None, max_length=100)


class EmailTemplateResponse(BaseModel):
    """Email template response schema."""
    id: UUID
    company_id: Optional[UUID] = None
    name: str
    subject: str
    body_html: str
    difficulty: DifficultyLevel
    category: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EmailTemplateListResponse(BaseModel):
    """Email template list response schema."""
    templates: List[EmailTemplateResponse]
    total: int


class EmailPreviewRequest(BaseModel):
    """Email preview request schema."""
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None

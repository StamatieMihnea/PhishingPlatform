from typing import List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.email_task import EmailTaskStatus


class EmailTaskResponse(BaseModel):
    id: UUID
    campaign_target_id: UUID
    campaign_id: Optional[UUID] = None
    user_email: Optional[str] = None
    status: EmailTaskStatus
    attempts: int
    last_error: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EmailTaskListResponse(BaseModel):
    tasks: List[EmailTaskResponse]
    total: int

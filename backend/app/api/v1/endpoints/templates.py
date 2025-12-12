"""
Email template management endpoints.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.user import User, UserRole
from app.schemas.email_template import (
    EmailTemplateCreate,
    EmailTemplateUpdate,
    EmailTemplateResponse,
    EmailTemplateListResponse,
    EmailPreviewRequest
)
from app.services.template_service import TemplateService

router = APIRouter()


@router.get("", response_model=EmailTemplateListResponse)
def list_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    include_global: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    List email templates (company-specific and global).
    """
    template_service = TemplateService(db)
    
    company_id = current_user.company_id if current_user.role == UserRole.ADMIN else None
    templates, total = template_service.get_templates(
        company_id, skip, limit, include_global
    )
    
    return EmailTemplateListResponse(
        templates=[EmailTemplateResponse.model_validate(t) for t in templates],
        total=total
    )


@router.post("", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    template_data: EmailTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Create a new email template.
    """
    template_service = TemplateService(db)
    template = template_service.create_template(template_data, current_user)
    return template


@router.get("/{template_id}", response_model=EmailTemplateResponse)
def get_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get template details by ID.
    """
    template_service = TemplateService(db)
    template = template_service.get_template_by_id(template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    if template.company_id and current_user.role == UserRole.ADMIN:
        if template.company_id != current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view templates from other companies"
            )
    
    return template


@router.put("/{template_id}", response_model=EmailTemplateResponse)
def update_template(
    template_id: UUID,
    template_data: EmailTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Update template details.
    """
    template_service = TemplateService(db)
    template = template_service.update_template(template_id, template_data, current_user)
    return template


@router.delete("/{template_id}")
def delete_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Delete an email template.
    """
    template_service = TemplateService(db)
    template_service.delete_template(template_id, current_user)
    return {"message": "Template deleted successfully"}


@router.post("/{template_id}/preview")
def preview_template(
    template_id: UUID,
    preview_data: EmailPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Preview an email template with sample data.
    """
    template_service = TemplateService(db)
    preview = template_service.preview_template(
        template_id,
        preview_data.recipient_email,
        preview_data.recipient_name
    )
    return preview

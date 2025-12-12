from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from jinja2 import Template

from app.models.email_template import EmailTemplate
from app.models.user import User, UserRole
from app.schemas.email_template import EmailTemplateCreate, EmailTemplateUpdate


class TemplateService:
    """Service for email template operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_template_by_id(self, template_id: UUID) -> Optional[EmailTemplate]:
        """Get a template by ID."""
        return self.db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
    
    def get_templates(
        self, 
        company_id: Optional[UUID] = None, 
        skip: int = 0, 
        limit: int = 100,
        include_global: bool = True
    ) -> Tuple[List[EmailTemplate], int]:
        """Get templates with pagination."""
        query = self.db.query(EmailTemplate)
        
        if company_id:
            if include_global:
                query = query.filter(
                    (EmailTemplate.company_id == company_id) | 
                    (EmailTemplate.company_id.is_(None))
                )
            else:
                query = query.filter(EmailTemplate.company_id == company_id)
        else:
            query = query.filter(EmailTemplate.company_id.is_(None))
        
        total = query.count()
        templates = query.order_by(EmailTemplate.created_at.desc()).offset(skip).limit(limit).all()
        
        return templates, total
    
    def create_template(
        self, 
        template_data: EmailTemplateCreate, 
        current_user: User
    ) -> EmailTemplate:
        """Create a new email template."""
        company_id = None
        if current_user.role == UserRole.ADMIN:
            company_id = current_user.company_id
        
        template = EmailTemplate(
            company_id=company_id,
            name=template_data.name,
            subject=template_data.subject,
            body_html=template_data.body_html,
            difficulty=template_data.difficulty,
            category=template_data.category
        )
        
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        return template
    
    def update_template(
        self, 
        template_id: UUID, 
        template_data: EmailTemplateUpdate, 
        current_user: User
    ) -> EmailTemplate:
        """Update an email template."""
        template = self.get_template_by_id(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        if current_user.role == UserRole.ADMIN:
            if template.company_id != current_user.company_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot update templates from other companies"
                )
        
        if template_data.name is not None:
            template.name = template_data.name
        if template_data.subject is not None:
            template.subject = template_data.subject
        if template_data.body_html is not None:
            template.body_html = template_data.body_html
        if template_data.difficulty is not None:
            template.difficulty = template_data.difficulty
        if template_data.category is not None:
            template.category = template_data.category
        
        self.db.commit()
        self.db.refresh(template)
        
        return template
    
    def delete_template(self, template_id: UUID, current_user: User) -> bool:
        """Delete an email template."""
        template = self.get_template_by_id(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        if current_user.role == UserRole.ADMIN:
            if template.company_id != current_user.company_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot delete templates from other companies"
                )
        
        self.db.delete(template)
        self.db.commit()
        
        return True
    
    def preview_template(
        self, 
        template_id: UUID, 
        recipient_email: Optional[str] = None,
        recipient_name: Optional[str] = None,
        tracking_url: Optional[str] = None
    ) -> dict:
        """Preview an email template with sample data."""
        template = self.get_template_by_id(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        context = {
            "recipient_email": recipient_email or "user@example.com",
            "recipient_name": recipient_name or "John Doe",
            "company_name": "Example Company",
            "tracking_url": tracking_url or "https://example.com/track",
            "phishing_url": tracking_url or "https://example.com/phishing",
            "current_date": "2024-01-01",
        }
        
        try:
            subject_template = Template(template.subject)
            body_template = Template(template.body_html)
            
            rendered_subject = subject_template.render(**context)
            rendered_body = body_template.render(**context)
            
            return {
                "subject": rendered_subject,
                "body_html": rendered_body,
                "template_id": str(template.id),
                "template_name": template.name
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Template rendering error: {str(e)}"
            )

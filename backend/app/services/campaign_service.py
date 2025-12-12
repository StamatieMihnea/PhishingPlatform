import logging
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_target import CampaignTarget
from app.models.email_task import EmailTask, EmailTaskStatus
from app.models.email_template import EmailTemplate
from app.models.user import User, UserRole
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignStats
from app.core.config import settings
from app.services.queue_service import get_queue_service

logger = logging.getLogger(__name__)


class CampaignService:
    """Service for campaign operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_campaign_by_id(self, campaign_id: UUID) -> Optional[Campaign]:
        """Get a campaign by ID."""
        return self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
    
    def get_campaigns_by_company(
        self, 
        company_id: UUID, 
        skip: int = 0, 
        limit: int = 100,
        status_filter: Optional[CampaignStatus] = None
    ) -> Tuple[List[Campaign], int]:
        """Get campaigns by company with pagination."""
        query = self.db.query(Campaign).filter(Campaign.company_id == company_id)
        
        if status_filter:
            query = query.filter(Campaign.status == status_filter)
        
        total = query.count()
        campaigns = query.order_by(Campaign.created_at.desc()).offset(skip).limit(limit).all()
        
        return campaigns, total
    
    def create_campaign(
        self, 
        campaign_data: CampaignCreate, 
        current_user: User
    ) -> Campaign:
        """Create a new campaign."""
        if not current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to a company to create campaigns"
            )
        
        campaign = Campaign(
            company_id=current_user.company_id,
            created_by=current_user.id,
            name=campaign_data.name,
            description=campaign_data.description,
            template_id=campaign_data.template_id,
            status=CampaignStatus.DRAFT
        )
        
        self.db.add(campaign)
        self.db.flush()
        
        campaign.phishing_url = f"{settings.TRACKING_BASE_URL}/api/v1/track/click/"
        
        for user_id in campaign_data.target_user_ids:
            user = self.db.query(User).filter(
                User.id == user_id,
                User.company_id == current_user.company_id
            ).first()
            
            if user:
                target = CampaignTarget(
                    campaign_id=campaign.id,
                    user_id=user_id
                )
                self.db.add(target)
        
        self.db.commit()
        self.db.refresh(campaign)
        
        return campaign
    
    def update_campaign(
        self, 
        campaign_id: UUID, 
        campaign_data: CampaignUpdate, 
        current_user: User
    ) -> Campaign:
        """Update a campaign."""
        campaign = self.get_campaign_by_id(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )
        
        if campaign.company_id != current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update campaigns from other companies"
            )
        
        if campaign.status != CampaignStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only update draft campaigns"
            )
        
        if campaign_data.name is not None:
            campaign.name = campaign_data.name
        if campaign_data.description is not None:
            campaign.description = campaign_data.description
        if campaign_data.template_id is not None:
            campaign.template_id = campaign_data.template_id
        
        self.db.commit()
        self.db.refresh(campaign)
        
        return campaign
    
    def delete_campaign(self, campaign_id: UUID, current_user: User) -> bool:
        """Delete a campaign (only DRAFT)."""
        campaign = self.get_campaign_by_id(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )
        
        if campaign.company_id != current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete campaigns from other companies"
            )
        
        if campaign.status != CampaignStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only delete draft campaigns"
            )
        
        self.db.delete(campaign)
        self.db.commit()
        
        return True
    
    def schedule_campaign(
        self, 
        campaign_id: UUID, 
        scheduled_at: datetime, 
        current_user: User
    ) -> Campaign:
        """Schedule a campaign for later execution."""
        campaign = self.get_campaign_by_id(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )
        
        if campaign.company_id != current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot schedule campaigns from other companies"
            )
        
        if campaign.status != CampaignStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only schedule draft campaigns"
            )
        
        if scheduled_at <= datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scheduled time must be in the future"
            )
        
        targets = self.db.query(CampaignTarget).filter(
            CampaignTarget.campaign_id == campaign_id
        ).all()
        
        if not targets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campaign must have at least one target"
            )
        
        if not campaign.template_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campaign must have an email template"
            )
        
        campaign.scheduled_at = scheduled_at
        campaign.status = CampaignStatus.SCHEDULED
        
        for target in targets:
            email_task = EmailTask(
                campaign_target_id=target.id,
                status=EmailTaskStatus.PENDING,
                scheduled_at=scheduled_at
            )
            self.db.add(email_task)
        
        self.db.commit()
        self.db.refresh(campaign)
        
        return campaign
    
    def start_campaign(self, campaign_id: UUID, current_user) -> Campaign:
        """Start a campaign immediately."""
        campaign = self.get_campaign_by_id(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )
        
        if str(campaign.company_id) != str(current_user.company_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot start campaigns from other companies"
            )
        
        if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campaign is already running or completed"
            )
        
        targets = self.db.query(CampaignTarget).filter(
            CampaignTarget.campaign_id == campaign_id
        ).all()
        
        if not targets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campaign must have at least one target"
            )
        
        if not campaign.template_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campaign must have an email template"
            )
        
        template = self.db.query(EmailTemplate).filter(
            EmailTemplate.id == campaign.template_id
        ).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email template not found"
            )
        
        campaign.status = CampaignStatus.RUNNING
        campaign.started_at = datetime.utcnow()
        
        queue_service = get_queue_service()
        
        for target in targets:
            target_user = target.user
            if not target_user:
                logger.warning(f"Target {target.id} has no associated user")
                continue
            
            existing_task = self.db.query(EmailTask).filter(
                EmailTask.campaign_target_id == target.id
            ).first()
            
            if existing_task:
                existing_task.status = EmailTaskStatus.QUEUED
                existing_task.scheduled_at = datetime.utcnow()
                task_id = str(existing_task.id)
            else:
                email_task = EmailTask(
                    campaign_target_id=target.id,
                    status=EmailTaskStatus.QUEUED,
                    scheduled_at=datetime.utcnow()
                )
                self.db.add(email_task)
                self.db.flush()
                task_id = str(email_task.id)
            
            body_html = self._personalize_email(
                template.body_html, 
                target_user, 
                target.tracking_token,
                campaign.phishing_url
            )
            
            success = queue_service.publish_email_task(
                task_id=task_id,
                campaign_target_id=str(target.id),
                recipient_email=target_user.email,
                recipient_name=target_user.full_name,
                subject=template.subject,
                body_html=body_html,
                tracking_token=target.tracking_token,
                immediate=True,
                priority=5
            )
            
            if not success:
                logger.error(f"Failed to publish email task for target {target.id}")
        
        self.db.commit()
        self.db.refresh(campaign)
        
        return campaign
    
    def _personalize_email(
        self, 
        body_html: str, 
        user: User, 
        tracking_token: str,
        phishing_url: str
    ) -> str:
        """Personalize email body with user info and tracking."""
        tracking_pixel = f'<img src="{settings.TRACKING_BASE_URL}/api/v1/track/open/{tracking_token}" width="1" height="1" style="display:none;" />'
        
        personalized = body_html.replace("{{first_name}}", user.first_name)
        personalized = personalized.replace("{{last_name}}", user.last_name)
        personalized = personalized.replace("{{full_name}}", user.full_name)
        personalized = personalized.replace("{{email}}", user.email)
        personalized = personalized.replace("{{tracking_link}}", f"{phishing_url}{tracking_token}")
        
        if "</body>" in personalized:
            personalized = personalized.replace("</body>", f"{tracking_pixel}</body>")
        else:
            personalized += tracking_pixel
        
        return personalized
    
    def stop_campaign(self, campaign_id: UUID, current_user: User) -> Campaign:
        """Stop a running campaign."""
        campaign = self.get_campaign_by_id(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )
        
        if campaign.company_id != current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot stop campaigns from other companies"
            )
        
        if campaign.status != CampaignStatus.RUNNING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only stop running campaigns"
            )
        
        campaign.status = CampaignStatus.COMPLETED
        campaign.completed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(campaign)
        
        return campaign
    
    def get_campaign_stats(self, campaign_id: UUID, current_user: User) -> CampaignStats:
        """Get statistics for a campaign."""
        campaign = self.get_campaign_by_id(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )
        
        if campaign.company_id != current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view campaigns from other companies"
            )
        
        targets = self.db.query(CampaignTarget).filter(
            CampaignTarget.campaign_id == campaign_id
        ).all()
        
        total_targets = len(targets)
        emails_sent = sum(1 for t in targets if t.email_sent)
        emails_opened = sum(1 for t in targets if t.email_opened)
        links_clicked = sum(1 for t in targets if t.link_clicked)
        credentials_submitted = sum(1 for t in targets if t.credentials_submitted)
        
        open_rate = (emails_opened / emails_sent * 100) if emails_sent > 0 else 0
        click_rate = (links_clicked / emails_sent * 100) if emails_sent > 0 else 0
        submission_rate = (credentials_submitted / emails_sent * 100) if emails_sent > 0 else 0
        
        return CampaignStats(
            campaign_id=campaign_id,
            campaign_name=campaign.name,
            status=campaign.status,
            total_targets=total_targets,
            emails_sent=emails_sent,
            emails_opened=emails_opened,
            links_clicked=links_clicked,
            credentials_submitted=credentials_submitted,
            open_rate=round(open_rate, 2),
            click_rate=round(click_rate, 2),
            submission_rate=round(submission_rate, 2)
        )
    
    def add_targets(
        self, 
        campaign_id: UUID, 
        user_ids: List[UUID], 
        current_user: User
    ) -> List[CampaignTarget]:
        """Add targets to a campaign."""
        campaign = self.get_campaign_by_id(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )
        
        if campaign.company_id != current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify campaigns from other companies"
            )
        
        if campaign.status != CampaignStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only add targets to draft campaigns"
            )
        
        added_targets = []
        for user_id in user_ids:
            user = self.db.query(User).filter(
                User.id == user_id,
                User.company_id == current_user.company_id
            ).first()
            
            if not user:
                continue
            
            existing = self.db.query(CampaignTarget).filter(
                CampaignTarget.campaign_id == campaign_id,
                CampaignTarget.user_id == user_id
            ).first()
            
            if existing:
                continue
            
            target = CampaignTarget(
                campaign_id=campaign_id,
                user_id=user_id
            )
            self.db.add(target)
            added_targets.append(target)
        
        self.db.commit()
        
        return added_targets

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.user import User
from app.models.campaign import CampaignStatus
from app.schemas.campaign import (
    CampaignCreate, 
    CampaignUpdate, 
    CampaignResponse, 
    CampaignListResponse,
    CampaignScheduleRequest,
    CampaignStats
)
from app.schemas.campaign_target import CampaignTargetResponse, CampaignTargetListResponse
from app.services.campaign_service import CampaignService

router = APIRouter()


@router.get("", response_model=CampaignListResponse)
def list_campaigns(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status_filter: Optional[CampaignStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    List campaigns in the current company.
    """
    if not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a company"
        )
    
    campaign_service = CampaignService(db)
    campaigns, total = campaign_service.get_campaigns_by_company(
        current_user.company_id, skip, limit, status_filter
    )
    
    return CampaignListResponse(
        campaigns=[CampaignResponse.model_validate(c) for c in campaigns],
        total=total
    )


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    campaign_data: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Create a new phishing campaign.
    """
    campaign_service = CampaignService(db)
    campaign = campaign_service.create_campaign(campaign_data, current_user)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get campaign details by ID.
    """
    campaign_service = CampaignService(db)
    campaign = campaign_service.get_campaign_by_id(campaign_id)
    
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
    
    return campaign


@router.put("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    campaign_id: UUID,
    campaign_data: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Update campaign details (only DRAFT campaigns).
    """
    campaign_service = CampaignService(db)
    campaign = campaign_service.update_campaign(campaign_id, campaign_data, current_user)
    return campaign


@router.delete("/{campaign_id}")
def delete_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Delete a campaign (only DRAFT campaigns).
    """
    campaign_service = CampaignService(db)
    campaign_service.delete_campaign(campaign_id, current_user)
    return {"message": "Campaign deleted successfully"}


@router.post("/{campaign_id}/schedule", response_model=CampaignResponse)
def schedule_campaign(
    campaign_id: UUID,
    schedule_data: CampaignScheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Schedule a campaign for later execution.
    """
    campaign_service = CampaignService(db)
    campaign = campaign_service.schedule_campaign(
        campaign_id, 
        schedule_data.scheduled_at, 
        current_user
    )
    return campaign


@router.post("/{campaign_id}/start", response_model=CampaignResponse)
def start_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Start a campaign immediately.
    """
    campaign_service = CampaignService(db)
    campaign = campaign_service.start_campaign(campaign_id, current_user)
    return campaign


@router.post("/{campaign_id}/stop", response_model=CampaignResponse)
def stop_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Stop a running campaign.
    """
    campaign_service = CampaignService(db)
    campaign = campaign_service.stop_campaign(campaign_id, current_user)
    return campaign


@router.get("/{campaign_id}/stats", response_model=CampaignStats)
def get_campaign_stats(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get campaign statistics.
    """
    campaign_service = CampaignService(db)
    stats = campaign_service.get_campaign_stats(campaign_id, current_user)
    return stats


@router.get("/{campaign_id}/targets", response_model=CampaignTargetListResponse)
def get_campaign_targets(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get campaign targets list.
    """
    campaign_service = CampaignService(db)
    campaign = campaign_service.get_campaign_by_id(campaign_id)
    
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
    
    targets = []
    for target in campaign.targets:
        target_response = CampaignTargetResponse(
            id=target.id,
            campaign_id=target.campaign_id,
            user_id=target.user_id,
            user_email=target.user.email if target.user else None,
            user_name=target.user.full_name if target.user else None,
            email_sent=target.email_sent,
            email_sent_at=target.email_sent_at,
            email_opened=target.email_opened,
            email_opened_at=target.email_opened_at,
            link_clicked=target.link_clicked,
            link_clicked_at=target.link_clicked_at,
            credentials_submitted=target.credentials_submitted,
            submitted_at=target.submitted_at,
            created_at=target.created_at
        )
        targets.append(target_response)
    
    return CampaignTargetListResponse(
        targets=targets,
        total=len(targets)
    )


@router.post("/{campaign_id}/targets")
def add_campaign_targets(
    campaign_id: UUID,
    user_ids: List[UUID],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Add targets to a campaign.
    """
    campaign_service = CampaignService(db)
    added = campaign_service.add_targets(campaign_id, user_ids, current_user)
    return {"message": f"Added {len(added)} targets to campaign"}

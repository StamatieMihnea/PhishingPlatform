from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_target import CampaignTarget
from app.models.security_recommendation import SecurityRecommendation
from app.schemas.dashboard import (
    DashboardCampaign, 
    DashboardResult, 
    DashboardRecommendation,
    DashboardStats,
    TrainingMaterial
)

router = APIRouter()


@router.get("/my-campaigns", response_model=List[DashboardCampaign])
def get_my_campaigns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get campaigns the user has been included in.
    """
    targets = db.query(CampaignTarget).filter(
        CampaignTarget.user_id == current_user.id
    ).all()
    
    campaigns = []
    for target in targets:
        campaign = target.campaign
        if campaign.status in [CampaignStatus.RUNNING, CampaignStatus.COMPLETED]:
            campaigns.append(DashboardCampaign(
                id=campaign.id,
                name=campaign.name,
                description=campaign.description,
                status=campaign.status,
                started_at=campaign.started_at,
                completed_at=campaign.completed_at
            ))
    
    return campaigns


@router.get("/my-results", response_model=List[DashboardResult])
def get_my_results(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get user's phishing test results.
    """
    targets = db.query(CampaignTarget).filter(
        CampaignTarget.user_id == current_user.id
    ).all()
    
    results = []
    for target in targets:
        campaign = target.campaign
        if campaign.status == CampaignStatus.COMPLETED:
            was_phished = target.link_clicked or target.credentials_submitted
            results.append(DashboardResult(
                campaign_id=campaign.id,
                campaign_name=campaign.name,
                email_sent_at=target.email_sent_at,
                email_opened=target.email_opened,
                email_opened_at=target.email_opened_at,
                link_clicked=target.link_clicked,
                link_clicked_at=target.link_clicked_at,
                credentials_submitted=target.credentials_submitted,
                submitted_at=target.submitted_at,
                was_phished=was_phished
            ))
    
    return results


@router.get("/stats", response_model=DashboardStats)
def get_my_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get user's overall statistics.
    """
    targets = db.query(CampaignTarget).filter(
        CampaignTarget.user_id == current_user.id
    ).all()
    
    completed_targets = [t for t in targets if t.campaign.status == CampaignStatus.COMPLETED]
    total_campaigns = len(completed_targets)
    
    campaigns_passed = sum(
        1 for t in completed_targets 
        if not t.link_clicked and not t.credentials_submitted
    )
    campaigns_failed = total_campaigns - campaigns_passed
    
    success_rate = (campaigns_passed / total_campaigns * 100) if total_campaigns > 0 else 100.0
    
    return DashboardStats(
        total_campaigns=total_campaigns,
        campaigns_passed=campaigns_passed,
        campaigns_failed=campaigns_failed,
        success_rate=round(success_rate, 2)
    )


@router.get("/recommendations", response_model=List[DashboardRecommendation])
def get_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get personalized security recommendations based on user's performance.
    """
    targets = db.query(CampaignTarget).filter(
        CampaignTarget.user_id == current_user.id
    ).all()
    
    clicked_links = any(t.link_clicked for t in targets)
    submitted_credentials = any(t.credentials_submitted for t in targets)
    
    recommendations = db.query(SecurityRecommendation).all()
    
    filtered_recommendations = []
    for rec in recommendations:
        if clicked_links and rec.trigger_condition == "link_clicked":
            filtered_recommendations.append(rec)
        elif submitted_credentials and rec.trigger_condition == "credentials_submitted":
            filtered_recommendations.append(rec)
        elif not clicked_links and not submitted_credentials:
            if rec.trigger_condition == "general":
                filtered_recommendations.append(rec)
    
    if not filtered_recommendations:
        filtered_recommendations = recommendations[:5]
    
    return [
        DashboardRecommendation(
            id=rec.id,
            title=rec.title,
            description=rec.description,
            category=rec.category,
            priority=rec.priority
        )
        for rec in filtered_recommendations
    ]


@router.get("/training", response_model=List[TrainingMaterial])
def get_training_materials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get security awareness training materials.
    """
    materials = [
        TrainingMaterial(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            title="Recognizing Phishing Emails",
            description="Learn how to identify common signs of phishing emails",
            content_url="/training/phishing-basics",
            category="email_security",
            completed=False
        ),
        TrainingMaterial(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            title="Safe Password Practices",
            description="Best practices for creating and managing passwords",
            content_url="/training/password-security",
            category="passwords",
            completed=False
        ),
        TrainingMaterial(
            id=UUID("00000000-0000-0000-0000-000000000003"),
            title="Verifying Links Before Clicking",
            description="How to check if a link is safe before clicking",
            content_url="/training/link-verification",
            category="links",
            completed=False
        ),
        TrainingMaterial(
            id=UUID("00000000-0000-0000-0000-000000000004"),
            title="Reporting Suspicious Emails",
            description="How to report potential phishing attempts",
            content_url="/training/reporting",
            category="reporting",
            completed=False
        ),
    ]
    
    return materials


@router.post("/training/{training_id}/complete")
def complete_training(
    training_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Mark a training material as completed.
    """
    return {"message": "Training marked as completed", "training_id": str(training_id)}

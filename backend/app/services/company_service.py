from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.company import Company
from app.models.user import User
from app.models.campaign import Campaign
from app.models.campaign_target import CampaignTarget
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyStats


class CompanyService:
    """Service for company operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_company_by_id(self, company_id: UUID) -> Optional[Company]:
        """Get a company by ID."""
        return self.db.query(Company).filter(Company.id == company_id).first()
    
    def get_company_by_domain(self, domain: str) -> Optional[Company]:
        """Get a company by domain."""
        return self.db.query(Company).filter(Company.domain == domain).first()
    
    def get_all_companies(self, skip: int = 0, limit: int = 100) -> Tuple[List[Company], int]:
        """Get all companies with pagination."""
        query = self.db.query(Company)
        total = query.count()
        companies = query.offset(skip).limit(limit).all()
        return companies, total
    
    def create_company(self, company_data: CompanyCreate) -> Company:
        """Create a new company."""
        existing_company = self.get_company_by_domain(company_data.domain)
        if existing_company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company with this domain already exists"
            )
        
        company = Company(
            name=company_data.name,
            domain=company_data.domain,
            logo_url=company_data.logo_url,
            is_active=True
        )
        
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        
        return company
    
    def update_company(self, company_id: UUID, company_data: CompanyUpdate) -> Company:
        """Update a company."""
        company = self.get_company_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        
        if company_data.domain and company_data.domain != company.domain:
            existing_company = self.get_company_by_domain(company_data.domain)
            if existing_company:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Company with this domain already exists"
                )
        
        if company_data.name is not None:
            company.name = company_data.name
        if company_data.domain is not None:
            company.domain = company_data.domain
        if company_data.logo_url is not None:
            company.logo_url = company_data.logo_url
        if company_data.is_active is not None:
            company.is_active = company_data.is_active
        
        self.db.commit()
        self.db.refresh(company)
        
        return company
    
    def deactivate_company(self, company_id: UUID) -> Company:
        """Deactivate a company."""
        company = self.get_company_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        
        company.is_active = False
        self.db.commit()
        self.db.refresh(company)
        
        return company
    
    def get_company_stats(self, company_id: UUID) -> CompanyStats:
        """Get statistics for a company."""
        company = self.get_company_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        
        total_users = self.db.query(User).filter(User.company_id == company_id).count()
        
        total_campaigns = self.db.query(Campaign).filter(Campaign.company_id == company_id).count()
        
        campaign_ids = [c.id for c in self.db.query(Campaign.id).filter(Campaign.company_id == company_id).all()]
        
        if campaign_ids:
            targets = self.db.query(CampaignTarget).filter(
                CampaignTarget.campaign_id.in_(campaign_ids)
            ).all()
            
            total_emails_sent = sum(1 for t in targets if t.email_sent)
            total_emails_opened = sum(1 for t in targets if t.email_opened)
            total_links_clicked = sum(1 for t in targets if t.link_clicked)
            total_credentials_submitted = sum(1 for t in targets if t.credentials_submitted)
        else:
            total_emails_sent = 0
            total_emails_opened = 0
            total_links_clicked = 0
            total_credentials_submitted = 0
        
        click_rate = (total_links_clicked / total_emails_sent * 100) if total_emails_sent > 0 else 0
        submission_rate = (total_credentials_submitted / total_emails_sent * 100) if total_emails_sent > 0 else 0
        
        return CompanyStats(
            company_id=company_id,
            company_name=company.name,
            total_users=total_users,
            total_campaigns=total_campaigns,
            total_emails_sent=total_emails_sent,
            total_emails_opened=total_emails_opened,
            total_links_clicked=total_links_clicked,
            total_credentials_submitted=total_credentials_submitted,
            click_rate=round(click_rate, 2),
            submission_rate=round(submission_rate, 2)
        )

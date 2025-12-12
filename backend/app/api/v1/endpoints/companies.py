from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_super_admin
from app.models.user import User
from app.schemas.company import (
    CompanyCreate, 
    CompanyUpdate, 
    CompanyResponse, 
    CompanyListResponse,
    CompanyStats
)
from app.services.company_service import CompanyService

router = APIRouter()


@router.get("", response_model=CompanyListResponse)
def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    List all companies (Super Admin only).
    """
    company_service = CompanyService(db)
    companies, total = company_service.get_all_companies(skip, limit)
    
    return CompanyListResponse(
        companies=[CompanyResponse.model_validate(c) for c in companies],
        total=total
    )


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    company_data: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Create a new company (Super Admin only).
    """
    company_service = CompanyService(db)
    company = company_service.create_company(company_data)
    return company


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Get company details by ID (Super Admin only).
    """
    company_service = CompanyService(db)
    company = company_service.get_company_by_id(company_id)
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    return company


@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: UUID,
    company_data: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Update company details (Super Admin only).
    """
    company_service = CompanyService(db)
    company = company_service.update_company(company_id, company_data)
    return company


@router.delete("/{company_id}", response_model=CompanyResponse)
def deactivate_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Deactivate a company (Super Admin only).
    """
    company_service = CompanyService(db)
    company = company_service.deactivate_company(company_id)
    return company


@router.get("/{company_id}/stats", response_model=CompanyStats)
def get_company_stats(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Get company statistics (Super Admin only).
    """
    company_service = CompanyService(db)
    stats = company_service.get_company_stats(company_id)
    return stats

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user, require_admin
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreate, 
    UserUpdate, 
    UserResponse, 
    UserListResponse,
    UserImportRequest,
    UserImportResponse
)
from app.services.user_service import UserService

router = APIRouter()


@router.get("", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[UserRole] = None,
    company_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    List users in the current company (Admin) or all/filtered users (Super Admin).
    Super Admins can filter by company_id or see all users.
    """
    user_service = UserService(db)
    
    skip = (page - 1) * page_size
    
    if current_user.role == UserRole.SUPER_ADMIN:
        if company_id:
            users, total = user_service.get_users_by_company(
                company_id, skip, page_size, role
            )
        else:
            users, total = user_service.get_all_users(skip, page_size, role)
    else:
        users, total = user_service.get_users_by_company(
            current_user.company_id, skip, page_size, role
        )
    
    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Create a new user in the company.
    """
    user_service = UserService(db)
    user = user_service.create_user(user_data, current_user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get user details by ID.
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if current_user.role == UserRole.USER:
        if user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view other users"
            )
    elif current_user.role == UserRole.ADMIN:
        if user.company_id != current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view users from other companies"
            )
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update user details.
    """
    user_service = UserService(db)
    user = user_service.update_user(user_id, user_data, current_user)
    return user


@router.delete("/{user_id}", response_model=UserResponse)
def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Deactivate a user (soft delete).
    """
    user_service = UserService(db)
    user = user_service.deactivate_user(user_id, current_user)
    return user


@router.post("/import", response_model=UserImportResponse)
def import_users(
    import_data: UserImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Import users from CSV data.
    CSV format: email,first_name,last_name,password (optional)
    SUPER_ADMIN can specify company_id in request body.
    """
    if current_user.role == UserRole.SUPER_ADMIN:
        if not import_data.company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Super admins must specify company_id for import"
            )
        company_id = import_data.company_id
    else:
        if not current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to a company to import users"
            )
        company_id = current_user.company_id
    
    user_service = UserService(db)
    imported, failed, errors = user_service.import_users_from_csv(
        import_data.csv_data,
        company_id
    )
    
    return UserImportResponse(
        imported=imported,
        failed=failed,
        errors=errors
    )

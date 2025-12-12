import csv
import io
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.models.company import Company
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash


class UserService:
    """Service for user operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get a user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_users_by_company(
        self, 
        company_id: UUID, 
        skip: int = 0, 
        limit: int = 100,
        role: Optional[UserRole] = None
    ) -> Tuple[List[User], int]:
        """Get users by company with pagination."""
        query = self.db.query(User).filter(User.company_id == company_id)
        
        if role:
            query = query.filter(User.role == role)
        
        total = query.count()
        users = query.offset(skip).limit(limit).all()
        
        return users, total
    
    def get_all_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None
    ) -> Tuple[List[User], int]:
        """Get all users across all companies (for SUPER_ADMIN)."""
        query = self.db.query(User)
        
        if role:
            query = query.filter(User.role == role)
        
        total = query.count()
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        
        return users, total
    
    def create_user(self, user_data: UserCreate, current_user: User) -> User:
        """Create a new user."""
        existing_user = self.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        company_id = user_data.company_id
        if current_user.role == UserRole.ADMIN:
            company_id = current_user.company_id
            if user_data.role == UserRole.SUPER_ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admins cannot create super admins"
                )
        elif current_user.role == UserRole.SUPER_ADMIN:
            if user_data.role != UserRole.SUPER_ADMIN and not company_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Company ID is required for non-super-admin users"
                )
        
        if company_id:
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Company not found"
                )
        
        user = User(
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role,
            company_id=company_id,
            is_active=True
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def update_user(
        self, 
        user_id: UUID, 
        user_data: UserUpdate, 
        current_user: User
    ) -> User:
        """Update a user."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if current_user.role == UserRole.ADMIN:
            if user.company_id != current_user.company_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot update users from other companies"
                )
        elif current_user.role == UserRole.USER:
            if user.id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot update other users"
                )
        
        if user_data.email and user_data.email != user.email:
            existing_user = self.get_user_by_email(user_data.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        if user_data.email is not None:
            user.email = user_data.email
        if user_data.first_name is not None:
            user.first_name = user_data.first_name
        if user_data.last_name is not None:
            user.last_name = user_data.last_name
        if user_data.password is not None:
            user.password_hash = get_password_hash(user_data.password)
        if user_data.is_active is not None and current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            user.is_active = user_data.is_active
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def deactivate_user(self, user_id: UUID, current_user: User) -> User:
        """Deactivate a user."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if current_user.role == UserRole.ADMIN:
            if user.company_id != current_user.company_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot deactivate users from other companies"
                )
            if user.role == UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admins cannot deactivate other admins"
                )
        
        user.is_active = False
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def import_users_from_csv(
        self, 
        csv_data: str, 
        company_id: UUID
    ) -> Tuple[int, int, List[str]]:
        """Import users from CSV data."""
        imported = 0
        failed = 0
        errors = []
        
        try:
            reader = csv.DictReader(io.StringIO(csv_data))
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    email = row.get('email', '').strip()
                    first_name = row.get('first_name', '').strip()
                    last_name = row.get('last_name', '').strip()
                    password = row.get('password', 'DefaultPass123!').strip()
                    
                    if not email or not first_name or not last_name:
                        raise ValueError("Missing required fields")
                    
                    if self.get_user_by_email(email):
                        raise ValueError(f"Email {email} already exists")
                    
                    user = User(
                        email=email,
                        password_hash=get_password_hash(password),
                        first_name=first_name,
                        last_name=last_name,
                        role=UserRole.USER,
                        company_id=company_id,
                        is_active=True
                    )
                    
                    self.db.add(user)
                    imported += 1
                    
                except Exception as e:
                    failed += 1
                    errors.append(f"Row {row_num}: {str(e)}")
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CSV parsing error: {str(e)}"
            )
        
        return imported, failed, errors

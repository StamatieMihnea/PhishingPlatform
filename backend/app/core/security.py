"""
Security utilities for authentication and authorization.
Supports both Keycloak SSO and legacy JWT authentication.
"""
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.keycloak import keycloak_service, KeycloakUser, get_current_keycloak_user

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

http_bearer = HTTPBearer(auto_error=False)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login/form",
    auto_error=False
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a legacy JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a legacy JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_legacy_token(token: str) -> dict:
    """Decode and validate a legacy JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthenticatedUser:
    """
    Unified user object that works with both Keycloak and legacy authentication.
    """
    def __init__(
        self,
        id: str,
        email: str,
        first_name: str,
        last_name: str,
        role: str,
        company_id: Optional[str] = None,
        is_active: bool = True,
        source: str = "keycloak"
    ):
        self.id = id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.role = role
        self.company_id = company_id
        self.is_active = is_active
        self.source = source
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
    
    @classmethod
    def from_keycloak(cls, keycloak_user: KeycloakUser) -> "AuthenticatedUser":
        """Create from Keycloak user."""
        return cls(
            id=keycloak_user.id,
            email=keycloak_user.email,
            first_name=keycloak_user.first_name,
            last_name=keycloak_user.last_name,
            role=keycloak_user.role,
            company_id=keycloak_user.company_id,
            is_active=True,
            source="keycloak"
        )
    
    @classmethod
    def from_db_user(cls, db_user) -> "AuthenticatedUser":
        """Create from database User model."""
        return cls(
            id=str(db_user.id),
            email=db_user.email,
            first_name=db_user.first_name,
            last_name=db_user.last_name,
            role=db_user.role.value if hasattr(db_user.role, 'value') else db_user.role,
            company_id=str(db_user.company_id) if db_user.company_id else None,
            is_active=db_user.is_active,
            source="database"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
    db: Session = Depends(get_db)
) -> AuthenticatedUser:
    """
    Get the current authenticated user.
    Tries Keycloak first, falls back to legacy JWT.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    try:
        token_payload = keycloak_service.decode_token(token)
        keycloak_user = KeycloakUser(token_payload)
        return AuthenticatedUser.from_keycloak(keycloak_user)
    except Exception as keycloak_error:
        try:
            payload = decode_legacy_token(token)
            user_id = payload.get("sub")
            token_type = payload.get("type")
            
            if user_id is None or token_type != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
            
            from app.models.user import User
            user = db.query(User).filter(User.id == user_id).first()
            
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is deactivated"
                )
            
            return AuthenticatedUser.from_db_user(user)
            
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )


async def get_current_active_user(
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> AuthenticatedUser:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def require_role(allowed_roles: list):
    """Dependency to require specific roles."""
    async def role_checker(
        current_user: AuthenticatedUser = Depends(get_current_active_user)
    ) -> AuthenticatedUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {allowed_roles}"
            )
        return current_user
    return role_checker


async def require_super_admin(
    current_user: AuthenticatedUser = Depends(get_current_active_user)
) -> AuthenticatedUser:
    """Require super admin role."""
    if current_user.role != 'SUPER_ADMIN':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user


async def require_admin(
    current_user: AuthenticatedUser = Depends(get_current_active_user)
) -> AuthenticatedUser:
    """Require admin or super admin role."""
    if current_user.role not in ['ADMIN', 'SUPER_ADMIN']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

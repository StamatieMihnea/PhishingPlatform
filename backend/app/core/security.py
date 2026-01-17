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
from app.models.user import User, UserRole

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
        if not token_payload.get("email"):
            # Attempt to enrich via userinfo; still require email after that
            try:
                userinfo = keycloak_service.get_userinfo_sync(token)  # type: ignore[attr-defined]
                token_payload.update({
                    "email": userinfo.get("email"),
                    "email_verified": userinfo.get("email_verified", False),
                    "given_name": userinfo.get("given_name"),
                    "family_name": userinfo.get("family_name"),
                    "preferred_username": userinfo.get("preferred_username"),
                })
            except Exception:
                # If userinfo fails (e.g., missing scope), try admin lookup
                try:
                    kc_user = keycloak_service.get_user_by_id_admin(token_payload.get("sub", ""))
                    token_payload.update({
                        "email": kc_user.get("email"),
                        "email_verified": kc_user.get("emailVerified", False),
                        "given_name": kc_user.get("firstName"),
                        "family_name": kc_user.get("lastName"),
                        "preferred_username": kc_user.get("username"),
                        "company_id": kc_user.get("attributes", {}).get("company_id", [None])[0] if kc_user.get("attributes") else None,
                    })
                except Exception:
                    pass
        if not token_payload.get("email"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email claim missing in token; enable email scope/mapper in Keycloak."
            )
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
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> User:
    """Require super admin role and ensure a persisted DB user."""
    if current_user.role != 'SUPER_ADMIN':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    if not current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required from identity provider"
        )
    db_user = db.query(User).filter(User.id == current_user.id).first()
    if db_user:
        return db_user
    email_user = db.query(User).filter(User.email == current_user.email).first()
    if email_user:
        email_user.id = current_user.id
        email_user.role = UserRole.SUPER_ADMIN
        db.commit()
        db.refresh(email_user)
        return email_user
    db_user = User(
        id=current_user.id,
        email=current_user.email,
        password_hash=get_password_hash("TempPassword123!"),
        first_name=current_user.first_name or "SSO",
        last_name=current_user.last_name or "User",
        role=UserRole.SUPER_ADMIN,
        company_id=None,
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


async def require_admin(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> User:
    """Require admin or super admin role and ensure a persisted DB user."""
    if current_user.role not in ['ADMIN', 'SUPER_ADMIN']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    if not current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required from identity provider"
        )
    db_user = db.query(User).filter(User.id == current_user.id).first()
    if db_user:
        return db_user
    email_user = db.query(User).filter(User.email == current_user.email).first()
    if email_user:
        email_user.id = current_user.id
        email_user.role = UserRole.SUPER_ADMIN if current_user.role == 'SUPER_ADMIN' else UserRole.ADMIN
        if email_user.role != UserRole.SUPER_ADMIN:
            email_user.company_id = current_user.company_id
        db.commit()
        db.refresh(email_user)
        return email_user
    role_value = UserRole.SUPER_ADMIN if current_user.role == 'SUPER_ADMIN' else UserRole.ADMIN
    db_user = User(
        id=current_user.id,
        email=current_user.email,
        password_hash=get_password_hash("TempPassword123!"),
        first_name=current_user.first_name or "SSO",
        last_name=current_user.last_name or "User",
        role=role_value,
        company_id=current_user.company_id if role_value != UserRole.SUPER_ADMIN else None,
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

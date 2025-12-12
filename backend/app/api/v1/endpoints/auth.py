from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    get_current_active_user, 
    AuthenticatedUser,
    create_access_token,
    create_refresh_token,
    decode_legacy_token,
    verify_password
)
from app.core.keycloak import keycloak_service
from app.models.user import User
from app.schemas.auth import Token, LoginRequest, RefreshTokenRequest, KeycloakTokenRequest
from app.schemas.user import UserResponse

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    login_request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Legacy login endpoint using email/password.
    For SSO, use Keycloak directly from the frontend.
    """
    user = db.query(User).filter(User.email == login_request.email).first()
    
    if not user or not verify_password(login_request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/login/form", response_model=Token)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible login endpoint using form data.
    """
    login_request = LoginRequest(email=form_data.username, password=form_data.password)
    return await login(login_request, db)


@router.post("/logout")
async def logout(current_user: AuthenticatedUser = Depends(get_current_active_user)):
    """
    Logout current user.
    For Keycloak users, also logout from Keycloak session on frontend.
    """
    return {
        "message": "Successfully logged out",
        "keycloak_logout_url": f"{keycloak_service.issuer}/protocol/openid-connect/logout"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token.
    Supports both Keycloak refresh tokens and legacy JWT refresh tokens.
    """
    try:
        tokens = await keycloak_service.refresh_token(refresh_request.refresh_token)
        return Token(
            access_token=tokens.get('access_token'),
            refresh_token=tokens.get('refresh_token'),
            token_type="bearer"
        )
    except Exception:
        pass
    
    try:
        payload = decode_legacy_token(refresh_request.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        new_access_token = create_access_token(data={"sub": str(user.id)})
        new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/keycloak/token", response_model=Token)
async def keycloak_token_exchange(
    token_request: KeycloakTokenRequest
):
    """
    Exchange Keycloak authorization code for tokens.
    Used by frontend after Keycloak redirect.
    """
    tokens = await keycloak_service.exchange_code_for_token(
        code=token_request.code,
        redirect_uri=token_request.redirect_uri
    )
    
    return Token(
        access_token=tokens.get('access_token'),
        refresh_token=tokens.get('refresh_token'),
        token_type="bearer"
    )


@router.get("/me")
async def get_current_user_info(
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """
    Get current authenticated user details.
    Works with both Keycloak and legacy JWT tokens.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "role": current_user.role,
        "company_id": current_user.company_id,
        "is_active": current_user.is_active,
        "auth_source": current_user.source
    }


@router.get("/keycloak/config")
async def get_keycloak_config():
    """
    Get Keycloak configuration for frontend.
    """
    return {
        "url": keycloak_service.server_url,
        "realm": keycloak_service.realm,
        "clientId": "phishing-frontend",
        "authUrl": keycloak_service.issuer + "/protocol/openid-connect/auth",
        "tokenUrl": keycloak_service.token_url,
        "logoutUrl": keycloak_service.issuer + "/protocol/openid-connect/logout"
    }

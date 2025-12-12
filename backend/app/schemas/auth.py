from typing import Optional
from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str
    type: str
    exp: int


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str


class KeycloakTokenRequest(BaseModel):
    """Keycloak token exchange request."""
    code: str
    redirect_uri: str


class KeycloakConfig(BaseModel):
    """Keycloak configuration for frontend."""
    url: str
    realm: str
    clientId: str
    authUrl: str
    tokenUrl: str
    logoutUrl: str

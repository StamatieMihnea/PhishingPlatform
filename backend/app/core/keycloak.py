"""
Keycloak integration for SSO authentication and authorization.
"""
import logging
from typing import Optional, Dict, Any, List
from functools import lru_cache
import httpx
from jose import jwt, JWTError
from cachetools import TTLCache
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer, HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

logger = logging.getLogger(__name__)

jwks_cache = TTLCache(maxsize=1, ttl=600)

oauth2_scheme = HTTPBearer(auto_error=False)


class KeycloakService:
    """Service for Keycloak operations."""
    
    def __init__(self):
        self.server_url = settings.KEYCLOAK_SERVER_URL 
        self.public_url = settings.KEYCLOAK_PUBLIC_URL 
        self.realm = settings.KEYCLOAK_REALM
        self.client_id = settings.KEYCLOAK_CLIENT_ID
        self.client_secret = settings.KEYCLOAK_CLIENT_SECRET
    
    @property
    def issuer(self) -> str:
        """Public issuer that appears in JWT tokens."""
        return f"{self.public_url}/realms/{self.realm}"
    
    @property
    def internal_issuer(self) -> str:
        """Internal issuer for backend-to-keycloak communication."""
        return f"{self.server_url}/realms/{self.realm}"
    
    @property
    def jwks_url(self) -> str:
        """Use internal URL to fetch JWKS (backend-to-keycloak)."""
        return f"{self.internal_issuer}/protocol/openid-connect/certs"
    
    @property
    def token_url(self) -> str:
        """Use internal URL for token operations."""
        return f"{self.internal_issuer}/protocol/openid-connect/token"
    
    @property
    def userinfo_url(self) -> str:
        """Use internal URL for userinfo."""
        return f"{self.internal_issuer}/protocol/openid-connect/userinfo"
    
    async def get_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from Keycloak (with caching)."""
        if 'jwks' in jwks_cache:
            return jwks_cache['jwks']
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url, timeout=10.0)
                response.raise_for_status()
                jwks = response.json()
                jwks_cache['jwks'] = jwks
                return jwks
        except Exception as e:
            logger.error(f"Failed to fetch JWKS from Keycloak: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )
    
    def get_jwks_sync(self) -> Dict[str, Any]:
        """Fetch JWKS from Keycloak synchronously (with caching)."""
        if 'jwks' in jwks_cache:
            return jwks_cache['jwks']
        
        try:
            with httpx.Client() as client:
                response = client.get(self.jwks_url, timeout=10.0)
                response.raise_for_status()
                jwks = response.json()
                jwks_cache['jwks'] = jwks
                return jwks
        except Exception as e:
            logger.error(f"Failed to fetch JWKS from Keycloak: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate a Keycloak access token."""
        try:
            jwks = self.get_jwks_sync()
            
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')
            
            rsa_key = None
            for key in jwks.get('keys', []):
                if key.get('kid') == kid:
                    rsa_key = key
                    break
            
            if not rsa_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to find appropriate key"
                )
            
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=['RS256'],
                audience=self.client_id,
                issuer=self.issuer,
                options={"verify_aud": False} 
            )
            
            return payload
            
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def get_user_roles(self, token_payload: Dict[str, Any]) -> List[str]:
        """Extract roles from token payload."""
        roles = []
        
        realm_access = token_payload.get('realm_access', {})
        roles.extend(realm_access.get('roles', []))
        
        resource_access = token_payload.get('resource_access', {})
        client_roles = resource_access.get(self.client_id, {})
        roles.extend(client_roles.get('roles', []))
        
        direct_roles = token_payload.get('roles', [])
        if isinstance(direct_roles, list):
            roles.extend(direct_roles)
        
        return list(set(roles))
    
    def get_user_company_id(self, token_payload: Dict[str, Any]) -> Optional[str]:
        """Extract company_id from token payload."""
        company_id = token_payload.get('company_id')
        if isinstance(company_id, list) and company_id:
            return company_id[0] if company_id[0] else None
        return company_id if company_id else None
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data={
                        'grant_type': 'authorization_code',
                        'client_id': self.client_id,
                        'client_secret': self.client_secret,
                        'code': code,
                        'redirect_uri': redirect_uri
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to exchange code for token"
            )
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data={
                        'grant_type': 'refresh_token',
                        'client_id': self.client_id,
                        'client_secret': self.client_secret,
                        'refresh_token': refresh_token
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to refresh token"
            )
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user info from Keycloak."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Get user info failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to get user info"
            )


keycloak_service = KeycloakService()


class KeycloakUser:
    """Represents an authenticated Keycloak user."""
    
    def __init__(self, token_payload: Dict[str, Any]):
        self.id = token_payload.get('sub')
        self.email = token_payload.get('email', '')
        self.email_verified = token_payload.get('email_verified', False)
        self.first_name = token_payload.get('given_name', '')
        self.last_name = token_payload.get('family_name', '')
        self.username = token_payload.get('preferred_username', '')
        self.roles = keycloak_service.get_user_roles(token_payload)
        self.company_id = keycloak_service.get_user_company_id(token_payload)
        self.token_payload = token_payload
    
    @property
    def role(self) -> str:
        """Get the primary role (highest privilege)."""
        if 'SUPER_ADMIN' in self.roles:
            return 'SUPER_ADMIN'
        elif 'ADMIN' in self.roles:
            return 'ADMIN'
        return 'USER'
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_active(self) -> bool:
        return True 


async def get_current_keycloak_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
) -> KeycloakUser:
    """
    Dependency to get the current authenticated Keycloak user.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    token_payload = keycloak_service.decode_token(token)
    return KeycloakUser(token_payload)


def require_keycloak_role(allowed_roles: List[str]):
    """Dependency factory to require specific Keycloak roles."""
    async def role_checker(user: KeycloakUser = Depends(get_current_keycloak_user)) -> KeycloakUser:
        if not any(role in user.roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {allowed_roles}"
            )
        return user
    return role_checker


def require_keycloak_super_admin(user: KeycloakUser = Depends(get_current_keycloak_user)) -> KeycloakUser:
    """Require SUPER_ADMIN role."""
    if 'SUPER_ADMIN' not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return user


def require_keycloak_admin(user: KeycloakUser = Depends(get_current_keycloak_user)) -> KeycloakUser:
    """Require ADMIN or SUPER_ADMIN role."""
    if 'ADMIN' not in user.roles and 'SUPER_ADMIN' not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

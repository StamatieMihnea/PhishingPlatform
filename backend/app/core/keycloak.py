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
from httpx import ConnectError, HTTPStatusError
import time
import asyncio

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
    def admin_token_url(self) -> str:
        """Token endpoint for admin client (master realm)."""
        return f"{self.server_url}/realms/master/protocol/openid-connect/token"
    
    @property
    def admin_users_url(self) -> str:
        """Admin users endpoint for the realm."""
        return f"{self.server_url}/admin/realms/{self.realm}/users"
    
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
                options={"verify_aud": False, "verify_iss": False}
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
    
    def get_userinfo_sync(self, access_token: str) -> Dict[str, Any]:
        """Sync variant to get user info from Keycloak."""
        try:
            with httpx.Client() as client:
                response = client.get(
                    self.userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Get user info failed (sync): {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to get user info"
            )

    def get_admin_token(self) -> str:
        """Obtain an admin token using admin-cli and credentials."""
        try:
            data = {
                'grant_type': 'password',
                'client_id': settings.KEYCLOAK_ADMIN_CLIENT_ID,
                'username': settings.KEYCLOAK_ADMIN_USERNAME,
                'password': settings.KEYCLOAK_ADMIN_PASSWORD,
            }
            with httpx.Client() as client:
                response = client.post(self.admin_token_url, data=data, timeout=10.0)
                response.raise_for_status()
                return response.json().get('access_token')
        except Exception as e:
            logger.error(f"Failed to obtain admin token: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Keycloak admin authentication failed"
            )

    def _get_realm_role(self, token: str, role_name: str) -> Dict[str, Any]:
        try:
            with httpx.Client() as client:
                resp = client.get(
                    f"{self.server_url}/admin/realms/{self.realm}/roles/{role_name}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch realm role {role_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch role {role_name} from Keycloak"
            )

    def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        password: str,
        role: str,
        company_id: Optional[str] = None,
    ) -> str:
        """
        Create a Keycloak user, set password, assign realm role, and add company_id attribute.
        Returns the Keycloak user ID.
        """
        token = self.get_admin_token()

        payload: Dict[str, Any] = {
            "username": email,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": True,
            "emailVerified": True,
        }
        if company_id:
            payload["attributes"] = {"company_id": [company_id]}

        try:
            with httpx.Client() as client:
                resp = client.post(
                    self.admin_users_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0,
                )
                # 201 created, 409 conflict if already exists
                if resp.status_code not in (201, 409):
                    logger.error(f"Keycloak create user failed: {resp.status_code} {resp.text}")
                    resp.raise_for_status()

                user_id = None
                if resp.status_code == 201 and resp.headers.get("Location"):
                    user_id = resp.headers["Location"].rstrip("/").split("/")[-1]
                else:
                    # fetch existing by username/email (Keycloak may store username != email)
                    query_urls = [
                        f"{self.admin_users_url}?username={email}",
                        f"{self.admin_users_url}?email={email}",
                        f"{self.admin_users_url}?search={email}",
                    ]
                    for url in query_urls:
                        query_resp = client.get(
                            url,
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=10.0,
                        )
                        query_resp.raise_for_status()
                        matches = query_resp.json()
                        if matches:
                            user_id = matches[0]["id"]
                            break

                if not user_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Failed to resolve Keycloak user ID"
                    )

                # Set password
                pwd_resp = client.put(
                    f"{self.admin_users_url}/{user_id}/reset-password",
                    json={"type": "password", "value": password, "temporary": False},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0,
                )
                pwd_resp.raise_for_status()

                # Assign role
                role_payload = self._get_realm_role(token, role)
                role_resp = client.post(
                    f"{self.admin_users_url}/{user_id}/role-mappings/realm",
                    json=[role_payload],
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0,
                )
                role_resp.raise_for_status()

                return user_id

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Keycloak user creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user in Keycloak"
            )

    def get_user_by_id_admin(self, user_id: str) -> Dict[str, Any]:
        """Fetch user details from Keycloak using admin API."""
        token = self.get_admin_token()
        try:
            with httpx.Client() as client:
                resp = client.get(
                    f"{self.admin_users_url}/{user_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch user {user_id} via admin API: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch user from Keycloak"
            )
    def wait_for_keycloak(self, timeout: int = 300, interval: int = 5):
        """Wait for Keycloak service to be ready."""
        logger.info("Waiting for Keycloak to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Try to fetch OIDC configuration which doesn't require auth
                oidc_url = f"{self.server_url}/realms/{self.realm}/.well-known/openid-configuration"
                with httpx.Client() as client:
                    response = client.get(oidc_url, timeout=5.0)
                    if response.status_code == 200:
                        logger.info("Keycloak is ready!")
                        return True
            except (ConnectError, HTTPStatusError, Exception) as e:
                logger.debug(f"Keycloak not ready yet: {e}")
            
            logger.info(f"Keycloak not ready. Retrying in {interval}s...")
            time.sleep(interval)
            
        raise TimeoutError("Timed out waiting for Keycloak to become ready")


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

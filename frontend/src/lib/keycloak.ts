import Keycloak from 'keycloak-js';
import { useAuthStore } from './store';
import { notifyError } from './notifications';

// Keycloak configuration from environment variables
const keycloakConfig = {
  // Default to prod-style /auth; dev overrides via compose to port 8080 with /auth.
  url: process.env.NEXT_PUBLIC_KEYCLOAK_URL || 'http://localhost/auth',
  realm: process.env.NEXT_PUBLIC_KEYCLOAK_REALM || 'phishing-platform',
  clientId: process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID || 'phishing-frontend',
};

// Create Keycloak instance (only on client side)
let keycloak: Keycloak | null = null;
let keycloakInitPromise: Promise<boolean> | null = null;

export function getKeycloak(): Keycloak {
  if (typeof window === 'undefined') {
    throw new Error('Keycloak can only be used on the client side');
  }
  
  if (!keycloak) {
    keycloak = new Keycloak(keycloakConfig);
  }
  
  return keycloak;
}

export interface KeycloakTokens {
  accessToken: string;
  refreshToken: string;
  idToken: string;
}

export interface KeycloakUserInfo {
  sub: string;
  email: string;
  email_verified: boolean;
  given_name: string;
  family_name: string;
  preferred_username: string;
  roles: string[];
  company_id?: string;
}

// Initialize Keycloak
export async function initKeycloak(): Promise<boolean> {
  const kc = getKeycloak();

  if (keycloakInitPromise) {
    return keycloakInitPromise;
  }

  keycloakInitPromise = (async () => {
    try {
      const authenticated = await kc.init({
        onLoad: 'check-sso',
        silentCheckSsoRedirectUri: typeof window !== 'undefined' 
          ? window.location.origin + '/silent-check-sso.html'
          : undefined,
        pkceMethod: 'S256',
        checkLoginIframe: false,
        scope: 'openid email profile',
      });
      
      if (authenticated) {
        console.log('User is authenticated via Keycloak');
      }

      kc.onTokenExpired = async () => {
        try {
          const refreshed = await kc.updateToken(5);
          if (!refreshed) {
            throw new Error('Token not refreshed');
          }
        } catch {
          const { logout } = useAuthStore.getState();
          logout();
          if (typeof window !== 'undefined') {
            notifyError('Your session expired. Please sign in again.');
            keycloakLogout(window.location.origin + '/login');
          }
        }
      };
      
      return authenticated;
    } catch (error) {
      console.error('Keycloak init error:', error);
      keycloakInitPromise = null;
      return false;
    }
  })();

  return keycloakInitPromise;
}

// Login via Keycloak
export function keycloakLogin(redirectUri?: string): void {
  const kc = getKeycloak();
  kc.login({
    redirectUri: redirectUri || window.location.origin + '/dashboard',
    scope: 'openid email profile',
  });
}

// Logout from Keycloak
export function keycloakLogout(redirectUri?: string): void {
  const kc = getKeycloak();
  kc.logout({
    redirectUri: redirectUri || window.location.origin + '/login',
  });
}

// Get current tokens
export function getTokens(): KeycloakTokens | null {
  const kc = getKeycloak();
  
  if (!kc.authenticated || !kc.token || !kc.refreshToken) {
    return null;
  }
  
  return {
    accessToken: kc.token,
    refreshToken: kc.refreshToken,
    idToken: kc.idToken || '',
  };
}

// Get user info from token
export function getUserInfo(): KeycloakUserInfo | null {
  const kc = getKeycloak();
  
  if (!kc.authenticated || !kc.tokenParsed) {
    return null;
  }
  
  const token = kc.tokenParsed as any;
  
  // Extract roles from token
  const roles: string[] = [];
  
  // Realm roles
  if (token.realm_access?.roles) {
    roles.push(...token.realm_access.roles);
  }
  
  // Direct roles claim (from our custom mapper)
  if (token.roles) {
    if (Array.isArray(token.roles)) {
      roles.push(...token.roles);
    }
  }
  
  // Get company_id
  let companyId = token.company_id;
  if (Array.isArray(companyId) && companyId.length > 0) {
    companyId = companyId[0];
  }
  
  return {
    sub: token.sub,
    email: token.email || '',
    email_verified: token.email_verified || false,
    given_name: token.given_name || '',
    family_name: token.family_name || '',
    preferred_username: token.preferred_username || '',
    roles: Array.from(new Set(roles)),
    company_id: companyId || undefined,
  };
}

// Get primary role
export function getPrimaryRole(roles: string[]): 'SUPER_ADMIN' | 'ADMIN' | 'USER' {
  if (roles.includes('SUPER_ADMIN')) return 'SUPER_ADMIN';
  if (roles.includes('ADMIN')) return 'ADMIN';
  return 'USER';
}

// Refresh token
export async function refreshToken(): Promise<boolean> {
  const kc = getKeycloak();
  
  try {
    const refreshed = await kc.updateToken(30); // Refresh if expires in 30 seconds
    return refreshed;
  } catch (error) {
    console.error('Token refresh failed:', error);
    return false;
  }
}

// Check if authenticated
export function isAuthenticated(): boolean {
  try {
    const kc = getKeycloak();
    return kc.authenticated || false;
  } catch {
    return false;
  }
}

export { keycloakConfig };

from app.schemas.auth import Token, TokenPayload, LoginRequest, RefreshTokenRequest
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse, CompanyStats
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignResponse, CampaignStats
from app.schemas.email_template import EmailTemplateCreate, EmailTemplateUpdate, EmailTemplateResponse
from app.schemas.campaign_target import CampaignTargetCreate, CampaignTargetResponse
from app.schemas.dashboard import DashboardCampaign, DashboardResult, DashboardRecommendation

__all__ = [
    "Token",
    "TokenPayload",
    "LoginRequest",
    "RefreshTokenRequest",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserListResponse",
    "CompanyCreate",
    "CompanyUpdate",
    "CompanyResponse",
    "CompanyStats",
    "CampaignCreate",
    "CampaignUpdate",
    "CampaignResponse",
    "CampaignStats",
    "EmailTemplateCreate",
    "EmailTemplateUpdate",
    "EmailTemplateResponse",
    "CampaignTargetCreate",
    "CampaignTargetResponse",
    "DashboardCampaign",
    "DashboardResult",
    "DashboardRecommendation",
]

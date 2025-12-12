"""
Main API v1 router.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, companies, campaigns, templates, dashboard, tracking

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(companies.router, prefix="/companies", tags=["Companies"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["Campaigns"])
api_router.include_router(templates.router, prefix="/templates", tags=["Email Templates"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["User Dashboard"])
api_router.include_router(tracking.router, prefix="/track", tags=["Tracking"])

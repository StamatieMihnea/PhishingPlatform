"""
Main application file for Email Interaction Tracker service.
"""
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
import base64
import logging
import os
from contextlib import asynccontextmanager

from app.core.database import create_engine_with_retry, get_db
from app.models.campaign_target import CampaignTarget

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Email Tracker Service...")
    create_engine_with_retry()
    yield
    # Shutdown
    logger.info("Shutting down Email Tracker Service...")

app = FastAPI(
    title="Email Interaction Tracker",
    description="Microservice for tracking phishing email opens and clicks",
    version="1.0.0",
    lifespan=lifespan
)

TRACKING_PIXEL = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/open/{token}")
def track_email_open(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Track email open via tracking pixel.
    Returns a 1x1 transparent GIF.
    """
    target = db.query(CampaignTarget).filter(
        CampaignTarget.tracking_token == token
    ).first()
    
    if target:
        if not target.email_opened:
            target.email_opened = True
            target.email_opened_at = datetime.utcnow()
            try:
                db.commit()
                logger.info(f"Tracked OPEN for token {token}")
            except Exception as e:
                logger.error(f"Error saving open event: {e}")
                db.rollback()
    
    return Response(
        content=TRACKING_PIXEL,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


from fastapi import Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

@app.get("/click/{token}", response_class=HTMLResponse)
def track_link_click(
    request: Request,
    token: str,
    db: Session = Depends(get_db)
):
    """
    Track link click and redirect to phishing awareness page.
    """
    target = db.query(CampaignTarget).filter(
        CampaignTarget.tracking_token == token
    ).first()
    
    if target:
        if not target.link_clicked:
            target.link_clicked = True
            target.link_clicked_at = datetime.utcnow()
            try:
                db.commit()
                logger.info(f"Tracked CLICK for token {token}")
            except Exception as e:
                logger.error(f"Error saving click event: {e}")
                db.rollback()
    
    return templates.TemplateResponse(
        request=request, 
        name="phishing_awareness.html", 
        context={
            "token": token,
            "frontend_url": os.getenv("FRONTEND_URL", "http://localhost")
        }
    )

@app.post("/submit/{token}")
def track_credentials_submit(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Track credentials submission (form submit on phishing page).
    """
    target = db.query(CampaignTarget).filter(
        CampaignTarget.tracking_token == token
    ).first()
    
    if target:
        if not target.credentials_submitted:
            target.credentials_submitted = True
            target.submitted_at = datetime.utcnow()
            try:
                db.commit()
                logger.info(f"Tracked SUBMIT for token {token}")
            except Exception as e:
                logger.error(f"Error saving submit event: {e}")
                db.rollback()
    
    return {
        "message": "This was a phishing awareness test. Your credentials were NOT captured.",
        "warning": "In a real attack, your credentials would have been stolen!",
        "tips": [
            "Never enter credentials on unfamiliar websites",
            "Always verify the URL before entering sensitive information",
            "Use a password manager to detect fake login pages",
            "Enable multi-factor authentication on all accounts"
        ]
    }

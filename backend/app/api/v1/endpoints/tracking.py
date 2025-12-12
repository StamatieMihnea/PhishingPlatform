"""
Tracking endpoints for phishing interactions (Public).
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
import base64

from app.core.database import get_db
from app.models.campaign_target import CampaignTarget

router = APIRouter()

TRACKING_PIXEL = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


@router.get("/open/{token}")
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
            db.commit()
    
    return Response(
        content=TRACKING_PIXEL,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@router.get("/click/{token}")
def track_link_click(
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
            db.commit()
    
    awareness_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Phishing Awareness Training</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 16px;
                padding: 40px;
                max-width: 600px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
            }
            .icon {
                font-size: 64px;
                margin-bottom: 20px;
            }
            h1 {
                color: #e74c3c;
                margin-bottom: 20px;
                font-size: 28px;
            }
            .subtitle {
                color: #27ae60;
                font-size: 18px;
                margin-bottom: 30px;
            }
            p {
                color: #555;
                line-height: 1.8;
                margin-bottom: 20px;
            }
            .tips {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
                text-align: left;
            }
            .tips h3 {
                color: #333;
                margin-bottom: 15px;
            }
            .tips ul {
                color: #555;
                padding-left: 20px;
            }
            .tips li {
                margin-bottom: 10px;
            }
            .button {
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px 30px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: bold;
                margin-top: 20px;
                transition: transform 0.2s;
            }
            .button:hover {
                transform: scale(1.05);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">🎣</div>
            <h1>You Clicked a Phishing Link!</h1>
            <p class="subtitle">Don't worry - this was a training exercise.</p>
            <p>
                This was a simulated phishing email sent by your organization's security team 
                to help you recognize and avoid real phishing attacks.
            </p>
            <div class="tips">
                <h3>🛡️ How to Spot Phishing Emails:</h3>
                <ul>
                    <li><strong>Check the sender</strong> - Verify the email address is legitimate</li>
                    <li><strong>Hover over links</strong> - Check where links actually lead before clicking</li>
                    <li><strong>Look for urgency</strong> - Phishing emails often create false urgency</li>
                    <li><strong>Check for errors</strong> - Look for spelling/grammar mistakes</li>
                    <li><strong>When in doubt</strong> - Contact the supposed sender through official channels</li>
                </ul>
            </div>
            <p>
                Remember: Your organization will never ask for passwords or sensitive information via email.
            </p>
            <a href="/" class="button">Learn More About Phishing</a>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=awareness_html)


@router.post("/submit/{token}")
def track_credentials_submit(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Track credentials submission (form submit on phishing page).
    Does NOT store actual credentials - only tracks the event.
    """
    target = db.query(CampaignTarget).filter(
        CampaignTarget.tracking_token == token
    ).first()
    
    if target:
        if not target.credentials_submitted:
            target.credentials_submitted = True
            target.submitted_at = datetime.utcnow()
            db.commit()
    
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

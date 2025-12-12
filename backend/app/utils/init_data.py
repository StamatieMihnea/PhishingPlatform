"""
Initialize default data for the application.
"""
import logging
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.company import Company
from app.models.email_template import EmailTemplate, DifficultyLevel
from app.models.security_recommendation import SecurityRecommendation, Priority

logger = logging.getLogger(__name__)


def init_default_data(db: Session):
    """Initialize default data if not exists."""
    
    super_admin_email = "superadmin@phishingplatform.com"
    super_admin = db.query(User).filter(User.email == super_admin_email).first()
    if not super_admin:
        super_admin = User(
            email=super_admin_email,
            password_hash=get_password_hash("SuperAdmin123!"),
            first_name="Super",
            last_name="Admin",
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        db.add(super_admin)
        db.commit()
        logger.info(f"Created super admin: {super_admin_email}")
    
    demo_company = db.query(Company).filter(Company.domain == "demo.com").first()
    if not demo_company:
        demo_company = Company(
            name="Demo Company",
            domain="demo.com",
            is_active=True
        )
        db.add(demo_company)
        db.commit()
        logger.info("Created demo company")
        
        demo_admin = User(
            email="admin@demo.com",
            password_hash=get_password_hash("Admin123!"),
            first_name="Demo",
            last_name="Admin",
            role=UserRole.ADMIN,
            company_id=demo_company.id,
            is_active=True
        )
        db.add(demo_admin)
        
        for i in range(1, 6):
            demo_user = User(
                email=f"user{i}@demo.com",
                password_hash=get_password_hash("User123!"),
                first_name=f"User{i}",
                last_name="Demo",
                role=UserRole.USER,
                company_id=demo_company.id,
                is_active=True
            )
            db.add(demo_user)
        
        db.commit()
        logger.info("Created demo users")
    
    if db.query(EmailTemplate).count() == 0:
        templates = [
            EmailTemplate(
                name="IT Password Reset",
                subject="[URGENT] Your password will expire in 24 hours",
                body_html="""
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto;">
                        <img src="https://via.placeholder.com/150x50?text=IT+Department" alt="IT Department" style="margin-bottom: 20px;">
                        <h2 style="color: #333;">Password Expiration Notice</h2>
                        <p>Dear {{ recipient_name }},</p>
                        <p>Our records indicate that your password will expire in <strong>24 hours</strong>.</p>
                        <p>To avoid losing access to your account, please reset your password immediately by clicking the button below:</p>
                        <p style="text-align: center; margin: 30px 0;">
                            <a href="{{ phishing_url }}{{ tracking_token }}" style="background-color: #0066cc; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset Password Now</a>
                        </p>
                        <p>If you do not reset your password within 24 hours, your account will be temporarily suspended.</p>
                        <p>Best regards,<br>IT Support Team</p>
                        <hr style="margin-top: 30px; border: none; border-top: 1px solid #ddd;">
                        <p style="font-size: 12px; color: #666;">This is an automated message from the IT Department. Please do not reply to this email.</p>
                    </div>
                    <img src="{{ tracking_url }}/api/v1/track/open/{{ tracking_token }}" width="1" height="1" style="display:none;">
                </body>
                </html>
                """,
                difficulty=DifficultyLevel.EASY,
                category="IT Support"
            ),
            EmailTemplate(
                name="Banking Security Alert",
                subject="Security Alert: Unusual activity detected on your account",
                body_html="""
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
                    <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px;">
                        <div style="text-align: center; margin-bottom: 30px;">
                            <h1 style="color: #1a1a1a; margin: 0;">🏦 SecureBank</h1>
                        </div>
                        <h2 style="color: #c0392b;">⚠️ Security Alert</h2>
                        <p>Dear Valued Customer,</p>
                        <p>We have detected <strong>unusual activity</strong> on your account. For your protection, we have temporarily limited some features.</p>
                        <div style="background: #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <strong>Detected Activity:</strong>
                            <ul>
                                <li>Multiple login attempts from unknown location</li>
                                <li>Unusual transaction patterns</li>
                            </ul>
                        </div>
                        <p>To restore full access to your account, please verify your identity:</p>
                        <p style="text-align: center;">
                            <a href="{{ phishing_url }}{{ tracking_token }}" style="background-color: #27ae60; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Verify My Identity</a>
                        </p>
                        <p style="font-size: 12px; color: #666; margin-top: 30px;">
                            If you did not initiate this request, please contact our support team immediately at 1-800-XXX-XXXX.
                        </p>
                    </div>
                    <img src="{{ tracking_url }}/api/v1/track/open/{{ tracking_token }}" width="1" height="1" style="display:none;">
                </body>
                </html>
                """,
                difficulty=DifficultyLevel.MEDIUM,
                category="Banking"
            ),
            EmailTemplate(
                name="HR Document Signing",
                subject="Action Required: New Company Policy - Signature Needed",
                body_html="""
                <html>
                <body style="font-family: 'Segoe UI', Arial, sans-serif; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto;">
                        <div style="background: #2c3e50; color: white; padding: 20px; text-align: center;">
                            <h1 style="margin: 0;">Human Resources</h1>
                        </div>
                        <div style="padding: 30px; border: 1px solid #ddd; border-top: none;">
                            <p>Hello {{ recipient_name }},</p>
                            <p>The HR department has uploaded a new company policy document that requires your electronic signature.</p>
                            <table style="width: 100%; margin: 20px 0; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Document:</strong></td>
                                    <td style="padding: 10px; border-bottom: 1px solid #eee;">Updated Remote Work Policy 2024</td>
                                </tr>
                                <tr>
                                    <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Due Date:</strong></td>
                                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{{ current_date }}</td>
                                </tr>
                            </table>
                            <p>Please review and sign the document at your earliest convenience.</p>
                            <p style="text-align: center; margin: 30px 0;">
                                <a href="{{ phishing_url }}{{ tracking_token }}" style="background: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px;">View & Sign Document</a>
                            </p>
                            <p style="font-size: 13px; color: #7f8c8d;">
                                Note: All employees are required to sign this document by the due date. Failure to comply may result in restricted access to remote work benefits.
                            </p>
                        </div>
                        <div style="text-align: center; padding: 20px; color: #95a5a6; font-size: 12px;">
                            Human Resources Department<br>
                            {{ company_name }}
                        </div>
                    </div>
                    <img src="{{ tracking_url }}/api/v1/track/open/{{ tracking_token }}" width="1" height="1" style="display:none;">
                </body>
                </html>
                """,
                difficulty=DifficultyLevel.HARD,
                category="HR"
            ),
            EmailTemplate(
                name="Package Delivery",
                subject="Your package delivery failed - Action required",
                body_html="""
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto;">
                        <div style="background: #ff9800; padding: 15px; text-align: center;">
                            <h1 style="color: white; margin: 0;">📦 FastShip Express</h1>
                        </div>
                        <div style="padding: 25px; border: 1px solid #ddd;">
                            <h2>Delivery Attempted - Action Required</h2>
                            <p>Dear Customer,</p>
                            <p>We attempted to deliver your package today but were unable to complete the delivery.</p>
                            <div style="background: #fff3e0; padding: 15px; border-left: 4px solid #ff9800; margin: 20px 0;">
                                <strong>Tracking Number:</strong> FSE{{ tracking_token[:8] | upper }}<br>
                                <strong>Status:</strong> Delivery Failed - Address Verification Needed
                            </div>
                            <p>To reschedule your delivery, please verify your address:</p>
                            <p style="text-align: center;">
                                <a href="{{ phishing_url }}{{ tracking_token }}" style="background: #ff9800; color: white; padding: 15px 35px; text-decoration: none; border-radius: 5px; display: inline-block;">Verify Address & Reschedule</a>
                            </p>
                            <p style="color: #c0392b;"><strong>Note:</strong> Packages not claimed within 5 days will be returned to sender.</p>
                        </div>
                    </div>
                    <img src="{{ tracking_url }}/api/v1/track/open/{{ tracking_token }}" width="1" height="1" style="display:none;">
                </body>
                </html>
                """,
                difficulty=DifficultyLevel.EASY,
                category="Delivery"
            ),
        ]
        
        for template in templates:
            db.add(template)
        
        db.commit()
        logger.info("Created default email templates")
    
    if db.query(SecurityRecommendation).count() == 0:
        recommendations = [
            SecurityRecommendation(
                title="Verify Email Sender Address",
                description="Always check the sender's email address carefully. Phishing emails often use addresses that look similar to legitimate ones but have slight variations.",
                category="email",
                priority=Priority.HIGH,
                trigger_condition="link_clicked"
            ),
            SecurityRecommendation(
                title="Hover Before You Click",
                description="Before clicking any link in an email, hover over it to see the actual URL. If it doesn't match the expected domain, don't click it.",
                category="links",
                priority=Priority.HIGH,
                trigger_condition="link_clicked"
            ),
            SecurityRecommendation(
                title="Never Share Credentials via Email",
                description="Legitimate organizations will never ask for your password or sensitive information via email. If asked, it's likely a phishing attempt.",
                category="passwords",
                priority=Priority.HIGH,
                trigger_condition="credentials_submitted"
            ),
            SecurityRecommendation(
                title="Use Multi-Factor Authentication",
                description="Enable MFA on all your accounts. Even if your password is compromised, MFA provides an additional layer of protection.",
                category="passwords",
                priority=Priority.MEDIUM,
                trigger_condition="credentials_submitted"
            ),
            SecurityRecommendation(
                title="Report Suspicious Emails",
                description="If you receive a suspicious email, report it to your IT security team. This helps protect the entire organization.",
                category="reporting",
                priority=Priority.MEDIUM,
                trigger_condition="general"
            ),
            SecurityRecommendation(
                title="Be Wary of Urgency",
                description="Phishing emails often create a false sense of urgency. Take your time to verify requests, especially those demanding immediate action.",
                category="awareness",
                priority=Priority.MEDIUM,
                trigger_condition="general"
            ),
            SecurityRecommendation(
                title="Check for Grammar and Spelling Errors",
                description="Many phishing emails contain grammar mistakes or spelling errors. Professional organizations typically have proper proofreading.",
                category="awareness",
                priority=Priority.LOW,
                trigger_condition="general"
            ),
        ]
        
        for rec in recommendations:
            db.add(rec)
        
        db.commit()
        logger.info("Created security recommendations")

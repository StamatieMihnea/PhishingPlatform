
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from jinja2 import Template

from app.config import settings

logger = logging.getLogger(__name__)


class EmailSender:
    """SMTP email sender with tracking pixel injection."""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME
        self.use_tls = settings.SMTP_USE_TLS
        self.tracking_base_url = settings.TRACKING_BASE_URL
    
    def inject_tracking_pixel(self, html_content: str, tracking_token: str) -> str:
        """Inject tracking pixel into HTML email."""
        tracking_pixel = f'<img src="{self.tracking_base_url}/api/v1/track/open/{tracking_token}" width="1" height="1" style="display:none;" alt="">'
                
        if '</body>' in html_content.lower():
            return html_content.replace('</body>', f'{tracking_pixel}</body>')
        else:
            return html_content + tracking_pixel
    
    def prepare_email(
        self,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        body_html: str,
        tracking_token: str
    ) -> MIMEMultipart:
        """Prepare email with tracking."""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = recipient_email
        
        context = {
            "recipient_email": recipient_email,
            "recipient_name": recipient_name,
            "tracking_token": tracking_token,
            "tracking_url": self.tracking_base_url,
            "phishing_url": f"{self.tracking_base_url}/api/v1/track/click/",
        }
        
        try:
            template = Template(body_html)
            rendered_html = template.render(**context)
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            rendered_html = body_html
        
        html_with_tracking = self.inject_tracking_pixel(rendered_html, tracking_token)
        
        html_part = MIMEText(html_with_tracking, 'html')
        msg.attach(html_part)
        
        return msg
    
    def send_email(
        self,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        body_html: str,
        tracking_token: str
    ) -> bool:
        """Send email via SMTP."""
        try:
            msg = self.prepare_email(
                recipient_email,
                recipient_name,
                subject,
                body_html,
                tracking_token
            )
            
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            
            server.sendmail(
                self.from_email,
                recipient_email,
                msg.as_string()
            )
            
            server.quit()
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return True
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending to {recipient_email}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error sending email to {recipient_email}: {e}")
            raise


email_sender = EmailSender()

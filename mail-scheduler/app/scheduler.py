
import json
import logging
import time
from datetime import datetime

import pika
from pika.exceptions import AMQPConnectionError
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.worker import EmailTask, EmailTaskStatus, CampaignTarget, Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - scheduler - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
    
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class EmailScheduler:
    """Scheduler that picks up pending email tasks and queues them."""
    
    IMMEDIATE_QUEUE = "email.immediate"
    
    def __init__(self):
        self.connection = None
        self.channel = None
    
    def connect_rabbitmq(self):
        """Connect to RabbitMQ."""
        try:
            credentials = pika.PlainCredentials(
                settings.RABBITMQ_USER,
                settings.RABBITMQ_PASSWORD
            )
            parameters = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                virtual_host=settings.RABBITMQ_VHOST,
                credentials=credentials
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            self.channel.queue_declare(
                queue=self.IMMEDIATE_QUEUE,
                durable=True,
                arguments={"x-max-priority": 10}
            )
            
            logger.info("Connected to RabbitMQ")
            return True
            
        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def get_pending_tasks(self, db):
        """Get tasks that are ready to be sent."""
        now = datetime.utcnow()
        
        tasks = db.query(EmailTask).filter(
            and_(
                EmailTask.status.in_([EmailTaskStatus.PENDING, EmailTaskStatus.QUEUED]),
                EmailTask.scheduled_at <= now
            )
        ).limit(100).all()
        
        return tasks
    
    def queue_task(self, task, target, template_subject, template_body, user_email, user_name):
        """Queue a task to RabbitMQ."""
        message = {
            "task_id": str(task.id),
            "campaign_target_id": str(target.id),
            "recipient_email": user_email,
            "recipient_name": user_name,
            "subject": template_subject,
            "body_html": template_body,
            "tracking_token": target.tracking_token,
            "attempt": 1
        }
        
        self.channel.basic_publish(
            exchange="",
            routing_key=self.IMMEDIATE_QUEUE,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,
                priority=5
            )
        )
        
        logger.info(f"Queued task {task.id} for {user_email}")
    
    def run(self):
        """Main scheduler loop."""
        logger.info("Starting email scheduler...")
        
        while True:
            try:
                if not self.channel or self.channel.is_closed:
                    if not self.connect_rabbitmq():
                        time.sleep(5)
                        continue
                
                db = SessionLocal()
                
                try:
                    tasks = self.get_pending_tasks(db)
                    
                    for task in tasks:
                        try:
                            target = db.query(CampaignTarget).filter(
                                CampaignTarget.id == task.campaign_target_id
                            ).first()
                            
                            if not target:
                                logger.warning(f"Target not found for task {task.id}")
                                task.status = EmailTaskStatus.FAILED
                                task.last_error = "Campaign target not found"
                                continue
                            
                            if target.email_sent:
                                task.status = EmailTaskStatus.SENT
                                continue
                            
                            user_email = f"user@example.com" 
                            user_name = "User" 
                            template_subject = "Phishing Test" 
                            template_body = "<html><body>Test</body></html>" 
                            
                            self.queue_task(
                                task, target,
                                template_subject, template_body,
                                user_email, user_name
                            )
                            
                            task.status = EmailTaskStatus.QUEUED
                            
                        except Exception as e:
                            logger.error(f"Error processing task {task.id}: {e}")
                            task.last_error = str(e)
                    
                    db.commit()
                    
                finally:
                    db.close()
                
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(5)


def main():
    """Main entry point."""
    scheduler = EmailScheduler()
    scheduler.run()


if __name__ == "__main__":
    main()

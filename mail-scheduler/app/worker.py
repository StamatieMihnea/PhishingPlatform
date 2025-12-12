import json
import logging
import time
import signal
import sys
from datetime import datetime
from typing import Optional

import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Enum, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import UUID
import enum
import uuid

from app.config import settings
from app.email_sender import email_sender

logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s - {settings.WORKER_ID} - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class EmailTaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    SENT = "SENT"
    FAILED = "FAILED"


class EmailTask(Base):
    """Email task model (mirrored from backend)."""
    __tablename__ = "email_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_target_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(Enum(EmailTaskStatus), nullable=False, default=EmailTaskStatus.PENDING)
    scheduled_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)


class CampaignTarget(Base):
    """Campaign target model (mirrored from backend)."""
    __tablename__ = "campaign_targets"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    campaign_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    tracking_token = Column(String(64), nullable=False)
    email_sent = Column(Boolean, default=False, nullable=False)
    email_sent_at = Column(DateTime, nullable=True)


class EmailWorker:
    """RabbitMQ consumer worker for email processing."""
    
    IMMEDIATE_QUEUE = "email.immediate"
    SCHEDULED_QUEUE = "email.scheduled"
    RETRY_QUEUE = "email.retry"
    DEAD_LETTER_QUEUE = "email.dead_letter"
    
    def __init__(self):
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self.should_stop = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}. Shutting down gracefully...")
        self.should_stop = True
        if self.channel:
            self.channel.stop_consuming()
    
    def connect(self) -> bool:
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
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            self.channel.basic_qos(prefetch_count=settings.PREFETCH_COUNT)
            
            self._declare_queues()
            
            logger.info(f"Worker {settings.WORKER_ID} connected to RabbitMQ")
            return True
            
        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def _declare_queues(self):
        """Declare required queues."""
        self.channel.exchange_declare(
            exchange="email.dlx",
            exchange_type="direct",
            durable=True
        )
        
        self.channel.queue_declare(
            queue=self.DEAD_LETTER_QUEUE,
            durable=True
        )
        self.channel.queue_bind(
            queue=self.DEAD_LETTER_QUEUE,
            exchange="email.dlx",
            routing_key="dead"
        )
        
        queue_args = {
            "x-dead-letter-exchange": "email.dlx",
            "x-dead-letter-routing-key": "dead"
        }
        
        self.channel.queue_declare(
            queue=self.IMMEDIATE_QUEUE,
            durable=True,
            arguments={**queue_args, "x-max-priority": 10}
        )
        
        self.channel.queue_declare(
            queue=self.SCHEDULED_QUEUE,
            durable=True,
            arguments=queue_args
        )
        
        self.channel.queue_declare(
            queue=self.RETRY_QUEUE,
            durable=True,
            arguments=queue_args
        )
    
    def process_message(self, ch, method, properties, body):
        """Process a single email task message."""
        try:
            message = json.loads(body)
            logger.info(f"Processing task: {message.get('task_id')}")
            
            task_id = message.get('task_id')
            campaign_target_id = message.get('campaign_target_id')
            recipient_email = message.get('recipient_email')
            recipient_name = message.get('recipient_name')
            subject = message.get('subject')
            body_html = message.get('body_html')
            tracking_token = message.get('tracking_token')
            attempt = message.get('attempt', 1)
            
            db = SessionLocal()
            
            try:
                email_sender.send_email(
                    recipient_email=recipient_email,
                    recipient_name=recipient_name,
                    subject=subject,
                    body_html=body_html,
                    tracking_token=tracking_token
                )
                
                if task_id:
                    task = db.query(EmailTask).filter(EmailTask.id == task_id).first()
                    if task:
                        task.status = EmailTaskStatus.SENT
                        task.processed_at = datetime.utcnow()
                        task.attempts = attempt
                
                if campaign_target_id:
                    target = db.query(CampaignTarget).filter(
                        CampaignTarget.id == campaign_target_id
                    ).first()
                    if target:
                        target.email_sent = True
                        target.email_sent_at = datetime.utcnow()
                
                db.commit()
                
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info(f"Task {task_id} completed successfully")
                
            except Exception as e:
                logger.error(f"Error processing task {task_id}: {e}")
                
                if task_id:
                    task = db.query(EmailTask).filter(EmailTask.id == task_id).first()
                    if task:
                        task.attempts = attempt
                        task.last_error = str(e)
                        
                        if attempt < settings.MAX_RETRIES:
                            retry_delay = settings.RETRY_DELAYS[min(attempt - 1, len(settings.RETRY_DELAYS) - 1)]
                            message['attempt'] = attempt + 1
                            
                            self.channel.basic_publish(
                                exchange="",
                                routing_key=self.RETRY_QUEUE,
                                body=json.dumps(message),
                                properties=pika.BasicProperties(
                                    delivery_mode=2,
                                    expiration=str(retry_delay * 1000)
                                )
                            )
                            logger.info(f"Task {task_id} requeued for retry in {retry_delay}s")
                        else:
                            task.status = EmailTaskStatus.FAILED
                            logger.error(f"Task {task_id} failed after {attempt} attempts")
                
                db.commit()
                
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
            finally:
                db.close()
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON message: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def start(self):
        """Start consuming messages from queues."""
        while not self.should_stop:
            try:
                if not self.connect():
                    logger.error("Failed to connect. Retrying in 5 seconds...")
                    time.sleep(5)
                    continue
                
                self.channel.basic_consume(
                    queue=self.IMMEDIATE_QUEUE,
                    on_message_callback=self.process_message
                )
                
                self.channel.basic_consume(
                    queue=self.SCHEDULED_QUEUE,
                    on_message_callback=self.process_message
                )
                
                self.channel.basic_consume(
                    queue=self.RETRY_QUEUE,
                    on_message_callback=self.process_message
                )
                
                logger.info(f"Worker {settings.WORKER_ID} started consuming messages...")
                self.channel.start_consuming()
                
            except AMQPConnectionError as e:
                logger.error(f"Connection lost: {e}. Reconnecting...")
                time.sleep(5)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(5)
        
        if self.connection and self.connection.is_open:
            self.connection.close()
        
        logger.info(f"Worker {settings.WORKER_ID} stopped")


def main():
    """Main entry point."""
    logger.info(f"Starting Mail Scheduler Worker: {settings.WORKER_ID}")
    worker = EmailWorker()
    worker.start()


if __name__ == "__main__":
    main()

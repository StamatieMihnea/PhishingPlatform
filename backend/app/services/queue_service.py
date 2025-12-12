
import json
import logging
from typing import Optional
import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError

from app.core.config import settings

logger = logging.getLogger(__name__)


class QueueService:
    """Service for RabbitMQ operations."""    
    IMMEDIATE_QUEUE = "email.immediate"
    SCHEDULED_QUEUE = "email.scheduled"
    RETRY_QUEUE = "email.retry"
    DEAD_LETTER_QUEUE = "email.dead_letter"
    
    def __init__(self):
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
    
    def connect(self) -> bool:
        """Establish connection to RabbitMQ."""
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
            
            self._declare_queues()
            
            logger.info("Successfully connected to RabbitMQ")
            return True
            
        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def _declare_queues(self):
        """Declare all required queues."""
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
            arguments={
                **queue_args,
                "x-message-ttl": 60000
            }
        )
    
    def disconnect(self):
        """Close connection to RabbitMQ."""
        try:
            if self.connection and self.connection.is_open:
                self.connection.close()
                logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")
    
    def publish_email_task(
        self, 
        task_id: str,
        campaign_target_id: str,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        body_html: str,
        tracking_token: str,
        immediate: bool = False,
        priority: int = 5
    ) -> bool:
        """Publish an email task to the queue."""
        try:
            if not self.channel or self.channel.is_closed:
                if not self.connect():
                    return False
            
            message = {
                "task_id": task_id,
                "campaign_target_id": campaign_target_id,
                "recipient_email": recipient_email,
                "recipient_name": recipient_name,
                "subject": subject,
                "body_html": body_html,
                "tracking_token": tracking_token,
                "attempt": 1
            }
            
            queue_name = self.IMMEDIATE_QUEUE if immediate else self.SCHEDULED_QUEUE
            
            self.channel.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    priority=priority if immediate else 0,
                    content_type="application/json"
                )
            )
            
            logger.info(f"Published email task {task_id} to {queue_name}")
            return True
            
        except (AMQPConnectionError, AMQPChannelError) as e:
            logger.error(f"Failed to publish message: {e}")
            return False
    
    def publish_retry(
        self, 
        task_id: str,
        campaign_target_id: str,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        body_html: str,
        tracking_token: str,
        attempt: int,
        delay_seconds: int = 60
    ) -> bool:
        """Publish an email task for retry with delay."""
        try:
            if not self.channel or self.channel.is_closed:
                if not self.connect():
                    return False
            
            message = {
                "task_id": task_id,
                "campaign_target_id": campaign_target_id,
                "recipient_email": recipient_email,
                "recipient_name": recipient_name,
                "subject": subject,
                "body_html": body_html,
                "tracking_token": tracking_token,
                "attempt": attempt
            }
            
            self.channel.basic_publish(
                exchange="",
                routing_key=self.RETRY_QUEUE,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                    expiration=str(delay_seconds * 1000)
                )
            )
            
            logger.info(f"Published retry task {task_id} with delay {delay_seconds}s")
            return True
            
        except (AMQPConnectionError, AMQPChannelError) as e:
            logger.error(f"Failed to publish retry message: {e}")
            return False


queue_service = QueueService()


def get_queue_service() -> QueueService:
    """Get the queue service instance."""
    return queue_service

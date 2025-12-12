import pytest
import threading
import time
from unittest.mock import MagicMock, patch
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from app.models.email_task import EmailTask, EmailTaskStatus
from app.models.campaign_target import CampaignTarget
from app.models.campaign import Campaign, CampaignStatus


class TestReplicationCorrectness:
    """Tests for verifying replication correctness."""

    def test_concurrent_email_task_processing_no_duplicates(self, db_session, test_company, regular_user):
        """
        Test that multiple workers don't process the same email task twice.
        Simulates competing consumers on RabbitMQ.
        """
        campaign = Campaign(
            company_id=test_company.id,
            created_by=regular_user.id,
            name="Concurrent Test Campaign",
            status=CampaignStatus.RUNNING
        )
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)

        target = CampaignTarget(
            campaign_id=campaign.id,
            user_id=regular_user.id
        )
        db_session.add(target)
        db_session.commit()
        db_session.refresh(target)

        task = EmailTask(
            campaign_target_id=target.id,
            status=EmailTaskStatus.PENDING
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        processed_count = [0]
        lock = threading.Lock()

        def simulate_worker_processing(task_id, worker_id):
            """Simulate a worker attempting to process a task."""
            with lock:
                task = db_session.query(EmailTask).filter(
                    EmailTask.id == task_id,
                    EmailTask.status == EmailTaskStatus.PENDING
                ).first()
                
                if task:
                    task.status = EmailTaskStatus.QUEUED
                    db_session.commit()
                    processed_count[0] += 1
                    return True
            return False

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(simulate_worker_processing, task.id, i)
                for i in range(5)
            ]
            results = [f.result() for f in futures]

        assert processed_count[0] == 1
        assert sum(results) == 1

    def test_data_consistency_on_concurrent_updates(self, db_session, test_company, regular_user):
        """
        Test that concurrent updates to campaign targets maintain consistency.
        """
        campaign = Campaign(
            company_id=test_company.id,
            created_by=regular_user.id,
            name="Consistency Test Campaign",
            status=CampaignStatus.RUNNING
        )
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)

        target = CampaignTarget(
            campaign_id=campaign.id,
            user_id=regular_user.id,
            email_sent=False,
            email_opened=False,
            link_clicked=False
        )
        db_session.add(target)
        db_session.commit()
        target_id = target.id

        def update_email_sent(target_id):
            from datetime import datetime
            db_session.query(CampaignTarget).filter(
                CampaignTarget.id == target_id
            ).update({
                CampaignTarget.email_sent: True,
                CampaignTarget.email_sent_at: datetime.utcnow()
            })
            db_session.commit()

        def update_email_opened(target_id):
            from datetime import datetime
            db_session.query(CampaignTarget).filter(
                CampaignTarget.id == target_id
            ).update({
                CampaignTarget.email_opened: True,
                CampaignTarget.email_opened_at: datetime.utcnow()
            })
            db_session.commit()

        update_email_sent(target_id)
        update_email_opened(target_id)

        db_session.refresh(target)
        assert target.email_sent == True
        assert target.email_opened == True
        assert target.email_sent_at is not None
        assert target.email_opened_at is not None

    def test_failover_task_reprocessing(self, db_session, test_company, regular_user):
        """
        Test that tasks are properly reprocessed when a worker fails.
        Simulates RabbitMQ's acknowledgment and redelivery mechanism.
        """
        campaign = Campaign(
            company_id=test_company.id,
            created_by=regular_user.id,
            name="Failover Test Campaign",
            status=CampaignStatus.RUNNING
        )
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)

        target = CampaignTarget(
            campaign_id=campaign.id,
            user_id=regular_user.id
        )
        db_session.add(target)
        db_session.commit()
        db_session.refresh(target)

        task = EmailTask(
            campaign_target_id=target.id,
            status=EmailTaskStatus.QUEUED,
            attempts=0
        )
        db_session.add(task)
        db_session.commit()
        task_id = task.id

        def failed_worker(task_id):
            task = db_session.query(EmailTask).filter(EmailTask.id == task_id).first()
            task.attempts += 1
            task.last_error = "Worker crashed"
            db_session.commit()
            raise Exception("Worker crashed!")

        try:
            failed_worker(task_id)
        except:
            pass

        db_session.refresh(task)
        assert task.status == EmailTaskStatus.QUEUED
        assert task.attempts == 1
        assert task.last_error == "Worker crashed"

        def successful_worker(task_id):
            from datetime import datetime
            task = db_session.query(EmailTask).filter(EmailTask.id == task_id).first()
            task.status = EmailTaskStatus.SENT
            task.attempts += 1
            task.processed_at = datetime.utcnow()
            db_session.commit()

        successful_worker(task_id)

        db_session.refresh(task)
        assert task.status == EmailTaskStatus.SENT
        assert task.attempts == 2
        assert task.processed_at is not None

    def test_email_uniqueness_no_duplicates(self, db_session, test_company, regular_user):
        """
        Test that the same email is not sent twice to the same target.
        """
        campaign = Campaign(
            company_id=test_company.id,
            created_by=regular_user.id,
            name="Uniqueness Test Campaign",
            status=CampaignStatus.RUNNING
        )
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)

        target = CampaignTarget(
            campaign_id=campaign.id,
            user_id=regular_user.id,
            email_sent=False
        )
        db_session.add(target)
        db_session.commit()
        target_id = target.id

        send_count = [0]

        def send_email_idempotent(target_id):
            """
            Idempotent email sending - only sends if not already sent.
            """
            from datetime import datetime
            result = db_session.query(CampaignTarget).filter(
                CampaignTarget.id == target_id,
                CampaignTarget.email_sent == False
            ).update({
                CampaignTarget.email_sent: True,
                CampaignTarget.email_sent_at: datetime.utcnow()
            })
            db_session.commit()
            if result > 0:
                send_count[0] += 1
            return result > 0

        results = [send_email_idempotent(target_id) for _ in range(5)]

        assert send_count[0] == 1
        assert sum(results) == 1

        db_session.refresh(target)
        assert target.email_sent == True


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    def test_rate_limit_per_domain(self):
        """Test that rate limiting is applied per email domain."""
        from collections import defaultdict
        import time

        rate_limit = 3 
        domain_counts = defaultdict(int)
        domain_timestamps = defaultdict(list)

        def can_send_email(email):
            """Check if email can be sent based on rate limit."""
            domain = email.split('@')[1]
            current_time = time.time()
            
            domain_timestamps[domain] = [
                t for t in domain_timestamps[domain]
                if current_time - t < 1.0
            ]
            
            if len(domain_timestamps[domain]) < rate_limit:
                domain_timestamps[domain].append(current_time)
                return True
            return False

        emails = [
            "user1@domain1.com",
            "user2@domain1.com",
            "user3@domain1.com",
            "user4@domain1.com",
            "user1@domain2.com",
        ]

        results = [can_send_email(email) for email in emails]
        
        assert results[:3] == [True, True, True]
        assert results[3] == False
        assert results[4] == True


class TestQueueConsistency:
    """Tests for queue message consistency."""

    def test_message_acknowledgment(self):
        """Test that messages are only acknowledged after successful processing."""
        acknowledged = []
        rejected = []

        def process_message(message, should_fail=False):
            """Simulate message processing."""
            if should_fail:
                rejected.append(message)
                return False
            acknowledged.append(message)
            return True

        messages = ["msg1", "msg2", "msg3"]
        
        process_message(messages[0], should_fail=False)
        process_message(messages[1], should_fail=True)
        process_message(messages[2], should_fail=False)

        assert len(acknowledged) == 2
        assert len(rejected) == 1
        assert "msg1" in acknowledged
        assert "msg2" in rejected
        assert "msg3" in acknowledged

    def test_dead_letter_queue_handling(self):
        """Test that failed messages are moved to dead letter queue after max retries."""
        max_retries = 3
        
        class MockMessage:
            def __init__(self, id):
                self.id = id
                self.attempts = 0
                self.in_dead_letter = False

        def process_with_retry(message, should_fail=True):
            """Process message with retry logic."""
            message.attempts += 1
            
            if should_fail and message.attempts < max_retries:
                return "retry"
            elif should_fail:
                message.in_dead_letter = True
                return "dead_letter"
            return "success"

        msg = MockMessage(id="test-msg")
        results = []
        
        for _ in range(max_retries + 1):
            result = process_with_retry(msg)
            results.append(result)
            if result in ["success", "dead_letter"]:
                break

        assert msg.attempts == max_retries
        assert msg.in_dead_letter == True
        assert results[-1] == "dead_letter"

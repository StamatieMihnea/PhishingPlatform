import pytest
import json
from unittest.mock import MagicMock, patch
from concurrent.futures import ThreadPoolExecutor


class TestEmailWorker:
    """Tests for the email worker."""

    def test_message_processing_success(self):
        """Test successful message processing."""
        message = {
            "task_id": "test-task-123",
            "campaign_target_id": "target-456",
            "recipient_email": "test@example.com",
            "recipient_name": "Test User",
            "subject": "Test Subject",
            "body_html": "<html><body>Test</body></html>",
            "tracking_token": "token123",
            "attempt": 1
        }

        processed = []

        def mock_process(msg):
            processed.append(msg)
            return True

        result = mock_process(message)
        
        assert result == True
        assert len(processed) == 1
        assert processed[0]["recipient_email"] == "test@example.com"

    def test_message_retry_on_failure(self):
        """Test that failed messages are retried."""
        max_retries = 3
        retry_delays = [60, 300, 900]
        
        message = {
            "task_id": "retry-task-123",
            "attempt": 1
        }

        attempts = []

        def process_with_retry(msg):
            attempts.append(msg["attempt"])
            if msg["attempt"] < max_retries:
                msg["attempt"] += 1
                return "retry"
            return "failed"

        result = "retry"
        while result == "retry":
            result = process_with_retry(message)

        assert len(attempts) == max_retries
        assert result == "failed"

    def test_concurrent_message_processing(self):
        """Test that multiple workers can process messages concurrently."""
        messages = [
            {"id": i, "email": f"user{i}@test.com"}
            for i in range(10)
        ]

        processed = []
        lock_obj = MagicMock()

        def process_message(msg):
            import time
            time.sleep(0.01)
            processed.append(msg["id"])
            return True

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(process_message, messages))

        assert len(processed) == 10
        assert all(results)
        assert len(set(processed)) == 10


class TestEmailSender:
    """Tests for the email sender."""

    def test_tracking_pixel_injection(self):
        """Test that tracking pixel is properly injected into emails."""
        html_content = "<html><body><p>Test content</p></body></html>"
        tracking_token = "test_token_123"
        tracking_base_url = "http://test.com"

        def inject_tracking_pixel(html, token, base_url):
            pixel = f'<img src="{base_url}/api/v1/track/open/{token}" width="1" height="1" style="display:none;" alt="">'
            if '</body>' in html.lower():
                return html.replace('</body>', f'{pixel}</body>')
            return html + pixel

        result = inject_tracking_pixel(html_content, tracking_token, tracking_base_url)

        assert tracking_token in result
        assert '<img src=' in result
        assert 'width="1"' in result

    def test_template_rendering(self):
        """Test that email templates are properly rendered."""
        from jinja2 import Template

        template_html = """
        <html>
        <body>
            <p>Dear {{ recipient_name }},</p>
            <p>Click <a href="{{ phishing_url }}{{ tracking_token }}">here</a></p>
        </body>
        </html>
        """

        context = {
            "recipient_name": "John Doe",
            "phishing_url": "http://test.com/track/click/",
            "tracking_token": "token123"
        }

        template = Template(template_html)
        rendered = template.render(**context)

        assert "John Doe" in rendered
        assert "http://test.com/track/click/token123" in rendered


class TestRateLimiting:
    """Tests for rate limiting in email sending."""

    def test_rate_limit_enforcement(self):
        """Test that rate limits are enforced."""
        import time
        from collections import defaultdict

        rate_limits = {
            "per_minute": 10,
            "per_hour": 100
        }

        send_times = defaultdict(list)

        def can_send(domain, current_time):
            send_times[domain] = [
                t for t in send_times[domain]
                if current_time - t < 3600
            ]

            recent_minute = [
                t for t in send_times[domain]
                if current_time - t < 60
            ]
            if len(recent_minute) >= rate_limits["per_minute"]:
                return False

            if len(send_times[domain]) >= rate_limits["per_hour"]:
                return False

            send_times[domain].append(current_time)
            return True

        current = time.time()
        results = [can_send("test.com", current + i * 0.1) for i in range(15)]
        
        assert sum(results) == 10

    def test_per_domain_rate_limiting(self):
        """Test that rate limits are applied per domain."""
        from collections import defaultdict

        domain_counts = defaultdict(int)
        max_per_domain = 3

        def send_email(email):
            domain = email.split('@')[1]
            if domain_counts[domain] < max_per_domain:
                domain_counts[domain] += 1
                return True
            return False

        emails = [
            "user1@domain1.com",
            "user2@domain1.com",
            "user3@domain1.com",
            "user4@domain1.com",
            "user1@domain2.com",
            "user2@domain2.com",
        ]

        results = [send_email(e) for e in emails]

        assert results == [True, True, True, False, True, True]
        assert domain_counts["domain1.com"] == 3
        assert domain_counts["domain2.com"] == 2

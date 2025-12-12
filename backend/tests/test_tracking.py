import pytest
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_target import CampaignTarget


class TestTracking:
    """Test tracking endpoints."""

    @pytest.fixture
    def campaign_target(self, db_session, test_company, regular_user):
        """Create a campaign target for tracking tests."""
        campaign = Campaign(
            company_id=test_company.id,
            created_by=regular_user.id,
            name="Tracking Test Campaign",
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
        return target

    def test_track_email_open(self, client, campaign_target):
        """Test tracking pixel (email open tracking)."""
        response = client.get(f"/api/v1/track/open/{campaign_target.tracking_token}")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/gif"

    def test_track_email_open_updates_target(self, client, campaign_target, db_session):
        """Test that email open tracking updates the target."""
        assert campaign_target.email_opened == False
        assert campaign_target.email_opened_at is None

        response = client.get(f"/api/v1/track/open/{campaign_target.tracking_token}")
        assert response.status_code == 200

        db_session.refresh(campaign_target)
        assert campaign_target.email_opened == True
        assert campaign_target.email_opened_at is not None

    def test_track_link_click(self, client, campaign_target):
        """Test link click tracking."""
        response = client.get(f"/api/v1/track/click/{campaign_target.tracking_token}")
        
        assert response.status_code == 200
        assert "Phishing" in response.text

    def test_track_link_click_updates_target(self, client, campaign_target, db_session):
        """Test that link click tracking updates the target."""
        assert campaign_target.link_clicked == False

        response = client.get(f"/api/v1/track/click/{campaign_target.tracking_token}")
        assert response.status_code == 200

        db_session.refresh(campaign_target)
        assert campaign_target.link_clicked == True
        assert campaign_target.link_clicked_at is not None

    def test_track_credentials_submit(self, client, campaign_target, db_session):
        """Test credentials submission tracking."""
        assert campaign_target.credentials_submitted == False

        response = client.post(f"/api/v1/track/submit/{campaign_target.tracking_token}")
        assert response.status_code == 200

        db_session.refresh(campaign_target)
        assert campaign_target.credentials_submitted == True
        assert campaign_target.submitted_at is not None

    def test_track_invalid_token(self, client):
        """Test tracking with invalid token (should still work but not update anything)."""
        response = client.get("/api/v1/track/open/invalid_token_12345")
        assert response.status_code == 200

        response = client.get("/api/v1/track/click/invalid_token_12345")
        assert response.status_code == 200

    def test_track_open_idempotent(self, client, campaign_target, db_session):
        """Test that multiple opens don't update timestamp after first."""
        client.get(f"/api/v1/track/open/{campaign_target.tracking_token}")
        db_session.refresh(campaign_target)
        first_opened_at = campaign_target.email_opened_at

        import time
        time.sleep(0.1)
        client.get(f"/api/v1/track/open/{campaign_target.tracking_token}")
        db_session.refresh(campaign_target)
        
        assert campaign_target.email_opened_at == first_opened_at

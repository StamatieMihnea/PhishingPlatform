import pytest
from app.models.email_template import EmailTemplate, DifficultyLevel


class TestCampaignManagement:
    """Test campaign management endpoints."""

    @pytest.fixture
    def test_template(self, db_session, test_company):
        """Create a test email template."""
        template = EmailTemplate(
            company_id=test_company.id,
            name="Test Template",
            subject="Test Subject",
            body_html="<html><body>Test {{ recipient_name }}</body></html>",
            difficulty=DifficultyLevel.MEDIUM,
            category="test"
        )
        db_session.add(template)
        db_session.commit()
        db_session.refresh(template)
        return template

    def test_list_campaigns(self, client, auth_token):
        """Test listing campaigns."""
        response = client.get(
            "/api/v1/campaigns",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "campaigns" in data
        assert "total" in data

    def test_create_campaign(self, client, auth_token, test_template, regular_user):
        """Test creating a campaign."""
        response = client.post(
            "/api/v1/campaigns",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Test Campaign",
                "description": "Test Description",
                "template_id": str(test_template.id),
                "target_user_ids": [str(regular_user.id)]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Campaign"
        assert data["status"] == "DRAFT"

    def test_get_campaign(self, client, auth_token, test_template, regular_user, db_session):
        """Test getting campaign details."""
        from app.models.campaign import Campaign, CampaignStatus
        
        campaign = Campaign(
            company_id=test_template.company_id,
            created_by=regular_user.id,
            name="Test Campaign",
            template_id=test_template.id,
            status=CampaignStatus.DRAFT
        )
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)

        response = client.get(
            f"/api/v1/campaigns/{campaign.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Campaign"

    def test_campaign_stats(self, client, auth_token, test_template, regular_user, db_session):
        """Test getting campaign statistics."""
        from app.models.campaign import Campaign, CampaignStatus
        
        campaign = Campaign(
            company_id=test_template.company_id,
            created_by=regular_user.id,
            name="Stats Test Campaign",
            template_id=test_template.id,
            status=CampaignStatus.DRAFT
        )
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)

        response = client.get(
            f"/api/v1/campaigns/{campaign.id}/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_targets" in data
        assert "emails_sent" in data
        assert "click_rate" in data

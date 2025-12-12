import pytest


class TestUserManagement:
    """Test user management endpoints."""

    def test_list_users(self, client, auth_token, regular_user):
        """Test listing users."""
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data

    def test_create_user(self, client, auth_token, test_company):
        """Test creating a new user."""
        response = client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "email": "newuser@test.com",
                "first_name": "New",
                "last_name": "User",
                "password": "NewUser123!",
                "role": "USER"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["role"] == "USER"

    def test_create_user_duplicate_email(self, client, auth_token, regular_user):
        """Test creating user with duplicate email."""
        response = client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "email": "user@test.com",
                "first_name": "Another",
                "last_name": "User",
                "password": "Password123!",
                "role": "USER"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_get_user(self, client, auth_token, regular_user):
        """Test getting user details."""
        response = client.get(
            f"/api/v1/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == regular_user.email

    def test_update_user(self, client, auth_token, regular_user):
        """Test updating user."""
        response = client.put(
            f"/api/v1/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"first_name": "Updated"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"

    def test_deactivate_user(self, client, auth_token, regular_user):
        """Test deactivating user."""
        response = client.delete(
            f"/api/v1/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] == False

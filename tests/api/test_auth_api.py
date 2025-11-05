import pytest
from fastapi.testclient import TestClient

@pytest.mark.api
def test_login_endpoint(client, test_user):
    """Test the login endpoint with valid credentials"""
    response = client.post(
        "/api/v1/auth/login-json",
        json={"username": "testuser", "password": "password"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.api
def test_login_invalid_credentials(client):
    """Test the login endpoint with invalid credentials"""
    response = client.post(
        "/api/v1/auth/login-json",
        json={"username": "testuser", "password": "wrongpassword"}
    )
    assert response.status_code == 401

@pytest.mark.api
def test_protected_endpoint(client, auth_headers):
    """Test accessing a protected endpoint with valid authentication"""
    response = client.get(
        "/api/v1/users/me",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
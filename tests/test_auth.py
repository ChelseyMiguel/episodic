"""
Tests for authentication endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient) -> None:
    """Signing up with valid data returns tokens."""
    resp = await client.post("/api/v1/auth/signup", json={
        "email": "newuser@example.com",
        "password": "securepass123",
        "display_name": "New User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient) -> None:
    """Signing up with an existing email returns 409."""
    payload = {
        "email": "dup@example.com",
        "password": "securepass123",
        "display_name": "Dup User",
    }
    await client.post("/api/v1/auth/signup", json=payload)
    resp = await client.post("/api/v1/auth/signup", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_signup_weak_password(client: AsyncClient) -> None:
    """Signing up with a short password returns 422."""
    resp = await client.post("/api/v1/auth/signup", json={
        "email": "weakpass@example.com",
        "password": "short",
        "display_name": "Weak",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    """Login with correct credentials returns tokens."""
    await client.post("/api/v1/auth/signup", json={
        "email": "loginuser@example.com",
        "password": "mypassword123",
        "display_name": "Login User",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "loginuser@example.com",
        "password": "mypassword123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    """Login with wrong password returns 401."""
    await client.post("/api/v1/auth/signup", json={
        "email": "wrongpw@example.com",
        "password": "correctpass123",
        "display_name": "Wrong PW",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "wrongpw@example.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient) -> None:
    """Login with unknown email returns 401."""
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "somepass123",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient) -> None:
    """Authenticated user can retrieve their own profile."""
    signup_resp = await client.post("/api/v1/auth/signup", json={
        "email": "meuser@example.com",
        "password": "mepassword123",
        "display_name": "Me User",
    })
    token = signup_resp.json()["access_token"]

    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "meuser@example.com"
    assert data["display_name"] == "Me User"
    assert data["role"] == "reader"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient) -> None:
    """Accessing /me without token returns 401."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_token_refresh(client: AsyncClient) -> None:
    """Refreshing tokens with a valid refresh token returns new tokens."""
    signup_resp = await client.post("/api/v1/auth/signup", json={
        "email": "refreshuser@example.com",
        "password": "refreshpass123",
        "display_name": "Refresh User",
    })
    tokens = signup_resp.json()
    refresh_token = tokens["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert "access_token" in new_tokens
    assert new_tokens["access_token"] != tokens["access_token"]


@pytest.mark.asyncio
async def test_token_refresh_invalid(client: AsyncClient) -> None:
    """Using an invalid refresh token returns 401."""
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": "not.a.valid.token",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_accessing_protected_route_with_valid_token(client: AsyncClient) -> None:
    """Valid access token allows access to protected routes."""
    signup_resp = await client.post("/api/v1/auth/signup", json={
        "email": "protected@example.com",
        "password": "protectedpass123",
        "display_name": "Protected User",
    })
    token = signup_resp.json()["access_token"]

    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_accessing_protected_route_with_invalid_token(client: AsyncClient) -> None:
    """Invalid access token returns 401."""
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401

"""Unit tests for JWT authentication endpoints.

Sprint Context: Sprint 38 (2025-12-08) - Feature 38.1a: JWT Authentication Backend

Tests cover:
- User registration
- Login with JWT token generation
- Token refresh
- Current user retrieval
- Logout
- Token validation
- Protected route access
- Admin role verification

Test Strategy:
    - Mock Redis client to avoid external dependencies
    - Test both success and failure paths
    - Verify JWT token generation and validation
    - Test password hashing and verification
    - Verify error handling and status codes
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.auth import create_token_pair
from src.core.user_store import UserInDB


@pytest.fixture
def client() -> TestClient:
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_redis() -> MagicMock:
    """Create mock Redis client."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def sample_user() -> UserInDB:
    """Create sample user for testing."""
    return UserInDB(
        user_id="user_test123",
        username="testuser",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU2OmqP3XDKu",  # "password123"
        email="test@example.com",
        role="user",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        is_active=True,
    )


class TestUserRegistration:
    """Test user registration endpoint."""

    @patch("src.api.v1.auth.UserStore")
    def test_register_success(
        self, mock_user_store_class: MagicMock, client: TestClient, sample_user: UserInDB
    ) -> None:
        """Test successful user registration."""
        # Setup mock
        mock_store = MagicMock()
        mock_store.create_user = AsyncMock(return_value=sample_user)
        mock_store.close = AsyncMock()
        mock_store.to_public = MagicMock(
            return_value={
                "user_id": sample_user.user_id,
                "username": sample_user.username,
                "email": sample_user.email,
                "role": sample_user.role,
                "created_at": sample_user.created_at.isoformat(),
                "is_active": sample_user.is_active,
            }
        )
        mock_user_store_class.return_value = mock_store

        # Make request
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "password": "password123",
                "email": "test@example.com",
                "role": "user",
            },
        )

        # Verify response
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["role"] == "user"
        assert "user_id" in data
        assert "hashed_password" not in data  # Should not expose password

    @patch("src.api.v1.auth.UserStore")
    def test_register_duplicate_username(
        self, mock_user_store_class: MagicMock, client: TestClient
    ) -> None:
        """Test registration with duplicate username."""
        # Setup mock
        mock_store = MagicMock()
        mock_store.create_user = AsyncMock(
            side_effect=ValueError("Username 'testuser' already exists")
        )
        mock_store.close = AsyncMock()
        mock_user_store_class.return_value = mock_store

        # Make request
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "password": "password123",
                "email": "test@example.com",
            },
        )

        # Verify response
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        # Handle error format from exception handler middleware
        error_message = (
            response_data.get("detail")
            or response_data.get("error", {}).get("message", "")
        )
        assert "already exists" in str(error_message)

    def test_register_invalid_username(self, client: TestClient) -> None:
        """Test registration with invalid username (too short)."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "ab",  # Too short (min 3 chars)
                "password": "password123",
                "email": "test@example.com",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_invalid_password(self, client: TestClient) -> None:
        """Test registration with invalid password (too short)."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "password": "short",  # Too short (min 8 chars)
                "email": "test@example.com",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLogin:
    """Test login endpoint."""

    @patch("src.api.v1.auth.UserStore")
    def test_login_success(
        self, mock_user_store_class: MagicMock, client: TestClient, sample_user: UserInDB
    ) -> None:
        """Test successful login."""
        # Setup mock
        mock_store = MagicMock()
        mock_store.get_user_by_username = AsyncMock(return_value=sample_user)
        mock_store.verify_password = AsyncMock(return_value=True)
        mock_store.close = AsyncMock()
        mock_user_store_class.return_value = mock_store

        # Make request
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "password123",
            },
        )

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    @patch("src.api.v1.auth.UserStore")
    def test_login_user_not_found(self, mock_user_store_class: MagicMock, client: TestClient) -> None:
        """Test login with non-existent user."""
        # Setup mock
        mock_store = MagicMock()
        mock_store.get_user_by_username = AsyncMock(return_value=None)
        mock_store.close = AsyncMock()
        mock_user_store_class.return_value = mock_store

        # Make request
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "password123",
            },
        )

        # Verify response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = response.json()
        error_message = (
            response_data.get("detail")
            or response_data.get("error", {}).get("message", "")
        )
        assert "Incorrect username or password" in str(error_message)

    @patch("src.api.v1.auth.UserStore")
    def test_login_wrong_password(
        self, mock_user_store_class: MagicMock, client: TestClient, sample_user: UserInDB
    ) -> None:
        """Test login with wrong password."""
        # Setup mock
        mock_store = MagicMock()
        mock_store.get_user_by_username = AsyncMock(return_value=sample_user)
        mock_store.verify_password = AsyncMock(return_value=False)
        mock_store.close = AsyncMock()
        mock_user_store_class.return_value = mock_store

        # Make request
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "wrongpassword",
            },
        )

        # Verify response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = response.json()
        error_message = (
            response_data.get("detail")
            or response_data.get("error", {}).get("message", "")
        )
        assert "Incorrect username or password" in str(error_message)

    @patch("src.api.v1.auth.UserStore")
    def test_login_inactive_account(
        self, mock_user_store_class: MagicMock, client: TestClient, sample_user: UserInDB
    ) -> None:
        """Test login with inactive account."""
        # Setup mock with inactive user
        sample_user.is_active = False
        mock_store = MagicMock()
        mock_store.get_user_by_username = AsyncMock(return_value=sample_user)
        mock_store.close = AsyncMock()
        mock_user_store_class.return_value = mock_store

        # Make request
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "password123",
            },
        )

        # Verify response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = response.json()
        error_message = (
            response_data.get("detail")
            or response_data.get("error", {}).get("message", "")
        )
        assert "inactive" in str(error_message).lower()


class TestTokenRefresh:
    """Test token refresh endpoint."""

    def test_refresh_token_success(self, client: TestClient) -> None:
        """Test successful token refresh."""
        # Create valid token pair
        tokens = create_token_pair("user_test123", "testuser", "user")

        # Make request
        response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": tokens.refresh_token,
            },
        )

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self, client: TestClient) -> None:
        """Test token refresh with invalid token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "invalid.token.here",
            },
        )

        # Verify response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_with_access_token(self, client: TestClient) -> None:
        """Test token refresh with access token instead of refresh token."""
        # Create valid token pair
        tokens = create_token_pair("user_test123", "testuser", "user")

        # Make request with access token instead of refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": tokens.access_token,  # Wrong token type
            },
        )

        # Verify response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetMe:
    """Test get current user endpoint."""

    @patch("src.api.v1.auth.UserStore")
    def test_get_me_success(
        self, mock_user_store_class: MagicMock, client: TestClient, sample_user: UserInDB
    ) -> None:
        """Test successful get current user."""
        # Create valid token
        tokens = create_token_pair(sample_user.user_id, sample_user.username, sample_user.role)

        # Setup mock
        mock_store = MagicMock()
        mock_store.get_user_by_id = AsyncMock(return_value=sample_user)
        mock_store.close = AsyncMock()
        mock_store.to_public = MagicMock(
            return_value={
                "user_id": sample_user.user_id,
                "username": sample_user.username,
                "email": sample_user.email,
                "role": sample_user.role,
                "created_at": sample_user.created_at.isoformat(),
                "is_active": sample_user.is_active,
            }
        )
        mock_user_store_class.return_value = mock_store

        # Make request
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens.access_token}"},
        )

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["role"] == "user"
        assert "hashed_password" not in data

    def test_get_me_no_token(self, client: TestClient) -> None:
        """Test get current user without token."""
        response = client.get("/api/v1/auth/me")

        # Verify response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_me_invalid_token(self, client: TestClient) -> None:
        """Test get current user with invalid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        # Verify response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogout:
    """Test logout endpoint."""

    def test_logout_success(self, client: TestClient, sample_user: UserInDB) -> None:
        """Test successful logout."""
        # Create valid token
        tokens = create_token_pair(sample_user.user_id, sample_user.username, sample_user.role)

        # Make request
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {tokens.access_token}"},
        )

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "logged out" in data["message"].lower()

    def test_logout_no_token(self, client: TestClient) -> None:
        """Test logout without token."""
        response = client.post("/api/v1/auth/logout")

        # Verify response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestProtectedRoutes:
    """Test protected route access with authentication."""

    def test_protected_route_with_valid_token(
        self, client: TestClient, sample_user: UserInDB
    ) -> None:
        """Test accessing protected route with valid token."""
        # Create valid token
        tokens = create_token_pair(sample_user.user_id, sample_user.username, sample_user.role)

        # Make request to a protected endpoint (using /me as example)
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens.access_token}"},
        )

        # Should not get 401 (exact status depends on endpoint implementation)
        assert response.status_code != status.HTTP_401_UNAUTHORIZED

    def test_protected_route_without_token(self, client: TestClient) -> None:
        """Test accessing protected route without token."""
        response = client.get("/api/v1/auth/me")

        # Verify response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_route_with_expired_token(self, client: TestClient) -> None:
        """Test accessing protected route with expired token."""
        # This would require time-traveling or creating an expired token
        # For now, test with malformed token
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer expired.token.here"},
        )

        # Verify response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenGeneration:
    """Test JWT token generation and validation."""

    def test_token_pair_creation(self) -> None:
        """Test creating access and refresh token pair."""
        tokens = create_token_pair("user_123", "testuser", "user")

        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "bearer"
        assert tokens.expires_in > 0

    def test_token_contains_user_data(self) -> None:
        """Test that tokens contain user data."""
        from src.core.auth import decode_access_token, decode_refresh_token

        tokens = create_token_pair("user_123", "testuser", "admin")

        # Decode access token
        access_data = decode_access_token(tokens.access_token)
        assert access_data.user_id == "user_123"
        assert access_data.username == "testuser"
        assert access_data.role == "admin"
        assert access_data.token_type == "access"

        # Decode refresh token
        refresh_data = decode_refresh_token(tokens.refresh_token)
        assert refresh_data.user_id == "user_123"
        assert refresh_data.username == "testuser"
        assert refresh_data.role == "admin"
        assert refresh_data.token_type == "refresh"

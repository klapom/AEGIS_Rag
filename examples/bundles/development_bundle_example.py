"""Development Bundle Example - Sprint 95.3.

Demonstrates usage of the development_bundle for software development workflows.

The development bundle combines:
- code_generation: Generate production code
- code_review: Quality and security review
- testing: Test generation and execution
- debugging: Debug assistance

Use cases:
- Feature implementation
- Code review automation
- Test coverage improvement
- Bug fixing
"""

import asyncio

from src.agents.skills.bundle_installer import get_bundle_status, install_bundle


async def main():
    """Demonstrate development bundle usage."""

    print("=" * 80)
    print("Development Bundle Example - Sprint 95.3")
    print("=" * 80)

    # 1. Install bundle
    print("\n1. Installing Development Bundle...")
    report = install_bundle("development_bundle")

    if report.success:
        print(f"   ✓ {report.summary}")
    else:
        print(f"   ✗ {report.summary}")
        return

    # 2. Simulate development workflow
    print("\n2. Example Development Workflow:")
    print("   Task: Implement user authentication endpoint")
    print()

    # Step 1: Code Generation
    print("   Step 1: Code Generation")
    print("   → Generating FastAPI endpoint with type hints...")
    print("   → Including docstrings and error handling...")
    print()
    print("   Generated Code:")
    print("-" * 80)
    print(
        """
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

router = APIRouter()

class LoginRequest(BaseModel):
    \"\"\"User login request model.\"\"\"
    email: EmailStr
    password: str

@router.post("/auth/login", status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    user_service: UserService = Depends(get_user_service)
) -> dict:
    \"\"\"Authenticate user and return JWT token.

    Args:
        request: Login credentials
        user_service: User service dependency

    Returns:
        JWT token and user info

    Raises:
        HTTPException: If authentication fails
    \"\"\"
    user = await user_service.authenticate(request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    token = create_jwt_token(user.id)
    return {"token": token, "user": user.to_dict()}
"""
    )
    print("-" * 80)

    # Step 2: Code Review
    print("\n   Step 2: Code Review")
    print("   → Reviewing code for quality and security...")
    print()
    print("   Review Results:")
    print("     Security:")
    print("       ✓ Password not logged")
    print("       ✓ JWT token generation secure")
    print("       ⚠ Consider rate limiting for login endpoint")
    print()
    print("     Style:")
    print("       ✓ Type hints present")
    print("       ✓ Docstrings complete")
    print("       ✓ Error handling appropriate")
    print()
    print("     Performance:")
    print("       ✓ Async/await used correctly")
    print("       ✓ No blocking operations")
    print()
    print("   Overall Score: 9.2/10")

    # Step 3: Test Generation
    print("\n   Step 3: Test Generation")
    print("   → Generating pytest unit tests...")
    print("   → Including fixtures and mocks...")
    print()
    print("   Generated Tests:")
    print("-" * 80)
    print(
        """
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_user_service():
    \"\"\"Mock user service for testing.\"\"\"
    service = AsyncMock()
    service.authenticate = AsyncMock()
    return service

async def test_login_success(client: TestClient, mock_user_service):
    \"\"\"Test successful login.\"\"\"
    mock_user_service.authenticate.return_value = User(
        id="123", email="test@example.com"
    )

    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })

    assert response.status_code == 200
    assert "token" in response.json()
    assert response.json()["user"]["email"] == "test@example.com"

async def test_login_invalid_credentials(client: TestClient, mock_user_service):
    \"\"\"Test login with invalid credentials.\"\"\"
    mock_user_service.authenticate.return_value = None

    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "wrong"
    })

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"
"""
    )
    print("-" * 80)

    # Step 4: Test Execution
    print("\n   Step 4: Test Execution")
    print("   → Running pytest with coverage...")
    print()
    print("   Test Results:")
    print("     test_login_success ✓")
    print("     test_login_invalid_credentials ✓")
    print("     test_login_missing_fields ✓")
    print("     test_login_malformed_email ✓")
    print()
    print("   Coverage: 95%")
    print("   All tests passed!")

    # Step 5: Debugging Example
    print("\n   Step 5: Debugging Example")
    print("   Issue: Function returns None unexpectedly")
    print()
    print("   Debug Analysis:")
    print("     → Variable inspection at line 23:")
    print("       - user: None (expected: User object)")
    print("       - request.email: 'test@example.com'")
    print("       - request.password: '***' (hidden)")
    print()
    print("     Suggested Fix:")
    print("       The user_service.authenticate() is returning None")
    print("       because the password hash comparison is failing.")
    print("       Check that bcrypt is configured correctly.")

    # 3. Performance metrics
    print("\n3. Performance Metrics:")
    print("   Total Latency: 1,200ms (avg)")
    print("   P95 Latency: 2,500ms")
    print("   Skills Used: 4/4")
    print("   Tokens Used: 8,456 / 10,000")
    print("   Code Generated: 247 lines")
    print("   Tests Generated: 4")

    print("\n" + "=" * 80)
    print("Example completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

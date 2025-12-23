#!/usr/bin/env python3
"""Generate JWT token for MCP authentication.

This script generates JWT tokens for use with MCP authentication.
Tokens are used to authenticate requests to MCP endpoints.

Usage:
    # Generate admin token (default 1 hour expiry)
    python scripts/generate_mcp_token.py --user-id admin

    # Generate user token (24 hour expiry)
    python scripts/generate_mcp_token.py --user-id user123 --expiry 24

    # Generate with specific role
    python scripts/generate_mcp_token.py --user-id ci-pipeline --role admin

    # Generate long-lived integration token (90 days)
    python scripts/generate_mcp_token.py --user-id pipeline --role admin --expiry 2160

Example Output:
    MCP Authentication Token Generated
    =====================================
    User ID:    admin
    Username:   admin
    Role:       admin
    Expires In: 24 hours
    Expiry:     2025-12-24T22:30:45Z

    Token:
    eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiYWRtaW4iLCJ1c2VybmFtZSI6ImFkbWluIiwicm9sZSI6ImFkbWluIiwicHJvdmlzaW9uIjoiYWRtaW4iLCJleHAiOjE3MDM0MjM2NDUsImlhdCI6MTcwMzMzNzI0NX0.xyz...

    Save this token securely. Do not commit to git or share in logs.

Sprint Context:
    Feature 63.7: MCP Authentication Guide (2 SP)
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, UTC

try:
    import jwt
except ImportError:
    print("Error: PyJWT not installed")
    print("Install with: pip install PyJWT")
    sys.exit(1)


def get_jwt_secret() -> str:
    """Get JWT secret from environment or raise error.

    Returns:
        JWT secret string

    Raises:
        ValueError: If MCP_JWT_SECRET not set
    """
    secret = os.getenv("MCP_JWT_SECRET")
    if not secret:
        raise ValueError(
            "MCP_JWT_SECRET environment variable not set. "
            "Generate with: openssl rand -hex 32"
        )

    if len(secret) < 32:
        raise ValueError(
            f"MCP_JWT_SECRET too short: {len(secret)} chars (min 32 required)"
        )

    return secret


def generate_token(
    user_id: str,
    username: str = None,
    role: str = "user",
    expiry_hours: int = 1,
) -> str:
    """Generate JWT token for MCP authentication.

    Args:
        user_id: Unique user identifier
        username: Username for display (defaults to user_id)
        role: User role (user, admin, superadmin)
        expiry_hours: Token lifetime in hours

    Returns:
        JWT token string

    Raises:
        ValueError: If secret not set or invalid
    """
    if not username:
        username = user_id

    secret = get_jwt_secret()

    now = datetime.now(UTC)
    expiry = now + timedelta(hours=expiry_hours)

    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "token_type": "access",
        "exp": expiry,
        "iat": now,
    }

    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


def format_duration(hours: int) -> str:
    """Format duration in human-readable form.

    Args:
        hours: Duration in hours

    Returns:
        Formatted string (e.g., "1 hour", "24 hours", "2 days")
    """
    if hours < 1:
        minutes = int(hours * 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    elif hours < 24:
        return f"{int(hours)} hour{'s' if int(hours) != 1 else ''}"
    elif hours < 24 * 30:
        days = hours / 24
        if days == int(days):
            return f"{int(days)} day{'s' if int(days) != 1 else ''}"
        else:
            return f"{days:.1f} days"
    else:
        months = hours / (24 * 30)
        if months == int(months):
            return f"{int(months)} month{'s' if int(months) != 1 else ''}"
        else:
            return f"{months:.1f} months"


def main():
    """Main entry point for token generation."""
    parser = argparse.ArgumentParser(
        description="Generate JWT token for MCP authentication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate admin token (1 hour, default)
    python scripts/generate_mcp_token.py --user-id admin

    # Generate user token (24 hours)
    python scripts/generate_mcp_token.py --user-id john --expiry 24

    # Generate integration token (90 days)
    python scripts/generate_mcp_token.py --user-id ci-pipeline --role admin --expiry 2160

    # With custom username
    python scripts/generate_mcp_token.py --user-id u123 --username "John Doe"
        """,
    )

    parser.add_argument(
        "--user-id",
        required=True,
        help="Unique user identifier (required)",
    )

    parser.add_argument(
        "--username",
        default=None,
        help="Username for display (defaults to user-id)",
    )

    parser.add_argument(
        "--role",
        choices=["user", "admin", "superadmin"],
        default="user",
        help="User role (default: user)",
    )

    parser.add_argument(
        "--expiry",
        type=int,
        default=1,
        help="Token lifetime in hours (default: 1)",
    )

    parser.add_argument(
        "--secret",
        help="JWT secret (uses MCP_JWT_SECRET env var if not provided)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed token information",
    )

    parser.add_argument(
        "--decode-output",
        action="store_true",
        help="Decode and display token payload",
    )

    args = parser.parse_args()

    try:
        # Generate token
        token = generate_token(
            user_id=args.user_id,
            username=args.username,
            role=args.role,
            expiry_hours=args.expiry,
        )

        # Calculate expiry time
        now = datetime.now(UTC)
        expiry_time = now + timedelta(hours=args.expiry)

        # Display output
        print("\n" + "=" * 60)
        print("MCP Authentication Token Generated")
        print("=" * 60)
        print(f"User ID:    {args.user_id}")
        print(f"Username:   {args.username or args.user_id}")
        print(f"Role:       {args.role}")
        print(f"Expires In: {format_duration(args.expiry)}")
        print(f"Expiry:     {expiry_time.strftime('%Y-%m-%dT%H:%M:%SZ')}")

        if args.verbose:
            print(f"Issued At:  {now.strftime('%Y-%m-%dT%H:%M:%SZ')}")
            print(f"Algorithm:  HS256")
            print(f"Token Type: access")

        print()
        print("Token:")
        print(token)
        print()

        if args.decode_output:
            # Decode and display payload
            try:
                decoded = jwt.decode(token, options={"verify_signature": False})
                print("Decoded Payload:")
                import json

                print(json.dumps(decoded, indent=2, default=str))
                print()
            except Exception as e:
                print(f"Could not decode token: {e}")

        print("=" * 60)
        print("IMPORTANT SECURITY NOTES:")
        print("=" * 60)
        print("- Save this token in a secure location")
        print("- Do NOT commit tokens to git or version control")
        print("- Do NOT share tokens in logs, chat, or email")
        print("- Use environment variables to store tokens")
        print("- Rotate tokens regularly (every 90 days)")
        print("- Use different tokens for different purposes")
        print()
        print("Usage in requests:")
        print(f'  curl -H "Authorization: Bearer {token[:20]}..." \\')
        print('       http://localhost:8000/api/v1/mcp/servers')
        print()

        # Return token for piping to other commands
        print("TOKEN=" + token, file=sys.stderr)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

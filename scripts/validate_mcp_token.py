#!/usr/bin/env python3
"""Validate JWT token for MCP authentication.

This script validates JWT tokens used for MCP authentication.
It checks token signature, expiration, and displays token details.

Usage:
    # Validate token (check signature and expiration)
    python scripts/validate_mcp_token.py --token "eyJhbGc..."

    # Show detailed token information
    python scripts/validate_mcp_token.py --token "eyJhbGc..." --verbose

    # Check token from environment variable
    python scripts/validate_mcp_token.py --token "$MCP_TOKEN"

    # Validate token from file
    TOKEN=$(cat /path/to/token.txt)
    python scripts/validate_mcp_token.py --token "$TOKEN"

Example Output:
    Token Validation Report
    =======================
    Status:          VALID
    Token Type:      access
    User ID:         admin
    Username:        admin
    Role:            admin
    Issued At:       2025-12-23T22:00:00Z
    Expires At:      2025-12-24T22:00:00Z
    Time Until Exp:  23h 59m 30s
    Current Time:    2025-12-23T22:00:30Z

Sprint Context:
    Feature 63.7: MCP Authentication Guide (2 SP)
"""

import argparse
import json
import os
import sys
from datetime import datetime, UTC

try:
    import jwt
except ImportError:
    print("Error: PyJWT not installed")
    print("Install with: pip install PyJWT")
    sys.exit(1)


def get_jwt_secret() -> str:
    """Get JWT secret from environment.

    Returns:
        JWT secret string or empty if not set

    Note:
        Returns empty string instead of raising error to allow
        token inspection without signature validation.
    """
    return os.getenv("MCP_JWT_SECRET", "")


def validate_token(token: str, verify_signature: bool = True) -> dict:
    """Validate JWT token.

    Args:
        token: JWT token string
        verify_signature: Whether to verify token signature (requires secret)

    Returns:
        Dictionary with validation result and decoded payload

    Raises:
        ValueError: If token is invalid or expired
    """
    try:
        secret = get_jwt_secret()

        # Decode token
        if verify_signature and secret:
            decoded = jwt.decode(token, secret, algorithms=["HS256"])
        else:
            decoded = jwt.decode(token, options={"verify_signature": False})

        return {
            "valid": True,
            "verified": bool(verify_signature and secret),
            "payload": decoded,
            "error": None,
        }

    except jwt.ExpiredSignatureError:
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            return {
                "valid": False,
                "verified": False,
                "payload": decoded,
                "error": "Token has expired",
                "error_type": "ExpiredSignatureError",
            }
        except Exception as e:
            return {
                "valid": False,
                "verified": False,
                "payload": None,
                "error": f"Expired and invalid: {str(e)}",
                "error_type": "ExpiredSignatureError",
            }

    except jwt.InvalidSignatureError:
        return {
            "valid": False,
            "verified": False,
            "payload": None,
            "error": "Invalid token signature",
            "error_type": "InvalidSignatureError",
        }

    except jwt.DecodeError as e:
        return {
            "valid": False,
            "verified": False,
            "payload": None,
            "error": f"Could not decode token: {str(e)}",
            "error_type": "DecodeError",
        }

    except jwt.InvalidTokenError as e:
        return {
            "valid": False,
            "verified": False,
            "payload": None,
            "error": f"Invalid token: {str(e)}",
            "error_type": "InvalidTokenError",
        }

    except Exception as e:
        return {
            "valid": False,
            "verified": False,
            "payload": None,
            "error": f"Unexpected error: {str(e)}",
            "error_type": type(e).__name__,
        }


def format_timestamp(timestamp: float) -> str:
    """Format Unix timestamp to ISO format.

    Args:
        timestamp: Unix timestamp

    Returns:
        ISO format string
    """
    try:
        dt = datetime.fromtimestamp(timestamp, tz=UTC)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return str(timestamp)


def format_time_remaining(expiry_timestamp: float) -> str:
    """Format time remaining until expiry.

    Args:
        expiry_timestamp: Unix timestamp of expiry

    Returns:
        Human-readable time remaining
    """
    try:
        now = datetime.now(UTC).timestamp()
        remaining = int(expiry_timestamp - now)

        if remaining < 0:
            return "EXPIRED"

        days = remaining // 86400
        hours = (remaining % 86400) // 3600
        minutes = (remaining % 3600) // 60
        seconds = remaining % 60

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    except Exception:
        return "Unknown"


def main():
    """Main entry point for token validation."""
    parser = argparse.ArgumentParser(
        description="Validate JWT token for MCP authentication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Validate token (show summary)
    python scripts/validate_mcp_token.py --token "eyJhbGc..."

    # Show detailed information
    python scripts/validate_mcp_token.py --token "eyJhbGc..." --verbose

    # No signature verification (if secret not available)
    python scripts/validate_mcp_token.py --token "eyJhbGc..." --no-verify

    # Parse token from environment variable
    python scripts/validate_mcp_token.py --token "$MCP_TOKEN"

    # Check token from file
    TOKEN=$(cat token.txt) && python scripts/validate_mcp_token.py --token "$TOKEN"
        """,
    )

    parser.add_argument(
        "--token",
        required=True,
        help="JWT token to validate",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed token information and payload",
    )

    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip signature verification (for inspection only)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()

    # Validate token
    verify_sig = not args.no_verify
    result = validate_token(args.token, verify_signature=verify_sig)

    if args.json:
        # JSON output
        output = {
            "valid": result["valid"],
            "verified": result.get("verified", False),
            "error": result["error"],
            "payload": result["payload"],
        }
        print(json.dumps(output, indent=2, default=str))
        sys.exit(0 if result["valid"] else 1)

    # Human-readable output
    print("\n" + "=" * 60)
    print("Token Validation Report")
    print("=" * 60)

    # Status
    if result["valid"]:
        status_symbol = "✓"
        status_text = "VALID"
        status_color = "\033[92m"  # Green
    else:
        status_symbol = "✗"
        status_text = "INVALID"
        status_color = "\033[91m"  # Red

    reset_color = "\033[0m"
    print(f"Status:          {status_color}{status_symbol} {status_text}{reset_color}")

    if result["error"]:
        print(f"Error:           {result['error']}")
        if result.get("error_type"):
            print(f"Error Type:      {result['error_type']}")

    if result["verified"]:
        print("Signature:       ✓ Verified")
    elif result.get("valid"):
        print("Signature:       ⚠ Not verified (no secret)")
    else:
        print("Signature:       ✗ Invalid or unverified")

    # Payload details
    if result["payload"]:
        payload = result["payload"]
        print()
        print("Payload:")
        print(f"  Token Type:     {payload.get('token_type', 'N/A')}")
        print(f"  User ID:        {payload.get('user_id', 'N/A')}")
        print(f"  Username:       {payload.get('username', 'N/A')}")
        print(f"  Role:           {payload.get('role', 'user')}")

        # Timestamps
        if "iat" in payload:
            issued_at = format_timestamp(payload["iat"])
            print(f"  Issued At:      {issued_at}")

        if "exp" in payload:
            expiry_at = format_timestamp(payload["exp"])
            print(f"  Expires At:     {expiry_at}")
            time_remaining = format_time_remaining(payload["exp"])
            print(f"  Time Until Exp: {time_remaining}")

        # Current time
        current_time = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        print(f"  Current Time:   {current_time}")

        # Additional claims
        if args.verbose:
            additional_claims = {
                k: v
                for k, v in payload.items()
                if k not in ["user_id", "username", "role", "token_type", "iat", "exp"]
            }
            if additional_claims:
                print()
                print("Additional Claims:")
                for key, value in additional_claims.items():
                    if key == "exp" or key == "iat":
                        value = format_timestamp(value)
                    print(f"  {key}: {value}")

    print()
    print("=" * 60)

    if args.verbose and result["payload"]:
        print()
        print("Full Payload (JSON):")
        print(json.dumps(result["payload"], indent=2, default=str))
        print()

    # Exit code
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()

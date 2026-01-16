"""Browser tool security filters.

Sprint 59 Feature 59.5: Security validation for browser operations.

This module provides URL validation and security checks for browser tools
to prevent access to dangerous sites or local file system.
"""

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class BrowserSecurityCheckResult:
    """Result of browser security validation."""

    safe: bool
    reason: str | None = None


# Blocked URL patterns
URL_BLACKLIST_PATTERNS = [
    r"^file://",  # Local file system access
    r"^ftp://",  # FTP protocol
    r"localhost",  # Localhost access
    r"127\.0\.0\.",  # Loopback
    r"0\.0\.0\.0",  # Any interface
    r"192\.168\.",  # Private network (optional, can be configured)
    r"10\.\d+\.\d+\.\d+",  # Private network
    r"172\.(1[6-9]|2[0-9]|3[0-1])\.",  # Private network
]

# Blocked JavaScript patterns (for evaluate function)
DANGEROUS_JS_PATTERNS = [
    r"window\.location\s*=",  # Navigation
    r"document\.cookie",  # Cookie access
    r"localStorage",  # Local storage access
    r"sessionStorage",  # Session storage access
    r"fetch\s*\(",  # Network requests
    r"XMLHttpRequest",  # AJAX requests
    r"eval\s*\(",  # Eval
    r"Function\s*\(",  # Function constructor
    r"import\s*\(",  # Dynamic imports
    r"require\s*\(",  # CommonJS require
]


def is_url_safe(url: str, allow_private: bool = False) -> BrowserSecurityCheckResult:
    """Check if URL is safe to navigate to.

    Args:
        url: URL to validate
        allow_private: Whether to allow private network IPs (default: False)

    Returns:
        BrowserSecurityCheckResult with safe flag and reason if blocked

    Examples:
        >>> result = is_url_safe("https://example.com")
        >>> result.safe
        True

        >>> result = is_url_safe("file:///etc/passwd")
        >>> result.safe
        False
        >>> "file://" in result.reason
        True

        >>> result = is_url_safe("http://localhost:8000")
        >>> result.safe
        False
    """
    if not url or not isinstance(url, str):
        logger.warning("invalid_url_format", url=url)
        return BrowserSecurityCheckResult(safe=False, reason="Invalid URL format")

    url_lower = url.lower().strip()

    # Private network pattern indicators for filtering
    private_pattern_indicators = [
        r"192\.168\.",
        r"10\.\d+\.\d+\.\d+",
        r"172\.(1[6-9]|2[0-9]|3[0-1])\.",
        r"localhost",
        r"127\.0\.0\.",
    ]

    # Check blocked patterns
    for pattern in URL_BLACKLIST_PATTERNS:
        # Skip private network checks if allowed
        if allow_private and pattern in private_pattern_indicators:
            continue

        if re.search(pattern, url_lower):
            logger.warning("url_blocked_by_pattern", url=url, pattern=pattern)
            return BrowserSecurityCheckResult(
                safe=False,
                reason=f"URL blocked: matches forbidden pattern ({pattern})",
            )

    # Validate URL structure
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            logger.warning("invalid_url_scheme", url=url, scheme=parsed.scheme)
            return BrowserSecurityCheckResult(
                safe=False,
                reason=f"Invalid URL scheme: {parsed.scheme} (only http/https allowed)",
            )
    except Exception as e:
        logger.error("url_parse_error", url=url, error=str(e))
        return BrowserSecurityCheckResult(
            safe=False,
            reason=f"URL parsing failed: {str(e)}",
        )

    logger.debug("url_validated", url=url)
    return BrowserSecurityCheckResult(safe=True)


def is_javascript_safe(javascript: str) -> BrowserSecurityCheckResult:
    """Check if JavaScript code is safe to execute.

    Args:
        javascript: JavaScript code to validate

    Returns:
        BrowserSecurityCheckResult with safe flag and reason if blocked

    Examples:
        >>> result = is_javascript_safe("document.title")
        >>> result.safe
        True

        >>> result = is_javascript_safe("window.location = 'https://evil.com'")
        >>> result.safe
        False
        >>> "window.location" in result.reason
        True
    """
    if not javascript or not isinstance(javascript, str):
        logger.warning("invalid_javascript_format")
        return BrowserSecurityCheckResult(safe=False, reason="Invalid JavaScript format")

    # Check dangerous patterns
    for pattern in DANGEROUS_JS_PATTERNS:
        if re.search(pattern, javascript, re.IGNORECASE):
            logger.warning("javascript_blocked", pattern=pattern)
            return BrowserSecurityCheckResult(
                safe=False,
                reason=f"JavaScript blocked: contains forbidden pattern ({pattern})",
            )

    # Check for excessive length (potential DoS)
    if len(javascript) > 10000:
        logger.warning("javascript_too_long", length=len(javascript))
        return BrowserSecurityCheckResult(
            safe=False,
            reason=f"JavaScript too long: {len(javascript)} chars (max 10000)",
        )

    logger.debug("javascript_validated", length=len(javascript))
    return BrowserSecurityCheckResult(safe=True)


def validate_selector(selector: str) -> BrowserSecurityCheckResult:
    """Validate CSS selector for safety.

    Args:
        selector: CSS selector string

    Returns:
        BrowserSecurityCheckResult with safe flag and reason if blocked

    Examples:
        >>> result = validate_selector("button.submit")
        >>> result.safe
        True

        >>> result = validate_selector("")
        >>> result.safe
        False
    """
    if not selector or not isinstance(selector, str):
        logger.warning("invalid_selector_format")
        return BrowserSecurityCheckResult(safe=False, reason="Invalid selector format")

    # Basic validation
    selector_stripped = selector.strip()
    if not selector_stripped:
        return BrowserSecurityCheckResult(safe=False, reason="Empty selector")

    if len(selector_stripped) > 500:
        logger.warning("selector_too_long", length=len(selector_stripped))
        return BrowserSecurityCheckResult(
            safe=False,
            reason=f"Selector too long: {len(selector_stripped)} chars (max 500)",
        )

    logger.debug("selector_validated", selector=selector_stripped)
    return BrowserSecurityCheckResult(safe=True)

"""Unit tests for browser security validation.

Sprint 59 Feature 59.5: Browser tool security tests.
"""

import pytest

from src.domains.llm_integration.tools.builtin.browser_security import (
    BrowserSecurityCheckResult,
    is_javascript_safe,
    is_url_safe,
    validate_selector,
)


class TestURLSafety:
    """Test URL security validation."""

    def test_valid_https_url(self):
        """Test that valid HTTPS URLs are allowed."""
        result = is_url_safe("https://example.com")
        assert result.safe is True
        assert result.reason is None

    def test_valid_http_url(self):
        """Test that valid HTTP URLs are allowed."""
        result = is_url_safe("http://example.com/path?query=value")
        assert result.safe is True
        assert result.reason is None

    def test_file_protocol_blocked(self):
        """Test that file:// URLs are blocked."""
        result = is_url_safe("file:///etc/passwd")
        assert result.safe is False
        assert "file://" in result.reason.lower()

    def test_ftp_protocol_blocked(self):
        """Test that FTP URLs are blocked."""
        result = is_url_safe("ftp://example.com")
        assert result.safe is False
        assert "ftp://" in result.reason.lower()

    def test_localhost_blocked(self):
        """Test that localhost URLs are blocked by default."""
        result = is_url_safe("http://localhost:8000")
        assert result.safe is False
        assert "localhost" in result.reason.lower()

    def test_loopback_blocked(self):
        """Test that loopback IPs are blocked."""
        result = is_url_safe("http://127.0.0.1:8000")
        assert result.safe is False

    def test_private_network_blocked(self):
        """Test that private network IPs are blocked."""
        result = is_url_safe("http://192.168.1.1")
        assert result.safe is False

        result = is_url_safe("http://10.0.0.1")
        assert result.safe is False

        result = is_url_safe("http://172.16.0.1")
        assert result.safe is False

    def test_allow_private_networks(self):
        """Test that private networks can be allowed with flag."""
        result = is_url_safe("http://192.168.1.1", allow_private=True)
        assert result.safe is True

    def test_empty_url(self):
        """Test that empty URLs are rejected."""
        result = is_url_safe("")
        assert result.safe is False
        assert "invalid" in result.reason.lower()

    def test_invalid_url_type(self):
        """Test that non-string URLs are rejected."""
        result = is_url_safe(None)
        assert result.safe is False

        result = is_url_safe(123)
        assert result.safe is False

    def test_invalid_scheme(self):
        """Test that invalid schemes are rejected."""
        result = is_url_safe("javascript:alert('xss')")
        assert result.safe is False

        result = is_url_safe("data:text/html,<script>alert('xss')</script>")
        assert result.safe is False


class TestJavaScriptSafety:
    """Test JavaScript security validation."""

    def test_safe_javascript(self):
        """Test that safe JavaScript is allowed."""
        result = is_javascript_safe("document.title")
        assert result.safe is True

        result = is_javascript_safe("document.querySelector('h1').textContent")
        assert result.safe is True

        result = is_javascript_safe("Math.random()")
        assert result.safe is True

    def test_window_location_blocked(self):
        """Test that window.location assignments are blocked."""
        result = is_javascript_safe("window.location = 'https://evil.com'")
        assert result.safe is False
        assert "forbidden pattern" in result.reason.lower()

    def test_cookie_access_blocked(self):
        """Test that cookie access is blocked."""
        result = is_javascript_safe("document.cookie")
        assert result.safe is False
        assert "forbidden pattern" in result.reason.lower()

    def test_localstorage_blocked(self):
        """Test that localStorage access is blocked."""
        result = is_javascript_safe("localStorage.getItem('key')")
        assert result.safe is False
        assert "localstorage" in result.reason.lower()

    def test_sessionstorage_blocked(self):
        """Test that sessionStorage access is blocked."""
        result = is_javascript_safe("sessionStorage.setItem('key', 'value')")
        assert result.safe is False
        assert "sessionstorage" in result.reason.lower()

    def test_fetch_blocked(self):
        """Test that fetch() calls are blocked."""
        result = is_javascript_safe("fetch('https://api.example.com')")
        assert result.safe is False
        assert "fetch" in result.reason.lower()

    def test_xmlhttprequest_blocked(self):
        """Test that XMLHttpRequest is blocked."""
        result = is_javascript_safe("new XMLHttpRequest()")
        assert result.safe is False
        assert "xmlhttprequest" in result.reason.lower()

    def test_eval_blocked(self):
        """Test that eval() is blocked."""
        result = is_javascript_safe("eval('malicious code')")
        assert result.safe is False
        assert "eval" in result.reason.lower()

    def test_function_constructor_blocked(self):
        """Test that Function constructor is blocked."""
        result = is_javascript_safe("new Function('return 1')")
        assert result.safe is False
        assert "function" in result.reason.lower()

    def test_dynamic_import_blocked(self):
        """Test that dynamic imports are blocked."""
        result = is_javascript_safe("import('module')")
        assert result.safe is False
        assert "import" in result.reason.lower()

    def test_empty_javascript(self):
        """Test that empty JavaScript is rejected."""
        result = is_javascript_safe("")
        assert result.safe is False

    def test_too_long_javascript(self):
        """Test that very long JavaScript is rejected."""
        long_js = "x = 1;" * 5000  # > 10000 chars
        result = is_javascript_safe(long_js)
        assert result.safe is False
        assert "too long" in result.reason.lower()

    def test_invalid_javascript_type(self):
        """Test that non-string JavaScript is rejected."""
        result = is_javascript_safe(None)
        assert result.safe is False

        result = is_javascript_safe(123)
        assert result.safe is False


class TestSelectorValidation:
    """Test CSS selector validation."""

    def test_valid_selectors(self):
        """Test that valid CSS selectors are allowed."""
        result = validate_selector("button.submit")
        assert result.safe is True

        result = validate_selector("#main-content")
        assert result.safe is True

        result = validate_selector("div > p.highlight")
        assert result.safe is True

        result = validate_selector("[data-testid='login-button']")
        assert result.safe is True

    def test_empty_selector(self):
        """Test that empty selectors are rejected."""
        result = validate_selector("")
        assert result.safe is False
        assert "invalid" in result.reason.lower() or "empty" in result.reason.lower()

        result = validate_selector("   ")
        assert result.safe is False
        assert "empty" in result.reason.lower()

    def test_too_long_selector(self):
        """Test that very long selectors are rejected."""
        long_selector = "div " * 200  # > 500 chars
        result = validate_selector(long_selector)
        assert result.safe is False
        assert "too long" in result.reason.lower()

    def test_invalid_selector_type(self):
        """Test that non-string selectors are rejected."""
        result = validate_selector(None)
        assert result.safe is False

        result = validate_selector(123)
        assert result.safe is False


class TestSecurityCheckResult:
    """Test BrowserSecurityCheckResult dataclass."""

    def test_safe_result(self):
        """Test safe result creation."""
        result = BrowserSecurityCheckResult(safe=True)
        assert result.safe is True
        assert result.reason is None

    def test_unsafe_result_with_reason(self):
        """Test unsafe result with reason."""
        result = BrowserSecurityCheckResult(safe=False, reason="Blocked pattern")
        assert result.safe is False
        assert result.reason == "Blocked pattern"

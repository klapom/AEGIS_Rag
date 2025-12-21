"""Unit tests for Python Tool.

Sprint 59 Feature 59.4: Python execution with AST validation.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.domains.llm_integration.tools.builtin.python_tool import (
    python_execute,
    python_execute_batch,
)
from src.domains.llm_integration.tools.builtin.python_security import (
    validate_python_code,
    create_restricted_globals,
    get_code_complexity,
    get_allowed_modules,
)


# =============================================================================
# Security Validation Tests
# =============================================================================


class TestPythonSecurity:
    """Tests for Python code security validation."""

    def test_safe_code_allowed(self):
        """Test that safe code is allowed."""
        code = "x = 1 + 2\nprint(x)"
        result = validate_python_code(code)

        assert result.valid is True
        assert result.error is None

    def test_blocked_import_rejected(self):
        """Test that blocked imports are rejected."""
        code = "import os"
        result = validate_python_code(code)

        assert result.valid is False
        assert "os" in result.error

    def test_blocked_import_from_rejected(self):
        """Test that blocked import from is rejected."""
        code = "from subprocess import run"
        result = validate_python_code(code)

        assert result.valid is False
        assert "subprocess" in result.error

    def test_dangerous_builtin_rejected(self):
        """Test that dangerous builtins are rejected."""
        code = "eval('print(1)')"
        result = validate_python_code(code)

        assert result.valid is False
        assert "eval" in result.error.lower()

    def test_dangerous_attribute_rejected(self):
        """Test that dangerous attribute access is rejected."""
        code = "x = ().__class__.__bases__"
        result = validate_python_code(code)

        assert result.valid is False
        assert "__class__" in result.error or "__bases__" in result.error

    def test_syntax_error_rejected(self):
        """Test that syntax errors are rejected."""
        code = "x = 1 +"  # Incomplete expression
        result = validate_python_code(code)

        assert result.valid is False
        assert "Syntax error" in result.error

    def test_restricted_globals_safe(self):
        """Test that restricted globals only include safe items."""
        globals_dict = create_restricted_globals()

        # Should have safe builtins
        assert "print" in globals_dict["__builtins__"]
        assert "len" in globals_dict["__builtins__"]
        assert "range" in globals_dict["__builtins__"]

        # Should have safe modules
        assert "math" in globals_dict
        assert "json" in globals_dict
        assert "datetime" in globals_dict

        # Should NOT have dangerous items
        assert "os" not in globals_dict
        assert "subprocess" not in globals_dict
        assert "eval" not in globals_dict["__builtins__"]
        assert "exec" not in globals_dict["__builtins__"]

    def test_code_complexity_analysis(self):
        """Test code complexity analysis."""
        code = """
def foo():
    return 1

class Bar:
    pass

x = 1
y = 2
"""
        metrics = get_code_complexity(code)

        assert metrics["functions"] == 1
        assert metrics["classes"] == 1
        assert metrics["lines"] > 0
        assert metrics["nodes"] > 0

    def test_allowed_modules_list(self):
        """Test that allowed modules list is comprehensive."""
        allowed = get_allowed_modules()

        assert "math" in allowed
        assert "json" in allowed
        assert "datetime" in allowed
        assert "re" in allowed

        # Dangerous modules should NOT be in allowed list
        assert "os" not in allowed
        assert "subprocess" not in allowed


# =============================================================================
# Python Execution Tests
# =============================================================================


class TestPythonExecution:
    """Tests for Python code execution."""

    @pytest.mark.asyncio
    async def test_simple_code_success(self):
        """Test successful execution of simple code."""
        code = "print('hello world')"
        result = await python_execute(code)

        assert result["success"] is True
        assert "hello world" in result["output"]

    @pytest.mark.asyncio
    async def test_code_with_calculations(self):
        """Test code with calculations."""
        code = "result = 10 + 20\nprint(result)"
        result = await python_execute(code)

        assert result["success"] is True
        assert "30" in result["output"]

    @pytest.mark.asyncio
    async def test_code_with_variables(self):
        """Test code that creates variables."""
        code = "x = 42\ny = 'hello'"
        result = await python_execute(code)

        assert result["success"] is True
        assert "variables" in result
        assert result["variables"]["x"] == 42
        assert result["variables"]["y"] == "hello"

    @pytest.mark.asyncio
    async def test_code_with_math(self):
        """Test code using math module (already in globals)."""
        # math is pre-loaded in restricted_globals, no import needed
        code = "print(math.pi)"
        result = await python_execute(code)

        assert result["success"] is True
        assert "3.14" in result["output"]

    @pytest.mark.asyncio
    async def test_code_with_json(self):
        """Test code using json module (already in globals)."""
        # json is pre-loaded in restricted_globals, no import needed
        code = "data = {'key': 'value'}\nprint(json.dumps(data))"
        result = await python_execute(code)

        assert result["success"] is True
        assert "key" in result["output"]
        assert "value" in result["output"]

    @pytest.mark.asyncio
    async def test_blocked_code_rejected(self):
        """Test that blocked code is rejected before execution."""
        code = "import os\nos.system('ls')"
        result = await python_execute(code)

        assert result["success"] is False
        assert "error" in result
        assert "Blocked module" in result["error"]

    @pytest.mark.asyncio
    async def test_runtime_error_caught(self):
        """Test that runtime errors are caught."""
        code = "x = 1 / 0"  # Division by zero
        result = await python_execute(code)

        assert result["success"] is False
        assert "error" in result
        assert "ZeroDivisionError" in result["error"]

    @pytest.mark.asyncio
    async def test_code_timeout(self):
        """Test that long-running code times out."""
        code = "import time\ntime.sleep(10)"  # Would sleep for 10 seconds
        result = await python_execute(code, timeout=1)

        # Note: time module might be blocked, but if not, it should timeout
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_code_too_long_rejected(self):
        """Test that very long code is rejected."""
        # Generate code with > 1000 lines
        code = "\n".join([f"x{i} = {i}" for i in range(1001)])
        result = await python_execute(code)

        assert result["success"] is False
        assert "too long" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_timeout_clamping(self):
        """Test that timeout is clamped to maximum."""
        code = "print('test')"

        with patch("src.domains.llm_integration.tools.builtin.python_tool.logger") as mock_logger:
            result = await python_execute(code, timeout=1000)

            # Should log timeout clamping
            mock_logger.warning.assert_called()


# =============================================================================
# Batch Execution Tests
# =============================================================================


class TestPythonBatchExecution:
    """Tests for batch Python code execution."""

    @pytest.mark.asyncio
    async def test_batch_execution_independent(self):
        """Test batch execution with independent snippets."""
        snippets = [
            "x = 10\nprint(x)",
            "y = 20\nprint(y)",
            "z = 30\nprint(z)",
        ]

        results = await python_execute_batch(snippets, shared_globals=False)

        assert len(results) == 3
        assert all(r["success"] for r in results)
        assert "10" in results[0]["output"]
        assert "20" in results[1]["output"]
        assert "30" in results[2]["output"]

    @pytest.mark.asyncio
    async def test_batch_execution_shared_globals(self):
        """Test batch execution with shared globals."""
        snippets = [
            "x = 10",
            "y = x + 5",
            "print(y)",
        ]

        results = await python_execute_batch(snippets, shared_globals=True)

        assert len(results) == 3
        assert all(r["success"] for r in results)
        # Last snippet should print 15 (10 + 5)
        assert "15" in results[2]["output"]

    @pytest.mark.asyncio
    async def test_batch_stops_on_error(self):
        """Test that batch execution stops on error."""
        snippets = [
            "x = 10",
            "y = 1 / 0",  # Error
            "z = 30",  # Should not execute
        ]

        results = await python_execute_batch(snippets, stop_on_error=True)

        assert len(results) == 2  # Stopped after error
        assert results[0]["success"] is True
        assert results[1]["success"] is False

    @pytest.mark.asyncio
    async def test_batch_continues_on_error(self):
        """Test that batch execution continues on error."""
        snippets = [
            "x = 10",
            "y = 1 / 0",  # Error
            "z = 30\nprint(z)",  # Should still execute
        ]

        results = await python_execute_batch(snippets, stop_on_error=False)

        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert results[2]["success"] is True
        assert "30" in results[2]["output"]


# =============================================================================
# Edge Cases
# =============================================================================


class TestPythonEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_code(self):
        """Test execution of empty code."""
        code = ""
        result = await python_execute(code)

        # Empty code is syntactically valid
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_code_with_print_to_stderr(self):
        """Test code that prints to stderr."""
        code = "import sys\nprint('error', file=sys.stderr)"
        result = await python_execute(code)

        # sys is blocked, so this should fail validation
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_code_with_loops(self):
        """Test code with loops."""
        code = """
total = 0
for i in range(10):
    total += i
print(total)
"""
        result = await python_execute(code)

        assert result["success"] is True
        assert "45" in result["output"]  # Sum of 0-9

    @pytest.mark.asyncio
    async def test_code_with_functions(self):
        """Test code with function definitions."""
        code = """
def add(a, b):
    return a + b

result = add(5, 3)
print(result)
"""
        result = await python_execute(code)

        assert result["success"] is True
        assert "8" in result["output"]

    @pytest.mark.asyncio
    async def test_code_with_list_comprehension(self):
        """Test code with list comprehension."""
        code = "result = [x*2 for x in range(5)]\nprint(result)"
        result = await python_execute(code)

        assert result["success"] is True
        assert "[0, 2, 4, 6, 8]" in result["output"]

    @pytest.mark.asyncio
    async def test_code_with_exception_handling(self):
        """Test code with try/except."""
        code = """
try:
    x = 1 / 0
except ZeroDivisionError:
    print('caught error')
"""
        result = await python_execute(code)

        assert result["success"] is True
        assert "caught error" in result["output"]

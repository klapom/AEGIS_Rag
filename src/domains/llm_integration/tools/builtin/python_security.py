"""Python code security validation.

Sprint 59 Feature 59.4: AST-based security validation for Python code execution.

This module provides AST analysis to detect and block dangerous Python code
patterns before execution.
"""

import ast
from dataclasses import dataclass
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of Python code validation."""

    valid: bool
    error: str | None = None


# Modules that should never be imported
BLOCKED_MODULES = [
    "os",
    "subprocess",
    "sys",
    "shutil",
    "socket",
    "ctypes",
    "multiprocessing",
    "__builtins__",
    "importlib",
    "imp",
    "code",
    "codeop",
    "compile",
    "eval",
    "exec",
    "open",
    "file",
    "input",
    "raw_input",
    "globals",
    "locals",
    "vars",
    "__import__",
]

# Dangerous builtin functions
DANGEROUS_BUILTINS = [
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",
    "file",
    "input",
    "raw_input",
    "globals",
    "locals",
    "vars",
    "dir",
    "getattr",
    "setattr",
    "delattr",
    "hasattr",
]

# Dangerous attribute access patterns
DANGEROUS_ATTRIBUTES = [
    "__class__",
    "__bases__",
    "__subclasses__",
    "__globals__",
    "__code__",
    "__closure__",
    "__func__",
    "__self__",
    "__dict__",
    "__import__",
]


def validate_python_code(code: str) -> ValidationResult:
    """Validate Python code for security issues.

    Args:
        code: Python code to validate

    Returns:
        ValidationResult with valid flag and error message if invalid

    Examples:
        >>> result = validate_python_code("print('hello')")
        >>> result.valid
        True

        >>> result = validate_python_code("import os")
        >>> result.valid
        False
        >>> "os" in result.error
        True
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        logger.warning("syntax_error", error=str(e))
        return ValidationResult(False, f"Syntax error: {e}")

    # Walk AST and check for dangerous patterns
    for node in ast.walk(tree):
        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in BLOCKED_MODULES:
                    logger.warning("blocked_import", module=alias.name)
                    return ValidationResult(False, f"Blocked module: {alias.name}")

        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module in BLOCKED_MODULES:
                logger.warning("blocked_import_from", module=node.module)
                return ValidationResult(False, f"Blocked module: {node.module}")

        # Check function calls
        elif isinstance(node, ast.Call):
            # Check for dangerous builtins
            if isinstance(node.func, ast.Name):
                if node.func.id in DANGEROUS_BUILTINS:
                    logger.warning("dangerous_builtin", function=node.func.id)
                    return ValidationResult(
                        False, f"Dangerous builtin function: {node.func.id}"
                    )

        # Check attribute access
        elif isinstance(node, ast.Attribute):
            if node.attr in DANGEROUS_ATTRIBUTES:
                logger.warning("dangerous_attribute", attribute=node.attr)
                return ValidationResult(
                    False, f"Dangerous attribute access: {node.attr}"
                )

        # Check for exec/eval as names
        elif isinstance(node, ast.Name):
            if node.id in ["exec", "eval", "__import__"]:
                logger.warning("dangerous_name", name=node.id)
                return ValidationResult(False, f"Dangerous builtin: {node.id}")

    logger.info("code_validation_passed", code_length=len(code))
    return ValidationResult(True, None)


def create_restricted_globals() -> dict[str, Any]:
    """Create restricted globals for code execution.

    Returns:
        Dict of allowed global objects and modules

    Examples:
        >>> globals_dict = create_restricted_globals()
        >>> "print" in globals_dict["__builtins__"]
        True
        >>> "os" in globals_dict
        False
    """
    import math
    import json
    import datetime
    import re
    from collections import defaultdict, Counter
    from itertools import islice, chain
    from functools import reduce

    # Safe builtins
    safe_builtins = {
        "print": print,
        "len": len,
        "range": range,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "frozenset": frozenset,
        "bytes": bytes,
        "bytearray": bytearray,
        "sum": sum,
        "min": min,
        "max": max,
        "abs": abs,
        "round": round,
        "sorted": sorted,
        "reversed": reversed,
        "enumerate": enumerate,
        "zip": zip,
        "map": map,
        "filter": filter,
        "all": all,
        "any": any,
        "chr": chr,
        "ord": ord,
        "hex": hex,
        "bin": bin,
        "oct": oct,
        "pow": pow,
        "divmod": divmod,
        "isinstance": isinstance,
        "issubclass": issubclass,
        "type": type,
        "callable": callable,
        "format": format,
        "slice": slice,
        # Exceptions
        "Exception": Exception,
        "ValueError": ValueError,
        "TypeError": TypeError,
        "KeyError": KeyError,
        "IndexError": IndexError,
        "AttributeError": AttributeError,
        "RuntimeError": RuntimeError,
        "ZeroDivisionError": ZeroDivisionError,
    }

    return {
        "__builtins__": safe_builtins,
        "math": math,
        "json": json,
        "datetime": datetime,
        "re": re,
        "defaultdict": defaultdict,
        "Counter": Counter,
        "islice": islice,
        "chain": chain,
        "reduce": reduce,
    }


def get_code_complexity(code: str) -> dict[str, int]:
    """Analyze code complexity metrics.

    Args:
        code: Python code to analyze

    Returns:
        Dict with complexity metrics

    Examples:
        >>> metrics = get_code_complexity("x = 1\\ny = 2")
        >>> metrics["lines"]
        2
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"lines": 0, "nodes": 0, "functions": 0, "classes": 0}

    lines = len(code.splitlines())
    nodes = len(list(ast.walk(tree)))
    functions = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
    classes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))

    return {
        "lines": lines,
        "nodes": nodes,
        "functions": functions,
        "classes": classes,
    }


def get_allowed_modules() -> list[str]:
    """Get list of explicitly allowed safe modules.

    Returns:
        List of module names that are considered safe
    """
    return [
        "math",
        "json",
        "datetime",
        "re",
        "collections",
        "itertools",
        "functools",
        "string",
        "random",
        "statistics",
        "decimal",
        "fractions",
        "uuid",
        "hashlib",
        "base64",
    ]

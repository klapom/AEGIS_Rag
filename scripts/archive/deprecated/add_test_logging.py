"""Script to add comprehensive logging to E2E test files for better debugging."""

import re
from pathlib import Path


def add_logging_to_test_file(file_path: Path) -> None:
    """Add comprehensive logging statements to a test file."""
    print(f"Processing {file_path.name}...")

    content = file_path.read_text(encoding="utf-8")

    # Already has logging import and logger setup - skip if present
    if "logger = logging.getLogger(__name__)" in content:
        print(f"  ✓ {file_path.name} already has logging configured")
        return

    # Add logging import after other imports (after pytest imports)
    if "import logging" not in content:
        content = content.replace("import pytest", "import logging\nimport pytest")
        print(f"  + Added logging import to {file_path.name}")

    # Add logger setup after imports, before first test
    if "logger = logging.getLogger(__name__)" not in content:
        # Find first @pytest.mark
        first_test_match = re.search(r"(@pytest\.mark)", content)
        if first_test_match:
            insert_pos = first_test_match.start()
            logger_setup = """
# Setup detailed logging for E2E tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)


"""
            content = content[:insert_pos] + logger_setup + content[insert_pos:]
            print(f"  + Added logger setup to {file_path.name}")

    # Write back
    file_path.write_text(content, encoding="utf-8")
    print(f"  ✓ Completed {file_path.name}")


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    test_integration_dir = project_root / "tests" / "integration"

    # Process E2E test files
    e2e_test_files = [
        test_integration_dir / "test_memory_e2e.py",
        test_integration_dir / "test_mcp_e2e.py",
    ]

    print("Adding comprehensive logging to E2E test files...")
    print("=" * 60)

    for test_file in e2e_test_files:
        if test_file.exists():
            try:
                add_logging_to_test_file(test_file)
            except Exception as e:
                print(f"  ✗ Error processing {test_file.name}: {e}")
        else:
            print(f"  ✗ File not found: {test_file.name}")

    print("=" * 60)
    print("✓ Logging configuration complete!")
    print("\nNow run tests with:")
    print("  poetry run pytest tests/integration/test_memory_e2e.py -v -s")
    print("  poetry run pytest tests/integration/test_mcp_e2e.py -v -s")

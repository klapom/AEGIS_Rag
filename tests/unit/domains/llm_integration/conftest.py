"""Pytest configuration and fixtures for LLM integration domain tests."""

import sqlite3
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domains.llm_integration.config import LLMProxyConfig
from src.domains.llm_integration.cost.cost_tracker import CostTracker


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    """Create temporary SQLite database for cost tracker tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def cost_tracker(temp_db_path: Path) -> CostTracker:
    """Create CostTracker with temporary database."""
    return CostTracker(db_path=temp_db_path)


@pytest.fixture
def mock_llm_config() -> LLMProxyConfig:
    """Create mock LLMProxyConfig for testing."""
    config_data = {
        "providers": {
            "local_ollama": {
                "enabled": True,
                "base_url": "http://localhost:11434",
            },
            "alibaba_cloud": {
                "enabled": True,
                "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
                "api_key": "test-key-alibaba",
            },
            "openai": {
                "enabled": True,
                "base_url": "https://api.openai.com/v1",
                "api_key": "test-key-openai",
            },
        },
        "budgets": {
            "monthly_limits": {
                "alibaba_cloud": 10.0,
                "openai": 20.0,
            }
        },
        "routing": {
            "default": "local_ollama",
            "prefer_cloud": False,
        },
        "model_defaults": {
            "local_ollama": {
                "extraction": "gemma-3-4b-it-Q8_0",
                "generation": "llama3.2:8b",
                "embedding": "bge-m3",
            },
            "alibaba_cloud": {
                "extraction": "qwen-turbo",
                "generation": "qwen-plus",
                "vision": "qwen3-vl-30b-a3b-instruct",
            },
            "openai": {
                "extraction": "gpt-4o-mini",
                "generation": "gpt-4o",
            },
        },
        "fallback": {
            "enabled": True,
            "order": ["local_ollama", "alibaba_cloud", "openai"],
        },
        "monitoring": {
            "prometheus_enabled": False,
            "langsmith_enabled": False,
        },
    }
    return LLMProxyConfig(**config_data)


@pytest.fixture
def mock_httpx_response() -> MagicMock:
    """Create mock httpx response for VLM API calls."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Image description: A person working at a desk with a computer."
                },
                "finish_reason": "stop",
            }
        ],
        "model": "qwen3-vl-30b-a3b-instruct",
        "usage": {
            "prompt_tokens": 1500,
            "completion_tokens": 50,
            "total_tokens": 1550,
        },
    }
    return response


@pytest.fixture
def sample_image_path(tmp_path: Path) -> Path:
    """Create a sample test image."""
    image_path = tmp_path / "test_image.png"
    # Create a minimal valid PNG file (1x1 pixel)
    # PNG magic number + minimal IHDR chunk
    png_data = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 pixel
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
        0x54, 0x08, 0x99, 0x01, 0x01, 0x00, 0x00, 0xFE,
        0xFF, 0x00, 0x00, 0x00, 0x02, 0x00, 0x01, 0xE5,
        0x27, 0xDE, 0xFC, 0x00, 0x00, 0x00, 0x00, 0x49,  # IEND chunk
        0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
    ])
    image_path.write_bytes(png_data)
    return image_path

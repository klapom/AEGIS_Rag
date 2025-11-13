"""
Configuration management for LLM proxy.

Sprint Context: Sprint 23 (2025-11-11+) - Feature 23.4
Related ADR: ADR-033 (Mozilla ANY-LLM Integration)

This module handles loading and validation of LLM proxy configuration
from YAML files and environment variables.
"""

import os
import re
from pathlib import Path
from typing import Any

import structlog
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

# Load environment variables from .env file
load_dotenv()


class LLMProxyConfig(BaseModel):
    """
    Configuration for AegisLLMProxy.

    This model validates the configuration loaded from llm_config.yml
    and environment variables.
    """

    providers: dict[str, dict[str, Any]] = Field(
        ...,
        description="Provider configuration (local_ollama, ollama_cloud, openai)",
    )
    budgets: dict[str, Any] = Field(..., description="Budget limits and thresholds")
    routing: dict[str, Any] = Field(..., description="Routing configuration")
    model_defaults: dict[str, dict[str, str]] = Field(
        ..., description="Default models per provider"
    )
    fallback: dict[str, Any] = Field(..., description="Fallback configuration")
    monitoring: dict[str, bool] = Field(..., description="Monitoring flags")

    @classmethod
    def from_env(cls, config_path: Path | None = None) -> "LLMProxyConfig":
        """
        Load configuration from YAML file with environment variable interpolation.

        Args:
            config_path: Path to llm_config.yml (defaults to config/llm_config.yml)

        Returns:
            LLMProxyConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        # Default config path
        if config_path is None:
            repo_root = Path(__file__).parent.parent.parent.parent
            config_path = repo_root / "config" / "llm_config.yml"

        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                f"Please create config/llm_config.yml"
            )

        # Load YAML
        with open(config_path, encoding="utf-8") as f:
            config_str = f.read()

        # Interpolate environment variables
        config_str = cls._interpolate_env_vars(config_str)

        # Parse YAML
        config_data = yaml.safe_load(config_str)

        # Validate required providers
        required_providers = ["local_ollama"]
        for provider in required_providers:
            if provider not in config_data.get("providers", {}):
                raise ValueError(
                    f"Required provider '{provider}' not found in configuration"
                )

        logger.info(
            "llm_config_loaded",
            config_path=str(config_path),
            providers=list(config_data.get("providers", {}).keys()),
        )

        return cls(**config_data)

    @staticmethod
    def _interpolate_env_vars(config_str: str) -> str:
        """
        Interpolate environment variables in config string.

        Supports two patterns:
        - ${VAR}: Required variable (raises error if not set)
        - ${VAR:-default}: Optional with default value

        Args:
            config_str: YAML config as string

        Returns:
            Config string with interpolated values

        Raises:
            ValueError: If required variable is not set
        """

        def replace_env_var(match: re.Match) -> str:
            """Replace single environment variable."""
            var_expr = match.group(1)

            # Check for default value syntax: VAR:-default
            if ":-" in var_expr:
                var_name, default = var_expr.split(":-", 1)
                return os.environ.get(var_name, default)
            else:
                var_name = var_expr
                if var_name not in os.environ:
                    raise ValueError(
                        f"Required environment variable not set: {var_name}\n"
                        f"Please set {var_name} in .env or environment"
                    )
                return os.environ[var_name]

        # Pattern: ${VAR} or ${VAR:-default}
        pattern = r"\$\{([^}]+)\}"
        return re.sub(pattern, replace_env_var, config_str)

    def get_provider_config(self, provider: str) -> dict[str, Any]:
        """
        Get configuration for specific provider.

        Args:
            provider: Provider name (local_ollama, ollama_cloud, openai)

        Returns:
            Provider configuration dict

        Raises:
            ValueError: If provider not configured
        """
        if provider not in self.providers:
            raise ValueError(
                f"Provider '{provider}' not configured. "
                f"Available: {list(self.providers.keys())}"
            )
        return self.providers[provider]

    def get_budget_limit(self, provider: str) -> float:
        """
        Get monthly budget limit for provider.

        Args:
            provider: Provider name

        Returns:
            Budget limit in USD (0.0 for local)
        """
        if provider == "local_ollama":
            return 0.0  # Local is free
        return self.budgets.get("monthly_limits", {}).get(provider, 0.0)

    def get_default_model(self, provider: str, task_type: str) -> str | None:
        """
        Get default model for provider and task type.

        Args:
            provider: Provider name
            task_type: Task type (extraction, generation, etc.)

        Returns:
            Model name or None if not configured
        """
        return self.model_defaults.get(provider, {}).get(task_type)

    def is_provider_enabled(self, provider: str) -> bool:
        """
        Check if provider is enabled (has required config).

        Args:
            provider: Provider name

        Returns:
            True if provider is properly configured
        """
        if provider not in self.providers:
            return False

        provider_config = self.providers[provider]

        # Check required fields based on provider
        if provider == "local_ollama":
            return "base_url" in provider_config

        elif provider in ["alibaba_cloud", "ollama_cloud"]:
            # Require non-empty api_key
            api_key = provider_config.get("api_key", "")
            return "base_url" in provider_config and api_key and api_key.strip()

        elif provider == "openai":
            # Require non-empty api_key
            api_key = provider_config.get("api_key", "")
            return api_key and api_key.strip()

        return False

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


# Convenience function for getting singleton config
_config_instance: LLMProxyConfig | None = None


def get_llm_proxy_config() -> LLMProxyConfig:
    """
    Get singleton LLMProxyConfig instance.

    This function caches the configuration to avoid reloading
    the YAML file on every call.

    Returns:
        LLMProxyConfig instance

    Example:
        from src.components.llm_proxy.config import get_llm_proxy_config

        config = get_llm_proxy_config()
        local_config = config.get_provider_config("local_ollama")
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = LLMProxyConfig.from_env()
    return _config_instance

"""
Models for prompt caching.

Sprint 63 Feature 63.3: Redis Prompt Caching
"""

from pydantic import BaseModel, Field


class CacheStats(BaseModel):
    """
    Cache statistics for monitoring and observability.

    Tracks cache performance metrics for insight into cache effectiveness
    and LLM cost reduction.

    Attributes:
        hits: Total number of cache hits
        misses: Total number of cache misses
        hit_rate: Percentage of hits (0.0 to 1.0)
        total_requests: Total cache lookup requests
        cached_size_bytes: Approximate total size of cached data in bytes
    """

    hits: int = Field(default=0, description="Total cache hits")
    misses: int = Field(default=0, description="Total cache misses")
    hit_rate: float = Field(default=0.0, description="Cache hit rate (0.0-1.0)")
    total_requests: int = Field(default=0, description="Total requests")
    cached_size_bytes: int = Field(default=0, description="Total cached size in bytes")

    class Config:
        """Pydantic config."""

        frozen = False


class CacheKey(BaseModel):
    """
    Cache key components for deterministic key generation.

    Attributes:
        namespace: Tenant/namespace for isolation
        model: LLM model name
        prompt: Full prompt text
    """

    namespace: str = Field(..., description="Tenant namespace")
    model: str = Field(..., description="LLM model name")
    prompt: str = Field(..., description="Full prompt text")

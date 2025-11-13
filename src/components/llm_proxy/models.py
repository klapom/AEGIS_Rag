"""
Pydantic models for LLM proxy component.

Sprint Context: Sprint 23 (2025-11-11+) - Feature 23.4
Related ADR: ADR-033 (Mozilla ANY-LLM Integration)

This module defines the data models for LLM tasks and responses,
including task types, quality requirements, and execution locations.
"""

from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """
    LLM task types.

    These categorize the nature of the work to be performed,
    which influences routing decisions.
    """

    EMBEDDING = "embedding"  # Always local (BGE-M3)
    EXTRACTION = "extraction"  # Entity/relation extraction
    GENERATION = "generation"  # Text generation (queries, responses)
    CODE_GENERATION = "code_generation"  # Technical docs, API specs
    RESEARCH = "research"  # Multi-hop reasoning, complex queries
    VISION = "vision"  # Image description/analysis with VLM (prefer Alibaba Cloud Qwen3-VL)


class DataClassification(str, Enum):
    """
    Data sensitivity classification for GDPR/HIPAA compliance.

    CRITICAL: Determines routing based on legal requirements.
    Sensitive data (PII, HIPAA, Confidential) NEVER leaves local.
    """

    PUBLIC = "public"  # No restrictions
    INTERNAL = "internal"  # Company internal, non-sensitive
    CONFIDENTIAL = "confidential"  # Business secrets → local only
    PII = "pii"  # Personal Identifiable Information → local only (GDPR)
    HIPAA = "hipaa"  # Protected Health Information → local only (HIPAA)


class QualityRequirement(str, Enum):
    """
    Quality requirement for task.

    Influences provider selection:
    - LOW: Local OK (75% accuracy)
    - MEDIUM: Local or Ollama Cloud (75-85%)
    - HIGH: Ollama Cloud preferred (85%)
    - CRITICAL: OpenAI required (95%)
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Complexity(str, Enum):
    """
    Task complexity level.

    Combined with quality requirement to determine optimal provider.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class ExecutionLocation(str, Enum):
    """
    Execution location for LLM tasks.

    Three-tier strategy (ADR-033):
    - LOCAL: Ollama on localhost (free)
    - OLLAMA_CLOUD: Ollama Cloud API ($0.001/1k tokens)
    - OPENAI: OpenAI API ($0.015/1k tokens)
    """

    LOCAL = "local_ollama"
    OLLAMA_CLOUD = "ollama_cloud"
    OPENAI = "openai"


class LLMTask(BaseModel):
    """
    LLM task definition for AegisLLMProxy.

    This model encapsulates all information needed for intelligent routing:
    task type, data classification, quality requirements, and generation params.

    Example:
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract entities from legal contract...",
            data_classification=DataClassification.CONFIDENTIAL,  # → local only
            quality_requirement=QualityRequirement.CRITICAL,
            complexity=Complexity.HIGH,
        )
        response = await proxy.generate(task)
    """

    # Task identification
    id: UUID = Field(default_factory=uuid4, description="Unique task ID")
    task_type: TaskType = Field(..., description="Type of LLM task")
    prompt: str = Field(..., min_length=1, description="Prompt text")

    # Routing criteria
    data_classification: DataClassification = Field(
        default=DataClassification.PUBLIC,
        description="Data sensitivity (determines routing for compliance)",
    )
    quality_requirement: QualityRequirement = Field(
        default=QualityRequirement.MEDIUM,
        description="Required quality level (influences provider selection)",
    )
    complexity: Complexity = Field(
        default=Complexity.MEDIUM,
        description="Task complexity (influences provider selection)",
    )

    # Model preferences (optional, provider-specific)
    model_local: Optional[str] = Field(
        default=None,
        description="Preferred local model (default: gemma-3-4b-it-Q8_0)",
    )
    model_cloud: Optional[str] = Field(
        default=None,
        description="Preferred Ollama Cloud model (default: llama3-70b)",
    )
    model_openai: Optional[str] = Field(
        default=None,
        description="Preferred OpenAI model (default: gpt-4o)",
    )

    # Generation parameters
    max_tokens: int = Field(
        default=1024,
        ge=1,
        le=32000,
        description="Maximum tokens to generate",
    )
    temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0=deterministic, 2=creative)",
    )

    # Batch processing
    batch_size: Optional[int] = Field(
        default=None,
        ge=1,
        description="Number of items in batch (for parallel processing)",
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True  # Serialize enums as strings
        json_schema_extra = {
            "example": {
                "task_type": "extraction",
                "prompt": "Extract entities from: John Smith works at Acme Corp.",
                "data_classification": "public",
                "quality_requirement": "medium",
                "complexity": "medium",
                "max_tokens": 1024,
                "temperature": 0.1,
            }
        }


class LLMResponse(BaseModel):
    """
    LLM response with execution metadata.

    This model contains the generated content plus metadata about
    which provider was used, costs, latency, etc.

    Example:
        response = LLMResponse(
            content="John Smith (Person) works at Acme Corp (Organization).",
            provider="local_ollama",
            model="gemma-3-4b-it-Q8_0",
            tokens_used=45,
            cost_usd=0.0,
            latency_ms=120,
        )
    """

    # Generated content
    content: str = Field(..., description="Generated text content")

    # Execution metadata
    provider: str = Field(..., description="Provider used (local/ollama_cloud/openai)")
    model: str = Field(..., description="Model name")
    tokens_used: int = Field(..., ge=0, description="Total tokens used (input + output)")

    # Cost & performance
    cost_usd: float = Field(..., ge=0.0, description="Cost in USD")
    latency_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Request latency in milliseconds",
    )

    # Optional: Structured metadata
    routing_reason: Optional[str] = Field(
        default=None,
        description="Reason for provider selection (for debugging)",
    )
    fallback_used: bool = Field(
        default=False,
        description="Whether fallback provider was used",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "content": "John Smith (Person) works at Acme Corp (Organization).",
                "provider": "local_ollama",
                "model": "gemma-3-4b-it-Q8_0",
                "tokens_used": 45,
                "cost_usd": 0.0,
                "latency_ms": 120.5,
                "routing_reason": "default_local",
                "fallback_used": False,
            }
        }

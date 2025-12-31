"""C-LARA Intent Classifier Data Generation.

Sprint 67 Feature 67.10: Generate synthetic labeled intent classification examples
using Qwen2.5:7b via Ollama for training a SetFit model.

Architecture:
    Qwen2.5:7b (Teacher) → Synthetic Examples → SetFit Training → Production Model

Intent Classes (from src/components/retrieval/intent_classifier.py):
    - factual: Specific fact lookups (Who, What, When, Where with a specific answer)
    - procedural: Step-by-step instructions (How-to guides)
    - comparison: Compare multiple entities (A vs B)
    - recommendation: Best practices, suggestions (What should I...)
    - navigation: Find location/category (Where to find X)

Quality Targets (TD-079):
    - 1000 labeled examples (200 per intent class)
    - Balanced distribution across 5 intent classes
    - Bilingual: 50% German, 50% English
    - Domain coverage: Software docs, business queries, research questions
    - Confidence >0.8 for 90% of examples

Output Format:
    JSONL with one example per line:
    {"query": "...", "intent": "factual", "confidence": 0.95, "language": "en"}

References:
    - TD-079: LLM Intent Classifier (C-LARA)
    - C-LARA Framework: https://www.amazon.science/publications/intent-detection-in-the-age-of-llms
"""

import asyncio
import json
import random
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class IntentExample:
    """Labeled intent classification example.

    Attributes:
        query: User query text
        intent: Intent label (factual, procedural, comparison, recommendation, navigation)
        confidence: LLM confidence in intent label (0.0-1.0)
        language: Language code ("en" or "de")
        domain: Domain category (software, business, research)
    """

    query: str
    intent: str
    confidence: float
    language: str
    domain: str = "general"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSONL serialization."""
        return asdict(self)


class CLARADataGenerator:
    """Generate intent classification training data using LLM.

    Sprint 67 Feature 67.10: Use Qwen2.5:7b to generate diverse, high-quality
    labeled examples for training a SetFit intent classifier.

    Features:
        - Few-shot prompting with task-specific examples
        - Bilingual generation (German/English)
        - Domain-specific variations (software, business, research)
        - Quality validation (confidence thresholds)
        - Balanced class distribution

    Example:
        generator = CLARADataGenerator(
            model="qwen2.5:7b",
            target_examples=1000
        )
        examples = await generator.generate_examples()
        await generator.save_dataset(examples, "data/intent_training_v1.jsonl")
    """

    # Intent class definitions with descriptions
    INTENT_DEFINITIONS = {
        "factual": (
            "Specific fact lookup question asking who, what, when, where "
            "with a concrete specific answer. Definition or meaning of a single term. "
            "Exact values, dates, names, locations, specific settings, single entity facts."
        ),
        "procedural": (
            "Step-by-step instructions or how-to guides. Questions asking how to do something, "
            "configure a system, troubleshoot an issue, or perform a specific task. "
            "Process explanations, tutorials, walkthroughs, installation guides."
        ),
        "comparison": (
            "Compare multiple entities, options, or approaches. Questions asking about "
            "differences, similarities, pros/cons, advantages/disadvantages, tradeoffs. "
            "A vs B questions, which is better, feature comparisons, alternative analysis."
        ),
        "recommendation": (
            "Best practices, suggestions, or recommendations. Questions asking what should I do, "
            "which option to choose, what is recommended, best approach, optimal solution. "
            "Advice-seeking, decision support, guidance requests."
        ),
        "navigation": (
            "Find location, category, or navigate to specific information. Questions asking "
            "where to find something, which section contains information, how to access a feature. "
            "Information location, menu navigation, search for category."
        ),
    }

    # Few-shot examples for each intent (German/English mix)
    FEW_SHOT_EXAMPLES = {
        "factual": [
            "What is the capital of France?",
            "Who is the CEO of OMNITRACKER?",
            "When was Python 3.12 released?",
            "Was ist die Definition von RAG?",
            "Welcher Port wird für PostgreSQL verwendet?",
        ],
        "procedural": [
            "How do I install Docker on Ubuntu?",
            "How to configure SSL certificates in Nginx?",
            "Wie erstelle ich ein neues Projekt in OMNITRACKER?",
            "Wie exportiere ich Daten als CSV?",
            "Steps to reset a user password",
        ],
        "comparison": [
            "What is the difference between REST and GraphQL?",
            "Compare Postgres vs MySQL for large datasets",
            "Unterschied zwischen Vector Search und BM25?",
            "Vor- und Nachteile von Docker vs Podman?",
            "Which is better: Redis or Memcached?",
        ],
        "recommendation": [
            "What is the best way to secure API endpoints?",
            "Which database should I use for time-series data?",
            "Welche Strategie empfehlen Sie für Backup?",
            "Was ist der beste Ansatz für Skalierung?",
            "Recommended settings for production deployment",
        ],
        "navigation": [
            "Where can I find the API documentation?",
            "How do I access the admin dashboard?",
            "Wo finde ich die Logs für den Service?",
            "Welches Menü enthält die Benutzereinstellungen?",
            "Where to download the installation guide?",
        ],
    }

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
        target_examples: int = 1000,
        examples_per_batch: int = 10,
        timeout: float = 60.0,
    ):
        """Initialize C-LARA data generator.

        Args:
            model: Ollama model to use (default: qwen2.5:7b)
            base_url: Ollama API base URL
            target_examples: Total number of examples to generate
            examples_per_batch: Examples to generate per LLM call
            timeout: Request timeout in seconds
        """
        self.model = model
        self.base_url = base_url
        self.target_examples = target_examples
        self.examples_per_batch = examples_per_batch
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

        # Track generation statistics
        self.stats = defaultdict(int)

        logger.info(
            "clara_data_generator_initialized",
            model=model,
            target_examples=target_examples,
            examples_per_batch=examples_per_batch,
        )

    def _build_generation_prompt(
        self, intent: str, language: str, domain: str, num_examples: int
    ) -> str:
        """Build few-shot prompt for generating intent examples.

        Args:
            intent: Intent class to generate
            language: Language code ("en" or "de")
            domain: Domain category (software, business, research)
            num_examples: Number of examples to generate

        Returns:
            Formatted prompt for LLM
        """
        intent_desc = self.INTENT_DEFINITIONS[intent]
        few_shot = self.FEW_SHOT_EXAMPLES[intent][:3]  # Use 3 examples per intent

        lang_instruction = (
            "Generiere die Queries auf Deutsch."
            if language == "de"
            else "Generate queries in English."
        )

        domain_instruction = {
            "software": "Focus on software development, IT infrastructure, and technical documentation.",
            "business": "Focus on business processes, project management, and enterprise systems.",
            "research": "Focus on academic research, scientific analysis, and knowledge discovery.",
        }.get(domain, "Focus on general knowledge and information retrieval.")

        prompt = f"""You are an expert at generating diverse query examples for intent classification.

Intent Class: {intent}
Description: {intent_desc}

Task: Generate {num_examples} diverse queries that clearly belong to this intent class.

Guidelines:
- {lang_instruction}
- {domain_instruction}
- Vary query length (5-20 words)
- Include technical terms and domain-specific vocabulary
- Ensure queries are realistic and natural
- Each query should have a clear, unambiguous intent

Few-shot Examples:
{chr(10).join(f"- {ex}" for ex in few_shot)}

Output Format (JSON array):
[
  {{"query": "...", "confidence": 0.95}},
  {{"query": "...", "confidence": 0.92}},
  ...
]

Generate exactly {num_examples} queries now:
"""
        return prompt

    async def _generate_batch(
        self, intent: str, language: str, domain: str, num_examples: int
    ) -> list[IntentExample]:
        """Generate a batch of examples using LLM.

        Args:
            intent: Intent class to generate
            language: Language code ("en" or "de")
            domain: Domain category
            num_examples: Number of examples to generate

        Returns:
            List of generated intent examples

        Raises:
            ValueError: If LLM response parsing fails
        """
        start_time = time.perf_counter()

        prompt = self._build_generation_prompt(intent, language, domain, num_examples)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",  # Request JSON output
            "options": {
                "temperature": 0.8,  # Higher temperature for diversity
                "num_predict": 2000,  # Allow longer responses
            },
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            raw_response = data.get("response", "").strip()

            # Parse JSON response
            try:
                generated = json.loads(raw_response)
                if not isinstance(generated, list):
                    logger.error(
                        "llm_response_not_list",
                        intent=intent,
                        language=language,
                        response_type=type(generated).__name__,
                    )
                    return []
            except json.JSONDecodeError as e:
                logger.error(
                    "llm_response_json_parse_error",
                    intent=intent,
                    language=language,
                    error=str(e),
                    raw_response=raw_response[:200],
                )
                return []

            # Convert to IntentExample objects
            examples = []
            for item in generated:
                if not isinstance(item, dict) or "query" not in item:
                    continue

                query = item["query"].strip()
                confidence = item.get("confidence", 0.85)

                # Basic quality checks
                if len(query) < 10 or len(query) > 300:
                    continue  # Skip too short or too long queries

                examples.append(
                    IntentExample(
                        query=query,
                        intent=intent,
                        confidence=confidence,
                        language=language,
                        domain=domain,
                    )
                )

            latency_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "batch_generated",
                intent=intent,
                language=language,
                domain=domain,
                requested=num_examples,
                generated=len(examples),
                latency_ms=round(latency_ms, 2),
            )

            self.stats["total_batches"] += 1
            self.stats[f"examples_{intent}"] += len(examples)

            return examples

        except Exception as e:
            logger.error(
                "batch_generation_failed",
                intent=intent,
                language=language,
                domain=domain,
                error=str(e),
            )
            self.stats["failed_batches"] += 1
            return []

    async def generate_examples(self) -> list[IntentExample]:
        """Generate all intent classification examples.

        Returns:
            List of generated intent examples

        Strategy:
            - Balanced distribution across 5 intent classes (200 per class)
            - Bilingual: 50% German, 50% English
            - Domain mix: 40% software, 30% business, 30% research
        """
        logger.info(
            "starting_generation",
            target_examples=self.target_examples,
            intents=list(self.INTENT_DEFINITIONS.keys()),
        )

        all_examples: list[IntentExample] = []
        intents = list(self.INTENT_DEFINITIONS.keys())
        examples_per_intent = self.target_examples // len(intents)

        # Generate examples for each intent class
        for intent in intents:
            intent_examples = []
            remaining = examples_per_intent

            while remaining > 0:
                # Determine language (50/50 split)
                language = random.choice(["en", "de"])

                # Determine domain (weighted distribution)
                domain = random.choices(
                    ["software", "business", "research"],
                    weights=[0.4, 0.3, 0.3],
                    k=1,
                )[0]

                # Generate batch
                batch_size = min(self.examples_per_batch, remaining)
                batch = await self._generate_batch(intent, language, domain, batch_size)

                intent_examples.extend(batch)
                remaining -= len(batch)

                # Rate limiting to avoid overwhelming Ollama
                await asyncio.sleep(1.0)

            logger.info(
                "intent_generation_complete",
                intent=intent,
                target=examples_per_intent,
                generated=len(intent_examples),
            )

            all_examples.extend(intent_examples)

        logger.info(
            "generation_complete",
            total_generated=len(all_examples),
            target=self.target_examples,
            stats=dict(self.stats),
        )

        return all_examples

    def validate_dataset(self, examples: list[IntentExample]) -> dict[str, Any]:
        """Validate generated dataset quality.

        Args:
            examples: List of generated examples

        Returns:
            Validation report with quality metrics

        Quality Checks:
            - Class balance (should be ~20% per class)
            - Language balance (should be ~50% each)
            - Confidence distribution (90% should have >0.8)
            - Query length distribution
            - Duplicate detection
        """
        if not examples:
            return {
                "valid": False,
                "error": "No examples generated",
            }

        # Class distribution
        class_counts = defaultdict(int)
        for ex in examples:
            class_counts[ex.intent] += 1

        # Language distribution
        lang_counts = defaultdict(int)
        for ex in examples:
            lang_counts[ex.language] += 1

        # Confidence distribution
        high_confidence = sum(1 for ex in examples if ex.confidence >= 0.8)
        high_conf_pct = (high_confidence / len(examples)) * 100

        # Query length distribution
        query_lengths = [len(ex.query.split()) for ex in examples]
        avg_length = sum(query_lengths) / len(query_lengths)

        # Duplicate detection
        unique_queries = len(set(ex.query.lower() for ex in examples))
        duplicate_pct = ((len(examples) - unique_queries) / len(examples)) * 100

        # Quality assessment
        valid = True
        issues = []

        # Check class balance (should be 15-25% per class)
        for intent, count in class_counts.items():
            pct = (count / len(examples)) * 100
            if pct < 15 or pct > 25:
                valid = False
                issues.append(f"Class imbalance: {intent} = {pct:.1f}% (expected 20%)")

        # Check confidence (90% should have >0.8)
        if high_conf_pct < 90:
            valid = False
            issues.append(
                f"Low confidence: {high_conf_pct:.1f}% with confidence ≥0.8 (expected ≥90%)"
            )

        # Check duplicates (should be <5%)
        if duplicate_pct > 5:
            valid = False
            issues.append(f"High duplicates: {duplicate_pct:.1f}% (expected <5%)")

        report = {
            "valid": valid,
            "total_examples": len(examples),
            "class_distribution": dict(class_counts),
            "language_distribution": dict(lang_counts),
            "high_confidence_pct": round(high_conf_pct, 2),
            "avg_query_length": round(avg_length, 2),
            "duplicate_pct": round(duplicate_pct, 2),
            "unique_queries": unique_queries,
            "issues": issues,
        }

        logger.info(
            "dataset_validation_complete",
            valid=valid,
            total_examples=len(examples),
            issues_count=len(issues),
        )

        return report

    async def save_dataset(
        self, examples: list[IntentExample], output_path: str | Path
    ) -> None:
        """Save generated dataset to JSONL file.

        Args:
            examples: List of generated examples
            output_path: Path to output JSONL file

        File Format:
            One JSON object per line:
            {"query": "...", "intent": "factual", "confidence": 0.95, "language": "en", "domain": "software"}
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            for example in examples:
                f.write(json.dumps(example.to_dict(), ensure_ascii=False) + "\n")

        logger.info(
            "dataset_saved",
            output_path=str(output_path),
            examples_count=len(examples),
            file_size_kb=output_path.stat().st_size / 1024,
        )

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()


async def main() -> None:
    """Main entry point for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate C-LARA intent training data")
    parser.add_argument(
        "--model",
        default="qwen2.5:7b",
        help="Ollama model to use (default: qwen2.5:7b)",
    )
    parser.add_argument(
        "--examples",
        type=int,
        default=1000,
        help="Total number of examples to generate (default: 1000)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Examples per batch (default: 10)",
    )
    parser.add_argument(
        "--output",
        default="data/intent_training_v1.jsonl",
        help="Output JSONL file path",
    )

    args = parser.parse_args()

    generator = CLARADataGenerator(
        model=args.model,
        target_examples=args.examples,
        examples_per_batch=args.batch_size,
    )

    try:
        # Generate examples
        examples = await generator.generate_examples()

        # Validate dataset
        validation = generator.validate_dataset(examples)
        print("\n=== Validation Report ===")
        print(json.dumps(validation, indent=2))

        if not validation["valid"]:
            print("\nWARNING: Dataset validation failed. Review issues above.")

        # Save dataset
        await generator.save_dataset(examples, args.output)
        print(f"\nDataset saved to: {args.output}")

    finally:
        await generator.close()


if __name__ == "__main__":
    asyncio.run(main())

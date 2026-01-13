"""Debug RAGAS prompts and responses to understand parsing failures.

Sprint 75: Investigating RAGAS output parsing errors.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Enable debug logging for RAGAS
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)

# Intercept LangChain LLM calls
from langchain_core.callbacks import BaseCallbackHandler
from typing import Any, Dict, List


class DebugCallbackHandler(BaseCallbackHandler):
    """Callback to intercept and log RAGAS prompts and responses."""

    def __init__(self):
        self.prompt_count = 0

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Log LLM prompts."""
        self.prompt_count += 1
        print(f"\n{'='*80}")
        print(f"🔵 RAGAS PROMPT #{self.prompt_count}")
        print(f"{'='*80}")
        for i, prompt in enumerate(prompts):
            print(f"\n--- Prompt {i+1} ---")
            print(prompt)
            print(f"--- End Prompt {i+1} ---\n")

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Log LLM responses."""
        print(f"\n{'='*80}")
        print(f"🟢 RAGAS RESPONSE #{self.prompt_count}")
        print(f"{'='*80}")

        # Extract text from response
        if hasattr(response, 'generations'):
            for i, generation_list in enumerate(response.generations):
                for j, generation in enumerate(generation_list):
                    print(f"\n--- Generation {i+1}.{j+1} ---")
                    print(generation.text)
                    print(f"--- End Generation ---\n")
        else:
            print(response)

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Log LLM errors."""
        print(f"\n{'='*80}")
        print(f"🔴 RAGAS ERROR #{self.prompt_count}")
        print(f"{'='*80}")
        print(f"Error: {error}")


async def main():
    print("🔧 Debugging RAGAS Prompts and Responses...")
    print("")

    from ragas.metrics import ContextPrecision
    from langchain_ollama import ChatOllama
    from datasets import Dataset

    # Create LLM with debug callback
    debug_handler = DebugCallbackHandler()

    llm = ChatOllama(
        model="qwen2.5:7b",
        base_url="http://localhost:11434",
        temperature=0.0,
        num_ctx=8192,
        num_predict=2048,
        format="json",
        callbacks=[debug_handler],
    )

    # Create metric
    metric = ContextPrecision()
    metric.llm = llm

    # Test data (minimal)
    test_data = {
        "question": ["What is BGE-M3?"],
        "contexts": [["BGE-M3 is a 1024-dimensional multilingual embedding model."]],
        "answer": ["BGE-M3 is an embedding model for semantic search."],
        "ground_truth": ["BGE-M3 is a multilingual embedding model."],
    }

    dataset = Dataset.from_dict(test_data)

    print("📊 Running ContextPrecision metric...")
    print("")

    try:
        # Run metric (will trigger callbacks)
        from ragas import evaluate
        result = evaluate(
            dataset=dataset,
            metrics=[metric],
            llm=llm,
        )

        print(f"\n{'='*80}")
        print("✅ Evaluation succeeded!")
        print(f"{'='*80}")
        print(f"Context Precision: {result['context_precision']}")

    except Exception as e:
        print(f"\n{'='*80}")
        print("❌ Evaluation failed!")
        print(f"{'='*80}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

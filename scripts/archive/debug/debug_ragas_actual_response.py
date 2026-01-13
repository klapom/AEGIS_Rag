"""Debug: Show EXACT LLM response that RAGAS is trying to parse.

Sprint 75: Understanding why parsing fails.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_ollama import ChatOllama
from ragas.metrics._context_precision import ContextPrecisionPrompt, QAC


async def main():
    print("🔍 Testing RAGAS Context Precision Prompt with qwen2.5:7b")
    print("="*80)

    # Create LLM
    llm = ChatOllama(
        model="qwen2.5:7b",
        base_url="http://localhost:11434",
        temperature=0.0,
        num_ctx=8192,
        num_predict=2048,
        format="json",
    )

    # Create prompt
    prompt = ContextPrecisionPrompt()

    # Test data (from our RAG retrieval)
    test_input = QAC(
        question="What is BGE-M3?",
        context="BGE-M3 is a 1024-dimensional multilingual embedding model used in AEGIS RAG for semantic search. The model is from the BAAI (Beijing Academy of Artificial Intelligence) team.",
        answer="BGE-M3 is a multilingual embedding model for semantic search with 1024 dimensions.",
    )

    # Generate prompt string
    prompt_str = prompt.to_string(test_input)

    print("\n📤 PROMPT SENT TO LLM:")
    print("-"*80)
    print(prompt_str)
    print("-"*80)

    # Call LLM
    print("\n⏳ Calling qwen2.5:7b...")
    response = await llm.ainvoke(prompt_str)

    print("\n📥 RAW LLM RESPONSE:")
    print("="*80)
    print(response.content)
    print("="*80)

    # Try to parse
    print("\n🔧 Attempting to parse as JSON...")
    try:
        import json
        parsed = json.loads(response.content)
        print("✅ JSON is valid!")
        print(f"Parsed: {parsed}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing failed: {e}")
        print(f"   At position: {e.pos}")
        print(f"   Problem area: ...{response.content[max(0,e.pos-50):e.pos+50]}...")

    # Try Pydantic validation
    print("\n🔧 Attempting Pydantic validation...")
    try:
        from ragas.metrics._context_precision import Verification
        result = Verification.model_validate_json(response.content)
        print(f"✅ Pydantic validation succeeded!")
        print(f"   Reason: {result.reason}")
        print(f"   Verdict: {result.verdict}")
    except Exception as e:
        print(f"❌ Pydantic validation failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())

"""Test RAGAS with REAL contexts from our RAG retrieval.

Sprint 75: Debug which of the 5 contexts causes parsing to fail.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_ollama import ChatOllama
from ragas.metrics._context_precision import ContextPrecisionPrompt, QAC, Verification


async def main():
    print("🔍 Testing Context Precision with REAL RAG contexts")
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

    # Get REAL contexts from our RAG system
    print("\n📥 Retrieving contexts from AEGIS RAG...")
    from src.components.retrieval.four_way_hybrid_search import get_four_way_hybrid_search

    search_engine = get_four_way_hybrid_search()
    results = await search_engine.search(
        query="What is BGE-M3?",
        top_k=5,
        allowed_namespaces=["default"],
        use_reranking=True,
    )

    contexts = [r["text"] for r in results.get("results", [])]
    print(f"✅ Retrieved {len(contexts)} contexts\n")

    # Create prompt
    prompt = ContextPrecisionPrompt()

    question = "What is BGE-M3?"
    answer = "BGE-M3 is a multilingual embedding model for semantic search with 1024 dimensions."

    # Test EACH context individually
    for i, context in enumerate(contexts, 1):
        print(f"\n{'='*80}")
        print(f"📄 Testing Context {i}/{len(contexts)}")
        print(f"{'='*80}")
        print(f"Length: {len(context)} chars")
        print(f"Preview: {context[:150]}...")

        test_input = QAC(
            question=question,
            context=context,
            answer=answer,
        )

        prompt_str = prompt.to_string(test_input)

        # Call LLM
        print(f"\n⏳ Calling qwen2.5:7b...")
        try:
            response = await llm.ainvoke(prompt_str)

            print(f"📥 Response length: {len(response.content)} chars")
            print(f"Response preview: {response.content[:200]}...")

            # Try to parse
            result = Verification.model_validate_json(response.content)
            print(f"✅ SUCCESS!")
            print(f"   Verdict: {result.verdict}")
            print(f"   Reason: {result.reason[:100]}...")

        except Exception as e:
            print(f"❌ FAILED: {e}")
            print(f"\n🔴 PROBLEMATIC CONTEXT FOUND: Context #{i}")
            print(f"Full context:\n{context}")
            print(f"\nFull response:\n{response.content if 'response' in locals() else 'No response'}")
            break

    print(f"\n{'='*80}")
    print("✅ All contexts tested!")


if __name__ == "__main__":
    asyncio.run(main())

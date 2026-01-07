"""Test RAGAS JSON output with gpt-oss:20b to identify parsing issues."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_ollama import ChatOllama

OLLAMA_BASE_URL = "http://localhost:11434"


def test_statement_generator():
    """Test StatementGeneratorPrompt output format."""
    print("=" * 80)
    print("Testing: StatementGeneratorPrompt")
    print("=" * 80)
    print()

    llm = ChatOllama(
        model="gpt-oss:20b",
        base_url=OLLAMA_BASE_URL,
        temperature=0.0,
        top_p=0.9,
        timeout=60,
        num_ctx=16384,
        num_predict=512,
        format="json",
    )

    # RAGAS prompt example
    prompt = """Given a question and an answer, analyze the complexity of each sentence in the answer. Break down each sentence into one or more fully understandable statements. Ensure that no pronouns are used in any statement. Format the outputs in JSON.

Example:
Question: Who was Albert Einstein and what is he best known for?
Answer: He was a German-born theoretical physicist, widely acknowledged to be one of the greatest and most influential physicists of all time. He was best known for developing the theory of relativity, he also made important contributions to the development of the theory of quantum mechanics.

Output:
{
  "statements": [
    "Albert Einstein was a German-born theoretical physicist.",
    "Albert Einstein is recognized as one of the greatest and most influential physicists of all time.",
    "Albert Einstein was best known for developing the theory of relativity.",
    "Albert Einstein also made important contributions to the development of the theory of quantum mechanics."
  ]
}

Now process:
Question: What is BGE-M3?
Answer: BGE-M3 is a 1024-dimensional multilingual embedding model from BAAI (Beijing Academy of Artificial Intelligence) used for semantic search and retrieval.

Output (JSON only):"""

    print("Prompt:")
    print(prompt)
    print()
    print("-" * 80)
    print("gpt-oss:20b Response:")
    print("-" * 80)

    response = llm.invoke(prompt)
    output = response.content

    print(output)
    print()
    print("-" * 80)

    # Try to parse
    try:
        parsed = json.loads(output)
        print("✅ PARSING SUCCESS")
        print(f"   Keys: {list(parsed.keys())}")
        if "statements" in parsed:
            print(f"   Statements count: {len(parsed['statements'])}")
        else:
            print(f"   ❌ Missing 'statements' key!")
            print(f"   Actual keys: {list(parsed.keys())}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON PARSING FAILED: {e}")
    except Exception as e:
        print(f"❌ OTHER ERROR: {e}")

    print()
    return output


def test_context_recall():
    """Test ContextRecallClassificationPrompt output format."""
    print("=" * 80)
    print("Testing: ContextRecallClassificationPrompt")
    print("=" * 80)
    print()

    llm = ChatOllama(
        model="gpt-oss:20b",
        base_url=OLLAMA_BASE_URL,
        temperature=0.0,
        top_p=0.9,
        timeout=60,
        num_ctx=16384,
        num_predict=512,
        format="json",
    )

    prompt = """Given a context, and an answer, analyze each sentence in the answer and classify if the sentence can be attributed to the given context or not. Use only 'Yes' (1) or 'No' (0) as a binary classification. Output json with reason.

Example Output:
{
  "classifications": [
    {
      "statement": "Albert Einstein was a German-born theoretical physicist.",
      "reason": "This is directly stated in the context.",
      "attributed": 1
    },
    {
      "statement": "Einstein published 4 papers in 1905.",
      "reason": "This is not mentioned in the context.",
      "attributed": 0
    }
  ]
}

Now process:
Context: BGE-M3 is a 1024-dimensional embedding model from BAAI.
Answer: BGE-M3 is a multilingual model used for semantic search.

Output (JSON only):"""

    print("Prompt:")
    print(prompt)
    print()
    print("-" * 80)
    print("gpt-oss:20b Response:")
    print("-" * 80)

    response = llm.invoke(prompt)
    output = response.content

    print(output)
    print()
    print("-" * 80)

    # Try to parse
    try:
        parsed = json.loads(output)
        print("✅ PARSING SUCCESS")
        print(f"   Keys: {list(parsed.keys())}")
        if "classifications" in parsed:
            print(f"   Classifications count: {len(parsed['classifications'])}")
            if parsed['classifications']:
                first = parsed['classifications'][0]
                print(f"   First item keys: {list(first.keys())}")
        else:
            print(f"   ❌ Missing 'classifications' key!")
    except json.JSONDecodeError as e:
        print(f"❌ JSON PARSING FAILED: {e}")
    except Exception as e:
        print(f"❌ OTHER ERROR: {e}")

    print()
    return output


def test_context_precision():
    """Test ContextPrecisionPrompt output format."""
    print("=" * 80)
    print("Testing: ContextPrecisionPrompt")
    print("=" * 80)
    print()

    llm = ChatOllama(
        model="gpt-oss:20b",
        base_url=OLLAMA_BASE_URL,
        temperature=0.0,
        top_p=0.9,
        timeout=60,
        num_ctx=16384,
        num_predict=512,
        format="json",
    )

    prompt = """Given question, answer and context verify if the context was useful in arriving at the given answer. Give verdict as "1" if useful and "0" if not with json output.

Example Output:
{
  "reason": "The provided context was indeed useful in arriving at the given answer.",
  "verdict": 1
}

Now process:
Question: What is BGE-M3?
Context: BGE-M3 is a 1024-dimensional multilingual embedding model from BAAI.
Answer: BGE-M3 is used for semantic search.

Output (JSON only):"""

    print("Prompt:")
    print(prompt)
    print()
    print("-" * 80)
    print("gpt-oss:20b Response:")
    print("-" * 80)

    response = llm.invoke(prompt)
    output = response.content

    print(output)
    print()
    print("-" * 80)

    # Try to parse
    try:
        parsed = json.loads(output)
        print("✅ PARSING SUCCESS")
        print(f"   Keys: {list(parsed.keys())}")
        if "verdict" in parsed and "reason" in parsed:
            print(f"   verdict: {parsed['verdict']} (type: {type(parsed['verdict'])})")
        else:
            print(f"   ❌ Missing required keys!")
    except json.JSONDecodeError as e:
        print(f"❌ JSON PARSING FAILED: {e}")
    except Exception as e:
        print(f"❌ OTHER ERROR: {e}")

    print()
    return output


if __name__ == "__main__":
    print("=" * 80)
    print("🔬 RAGAS JSON Output Analysis with gpt-oss:20b")
    print("=" * 80)
    print()

    try:
        # Test all three problematic prompts
        output1 = test_statement_generator()
        output2 = test_context_recall()
        output3 = test_context_precision()

        # Summary
        print("=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print()
        print("Review the outputs above to identify:")
        print("  1. Extra fields not in schema")
        print("  2. Wrong key names")
        print("  3. Markdown formatting (```json blocks)")
        print("  4. Type mismatches (string vs int)")
        print("  5. Trailing commas or malformed JSON")
        print()

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

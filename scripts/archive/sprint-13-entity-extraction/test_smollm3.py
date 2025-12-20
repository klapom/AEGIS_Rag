"""
Test SmolLM3 model with LightRAG delimiter format.
"""

import asyncio
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import ollama

TEST_TEXT = """
Apple Inc. was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in 1976.
Steve Jobs served as CEO and led product development. The company's headquarters
is located in Cupertino, California. Apple is known for products like the iPhone,
iPad, and Mac computers.
"""

LIGHTRAG_PROMPT = """---Role---
You are a Knowledge Graph Specialist responsible for extracting entities and relationships from the input text.

---Instructions---
1.  **Entity Extraction & Output:**
    *   **Identification:** Identify clearly defined and meaningful entities in the input text.
    *   **Entity Details:** For each identified entity, extract the following information:
        *   `entity_name`: The name of the entity. Capitalize the first letter of each significant word (title case).
        *   `entity_type`: Categorize the entity using one of the following types: [organization, person, location, product, event, date]. If none apply, classify it as `Other`.
        *   `entity_description`: Provide a concise yet comprehensive description of the entity's attributes and activities.
    *   **Output Format - Entities:** Output a total of 4 fields for each entity, delimited by `<|#|>`, on a single line. The first field *must* be the literal string `entity`.
        *   Format: `entity<|#|>entity_name<|#|>entity_type<|#|>entity_description`

2.  **Relationship Extraction & Output:**
    *   **Identification:** Identify direct, clearly stated, and meaningful relationships between previously extracted entities.
    *   **Relationship Details:** For each binary relationship, extract the following fields:
        *   `source_entity`: The name of the source entity.
        *   `target_entity`: The name of the target entity.
        *   `relationship_keywords`: One or more high-level keywords summarizing the relationship (comma-separated).
        *   `relationship_description`: A concise explanation of the nature of the relationship.
    *   **Output Format - Relationships:** Output a total of 5 fields for each relationship, delimited by `<|#|>`, on a single line. The first field *must* be the literal string `relation`.
        *   Format: `relation<|#|>source_entity<|#|>target_entity<|#|>relationship_keywords<|#|>relationship_description`

3.  **Output Order:** Output all extracted entities first, followed by all extracted relationships.

4.  **Completion Signal:** Output the literal string `<|COMPLETE|>` only after all entities and relationships have been completely extracted.

---Example---
Input: "Alex works at Control, coordinating with Taylor."
Output:
entity<|#|>Alex<|#|>person<|#|>Alex is a coordinator.
entity<|#|>Control<|#|>organization<|#|>Control is the central authority.
entity<|#|>Taylor<|#|>person<|#|>Taylor is a team member.
relation<|#|>Alex<|#|>Control<|#|>employment<|#|>Alex works at Control.
relation<|#|>Alex<|#|>Taylor<|#|>collaboration<|#|>Alex coordinates with Taylor.
<|COMPLETE|>

---Task---
Extract entities and relationships from the following text:

{text}

---Output---
"""


async def test_smollm3():
    """Test SmolLM3 with LightRAG format."""
    print("=" * 80)
    print("TESTING SMOLLM3 WITH LIGHTRAG FORMAT")
    print("=" * 80)
    print()

    model_name = "smollm"
    prompt = LIGHTRAG_PROMPT.format(text=TEST_TEXT.strip())

    print(f"Model: {model_name}")
    print("Test: Apple Inc. founding story")
    print()

    client = ollama.AsyncClient()

    try:
        print("Generating response...")
        start_time = time.time()

        response = await client.generate(
            model=model_name,
            prompt=prompt,
            options={
                "temperature": 0.0,
                "num_predict": 2000,
                "num_ctx": 32768,
            },
        )

        elapsed = time.time() - start_time
        output = response["response"]

        print(f"\n[DONE] Generation time: {elapsed:.2f}s")
        print()
        print("=" * 80)
        print("MODEL OUTPUT:")
        print("=" * 80)
        print(output)
        print("=" * 80)
        print()

        # Analysis
        print("=" * 80)
        print("ANALYSIS:")
        print("=" * 80)

        entities = output.count("entity<|#|>")
        relations = output.count("relation<|#|>")
        has_delimiter = "<|#|>" in output
        has_completion = "<|COMPLETE|>" in output

        print(f"Entities found: {entities}")
        print(f"Relationships found: {relations}")
        print(f"Uses correct delimiter (<|#|>): {has_delimiter}")
        print(f"Has completion marker: {has_completion}")
        print()

        if entities >= 3 and has_delimiter:
            print("[OK] SmolLM3 WORKS with LightRAG format!")
        else:
            print("[FAIL] SmolLM3 does not produce correct format")

        print("=" * 80)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_smollm3())

"""
Test script to inspect LightRAG prompts and responses.
Shows exactly what prompt is sent to the model and what comes back.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import ollama


async def test_entity_extraction_prompt():
    """Test the exact prompt that LightRAG uses for entity extraction."""

    # This is the test document from the E2E test
    test_text = """
    Apple Inc. was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in 1976.
    Steve Jobs served as CEO and led product development. The company's headquarters
    is located in Cupertino, California. Apple is known for products like the iPhone,
    iPad, and Mac computers.
    """

    # This is approximately what LightRAG sends (based on lightrag source code)
    # The actual prompt template is in lightrag/operate.py
    prompt = f"""
-Target activity-
You are an intelligent assistant that helps a human analyst to analyze claims against certain entities presented in a text document.

-Goal-
Given a text document that is potentially relevant to this activity, an entity type, and a list of entity categories, identify all entities of those types from the text and all relationships among the identified entities.

-Steps-
1. Identify all entities. For each identified entity, extract the following information:
- entity_name: Name of the entity, capitalized
- entity_type: One of the following types: [organization, person, location, product, event, date]
- entity_description: Comprehensive description of the entity's attributes and activities
Format each entity as ("entity"<|#|><entity_name><|#|><entity_type><|#|><entity_description>)

2. From the entities identified in step 1, identify all pairs of (source_entity, target_entity) that are *clearly related* to each other.
For each pair of related entities, extract the following information:
- source_entity: name of the source entity, as identified in step 1
- target_entity: name of the target entity, as identified in step 1
- relationship_description: explanation as to why you think the source entity and the target entity are related to each other
- relationship_strength: a numeric score indicating strength of the relationship between the source entity and target entity
Format each relationship as ("relationship"<|#|><source_entity><|#|><target_entity><|#|><relationship_description><|#|><relationship_strength>)

3. Return output in English as a single list of all the entities and relationships identified in steps 1 and 2. Use **##** as the list delimiter.

4. When finished, output <|COMPLETE|>

######################
-Examples-
######################
Example 1:

entity_types: [person, technology, mission, organization, location]
text:
their voice slicing through the buzz of activity. "Control, this is Parker. We have a situation." The tension in their voice was palpable. "I'm routing you through now," Devi said, fingers flying across the keys with practiced ease.
------------------------
output:
("entity"<|#|>Parker<|#|>person<|#|>Parker is a communications specialist working at a central control station, coordinating responses during a critical incident. They are under significant stress and need to relay urgent information to decision-makers.)
("entity"<|#|>Control<|#|>organization<|#|>Control is the central authority managing and coordinating responses to the crisis. It serves as the decision-making hub for all operations.)
("entity"<|#|>Devi<|#|>person<|#|>Devi is a technical operator working under pressure to facilitate critical communications between field operatives and command structures.)
("relationship"<|#|>Parker<|#|>Control<|#|>Parker reports directly to Control, indicating a hierarchical relationship where Parker provides real-time updates.<|#|>8)
("relationship"<|#|>Devi<|#|>Parker<|#|>Devi assists Parker by routing communications, showing a supportive and collaborative relationship.<|#|>7)
<|COMPLETE|>

######################
-Real Data-
######################
entity_types: [organization, person, location, product, event, date]
text: {test_text.strip()}
######################
output:
"""

    print("=" * 80)
    print("PROMPT SENT TO MODEL:")
    print("=" * 80)
    print(prompt)
    print("=" * 80)
    print()

    # Call the model
    model = "qwen3:0.6b"
    print(f"Calling {model}...")
    print()

    client = ollama.AsyncClient()

    try:
        response = await client.generate(
            model=model,
            prompt=prompt,
            options={
                "temperature": 0.0,  # LightRAG default
                "num_predict": 2000,  # LightRAG default max tokens
                "num_ctx": 32768,     # 32K context window
            },
        )

        output = response["response"]

        print("=" * 80)
        print("RESPONSE FROM MODEL:")
        print("=" * 80)
        print(output)
        print("=" * 80)
        print()

        # Analyze the output
        print("=" * 80)
        print("ANALYSIS:")
        print("=" * 80)

        # Check for delimiter
        if "##" in output:
            print("✓ Found delimiter '##' in output")
            records = output.split("##")
            print(f"  Number of records: {len(records)}")
            for i, record in enumerate(records[:5], 1):  # Show first 5
                print(f"  Record {i}: {record[:100]}...")
        else:
            print("✗ Delimiter '##' NOT found in output")

        # Check for alternative delimiter
        if "<|#|>" in output:
            print("⚠ Found alternative delimiter '<|#|>' (INCOMPATIBLE)")
            records = output.split("<|#|>")
            print(f"  Number of records with '<|#|>': {len(records)}")

        # Check for newlines
        if "\n" in output:
            print("  Output contains newlines")
            lines = output.strip().split("\n")
            print(f"  Number of lines: {len(lines)}")

        # Check for entity format
        if '("entity"' in output or "(\"entity\"" in output:
            print("✓ Found entity format markers")
        else:
            print("✗ Entity format markers NOT found")

        # Check for relationship format
        if '("relationship"' in output or "(\"relationship\"" in output:
            print("✓ Found relationship format markers")
        else:
            print("✗ Relationship format markers NOT found")

        # Check for completion marker
        if "COMPLETE" in output:
            print("✓ Found completion marker")
        else:
            print("✗ Completion marker NOT found")

        print("=" * 80)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_entity_extraction_prompt())

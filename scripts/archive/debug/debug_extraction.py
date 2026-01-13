"""Debug script for Entity Extraction Pipeline.

Sprint 32 Post-Mortem: Diagnose why Entity extraction is not working.
Tests the full extraction pipeline step by step.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog

logger = structlog.get_logger(__name__)


async def main():
    print("=" * 60)
    print("DEBUG EXTRACTION PIPELINE")
    print("=" * 60)

    # Step 1: Test ExtractionService directly
    print("\n[1] Testing ExtractionService...")
    try:
        from src.components.graph_rag.extraction_service import ExtractionService

        service = ExtractionService()
        print(f"    LLM Model: {service.llm_model}")
        print(f"    Temperature: {service.temperature}")
        print(f"    Max Tokens: {service.max_tokens}")

        # Test with simple text
        test_text = """
        AEGIS RAG is a hybrid retrieval augmented generation system developed by Klaus Pommer.
        It uses Neo4j as graph database and Qdrant for vector search.
        The system is built with Python and uses LangGraph for orchestration.
        """

        print("\n    Extracting entities from test text...")
        entities = await service.extract_entities(test_text, "debug_test_doc")
        print(f"    Entities extracted: {len(entities)}")

        for entity in entities:
            print(f"      - {entity.name} ({entity.type})")

        if entities:
            print("\n    Extracting relationships...")
            relationships = await service.extract_relationships(test_text, entities, "debug_test_doc")
            print(f"    Relationships extracted: {len(relationships)}")

            for rel in relationships:
                print(f"      - {rel.source} --[{rel.type}]--> {rel.target}")
        else:
            print("    PROBLEM: No entities extracted! Check LLM response.")

    except Exception as e:
        print(f"    ERROR: {e}")
        import traceback
        traceback.print_exc()

    # Step 2: Test LLMExtractionPipeline via factory
    print("\n[2] Testing LLMExtractionPipeline via factory...")
    try:
        from src.components.graph_rag.extraction_factory import (
            create_extraction_pipeline_from_config,
        )

        pipeline = create_extraction_pipeline_from_config()
        print(f"    Pipeline type: {type(pipeline).__name__}")

        test_text = "Neo4j is a graph database. Qdrant is a vector database."

        print("    Running pipeline.extract()...")
        entities, relations = await pipeline.extract(test_text, "debug_test_doc_2")

        print(f"    Entities: {len(entities)}")
        print(f"    Relations: {len(relations)}")

        for entity in entities:
            print(f"      Entity: {entity}")
        for rel in relations:
            print(f"      Relation: {rel}")

    except Exception as e:
        print(f"    ERROR: {e}")
        import traceback
        traceback.print_exc()

    # Step 3: Check Neo4j connection
    print("\n[3] Testing Neo4j connection...")
    try:
        from src.components.graph_rag.neo4j_client import Neo4jClient

        client = Neo4jClient()

        # Count current entities (should use :base label per migration)
        result = await client.execute_query("""
            MATCH (n:base)
            RETURN count(n) as count
        """)
        print(f"    Current entities with :base label: {result[0]['count'] if result else 0}")

        # Count all node labels
        result2 = await client.execute_query("""
            MATCH (n)
            RETURN labels(n) as labels, count(n) as count
            ORDER BY count DESC
        """)
        print("    All node counts by label:")
        for r in result2:
            print(f"      {r}")

        await client.close()

    except Exception as e:
        print(f"    ERROR: {e}")
        import traceback
        traceback.print_exc()

    # Step 4: Test AegisLLMProxy
    print("\n[4] Testing AegisLLMProxy...")
    try:
        from src.components.llm_proxy import get_aegis_llm_proxy
        from src.components.llm_proxy.models import (
            Complexity,
            LLMTask,
            QualityRequirement,
            TaskType,
        )

        proxy = get_aegis_llm_proxy()

        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract entities from: 'Neo4j is a graph database'. Return JSON array.",
            quality_requirement=QualityRequirement.HIGH,
            complexity=Complexity.HIGH,
            max_tokens=1000,
            temperature=0.1,
        )

        print("    Calling AegisLLMProxy.generate()...")
        result = await proxy.generate(task)

        print(f"    Provider: {result.provider}")
        print(f"    Model: {result.model}")
        print(f"    Cost: ${result.cost_usd}")
        print(f"    Response preview: {result.content[:500] if result.content else 'EMPTY'}")

    except Exception as e:
        print(f"    ERROR: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("DEBUG COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

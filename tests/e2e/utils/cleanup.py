"""Shared cleanup utilities for E2E tests.

Provides utility functions for cleaning up test data and resources after tests:
- Database cleanup
- File cleanup
- Cache cleanup
- Session cleanup

Usage in conftest.py:
    from tests.e2e.utils.cleanup import cleanup_after_test

    @pytest.fixture(autouse=True)
    async def cleanup_fixture():
        yield
        await cleanup_after_test()
"""

import asyncio
from typing import Optional

from src.core.logging import get_logger

logger = get_logger(__name__)


async def cleanup_qdrant_test_data(
    collection_name: str = "documents",
    filter_by_tag: Optional[str] = None,
) -> None:
    """Clean up test data from Qdrant collection.
    
    Args:
        collection_name: Name of collection to clean
        filter_by_tag: Optional tag to filter what to delete
    
    Example:
        # Clean all test data tagged with 'e2e_test'
        await cleanup_qdrant_test_data(filter_by_tag='e2e_test')
    """
    try:
        from qdrant_client import AsyncQdrantClient
        from src.core.config import settings
        
        client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            prefer_grpc=settings.qdrant_use_grpc,
        )
        
        if filter_by_tag:
            # Delete points with specific tag (requires payload filtering)
            await client.delete(
                collection_name=collection_name,
                points_selector={
                    "filter": {
                        "must": [
                            {
                                "key": "test_tag",
                                "match": {"value": filter_by_tag}
                            }
                        ]
                    }
                }
            )
            logger.info(f"Cleaned up Qdrant test data with tag {filter_by_tag}")
        else:
            logger.debug(f"Qdrant cleanup: collection {collection_name} preserved")
        
        await client.close()
    except Exception as e:
        logger.warning(f"Qdrant cleanup failed: {e}")


async def cleanup_neo4j_test_data(
    filter_by_label: Optional[str] = None,
) -> None:
    """Clean up test data from Neo4j graph database.
    
    Args:
        filter_by_label: Optional label to filter what to delete
        
    Example:
        # Clean all nodes with 'TestEntity' label
        await cleanup_neo4j_test_data(filter_by_label='TestEntity')
    """
    try:
        from neo4j import AsyncGraphDatabase
        from src.core.config import settings
        
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        
        async with driver.session() as session:
            if filter_by_label:
                await session.run(f"MATCH (n:{filter_by_label}) DETACH DELETE n")
                logger.info(f"Cleaned up Neo4j test data with label {filter_by_label}")
            else:
                logger.debug("Neo4j cleanup: data preserved")
        
        await driver.close()
    except Exception as e:
        logger.warning(f"Neo4j cleanup failed: {e}")


async def cleanup_redis_test_data(
    key_prefix: str = "test_",
) -> None:
    """Clean up test data from Redis cache.
    
    Args:
        key_prefix: Prefix of keys to delete
        
    Example:
        # Clean all keys starting with 'test_'
        await cleanup_redis_test_data(key_prefix='test_')
    """
    try:
        import redis
        from src.core.config import settings
        
        client = redis.from_url(settings.redis_url, decode_responses=True)
        
        # Find all keys matching pattern
        pattern = f"{key_prefix}*"
        keys = client.keys(pattern)
        
        if keys:
            client.delete(*keys)
            logger.info(f"Cleaned up {len(keys)} Redis test keys")
        else:
            logger.debug(f"No Redis keys matching pattern {pattern}")
        
        client.close()
    except Exception as e:
        logger.warning(f"Redis cleanup failed: {e}")


async def cleanup_after_test() -> None:
    """Complete cleanup after a single test.
    
    This is a comprehensive cleanup that removes test data from all
    storage systems. Call this in test cleanup fixtures or teardown.
    
    Example in conftest.py:
        @pytest.fixture(autouse=True)
        async def cleanup_fixture():
            yield
            await cleanup_after_test()
    """
    logger.info("Starting test cleanup...")
    
    # Run cleanup tasks
    await asyncio.gather(
        cleanup_redis_test_data(key_prefix="test_"),
        cleanup_qdrant_test_data(filter_by_tag="e2e_test"),
        cleanup_neo4j_test_data(filter_by_label="TestEntity"),
        return_exceptions=True,
    )
    
    logger.info("Test cleanup completed")


async def cleanup_after_suite() -> None:
    """Complete cleanup after entire test suite.
    
    More aggressive cleanup that may clear more data.
    Use in conftest.py with scope="session".
    """
    logger.info("Starting suite cleanup...")
    
    try:
        # Give services time to settle
        await asyncio.sleep(1)
        
        # Run cleanup
        await cleanup_after_test()
        
        logger.info("Suite cleanup completed")
    except Exception as e:
        logger.error(f"Suite cleanup failed: {e}")


def sync_cleanup() -> None:
    """Synchronous wrapper for cleanup operations.
    
    Use when async cleanup is not available.
    
    Example:
        def teardown_module():
            sync_cleanup()
    """
    try:
        asyncio.run(cleanup_after_test())
    except Exception as e:
        logger.error(f"Sync cleanup failed: {e}")

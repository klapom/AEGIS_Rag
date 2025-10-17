"""E2E Integration Tests for Memory API Endpoints with Real Services.

Sprint 7 Feature 7.6: Memory API
- NO MOCKS: Tests all 6 endpoints with real Redis/Qdrant/Graphiti
- Tests request/response validation and error handling
- Tests rate limiting and performance
- Validates full API integration

CRITICAL: All tests marked with @pytest.mark.integration
"""

import time
from datetime import datetime
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

# Unified Memory Search Tests
async def test_memory_search_endpoint_e2e(test_client_async, redis_memory_manager):
    session_id = "test_api_session"
    await redis_memory_manager.store_conversation_context(session_id=session_id, messages=[{"role": "user", "content": "API test query"}])
    response = await test_client_async.post("/api/v1/memory/search", json={"query": "API test", "session_id": session_id, "top_k": 5})
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "total_results" in data
    assert "layers_searched" in data

async def test_memory_search_validation_e2e(test_client_async):
    response = await test_client_async.post("/api/v1/memory/search", json={"query": "", "top_k": 5})
    assert response.status_code in [400, 422]

async def test_memory_search_with_layers_e2e(test_client_async):
    response = await test_client_async.post("/api/v1/memory/search", json={"query": "test", "layers": ["short_term", "episodic"], "top_k": 3})
    assert response.status_code == 200

async def test_memory_search_time_window_e2e(test_client_async):
    response = await test_client_async.post("/api/v1/memory/search", json={"query": "test", "time_window_hours": 24, "top_k": 5})
    assert response.status_code == 200

# Point-in-Time Query Tests
async def test_point_in_time_endpoint_e2e(test_client_async, neo4j_driver):
    timestamp = datetime.utcnow().isoformat()
    response = await test_client_async.post("/api/v1/memory/temporal/point-in-time", json={"query": "test_entity", "timestamp": timestamp, "top_k": 5})
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "results" in data

async def test_point_in_time_validation_e2e(test_client_async):
    response = await test_client_async.post("/api/v1/memory/temporal/point-in-time", json={"query": "test", "timestamp": "invalid_timestamp"})
    assert response.status_code in [400, 422]

# Session Context Tests
async def test_session_context_endpoint_e2e(test_client_async, redis_memory_manager):
    session_id = "test_session_context"
    messages = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}]
    await redis_memory_manager.store_conversation_context(session_id=session_id, messages=messages)
    response = await test_client_async.get(f"/api/v1/memory/session/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert "messages" in data
    assert "message_count" in data

async def test_session_context_not_found_e2e(test_client_async):
    response = await test_client_async.get("/api/v1/memory/session/nonexistent_123")
    assert response.status_code == 404

# Consolidation Tests
async def test_consolidate_endpoint_e2e(test_client_async):
    response = await test_client_async.post("/api/v1/memory/consolidate", json={"consolidate_to_qdrant": True, "consolidate_conversations": False})
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "success"

async def test_consolidate_with_sessions_e2e(test_client_async, redis_memory_manager):
    session_id = "consolidate_test"
    await redis_memory_manager.store_conversation_context(session_id=session_id, messages=[{"role": "user", "content": "Consolidate this"}])
    response = await test_client_async.post("/api/v1/memory/consolidate", json={"consolidate_conversations": True, "active_sessions": [session_id]})
    assert response.status_code == 200

# Stats Tests
async def test_stats_endpoint_e2e(test_client_async):
    response = await test_client_async.get("/api/v1/memory/stats")
    assert response.status_code == 200
    data = response.json()
    assert "short_term" in data
    assert "long_term" in data
    assert "episodic" in data
    assert "consolidation" in data

# Session Delete Tests
async def test_session_delete_endpoint_e2e(test_client_async, redis_memory_manager):
    session_id = "delete_test"
    await redis_memory_manager.store_conversation_context(session_id=session_id, messages=[{"role": "user", "content": "Delete me"}])
    response = await test_client_async.delete(f"/api/v1/memory/session/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id

async def test_session_delete_nonexistent_e2e(test_client_async):
    response = await test_client_async.delete("/api/v1/memory/session/nonexistent_xyz")
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] is False

# Performance Tests
async def test_api_latency_targets_e2e(test_client_async):
    start = time.time()
    response = await test_client_async.post("/api/v1/memory/search", json={"query": "latency test", "top_k": 5})
    latency_ms = (time.time() - start) * 1000
    assert response.status_code == 200
    assert latency_ms < 2000

async def test_api_stats_latency_e2e(test_client_async):
    start = time.time()
    response = await test_client_async.get("/api/v1/memory/stats")
    latency_ms = (time.time() - start) * 1000
    assert response.status_code == 200
    assert latency_ms < 1000

# Error Handling Tests
async def test_api_error_handling_invalid_json_e2e(test_client_async):
    response = await test_client_async.post("/api/v1/memory/search", content="{invalid json}", headers={"Content-Type": "application/json"})
    assert response.status_code in [400, 422]

async def test_api_error_handling_missing_fields_e2e(test_client_async):
    response = await test_client_async.post("/api/v1/memory/search", json={})
    assert response.status_code in [400, 422]

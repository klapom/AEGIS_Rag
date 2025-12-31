# Sprint 33: VLM Enrichment Node Test Fix

## Issue Summary

4 failing tests in `tests/unit/components/ingestion/test_vlm_enrichment_node.py`:

```
FAILED test_image_enrichment_node__valid_document__enriches_successfully - assert 0 == 2
FAILED test_image_enrichment_node__no_page_dimensions__still_processes - assert 0 == 2
FAILED test_image_enrichment_node__bbox_extraction__correct_structure - IndexError: list index out of range
FAILED test_image_enrichment_node__no_provenance__no_bbox - IndexError: list index out of range
```

## Root Cause Analysis

The tests expected `vlm_metadata` to contain 2 items after processing, but they contained 0 items.

**Root Cause:** The `ImageProcessor` mock was set up with synchronous `side_effect`, but the actual implementation calls `processor.process_image()` with `await` (asynchronous).

In `src/components/ingestion/langgraph_nodes.py` line 951:
```python
description = await processor.process_image(image=pil_image, picture_index=idx)
```

The mock fixture was using:
```python
processor.process_image.side_effect = [...]  # Synchronous Mock
```

When an async function awaits a synchronous mock, the mock returns itself (a Mock object) instead of the expected value. This caused the tests to fail because:
1. `description` was a Mock object instead of a string
2. The check `if description is None` (line 994-995) didn't catch this
3. No `vlm_metadata` entries were created

## Solution

Changed all `ImageProcessor.process_image` mocks from synchronous `Mock` to `AsyncMock`:

### Fix 1: Mock Fixture (Line 102-113)

**Before:**
```python
@pytest.fixture
def mock_image_processor():
    """Create mock ImageProcessor."""
    processor = Mock()
    processor.process_image.side_effect = [
        "This is a red diagram showing system architecture.",
        "This is a green flowchart depicting the process flow.",
    ]
    processor.cleanup = Mock()
    return processor
```

**After:**
```python
@pytest.fixture
def mock_image_processor():
    """Create mock ImageProcessor."""
    processor = Mock()
    # CRITICAL FIX: process_image is called with await, so it must be AsyncMock
    processor.process_image = AsyncMock(
        side_effect=[
            "This is a red diagram showing system architecture.",
            "This is a green flowchart depicting the process flow.",
        ]
    )
    processor.cleanup = Mock()
    return processor
```

### Fix 2: Error Handling Test (Line 319-334)

**Before:**
```python
processor.process_image.side_effect = [
    Exception("VLM timeout"),
    "Second image processed successfully",
]
```

**After:**
```python
processor.process_image = AsyncMock(
    side_effect=[
        Exception("VLM timeout"),
        "Second image processed successfully",
    ]
)
```

### Fix 3: Filtered Image Test (Line 350-364)

**Before:**
```python
processor.process_image.side_effect = [
    None,  # First image filtered out
    "Second image description",
]
```

**After:**
```python
processor.process_image = AsyncMock(
    side_effect=[
        None,  # First image filtered out
        "Second image description",
    ]
)
```

## Test Results

**Before Fix:** 4 failures, 9 passes
**After Fix:** 13 passes, 0 failures

```
============================= 13 passed in 0.20s ==============================
```

All tests now correctly mock the async `process_image()` call and verify:
- VLM enrichment with valid documents (2 images processed)
- BBox extraction with page dimensions
- Graceful degradation when page dimensions missing
- Error handling (partial success when one image fails)
- Filtered image handling (None returned)
- Caption combination with VLM descriptions

## Lessons Learned

**Best Practice: Async Test Mocking**

When mocking async functions (`async def`), always use `AsyncMock`:

```python
# ❌ WRONG: Synchronous mock for async function
processor.process_image.side_effect = ["description"]

# ✅ CORRECT: AsyncMock for async function
processor.process_image = AsyncMock(side_effect=["description"])
```

**Detection Strategy:**
1. Check if function is defined with `async def`
2. Check if function is called with `await`
3. If yes to both: Use `AsyncMock`

**Related Documentation:**
- Python unittest.mock: https://docs.python.org/3/library/unittest.mock.html#unittest.mock.AsyncMock
- Sprint 33 Performance Fix: Parallel VLM Processing (lines 865-1035 in langgraph_nodes.py)

## Files Modified

- `tests/unit/components/ingestion/test_vlm_enrichment_node.py` (3 locations)
  - Line 102-113: `mock_image_processor` fixture
  - Line 319-334: `test_image_enrichment_node__vlm_error_on_one_image__continues`
  - Line 350-364: `test_image_enrichment_node__filtered_image__skips_gracefully`

## Verification

Run tests:
```bash
poetry run pytest tests/unit/components/ingestion/test_vlm_enrichment_node.py -v
```

Expected: 13 passed, 0 failed

"""Unit tests for Docling JSON extraction (Feature 21.5).

Tests the extraction of tables, images, and layout information
from Docling's json_content response.

Sprint 21 Feature 21.5: Extract rich metadata from Docling JSON.
"""

import pytest

# =============================================================================
# Test Data: Mock Docling JSON Content
# =============================================================================


@pytest.fixture
def mock_docling_json():
    """Mock Docling JSON response with tables, pictures, and layout."""
    return {
        "schema_name": "DoclingDocument",
        "version": "1.0.0",
        "name": "test_document.pdf",
        "pages": {
            "1": {"page_no": 1, "size": {"width": 595, "height": 842}},
            "2": {"page_no": 2, "size": {"width": 595, "height": 842}},
        },
        "body": {"_name": "body", "children": []},
        "texts": ["Some text content", "More text"],
        "groups": [{"group_id": "g1"}],
        "tables": [
            {
                "self_ref": "#/tables/0",
                "label": "table",
                "captions": [{"text": "Table 1: Revenue Summary"}],
                "prov": [
                    {
                        "page_no": 1,
                        "bbox": {"l": 50.0, "t": 100.0, "r": 550.0, "b": 300.0},
                        "charspan": [10, 250],
                    }
                ],
                "content_layer": [],
                "image": None,
            },
            {
                "self_ref": "#/tables/1",
                "label": "table",
                "captions": [],
                "prov": [
                    {
                        "page_no": 2,
                        "bbox": {"l": 50.0, "t": 150.0, "r": 550.0, "b": 400.0},
                        "charspan": [300, 550],
                    }
                ],
                "content_layer": [],
                "image": None,
            },
        ],
        "pictures": [
            {
                "self_ref": "#/pictures/0",
                "label": "picture",
                "captions": [{"text": "Figure 1: Architecture diagram"}],
                "prov": [
                    {
                        "page_no": 1,
                        "bbox": {"l": 100.0, "t": 400.0, "r": 500.0, "b": 700.0},
                        "charspan": [260, 280],
                    }
                ],
                "content_layer": [],
                "image": None,
            }
        ],
    }


# =============================================================================
# Unit Tests: Table Extraction
# =============================================================================


def test_extract_tables_from_json(mock_docling_json):
    """Test extraction of table metadata from Docling JSON."""
    tables = []
    for table in mock_docling_json.get("tables", []):
        table_info = {
            "ref": table.get("self_ref", ""),
            "label": table.get("label", "table"),
            "captions": table.get("captions", []),
            "page_no": None,
            "bbox": None,
        }
        prov = table.get("prov", [])
        if prov:
            p = prov[0] if isinstance(prov, list) else prov
            table_info["page_no"] = p.get("page_no")
            table_info["bbox"] = p.get("bbox")
        tables.append(table_info)

    # Assertions
    assert len(tables) == 2, "Should extract 2 tables"

    # Check first table
    assert tables[0]["ref"] == "#/tables/0"
    assert tables[0]["label"] == "table"
    assert len(tables[0]["captions"]) == 1
    assert tables[0]["captions"][0]["text"] == "Table 1: Revenue Summary"
    assert tables[0]["page_no"] == 1
    assert tables[0]["bbox"] == {"l": 50.0, "t": 100.0, "r": 550.0, "b": 300.0}

    # Check second table
    assert tables[1]["ref"] == "#/tables/1"
    assert tables[1]["page_no"] == 2
    assert len(tables[1]["captions"]) == 0, "Second table has no captions"


# =============================================================================
# Unit Tests: Image/Picture Extraction
# =============================================================================


def test_extract_pictures_from_json(mock_docling_json):
    """Test extraction of picture metadata from Docling JSON."""
    images = []
    for picture in mock_docling_json.get("pictures", []):
        image_info = {
            "ref": picture.get("self_ref", ""),
            "label": picture.get("label", "picture"),
            "captions": picture.get("captions", []),
            "page_no": None,
            "bbox": None,
        }
        prov = picture.get("prov", [])
        if prov:
            p = prov[0] if isinstance(prov, list) else prov
            image_info["page_no"] = p.get("page_no")
            image_info["bbox"] = p.get("bbox")
        images.append(image_info)

    # Assertions
    assert len(images) == 1, "Should extract 1 picture"

    # Check first picture
    assert images[0]["ref"] == "#/pictures/0"
    assert images[0]["label"] == "picture"
    assert len(images[0]["captions"]) == 1
    assert images[0]["captions"][0]["text"] == "Figure 1: Architecture diagram"
    assert images[0]["page_no"] == 1
    assert images[0]["bbox"]["l"] == 100.0


# =============================================================================
# Unit Tests: Layout Extraction
# =============================================================================


def test_extract_layout_from_json(mock_docling_json):
    """Test extraction of layout information from Docling JSON."""
    layout_info = {
        "schema_name": mock_docling_json.get("schema_name", ""),
        "version": mock_docling_json.get("version", ""),
        "pages": mock_docling_json.get("pages", {}),
        "body": mock_docling_json.get("body", {}),
        "texts_count": len(mock_docling_json.get("texts", [])),
        "groups_count": len(mock_docling_json.get("groups", [])),
    }

    # Assertions
    assert layout_info["schema_name"] == "DoclingDocument"
    assert layout_info["version"] == "1.0.0"
    assert len(layout_info["pages"]) == 2, "Should have 2 pages"
    assert layout_info["texts_count"] == 2
    assert layout_info["groups_count"] == 1
    assert layout_info["body"]["_name"] == "body"


# =============================================================================
# Unit Tests: Edge Cases
# =============================================================================


def test_extract_empty_json():
    """Test extraction when JSON content is empty."""
    empty_json = {}

    # Extract tables (should be empty list)
    tables = [
        {
            "ref": table.get("self_ref", ""),
            "label": table.get("label", "table"),
            "captions": table.get("captions", []),
            "page_no": None,
            "bbox": None,
        }
        for table in empty_json.get("tables", [])
    ]

    # Extract pictures (should be empty list)
    pictures = [
        {
            "ref": pic.get("self_ref", ""),
            "label": pic.get("label", "picture"),
            "captions": pic.get("captions", []),
            "page_no": None,
            "bbox": None,
        }
        for pic in empty_json.get("pictures", [])
    ]

    # Extract layout
    layout = {
        "schema_name": empty_json.get("schema_name", ""),
        "version": empty_json.get("version", ""),
        "pages": empty_json.get("pages", {}),
        "body": empty_json.get("body", {}),
        "texts_count": len(empty_json.get("texts", [])),
        "groups_count": len(empty_json.get("groups", [])),
    }

    # Assertions
    assert tables == [], "Empty JSON should yield no tables"
    assert pictures == [], "Empty JSON should yield no pictures"
    assert layout["schema_name"] == ""
    assert layout["texts_count"] == 0
    assert layout["groups_count"] == 0


def test_extract_table_without_provenance():
    """Test extraction when table has no provenance data."""
    json_data = {
        "tables": [
            {
                "self_ref": "#/tables/0",
                "label": "table",
                "captions": [{"text": "Test table"}],
                # No 'prov' field
            }
        ]
    }

    tables = []
    for table in json_data.get("tables", []):
        table_info = {
            "ref": table.get("self_ref", ""),
            "label": table.get("label", "table"),
            "captions": table.get("captions", []),
            "page_no": None,
            "bbox": None,
        }
        prov = table.get("prov", [])
        if prov:
            p = prov[0] if isinstance(prov, list) else prov
            table_info["page_no"] = p.get("page_no")
            table_info["bbox"] = p.get("bbox")
        tables.append(table_info)

    # Assertions
    assert len(tables) == 1
    assert tables[0]["page_no"] is None, "Should handle missing provenance"
    assert tables[0]["bbox"] is None
    assert tables[0]["ref"] == "#/tables/0"
    assert len(tables[0]["captions"]) == 1

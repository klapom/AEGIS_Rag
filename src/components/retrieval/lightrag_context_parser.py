"""LightRAG Context Parser - Extract structured entities from LightRAG context strings.

Sprint 51 - Feature 51.7: Maximum Hybrid Search Foundation

This module parses LightRAG's context output (local/global modes) into structured entities
for cross-modal fusion with chunk-based retrieval.

LightRAG Context Format:
    Local mode returns: "# Entities\n- Entity1: description\n- Entity2: description\n\n# Relationships\n..."
    Global mode returns: "# Communities\n## Community 1\n- Theme: ...\n- Entities: ...\n\n"

Output Format:
    - Entities: list of {"name": str, "description": str, "type": str, "score": float}
    - Communities: list of {"id": str, "theme": str, "entities": list[str]}
"""

import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def parse_lightrag_local_context(context: str) -> dict[str, Any]:
    """Parse LightRAG local mode context into structured entities.

    Local mode provides entity-level information with facts and relationships.

    Args:
        context: Raw context string from LightRAG local mode

    Returns:
        Dictionary with:
        - entities: list of entity dicts (name, description, type, score)
        - relationships: list of relationship dicts (source, target, description)

    Example:
        >>> context = "# Entities\\n- Amsterdam: Capital city of Netherlands\\n- Netherlands: Country in Europe"
        >>> result = parse_lightrag_local_context(context)
        >>> result["entities"][0]["name"]
        'Amsterdam'
    """
    result = {
        "entities": [],
        "relationships": [],
    }

    if not context or not context.strip():
        logger.debug("parse_lightrag_local_empty", context_length=len(context))
        return result

    try:
        # Split by major sections (# Entities, # Relationships)
        sections = re.split(r"\n#\s+", context)

        for section in sections:
            section_lines = section.strip().split("\n")
            if not section_lines:
                continue

            section_title = section_lines[0].strip().lower()

            # Parse Entities section
            if "entit" in section_title:
                for line in section_lines[1:]:
                    line = line.strip()
                    if not line or not line.startswith("-"):
                        continue

                    # Format: "- EntityName: Description"
                    match = re.match(r"-\s*([^:]+):\s*(.+)", line)
                    if match:
                        entity_name = match.group(1).strip()
                        description = match.group(2).strip()

                        # Infer entity type from description (simple heuristic)
                        entity_type = _infer_entity_type(entity_name, description)

                        result["entities"].append(
                            {
                                "name": entity_name,
                                "description": description,
                                "type": entity_type,
                                "score": 1.0,  # LightRAG doesn't provide scores
                                "source": "lightrag_local",
                            }
                        )

            # Parse Relationships section
            elif "relation" in section_title:
                for line in section_lines[1:]:
                    line = line.strip()
                    if not line or not line.startswith("-"):
                        continue

                    # Format: "- Entity1 -> Entity2: Description"
                    match = re.match(r"-\s*([^-]+)->([^:]+):\s*(.+)", line)
                    if match:
                        source_entity = match.group(1).strip()
                        target_entity = match.group(2).strip()
                        description = match.group(3).strip()

                        result["relationships"].append(
                            {
                                "source": source_entity,
                                "target": target_entity,
                                "description": description,
                                "type": "RELATED_TO",
                                "origin": "lightrag_local",  # Changed key name to avoid conflict
                            }
                        )

        logger.debug(
            "parse_lightrag_local_complete",
            entities_found=len(result["entities"]),
            relationships_found=len(result["relationships"]),
            context_length=len(context),
        )

    except Exception as e:
        logger.warning(
            "parse_lightrag_local_failed",
            error=str(e),
            context_preview=context[:200] if context else "",
        )

    return result


def parse_lightrag_global_context(context: str) -> dict[str, Any]:
    """Parse LightRAG global mode context into structured communities.

    Global mode provides community/theme-level information with entity clusters.

    Args:
        context: Raw context string from LightRAG global mode

    Returns:
        Dictionary with:
        - communities: list of community dicts (id, theme, entities, description)
        - entities: list of entity names mentioned (for cross-modal fusion)

    Example:
        >>> context = "## Community 1\\n- Theme: European Geography\\n- Entities: Amsterdam, Netherlands"
        >>> result = parse_lightrag_global_context(context)
        >>> result["communities"][0]["theme"]
        'European Geography'
    """
    result = {
        "communities": [],
        "entities": [],  # Flat list for cross-modal fusion
    }

    if not context or not context.strip():
        logger.debug("parse_lightrag_global_empty", context_length=len(context))
        return result

    try:
        # Split by community sections (## Community N)
        # Use positive lookahead to keep the delimiter
        parts = re.split(r"(##\s+Community\s+\d+)", context)

        current_community_header = None
        current_community_content = []

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check if this is a community header
            header_match = re.match(r"##\s+Community\s+(\d+)", part)
            if header_match:
                # Save previous community if exists
                if current_community_header is not None and current_community_content:
                    _parse_community_content(
                        result, current_community_header, "\n".join(current_community_content)
                    )

                # Start new community
                current_community_header = header_match.group(1)
                current_community_content = []
            else:
                # This is content for the current community
                if current_community_header is not None:
                    current_community_content.append(part)

        # Don't forget the last community
        if current_community_header is not None and current_community_content:
            _parse_community_content(
                result, current_community_header, "\n".join(current_community_content)
            )

        logger.debug(
            "parse_lightrag_global_complete",
            communities_found=len(result["communities"]),
            total_entities=len(result["entities"]),
            context_length=len(context),
        )

    except Exception as e:
        logger.warning(
            "parse_lightrag_global_failed",
            error=str(e),
            context_preview=context[:200] if context else "",
        )

    return result


def _parse_community_content(result: dict[str, Any], community_id: str, content: str) -> None:
    """Parse community content and add to result.

    Args:
        result: Result dictionary to add community to
        community_id: Community ID (number as string)
        content: Community content string with key-value pairs
    """
    community_data = {
        "id": f"community_{community_id}",
        "theme": "",
        "entities": [],
        "description": "",
    }

    # Parse community content line by line
    for line in content.split("\n"):
        line = line.strip()
        if not line or not line.startswith("-"):
            continue

        # Format: "- Key: Value"
        match = re.match(r"-\s*([^:]+):\s*(.+)", line)
        if match:
            key = match.group(1).strip().lower()
            value = match.group(2).strip()

            if "theme" in key or "topic" in key:
                community_data["theme"] = value
            elif "entit" in key:
                # Parse comma-separated entity list
                entities = [e.strip() for e in value.split(",")]
                community_data["entities"] = entities
                result["entities"].extend(entities)
            elif "description" in key or "summary" in key:
                community_data["description"] = value

    result["communities"].append(community_data)


def _infer_entity_type(entity_name: str, description: str) -> str:
    """Infer entity type from name and description using heuristics.

    Args:
        entity_name: Entity name
        description: Entity description

    Returns:
        Entity type (ORGANIZATION, PERSON, LOCATION, TECHNOLOGY, CONCEPT)
    """
    desc_lower = description.lower()

    # Location indicators
    if any(kw in desc_lower for kw in ["city", "country", "capital", "region", "province"]):
        return "LOCATION"

    # Person indicators
    if any(kw in desc_lower for kw in ["ceo", "founder", "director", "manager", "developer"]):
        return "PERSON"

    # Organization indicators
    if any(kw in desc_lower for kw in ["company", "organization", "corporation", "startup"]):
        return "ORGANIZATION"

    # Technology indicators
    if any(kw in desc_lower for kw in ["framework", "library", "database", "system", "platform"]):
        return "TECHNOLOGY"

    # Concept indicators
    if any(kw in desc_lower for kw in ["concept", "method", "algorithm", "technique", "approach"]):
        return "CONCEPT"

    # Default fallback
    return "ENTITY"


def extract_entity_names(parsed_result: dict[str, Any]) -> list[str]:
    """Extract all entity names from parsed LightRAG result.

    This is a convenience function for cross-modal fusion that returns
    a flat list of entity names from both local and global parsing results.

    Args:
        parsed_result: Result from parse_lightrag_local_context or parse_lightrag_global_context

    Returns:
        List of entity names (deduplicated)
    """
    entity_names = set()

    # Extract from entities list (local mode)
    for entity in parsed_result.get("entities", []):
        if "name" in entity:
            entity_names.add(entity["name"])

    # Extract from communities list (global mode)
    for community in parsed_result.get("communities", []):
        entity_names.update(community.get("entities", []))

    return sorted(entity_names)

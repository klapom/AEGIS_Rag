"""Version Manager for Graph Entity Versioning.

This module manages entity versions with bi-temporal model support.
Implements version retention, comparison, and rollback functionality.
"""

import uuid
from datetime import datetime
from typing import Any

import structlog

from src.components.graph_rag.neo4j_client import Neo4jClient, get_neo4j_client
from src.core.config import settings

logger = structlog.get_logger(__name__)


class VersionManager:
    """Manages entity versions with bi-temporal tracking."""

    def __init__(
        self,
        neo4j_client: Neo4jClient | None = None,
        retention_count: int | None = None,
    ):
        """Initialize version manager.

        Args:
            neo4j_client: Neo4j client instance (default: from singleton)
            retention_count: Max versions to retain per entity (default: from settings)
        """
        self.client = neo4j_client or get_neo4j_client()
        # Use 'is not None' instead of 'or' to allow retention_count=0
        self.retention_count = (
            retention_count
            if retention_count is not None
            else getattr(settings, "graph_version_retention_count", 10)
        )
        logger.info("Initialized VersionManager", retention_count=self.retention_count)

    async def create_version(
        self,
        entity: dict[str, Any],
        changed_by: str = "system",
        change_reason: str = "",
    ) -> dict[str, Any]:
        """Create new version of an entity.

        Closes the current version (sets valid_to and transaction_to) and creates
        a new version with incremented version_number.

        Args:
            entity: Entity data (must include 'id' or 'name')
            changed_by: User/system that made the change
            change_reason: Reason for the change

        Returns:
            New version data with version metadata

        Raises:
            ValueError: If entity missing required fields
        """
        entity_id = entity.get("id") or entity.get("name")
        if not entity_id:
            raise ValueError("Entity must have 'id' or 'name' field")

        now = datetime.utcnow()
        now_iso = now.isoformat()

        # Get current version
        current_versions = await self.get_versions(entity_id, limit=1)
        current_version_number = 0
        if current_versions:
            current_version_number = current_versions[0].get("version_number", 0)

        # Close current version
        close_query = """
        MATCH (e:Entity {id: $entity_id})
        WHERE e.valid_to IS NULL
        SET e.valid_to = datetime($now),
            e.transaction_to = datetime($now)
        RETURN count(e) as closed_count
        """
        close_result = await self.client.execute_write(
            close_query, {"entity_id": entity_id, "now": now_iso}
        )

        # Create new version
        new_version_id = str(uuid.uuid4())
        new_version_number = current_version_number + 1

        # Prepare entity properties
        properties = entity.copy()
        properties.update(
            {
                "version_id": new_version_id,
                "version_number": new_version_number,
                "valid_from": now_iso,
                "valid_to": None,
                "transaction_from": now_iso,
                "transaction_to": None,
                "changed_by": changed_by,
                "change_reason": change_reason,
            }
        )

        # Build property assignments for Cypher
        prop_assignments = []
        params = {"entity_id": entity_id}
        for key, value in properties.items():
            if key not in ["id", "name"]:  # Don't set id/name in SET clause
                param_key = f"prop_{key}"
                params[param_key] = value
                if value is None:
                    prop_assignments.append(f"e.{key} = null")
                else:
                    prop_assignments.append(f"e.{key} = ${param_key}")

        create_query = f"""
        CREATE (e:Entity {{id: $entity_id}})
        SET {', '.join(prop_assignments)}
        RETURN e
        """

        await self.client.execute_write(create_query, params)

        # Enforce retention policy
        await self._enforce_retention(entity_id)

        logger.info(
            "Created entity version",
            entity_id=entity_id,
            version_number=new_version_number,
            version_id=new_version_id,
            changed_by=changed_by,
            closed_count=close_result.get("nodes_deleted", 0),
        )

        return properties

    async def get_versions(
        self,
        entity_id: str,
        limit: int | None = None,
        include_deleted: bool = False,
    ) -> list[dict[str, Any]]:
        """Get all versions of an entity.

        Args:
            entity_id: Entity ID
            limit: Maximum versions to return (default: all)
            include_deleted: Include soft-deleted versions

        Returns:
            List of version records ordered by version_number descending
        """
        query = """
        MATCH (e:Entity {id: $entity_id})
        """

        if not include_deleted:
            query += "\nWHERE e.transaction_to IS NULL OR e.transaction_to >= datetime()"

        query += """
        RETURN e
        ORDER BY e.version_number DESC
        """

        if limit:
            query += f"\nLIMIT {limit}"

        results = await self.client.execute_read(query, {"entity_id": entity_id})

        versions = []
        for record in results:
            entity_data = dict(record["e"])
            # Convert datetime objects to ISO strings
            for key in ["valid_from", "valid_to", "transaction_from", "transaction_to"]:
                if key in entity_data and entity_data[key] and hasattr(entity_data[key], "isoformat"):
                    entity_data[key] = entity_data[key].isoformat()
            versions.append(entity_data)

        logger.debug("Retrieved versions", entity_id=entity_id, count=len(versions))
        return versions

    async def get_version_at(
        self,
        entity_id: str,
        timestamp: datetime,
    ) -> dict[str, Any] | None:
        """Get specific version of entity at a given timestamp.

        Args:
            entity_id: Entity ID
            timestamp: Point in time to query

        Returns:
            Version data at timestamp or None if not found
        """
        query = """
        MATCH (e:Entity {id: $entity_id})
        WHERE e.valid_from <= datetime($timestamp)
          AND (e.valid_to IS NULL OR e.valid_to > datetime($timestamp))
          AND e.transaction_from <= datetime($timestamp)
          AND (e.transaction_to IS NULL OR e.transaction_to > datetime($timestamp))
        RETURN e
        ORDER BY e.version_number DESC
        LIMIT 1
        """

        results = await self.client.execute_read(
            query, {"entity_id": entity_id, "timestamp": timestamp.isoformat()}
        )

        if results:
            entity_data = dict(results[0]["e"])
            # Convert datetime objects
            for key in ["valid_from", "valid_to", "transaction_from", "transaction_to"]:
                if key in entity_data and entity_data[key] and hasattr(entity_data[key], "isoformat"):
                    entity_data[key] = entity_data[key].isoformat()

            logger.debug(
                "Retrieved version at timestamp",
                entity_id=entity_id,
                timestamp=timestamp.isoformat(),
                version_number=entity_data.get("version_number"),
            )
            return entity_data

        logger.debug("No version found at timestamp", entity_id=entity_id, timestamp=timestamp)
        return None

    async def compare_versions(
        self,
        entity_id: str,
        version1: int,
        version2: int,
    ) -> dict[str, Any]:
        """Compare two versions of an entity.

        Args:
            entity_id: Entity ID
            version1: First version number
            version2: Second version number

        Returns:
            Comparison result with changed fields and differences
        """
        query = """
        MATCH (e:Entity {id: $entity_id})
        WHERE e.version_number IN [$version1, $version2]
        RETURN e
        ORDER BY e.version_number
        """

        results = await self.client.execute_read(
            query, {"entity_id": entity_id, "version1": version1, "version2": version2}
        )

        if len(results) < 2:
            logger.warning(
                "Cannot compare - insufficient versions found",
                entity_id=entity_id,
                found=len(results),
            )
            return {
                "entity_id": entity_id,
                "version1": version1,
                "version2": version2,
                "changed_fields": [],
                "error": "Insufficient versions found for comparison",
            }

        v1_data = dict(results[0]["e"])
        v2_data = dict(results[1]["e"])

        # Compare fields
        changed_fields = []
        differences = {}

        all_keys = set(v1_data.keys()) | set(v2_data.keys())
        ignore_keys = {
            "version_id",
            "version_number",
            "valid_from",
            "valid_to",
            "transaction_from",
            "transaction_to",
            "changed_by",
            "change_reason",
        }

        for key in all_keys:
            if key in ignore_keys:
                continue

            v1_value = v1_data.get(key)
            v2_value = v2_data.get(key)

            if v1_value != v2_value:
                changed_fields.append(key)
                differences[key] = {"from": v1_value, "to": v2_value}

        result = {
            "entity_id": entity_id,
            "version1": version1,
            "version2": version2,
            "changed_fields": changed_fields,
            "differences": differences,
            "change_count": len(changed_fields),
        }

        logger.debug("Compared versions", entity_id=entity_id, changes=len(changed_fields))
        return result

    async def get_evolution(self, entity_id: str) -> dict[str, Any]:
        """Get change timeline for an entity.

        Args:
            entity_id: Entity ID

        Returns:
            Evolution timeline with version history
        """
        versions = await self.get_versions(entity_id)

        if not versions:
            return {
                "entity_id": entity_id,
                "version_count": 0,
                "timeline": [],
                "first_seen": None,
                "last_updated": None,
            }

        timeline = []
        for i, version in enumerate(reversed(versions)):  # Oldest to newest
            entry = {
                "version_number": version.get("version_number"),
                "version_id": version.get("version_id"),
                "valid_from": version.get("valid_from"),
                "valid_to": version.get("valid_to"),
                "changed_by": version.get("changed_by"),
                "change_reason": version.get("change_reason"),
            }

            # Add changes if not first version
            if i > 0:
                prev_version = versions[len(versions) - i]
                curr_version = version
                changes = []

                all_keys = set(prev_version.keys()) | set(curr_version.keys())
                ignore_keys = {
                    "version_id",
                    "version_number",
                    "valid_from",
                    "valid_to",
                    "transaction_from",
                    "transaction_to",
                    "changed_by",
                    "change_reason",
                }

                for key in all_keys:
                    if key in ignore_keys:
                        continue
                    if prev_version.get(key) != curr_version.get(key):
                        changes.append(
                            {
                                "field": key,
                                "old_value": prev_version.get(key),
                                "new_value": curr_version.get(key),
                            }
                        )

                entry["changes"] = changes

            timeline.append(entry)

        result = {
            "entity_id": entity_id,
            "version_count": len(versions),
            "timeline": timeline,
            "first_seen": versions[-1].get("valid_from") if versions else None,
            "last_updated": versions[0].get("valid_from") if versions else None,
        }

        logger.debug("Retrieved evolution", entity_id=entity_id, versions=len(versions))
        return result

    async def revert_to_version(
        self,
        entity_id: str,
        version_id: str,
        changed_by: str = "system",
        change_reason: str = "Reverted to previous version",
    ) -> dict[str, Any]:
        """Revert entity to a previous version.

        Creates a new version with the data from the specified version.

        Args:
            entity_id: Entity ID
            version_id: Version ID to revert to
            changed_by: User/system performing revert
            change_reason: Reason for revert

        Returns:
            New version data after revert
        """
        # Get target version
        query = """
        MATCH (e:Entity {id: $entity_id, version_id: $version_id})
        RETURN e
        """

        results = await self.client.execute_read(
            query, {"entity_id": entity_id, "version_id": version_id}
        )

        if not results:
            raise ValueError(f"Version {version_id} not found for entity {entity_id}")

        target_version = dict(results[0]["e"])

        # Remove temporal and version metadata
        entity_data = {
            k: v
            for k, v in target_version.items()
            if k
            not in {
                "version_id",
                "version_number",
                "valid_from",
                "valid_to",
                "transaction_from",
                "transaction_to",
                "changed_by",
                "change_reason",
            }
        }

        # Create new version with reverted data
        new_version = await self.create_version(
            entity_data,
            changed_by=changed_by,
            change_reason=f"{change_reason} (reverted to version {version_id})",
        )

        logger.info(
            "Reverted to version",
            entity_id=entity_id,
            target_version_id=version_id,
            new_version_id=new_version["version_id"],
        )

        return new_version

    async def _enforce_retention(self, entity_id: str) -> int:
        """Enforce version retention policy.

        Soft-deletes old versions beyond retention limit by setting transaction_to.

        Args:
            entity_id: Entity ID

        Returns:
            Number of versions deleted
        """
        if self.retention_count <= 0:
            return 0  # No retention limit

        now_iso = datetime.utcnow().isoformat()

        # Soft delete versions beyond retention limit
        query = """
        MATCH (e:Entity {id: $entity_id})
        WHERE e.transaction_to IS NULL
        WITH e
        ORDER BY e.version_number DESC
        SKIP $retention_count
        SET e.transaction_to = datetime($now)
        RETURN count(e) as deleted_count
        """

        result = await self.client.execute_write(
            query,
            {
                "entity_id": entity_id,
                "retention_count": self.retention_count,
                "now": now_iso,
            },
        )

        deleted = result.get("properties_set", 0)
        if deleted > 0:
            logger.info(
                "Enforced retention policy",
                entity_id=entity_id,
                deleted_versions=deleted,
                retention_limit=self.retention_count,
            )

        return deleted


# Singleton instance
_version_manager: VersionManager | None = None


def get_version_manager() -> VersionManager:
    """Get global version manager instance (singleton).

    Returns:
        VersionManager instance
    """
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionManager()
    return _version_manager

// Neo4j Temporal Indexes for Bi-Temporal Queries
// Sprint 39 Feature 39.1: Temporal Indexes & Feature Flag
// ADR-042: Bi-Temporal Opt-In Strategy
//
// These indexes are REQUIRED when temporal_queries_enabled = true
// Run this script via Neo4j Browser or cypher-shell:
//   cat neo4j_temporal_indexes.cypher | cypher-shell -u neo4j -p password

// Composite Index for Temporal Queries (valid_from, valid_to)
// Enables efficient point-in-time queries: "Show entities as of timestamp X"
CREATE INDEX temporal_validity_idx IF NOT EXISTS
FOR (e:base) ON (e.valid_from, e.valid_to);

// Composite Index for Transaction Time (transaction_from, transaction_to)
// Enables queries: "What was recorded in the database at timestamp X?"
CREATE INDEX temporal_transaction_idx IF NOT EXISTS
FOR (e:base) ON (e.transaction_from, e.transaction_to);

// Partial Index for Current Versions (Performance Optimization)
// Most queries fetch current version (valid_to IS NULL)
// This index dramatically speeds up "current only" queries
CREATE INDEX current_version_idx IF NOT EXISTS
FOR (e:base) ON (e.valid_to)
WHERE e.valid_to IS NULL;

// Index for Audit Trail (changed_by field)
// Enables queries: "Show all changes by user X"
// Sprint 38 JWT Auth integration - changed_by populated from JWT
CREATE INDEX changed_by_idx IF NOT EXISTS
FOR (e:base) ON (e.changed_by);

// Index for Version Numbers
// Enables fast version lookups and ordering
CREATE INDEX version_number_idx IF NOT EXISTS
FOR (e:base) ON (e.version_number);

// Index for Version IDs
// Enables fast version_id lookups for rollback operations
CREATE INDEX version_id_idx IF NOT EXISTS
FOR (e:base) ON (e.version_id);

// Verify indexes were created
SHOW INDEXES YIELD name, type, state, populationPercent
WHERE name IN [
  'temporal_validity_idx',
  'temporal_transaction_idx',
  'current_version_idx',
  'changed_by_idx',
  'version_number_idx',
  'version_id_idx'
]
RETURN name, type, state, populationPercent
ORDER BY name;

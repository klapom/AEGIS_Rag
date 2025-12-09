/**
 * Graph Visualization Types
 * Sprint 29 Feature 29.1: Graph Viewer Component
 */

export interface GraphNode {
  id: string;
  label: string;
  type: string; // Entity type (PERSON, ORGANIZATION, LOCATION, etc.)
  community?: string;
  degree?: number; // Number of connections
  metadata?: Record<string, any>;
}

export interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  label: string; // Relationship type (RELATES_TO, MENTIONED_IN, etc.)
  weight?: number;
  description?: string; // Relationship description
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface GraphFilters {
  maxNodes?: number;
  entityTypes?: string[];
  highlightCommunities?: string[];
}

// Sprint 34 Feature 34.6: Edge Filter Types
export interface EdgeFilters {
  showRelatesTo: boolean;
  showCoOccurs: boolean;
  showMentionedIn: boolean;
  minWeight: number;
}

export interface GraphExportRequest {
  format: 'json' | 'graphml' | 'gexf';
  max_nodes?: number;
  entity_types?: string[];
  include_communities?: boolean;
}

export interface GraphExportResponse {
  nodes: Array<{
    id: string;
    label: string;
    type: string;
    community?: string;
    metadata?: Record<string, any>;
  }>;
  edges: Array<{
    source: string;
    target: string;
    type: string;
    weight?: number;
  }>;
  metadata?: {
    node_count: number;
    edge_count: number;
    community_count?: number;
  };
}

// Type aliases for react-force-graph
export interface ForceGraphNode extends GraphNode {
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface ForceGraphLink extends GraphLink {
  source: string | ForceGraphNode;
  target: string | ForceGraphNode;
}

// Sprint 29 Feature 29.4: Knowledge Graph Dashboard Types
export interface GraphStatistics {
  node_count: number;
  edge_count: number;
  community_count: number;
  avg_degree: number;
  entity_type_distribution: Record<string, number>;
  orphaned_nodes: number;
  disconnected_components?: number;
  largest_component_size?: number;
  timestamp: string;
}

export interface Community {
  id: string;
  topic: string;
  size: number; // Number of members (alias for member_count for consistency with API)
  member_count?: number; // Deprecated: Use 'size' instead
  density?: number;
  description?: string;
}

// Sprint 29 Feature 29.6: Node-Document Search Types
export interface RelatedDocument {
  id: string;
  title: string;
  excerpt: string;
  similarity: number; // Similarity score (0-1)
  source: string;
  chunk_id: string;
  metadata?: Record<string, any>;
}

export interface NodeDocumentsResponse {
  entity_name: string;
  documents: RelatedDocument[];
  total: number;
}

// Sprint 29 Feature 29.7: Community Document Browser Types
export interface CommunityDocument {
  id: string;
  title: string;
  excerpt: string;
  entities: string[]; // Entity names from community mentioned in document
  chunk_id?: string;
  source?: string;
  metadata?: Record<string, any>;
}

export interface CommunityDocumentsResponse {
  community_id: string;
  documents: CommunityDocument[];
  community?: Community;
  total: number;
}

// Sprint 39 Feature 39.5-39.7: Bi-Temporal Knowledge Graph Types

export interface EntitySnapshot {
  id: string;
  name: string;
  type: string;
  properties: Record<string, any>;
  valid_from: string;
  valid_to: string | null;
  version_number: number;
}

export interface TemporalQueryResponse {
  entities: EntitySnapshot[];
  as_of: string;
  total_count: number;
  changed_count?: number;
  new_count?: number;
  graphData?: GraphData;
}

export interface ChangeEvent {
  id: string;
  timestamp: string;
  changedBy: string;
  changeType: 'create' | 'update' | 'delete' | 'relation_added' | 'relation_removed';
  changedFields: string[];
  oldValues: Record<string, unknown>;
  newValues: Record<string, unknown>;
  reason: string;
  version: number;
}

export interface ChangelogResponse {
  changes: ChangeEvent[];
  total: number;
}

export interface EntityVersion {
  version: number;
  timestamp: string;
  changedBy: string;
  properties: Record<string, any>;
  relationships: Array<{
    type: string;
    target: string;
    weight?: number;
  }>;
}

export interface FieldChange {
  field: string;
  oldValue?: unknown;
  newValue?: unknown;
  changeType: 'added' | 'removed' | 'changed';
}

export interface VersionDiff {
  versionA: EntityVersion;
  versionB: EntityVersion;
  changes: {
    added: FieldChange[];
    removed: FieldChange[];
    changed: FieldChange[];
  };
  summary: string;
}

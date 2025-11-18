/**
 * Graph Visualization API Client
 * Sprint 29 Feature 29.1: Graph Export API
 * Sprint 29 Feature 29.2: Query Result Graph Visualization
 * Sprint 29 Feature 29.4: Graph Statistics API
 */

import type {
  GraphData,
  GraphExportRequest,
  GraphExportResponse,
  GraphStatistics,
  Community,
  NodeDocumentsResponse,
} from '../types/graph';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Fetch graph data from the backend API
 *
 * @param params Graph export parameters
 * @returns GraphData with nodes and links
 */
export async function fetchGraphData(params: GraphExportRequest): Promise<GraphData> {
  const response = await fetch(`${API_BASE_URL}/api/v1/graph/viz/export`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      format: params.format || 'json',
      max_nodes: params.max_nodes || 100,
      entity_types: params.entity_types,
      include_communities: params.include_communities ?? true,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`HTTP ${response.status}: ${error}`);
  }

  const data: GraphExportResponse = await response.json();

  return transformGraphExportResponse(data);
}

/**
 * Fetch subgraph for specific entities (query results)
 * Sprint 29 Feature 29.2: Query Result Graph Visualization
 *
 * @param entityNames List of entity names from query results
 * @returns GraphData containing entities and their 1-hop relationships
 */
export async function fetchQuerySubgraph(entityNames: string[]): Promise<GraphData> {
  const response = await fetch(`${API_BASE_URL}/api/v1/graph/viz/query-subgraph`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      entity_names: entityNames,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`HTTP ${response.status}: ${error}`);
  }

  const data: GraphExportResponse = await response.json();

  return transformGraphExportResponse(data);
}

/**
 * Transform GraphExportResponse to GraphData format
 * Helper function to reduce code duplication
 */
function transformGraphExportResponse(data: GraphExportResponse): GraphData {
  // Calculate node degrees from edges
  const nodeDegrees = new Map<string, number>();
  data.edges.forEach((edge) => {
    nodeDegrees.set(edge.source, (nodeDegrees.get(edge.source) || 0) + 1);
    nodeDegrees.set(edge.target, (nodeDegrees.get(edge.target) || 0) + 1);
  });

  return {
    nodes: data.nodes.map((node) => ({
      id: node.id,
      label: node.label,
      type: node.type,
      community: node.community,
      degree: nodeDegrees.get(node.id) || 0,
      metadata: node.metadata,
    })),
    links: data.edges.map((edge) => ({
      source: edge.source,
      target: edge.target,
      label: edge.type,
      weight: edge.weight,
    })),
  };
}

/**
 * Fetch comprehensive graph statistics
 * Sprint 29 Feature 29.4: Knowledge Graph Dashboard
 *
 * @returns Graph statistics including counts, distributions, and health metrics
 */
export async function fetchGraphStatistics(): Promise<GraphStatistics> {
  const response = await fetch(`${API_BASE_URL}/api/v1/graph/viz/statistics`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`HTTP ${response.status}: ${error}`);
  }

  return await response.json();
}

/**
 * Fetch top N communities by member count
 * Sprint 29 Feature 29.4: Knowledge Graph Dashboard
 *
 * @param limit Maximum number of communities to return (default: 10)
 * @returns List of top communities sorted by size
 */
export async function fetchTopCommunities(limit: number = 10): Promise<Community[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/graph/viz/communities?limit=${limit}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`HTTP ${response.status}: ${error}`);
  }

  return await response.json();
}

/**
 * Fetch related documents for a graph node using vector similarity
 * Sprint 29 Feature 29.6: Embedding-based Document Search from Graph
 *
 * @param entityName Entity name to search for (e.g., "Transformer")
 * @param topK Number of top documents to return (default: 10)
 * @returns List of documents with similarity scores
 */
export async function fetchDocumentsByNode(
  entityName: string,
  topK: number = 10
): Promise<NodeDocumentsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/graph/viz/node-documents`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      entity_name: entityName,
      top_k: topK,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`HTTP ${response.status}: ${error}`);
  }

  return await response.json();
}

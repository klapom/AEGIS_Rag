/**
 * Health API Client
 * Sprint 15 Feature 15.6: System health monitoring
 * Updated: Sprint 47 - Use /health endpoint (not /health/detailed)
 */

import type { HealthResponse } from '../types/health';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Get system health status with service details
 *
 * Calls the /health endpoint which returns:
 * - Overall system status
 * - Version info
 * - Service health for Qdrant, Neo4j, Redis, Ollama
 *
 * @returns Health response with all services
 */
export async function getSystemHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }

  return response.json();
}

/**
 * Alias for getSystemHealth for backward compatibility
 * @deprecated Use getSystemHealth instead
 */
export const getDetailedHealth = getSystemHealth;

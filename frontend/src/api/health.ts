/**
 * Health API Client
 * Sprint 15 Feature 15.6: System health monitoring
 * Updated: Sprint 47 - Use /health endpoint (not /health/detailed)
 * Updated: Sprint 51 - Added containers and Prometheus metrics endpoints
 */

import type { HealthResponse, ContainersResponse, PrometheusMetricsResponse } from '../types/health';

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

/**
 * Get Docker container health status and logs
 * Sprint 51 Feature: Container health monitoring
 *
 * @param tail Number of log lines to fetch per container
 * @returns Container health information with logs
 */
export async function getContainerHealth(tail: number = 50): Promise<ContainersResponse> {
  const response = await fetch(`${API_BASE_URL}/health/containers?tail=${tail}`, {
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
 * Get Prometheus performance metrics
 * Sprint 51 Feature: Prometheus metrics display
 *
 * @returns Prometheus metrics for dashboard display
 */
export async function getPrometheusMetrics(): Promise<PrometheusMetricsResponse> {
  const response = await fetch(`${API_BASE_URL}/health/metrics`, {
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

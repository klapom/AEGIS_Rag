/**
 * Health API Client
 * Sprint 15 Feature 15.6: System health monitoring
 */

import type { HealthResponse, DetailedHealthResponse } from '../types/health';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Get basic system health status
 *
 * @returns Basic health response
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
 * Get detailed system health with dependencies
 *
 * @returns Detailed health response with all dependencies
 */
export async function getDetailedHealth(): Promise<DetailedHealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health/detailed`, {
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

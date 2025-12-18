/**
 * Health API Types
 * Sprint 15 Feature 15.6
 * Updated: Sprint 47 - Aligned with backend /health response
 * Updated: Sprint 51 - Added container and Prometheus metrics types
 */

/**
 * Service health status from backend /health endpoint
 */
export interface ServiceHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  latency_ms?: number;
}

/**
 * Health response from backend /health endpoint
 *
 * Example response:
 * {
 *   "status": "healthy",
 *   "version": "0.1.0",
 *   "services": {
 *     "qdrant": {"status": "healthy", "latency_ms": 16.64},
 *     "neo4j": {"status": "healthy", "latency_ms": 1.19},
 *     "redis": {"status": "healthy", "latency_ms": 0.82},
 *     "ollama": {"status": "healthy", "latency_ms": 16.84},
 *     "docling": {"status": "healthy", "latency_ms": 5.12}
 *   }
 * }
 */
export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  services: {
    qdrant: ServiceHealth;
    neo4j: ServiceHealth;
    redis: ServiceHealth;
    ollama: ServiceHealth;
    docling: ServiceHealth;
    [key: string]: ServiceHealth;
  };
}

/**
 * Legacy type alias for backward compatibility
 * @deprecated Use HealthResponse instead
 */
export type DetailedHealthResponse = HealthResponse;

/**
 * Legacy type alias for backward compatibility
 * @deprecated Use ServiceHealth instead
 */
export type DependencyHealth = ServiceHealth;


// Sprint 51: Container health types
export interface ContainerHealth {
  name: string;
  status: string;
  health: string;
  image: string;
  created: string;
  logs: string[];
}

export interface ContainersResponse {
  containers: ContainerHealth[];
  docker_available: boolean;
  error: string | null;
}

// Sprint 51: Prometheus metrics types
export interface PrometheusMetric {
  name: string;
  value: number;
  labels: Record<string, string>;
}

export interface PrometheusMetricsResponse {
  metrics: PrometheusMetric[];
  prometheus_available: boolean;
  error: string | null;
}

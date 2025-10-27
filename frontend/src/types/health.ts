/**
 * Health API Types
 * Sprint 15 Feature 15.6
 */

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
}

export interface DependencyHealth {
  status: 'up' | 'down' | 'degraded';
  latency_ms?: number;
  details?: Record<string, any>;
}

export interface DetailedHealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  uptime?: number;
  dependencies: {
    qdrant: DependencyHealth;
    ollama: DependencyHealth;
    neo4j: DependencyHealth;
    redis: DependencyHealth;
    [key: string]: DependencyHealth;
  };
}

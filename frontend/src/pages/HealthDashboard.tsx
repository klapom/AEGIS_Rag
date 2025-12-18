/**
 * HealthDashboard Page
 * Sprint 15 Feature 15.6: System health monitoring
 * Updated: Sprint 47 - Use /health endpoint structure
 *
 * Real-time system health dashboard with:
 * - Overall health status
 * - Service health cards (Qdrant, Ollama, Neo4j, Redis)
 * - Version info
 * - Auto-refresh every 30s
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getSystemHealth, getContainerHealth, getPrometheusMetrics } from '../api/health';
import type {
  HealthResponse,
  ServiceHealth,
  ContainersResponse,
  ContainerHealth as ContainerHealthType,
  PrometheusMetricsResponse,
} from '../types/health';

export function HealthDashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [containers, setContainers] = useState<ContainersResponse | null>(null);
  const [metrics, setMetrics] = useState<PrometheusMetricsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  useEffect(() => {
    fetchHealth();

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      fetchHealth();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const fetchHealth = async () => {
    try {
      // Fetch all health data in parallel
      const [healthData, containersData, metricsData] = await Promise.all([
        getSystemHealth(),
        getContainerHealth(30).catch(() => null),
        getPrometheusMetrics().catch(() => null),
      ]);

      setHealth(healthData);
      setContainers(containersData);
      setMetrics(metricsData);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      console.error('Failed to fetch health:', err);
      setError(err instanceof Error ? err.message : 'Fehler beim Laden');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-gray-600">Lade System-Status...</p>
        </div>
      </div>
    );
  }

  if (error || !health) {
    return (
      <div className="flex items-center justify-center min-h-screen p-6" data-testid="health-error-state">
        <div className="max-w-md w-full bg-red-50 border border-red-200 rounded-xl p-6 space-y-4">
          <div className="flex items-center space-x-2 text-red-700">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="font-semibold">Fehler beim Laden des System-Status</h3>
          </div>
          <p className="text-red-600 text-sm">{error}</p>
          <button
            onClick={fetchHealth}
            className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
          >
            Erneut versuchen
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-4">
        {/* Back Link */}
        <Link
          to="/admin"
          className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Admin
        </Link>

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center space-x-2">
              <span className="text-lg">🏥</span>
              <span>System Health</span>
            </h1>
            <p className="text-xs text-gray-600 mt-1">
              Letztes Update: {lastUpdated.toLocaleTimeString('de-DE')}
            </p>
          </div>
          <StatusBadge status={health.status} />
        </div>

        {/* Overall Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <StatCard
            label="Version"
            value={health.version || 'N/A'}
            icon="📦"
          />
          <StatCard
            label="Services"
            value={`${Object.values(health.services).filter(s => s.status === 'healthy').length}/${Object.keys(health.services).length}`}
            icon="🔗"
          />
          <StatCard
            label="Status"
            value={health.status}
            icon={health.status === 'healthy' ? '✅' : '⚠️'}
          />
        </div>

        {/* Services Grid */}
        <div data-testid="services-section">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Services</h2>
          <div data-testid="services-grid" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {Object.entries(health.services).map(([key, service]) => (
              <ServiceCard key={key} name={key} service={service} />
            ))}
          </div>
        </div>

        {/* Docker Containers Section */}
        {containers && (
          <div data-testid="containers-section">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Docker Container</h2>
            {containers.docker_available ? (
              <div className="space-y-2">
                {containers.containers.length > 0 ? (
                  containers.containers.map((container) => (
                    <ContainerCard key={container.name} container={container} />
                  ))
                ) : (
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 text-center text-gray-500">
                    Keine Container gefunden
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-sm text-yellow-700">
                  {containers.error || 'Docker ist nicht verfügbar'}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Performance Metrics Section */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Performance-Metriken</h2>
          {metrics?.prometheus_available ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {metrics.metrics.map((metric) => (
                <MetricCard key={metric.name} metric={metric} />
              ))}
            </div>
          ) : (
            <div className="text-center py-4 text-gray-500">
              <div className="text-2xl mb-2">📊</div>
              <p className="text-sm">
                {metrics?.error || 'Prometheus nicht erreichbar'}
              </p>
              <p className="text-xs mt-1 text-gray-400">
                Starten Sie Prometheus auf Port 9090 für Metriken
              </p>
            </div>
          )}
        </div>

        {/* Refresh Button */}
        <div className="text-center">
          <button
            onClick={fetchHealth}
            className="px-4 py-2 text-sm bg-primary text-white rounded-md hover:bg-primary-hover
                       transition-all flex items-center space-x-1.5 mx-auto"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Aktualisieren</span>
          </button>
        </div>
      </div>
    </div>
  );
}

interface StatusBadgeProps {
  status: string;
}

function StatusBadge({ status }: StatusBadgeProps) {
  const getStatusColor = () => {
    switch (status.toLowerCase()) {
      case 'healthy':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'degraded':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'unhealthy':
        return 'bg-red-100 text-red-700 border-red-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  return (
    <div
      data-testid="overall-status"
      className={`px-4 py-1.5 rounded-full border font-semibold text-sm ${getStatusColor()}`}
    >
      {status.toUpperCase()}
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: string;
  icon: string;
}

function StatCard({ label, value, icon }: StatCardProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-500 text-xs font-medium">{label}</p>
          <p className="text-xl font-bold text-gray-900 mt-0.5">{value}</p>
        </div>
        <div className="text-2xl">{icon}</div>
      </div>
    </div>
  );
}

interface ServiceCardProps {
  name: string;
  service: ServiceHealth;
}

function ServiceCard({ name, service }: ServiceCardProps) {
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
        return 'bg-green-500';
      case 'unhealthy':
        return 'bg-red-500';
      case 'degraded':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusTextColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
        return 'text-green-600';
      case 'unhealthy':
        return 'text-red-600';
      case 'degraded':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  };

  const getIcon = (name: string) => {
    switch (name.toLowerCase()) {
      case 'qdrant':
        return '🔍';
      case 'ollama':
        return '🤖';
      case 'neo4j':
        return '🕸️';
      case 'redis':
        return '💾';
      case 'docling':
        return '📄';
      default:
        return '🔧';
    }
  };

  return (
    <div
      data-testid={`service-card-${name.toLowerCase()}`}
      className="bg-white rounded-lg shadow-sm border border-gray-200 hover:border-primary/50 transition-all p-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-1.5">
          <div className="text-lg">{getIcon(name)}</div>
          <h3 data-testid={`service-name-${name.toLowerCase()}`} className="text-sm font-semibold text-gray-900 capitalize">{name}</h3>
        </div>
        <div
          data-testid={`service-status-indicator-${name.toLowerCase()}`}
          className={`w-2 h-2 rounded-full ${getStatusColor(service.status)}`}
          title={service.status}
        />
      </div>

      {/* Stats */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs">
          <span className="text-gray-500">Status:</span>
          <span className={`font-medium ${getStatusTextColor(service.status)}`}>
            {service.status.toUpperCase()}
          </span>
        </div>

        {service.latency_ms !== undefined && (
          <div className="flex justify-between text-xs">
            <span className="text-gray-500">Latency:</span>
            <span className="font-medium text-gray-900">
              {typeof service.latency_ms === 'number'
                ? `${service.latency_ms.toFixed(2)}ms`
                : `${service.latency_ms}ms`}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Container Card with expandable logs
 * Sprint 51 Feature: Container health monitoring
 */
interface ContainerCardProps {
  container: ContainerHealthType;
}

function ContainerCard({ container }: ContainerCardProps) {
  const [expanded, setExpanded] = useState(false);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'running':
        return 'bg-green-500';
      case 'exited':
      case 'dead':
        return 'bg-red-500';
      case 'paused':
      case 'restarting':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getContainerIcon = (name: string) => {
    const lowerName = name.toLowerCase();
    if (lowerName.includes('qdrant')) return '🔍';
    if (lowerName.includes('neo4j')) return '🕸️';
    if (lowerName.includes('redis')) return '💾';
    if (lowerName.includes('ollama')) return '🤖';
    if (lowerName.includes('docling')) return '📄';
    if (lowerName.includes('api') || lowerName.includes('backend')) return '⚙️';
    if (lowerName.includes('frontend')) return '🖥️';
    return '📦';
  };

  return (
    <div
      data-testid={`container-card-${container.name}`}
      className="bg-white rounded-lg shadow-sm border border-gray-200"
    >
      {/* Header - Clickable */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center space-x-2">
          <span className="text-lg">{getContainerIcon(container.name)}</span>
          <span className="font-medium text-gray-900 text-sm">{container.name}</span>
          <div
            className={`w-2 h-2 rounded-full ${getStatusColor(container.status)}`}
            title={container.status}
          />
          <span className="text-xs text-gray-500">{container.status}</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-400 truncate max-w-32">{container.image}</span>
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Expandable Logs Section */}
      {expanded && (
        <div className="border-t border-gray-200 p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-700">Container Logs</span>
            <span className="text-xs text-gray-400">{container.logs.length} Zeilen</span>
          </div>
          <div className="bg-gray-900 rounded-md p-2 max-h-48 overflow-y-auto">
            {container.logs.length > 0 ? (
              <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap break-all">
                {container.logs.join('\n')}
              </pre>
            ) : (
              <p className="text-xs text-gray-500 text-center py-2">Keine Logs verfügbar</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Prometheus Metric Card
 * Sprint 51 Feature: Prometheus metrics display
 */
interface MetricCardProps {
  metric: {
    name: string;
    value: number;
    labels: Record<string, string>;
  };
}

function MetricCard({ metric }: MetricCardProps) {
  const formatValue = (name: string, value: number): string => {
    if (name.includes('bytes')) {
      // Format as MB or GB
      if (value > 1e9) return `${(value / 1e9).toFixed(1)} GB`;
      if (value > 1e6) return `${(value / 1e6).toFixed(1)} MB`;
      return `${(value / 1e3).toFixed(1)} KB`;
    }
    if (name.includes('seconds') && !name.includes('total')) {
      // Format as ms
      return `${(value * 1000).toFixed(1)} ms`;
    }
    if (value > 1000) {
      return `${(value / 1000).toFixed(1)}k`;
    }
    return value.toFixed(2);
  };

  const getMetricLabel = (name: string): string => {
    const labels: Record<string, string> = {
      http_requests_total: 'HTTP Requests',
      http_request_duration_p99: 'Latency (p99)',
      process_cpu_seconds_total: 'CPU Time',
      process_resident_memory_bytes: 'Memory',
      qdrant_grpc_requests_total: 'Qdrant Requests',
    };
    return labels[name] || name;
  };

  return (
    <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
      <p className="text-xs text-gray-500 truncate" title={metric.name}>
        {getMetricLabel(metric.name)}
      </p>
      <p className="text-lg font-bold text-gray-900 mt-1">
        {formatValue(metric.name, metric.value)}
      </p>
    </div>
  );
}

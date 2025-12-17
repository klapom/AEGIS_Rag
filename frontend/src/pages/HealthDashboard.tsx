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
import { getSystemHealth } from '../api/health';
import type { HealthResponse, ServiceHealth } from '../types/health';

export function HealthDashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
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
      const data = await getSystemHealth();
      setHealth(data);
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

        {/* Performance Section (Placeholder) */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Performance-Metriken</h2>
          <div className="text-center py-8 text-gray-500">
            <div className="text-2xl mb-2">📊</div>
            <p className="text-sm">Performance-Diagramme werden in Zukunft hier angezeigt</p>
            <p className="text-xs mt-1">
              (Prometheus-Integration geplant)
            </p>
          </div>
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

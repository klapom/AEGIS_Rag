/**
 * HealthDashboard Page
 * Sprint 15 Feature 15.6: System health monitoring
 *
 * Real-time system health dashboard with:
 * - Overall health status
 * - Dependency health cards (Qdrant, Ollama, Neo4j, Redis)
 * - Performance metrics
 * - Auto-refresh every 30s
 */

import { useState, useEffect } from 'react';
import { getDetailedHealth } from '../api/health';
import type { DetailedHealthResponse, DependencyHealth } from '../types/health';

export function HealthDashboard() {
  const [health, setHealth] = useState<DetailedHealthResponse | null>(null);
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
      const data = await getDetailedHealth();
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
      <div className="flex items-center justify-center min-h-screen p-6">
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
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 flex items-center space-x-3">
              <span>🏥</span>
              <span>System Health</span>
            </h1>
            <p className="text-gray-600 mt-2">
              Letztes Update: {lastUpdated.toLocaleTimeString('de-DE')}
            </p>
          </div>
          <StatusBadge status={health.status} />
        </div>

        {/* Overall Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StatCard
            label="Uptime"
            value={health.uptime ? `${Math.floor(health.uptime / 3600)}h` : 'N/A'}
            icon="⏱️"
          />
          <StatCard
            label="Dependencies"
            value={`${Object.values(health.dependencies).filter(d => d.status === 'up').length}/${Object.keys(health.dependencies).length}`}
            icon="🔗"
          />
          <StatCard
            label="Status"
            value={health.status}
            icon={health.status === 'healthy' ? '✅' : '⚠️'}
          />
        </div>

        {/* Dependencies Grid */}
        <div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Abhängigkeiten</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {Object.entries(health.dependencies).map(([key, dep]) => (
              <DependencyCard key={key} name={key} dependency={dep} />
            ))}
          </div>
        </div>

        {/* Performance Section (Placeholder) */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Performance-Metriken</h2>
          <div className="text-center py-12 text-gray-500">
            <div className="text-4xl mb-3">📊</div>
            <p>Performance-Diagramme werden in Zukunft hier angezeigt</p>
            <p className="text-sm mt-2">
              (Prometheus-Integration geplant)
            </p>
          </div>
        </div>

        {/* Refresh Button */}
        <div className="text-center">
          <button
            onClick={fetchHealth}
            className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-hover
                       transition-all flex items-center space-x-2 mx-auto"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
      className={`px-6 py-3 rounded-full border-2 font-semibold text-lg ${getStatusColor()}`}
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
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-500 text-sm font-medium">{label}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
        </div>
        <div className="text-4xl">{icon}</div>
      </div>
    </div>
  );
}

interface DependencyCardProps {
  name: string;
  dependency: DependencyHealth;
}

function DependencyCard({ name, dependency }: DependencyCardProps) {
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'up':
        return 'bg-green-500';
      case 'down':
        return 'bg-red-500';
      case 'degraded':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
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
    <div className="bg-white rounded-xl shadow-sm border-2 border-gray-200 hover:border-primary/50 transition-all p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <div className="text-3xl">{getIcon(name)}</div>
          <h3 className="font-semibold text-gray-900 capitalize">{name}</h3>
        </div>
        <div
          className={`w-3 h-3 rounded-full ${getStatusColor(dependency.status)}`}
          title={dependency.status}
        />
      </div>

      {/* Stats */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Status:</span>
          <span
            className={`font-medium ${
              dependency.status === 'up'
                ? 'text-green-600'
                : dependency.status === 'down'
                ? 'text-red-600'
                : 'text-yellow-600'
            }`}
          >
            {dependency.status.toUpperCase()}
          </span>
        </div>

        {dependency.latency_ms !== undefined && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Latency:</span>
            <span className="font-medium text-gray-900">{dependency.latency_ms}ms</span>
          </div>
        )}

        {dependency.details && Object.entries(dependency.details).length > 0 && (
          <div className="pt-2 mt-2 border-t border-gray-200 space-y-1">
            {Object.entries(dependency.details).slice(0, 3).map(([key, value]) => (
              <div key={key} className="flex justify-between text-xs text-gray-600">
                <span className="truncate">{key}:</span>
                <span className="font-medium ml-2">{String(value)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

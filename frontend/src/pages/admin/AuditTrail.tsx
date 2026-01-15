/**
 * AuditTrail Page
 * Sprint 98 Feature 98.4: Audit Trail Viewer
 *
 * Main page for audit trail viewing and compliance reporting.
 * Implements EU AI Act Article 12.
 */

import { useState, useEffect } from 'react';
import { Shield } from 'lucide-react';
import { AuditLogBrowser } from '../../components/audit/AuditLogBrowser';
import { ComplianceReports } from '../../components/audit/ComplianceReports';
import { IntegrityVerification } from '../../components/audit/IntegrityVerification';
import { AuditExport } from '../../components/audit/AuditExport';
import type {
  AuditEvent,
  AuditEventFilters,
  ComplianceReportType,
  IntegrityVerificationResult,
} from '../../types/audit';

type TabType = 'events' | 'reports' | 'integrity' | 'export';

export function AuditTrailPage() {
  const [activeTab, setActiveTab] = useState<TabType>('events');
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [totalEvents, setTotalEvents] = useState(0);
  const [filters, setFilters] = useState<AuditEventFilters>({ page: 1, pageSize: 50 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch events on mount and filter change
  useEffect(() => {
    loadEvents();
  }, [filters]);

  const loadEvents = async () => {
    try {
      setLoading(true);
      setError(null);

      // Build query params
      const params = new URLSearchParams();
      if (filters.eventType) params.append('eventType', filters.eventType);
      if (filters.outcome) params.append('outcome', filters.outcome);
      if (filters.actorId) params.append('actorId', filters.actorId);
      if (filters.startTime) params.append('startTime', filters.startTime);
      if (filters.endTime) params.append('endTime', filters.endTime);
      if (filters.searchQuery) params.append('search', filters.searchQuery);
      params.append('page', String(filters.page || 1));
      params.append('pageSize', String(filters.pageSize || 50));

      const response = await fetch(`/api/v1/audit/events?${params.toString()}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        // Sprint 100 Fix #3: Use standardized "items" field (not "events")
        setEvents(data.items || []);
        setTotalEvents(data.total || 0);
      } else {
        throw new Error('Failed to fetch events');
      }
    } catch (err) {
      console.error('Failed to load audit events:', err);
      setError('Failed to load audit events. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async (reportType: ComplianceReportType, timeRange: string) => {
    try {
      // Sprint 100 Fix #4: Convert timeRange to start_time/end_time ISO 8601 timestamps
      const end_time = new Date();
      const start_time = new Date();

      switch (timeRange) {
        case '24h':
          start_time.setHours(start_time.getHours() - 24);
          break;
        case '7d':
          start_time.setDate(start_time.getDate() - 7);
          break;
        case '30d':
          start_time.setDate(start_time.getDate() - 30);
          break;
        case '90d':
          start_time.setDate(start_time.getDate() - 90);
          break;
        default:
          start_time.setDate(start_time.getDate() - 7); // Default to 7 days
      }

      const start_time_iso = start_time.toISOString();
      const end_time_iso = end_time.toISOString();

      const response = await fetch(
        `/api/v1/audit/reports/${reportType}?start_time=${encodeURIComponent(start_time_iso)}&end_time=${encodeURIComponent(end_time_iso)}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
          },
        }
      );

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${reportType}-report-${timeRange}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } else {
        throw new Error('Failed to generate report');
      }
    } catch (err) {
      console.error('Failed to generate report:', err);
      alert('Failed to generate report. Please try again.');
    }
  };

  const handleVerifyIntegrity = async (
    startTime?: string,
    endTime?: string
  ): Promise<IntegrityVerificationResult> => {
    try {
      const params = new URLSearchParams();
      if (startTime) params.append('startTime', startTime);
      if (endTime) params.append('endTime', endTime);

      const response = await fetch(`/api/v1/audit/integrity?${params.toString()}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (response.ok) {
        return await response.json();
      } else {
        throw new Error('Failed to verify integrity');
      }
    } catch (err) {
      console.error('Failed to verify integrity:', err);
      throw err;
    }
  };

  const handleExport = async (format: 'json' | 'csv', includeMetadata: boolean) => {
    try {
      const params = new URLSearchParams();
      params.append('format', format);
      params.append('includeMetadata', String(includeMetadata));
      if (filters.eventType) params.append('eventType', filters.eventType);
      if (filters.outcome) params.append('outcome', filters.outcome);
      if (filters.actorId) params.append('actorId', filters.actorId);
      if (filters.startTime) params.append('startTime', filters.startTime);
      if (filters.endTime) params.append('endTime', filters.endTime);

      const response = await fetch(`/api/v1/audit/export?${params.toString()}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit-log-${Date.now()}.${format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } else {
        throw new Error('Failed to export');
      }
    } catch (err) {
      console.error('Failed to export:', err);
      alert('Failed to export audit log. Please try again.');
    }
  };

  const handleViewEventDetails = (event: AuditEvent) => {
    // Show event details in modal (implementation depends on your modal system)
    alert(`Event Details:\n\n${JSON.stringify(event, null, 2)}`);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto py-8 px-6 space-y-6">
        {/* Header */}
        <header className="space-y-2">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-600 dark:text-blue-400" />
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                Audit Trail Viewer
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                EU AI Act Article 12 - Immutable Audit Log & Compliance Reporting
              </p>
            </div>
          </div>
        </header>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-red-700 dark:text-red-300">{error}</p>
          </div>
        )}

        {/* Tabs */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="flex gap-4">
            {[
              { id: 'events' as TabType, label: 'Audit Events', count: totalEvents },
              { id: 'reports' as TabType, label: 'Compliance Reports', count: undefined },
              { id: 'integrity' as TabType, label: 'Integrity Verification', count: undefined },
              { id: 'export' as TabType, label: 'Export', count: undefined },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                }`}
              >
                {tab.label}
                {tab.count !== undefined && (
                  <span className="ml-2 px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 rounded-full">
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div>
          {loading && activeTab === 'events' ? (
            <div className="text-center py-8 text-gray-600 dark:text-gray-400">
              Loading audit events...
            </div>
          ) : (
            <>
              {activeTab === 'events' && (
                <AuditLogBrowser
                  events={events}
                  filters={filters}
                  total={totalEvents}
                  onFiltersChange={setFilters}
                  onViewDetails={handleViewEventDetails}
                />
              )}
              {activeTab === 'reports' && (
                <ComplianceReports onGenerateReport={handleGenerateReport} />
              )}
              {activeTab === 'integrity' && (
                <IntegrityVerification onVerify={handleVerifyIntegrity} />
              )}
              {activeTab === 'export' && (
                <AuditExport filters={filters} onExport={handleExport} />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default AuditTrailPage;

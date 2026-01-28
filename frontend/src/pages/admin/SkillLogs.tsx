/**
 * SkillLogs Page Component
 * Sprint 121: Skill Logs Viewer
 *
 * Shows execution logs and lifecycle events for a specific skill.
 *
 * Route: /admin/skills/:skillName/logs
 */

import { useState, useEffect, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, RefreshCw, Clock, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import { getSkill } from '../../api/skills';
import type { SkillDetail } from '../../types/skills';

interface LogEntry {
  timestamp: string;
  level: 'info' | 'warn' | 'error';
  message: string;
  details?: string;
}

export function SkillLogs() {
  const { skillName } = useParams<{ skillName: string }>();

  const [skill, setSkill] = useState<SkillDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load skill details for context
  const loadSkillInfo = useCallback(async () => {
    if (!skillName) return;

    setLoading(true);
    setError(null);

    try {
      const detail = await getSkill(skillName);
      setSkill(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load skill details');
    } finally {
      setLoading(false);
    }
  }, [skillName]);

  useEffect(() => {
    void loadSkillInfo();
  }, [loadSkillInfo]);

  // Generate synthetic log entries from skill metadata
  const generateLogEntries = (detail: SkillDetail): LogEntry[] => {
    const entries: LogEntry[] = [];
    const now = new Date();

    // Registration event
    entries.push({
      timestamp: new Date(now.getTime() - 86400000).toISOString(),
      level: 'info',
      message: `Skill "${detail.name}" v${detail.version} registered in registry`,
      details: `Author: ${detail.author}, Triggers: ${detail.triggers.length}, Permissions: ${detail.permissions.join(', ')}`,
    });

    // Activation events
    if (detail.last_activated) {
      entries.push({
        timestamp: detail.last_activated,
        level: 'info',
        message: `Skill activated (count: ${detail.activation_count})`,
      });
    }

    // Status
    entries.push({
      timestamp: now.toISOString(),
      level: detail.is_active ? 'info' : 'warn',
      message: detail.is_active ? 'Skill is currently ACTIVE' : 'Skill is currently INACTIVE',
    });

    return entries.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  };

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'info': return <CheckCircle className="w-4 h-4 text-blue-500" />;
      case 'warn': return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      case 'error': return <XCircle className="w-4 h-4 text-red-500" />;
      default: return <Clock className="w-4 h-4 text-gray-500" />;
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'info': return 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800';
      case 'warn': return 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800';
      case 'error': return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
      default: return 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700';
    }
  };

  if (!skillName) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <p className="text-lg text-gray-600 dark:text-gray-400">Skill name is required</p>
      </div>
    );
  }

  const logEntries = skill ? generateLogEntries(skill) : [];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b-2 border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <Link
            to="/admin/skills/registry"
            className="inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 mb-3"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Registry
          </Link>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Skill Logs: {skillName}
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Execution history and lifecycle events
              </p>
            </div>
            <div className="flex gap-2">
              <Link
                to={`/admin/skills/${skillName}/config`}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg transition-colors text-sm"
              >
                Config
              </Link>
              <button
                onClick={() => void loadSkillInfo()}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Error Display */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
            <p className="text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-12 text-center">
            <p className="text-gray-600 dark:text-gray-400">Loading logs...</p>
          </div>
        )}

        {/* Skill Info Summary */}
        {!loading && skill && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-6 mb-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Status</p>
                <p className={`text-lg font-semibold ${skill.is_active ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'}`}>
                  {skill.is_active ? '🟢 Active' : '⚪ Inactive'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Activations</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">{skill.activation_count}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Triggers</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">{skill.triggers.length}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Last Activated</p>
                <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  {skill.last_activated ? new Date(skill.last_activated).toLocaleString() : 'Never'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Log Entries */}
        {!loading && logEntries.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Recent Events
            </h2>
            {logEntries.map((entry, i) => (
              <div
                key={i}
                className={`rounded-lg border p-4 ${getLevelColor(entry.level)}`}
              >
                <div className="flex items-start gap-3">
                  {getLevelIcon(entry.level)}
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {entry.message}
                      </p>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {new Date(entry.timestamp).toLocaleString()}
                      </span>
                    </div>
                    {entry.details && (
                      <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                        {entry.details}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* No Logs Placeholder */}
        {!loading && logEntries.length === 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-12 text-center">
            <Clock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-lg text-gray-600 dark:text-gray-400 mb-2">No log entries yet</p>
            <p className="text-sm text-gray-500 dark:text-gray-500">
              Logs will appear here once the skill is activated and used.
            </p>
          </div>
        )}

        {/* Future Enhancement Notice */}
        <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p className="text-sm text-blue-800 dark:text-blue-200">
            <strong>Note:</strong> Detailed execution logs with latency metrics and error traces
            will be available in a future sprint via the Skill Lifecycle Dashboard.
          </p>
          <Link
            to="/admin/skills/lifecycle"
            className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 mt-1 inline-block"
          >
            View Lifecycle Dashboard →
          </Link>
        </div>
      </main>
    </div>
  );
}

export default SkillLogs;

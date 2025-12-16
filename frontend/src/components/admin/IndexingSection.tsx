/**
 * IndexingSection Component
 * Sprint 46 Feature 46.8: Admin Area Consolidation
 *
 * Compact indexing status section for the admin dashboard.
 * Shows last indexing status and provides quick access to indexing page.
 */

import { useEffect, useState, useCallback } from 'react';
import { FolderOpen, Clock, FileText, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { AdminSection } from './AdminSection';
import { getSystemStats } from '../../api/admin';
import type { SystemStats } from '../../types/admin';

/**
 * Format a timestamp to a readable date/time string
 */
function formatTimestamp(timestamp: string | null | undefined): string {
  if (!timestamp) return 'Never';

  try {
    const date = new Date(timestamp);
    return date.toLocaleString('de-DE', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return 'Invalid date';
  }
}

/**
 * Stat item for compact display
 */
interface StatItemProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
}

function StatItem({ icon, label, value }: StatItemProps) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-gray-400 dark:text-gray-500">{icon}</span>
      <span className="text-gray-600 dark:text-gray-400">{label}:</span>
      <span className="font-medium text-gray-900 dark:text-gray-100">{value}</span>
    </div>
  );
}

/**
 * Index Directory Button
 */
interface IndexButtonProps {
  onClick: () => void;
}

function IndexButton({ onClick }: IndexButtonProps) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
      data-testid="index-directory-button"
    >
      <FolderOpen className="w-4 h-4" />
      <span>Index Dir</span>
    </button>
  );
}

/**
 * IndexingSection - Compact indexing status for admin dashboard
 */
export function IndexingSection() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch system stats on mount
  useEffect(() => {
    const fetchStats = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getSystemStats();
        setStats(data);
      } catch (err) {
        console.error('Failed to fetch system stats:', err);
        setError(err instanceof Error ? err.message : 'Failed to load indexing status');
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
  }, []);

  const handleIndexClick = useCallback(() => {
    navigate('/admin/indexing');
  }, [navigate]);

  const handleOpenIndexingPage = useCallback(() => {
    navigate('/admin/indexing');
  }, [navigate]);

  return (
    <AdminSection
      title="Indexing"
      icon={<FolderOpen className="w-5 h-5" />}
      action={<IndexButton onClick={handleIndexClick} />}
      defaultExpanded={true}
      testId="admin-indexing-section"
      isLoading={isLoading}
      error={error}
    >
      {stats && (
        <div className="space-y-3">
          {/* Last Run Info */}
          <div
            className="flex items-center justify-between py-2 px-3 rounded-lg bg-gray-50 dark:bg-gray-700/30 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors group"
            onClick={handleOpenIndexingPage}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleOpenIndexingPage();
              }
            }}
            data-testid="indexing-status-card"
          >
            <div className="space-y-2">
              <StatItem
                icon={<Clock className="w-4 h-4" />}
                label="Last run"
                value={formatTimestamp(stats.last_reindex_timestamp)}
              />
              <StatItem
                icon={<FileText className="w-4 h-4" />}
                label="Documents indexed"
                value={stats.qdrant_total_chunks.toLocaleString()}
              />
            </div>
            <ExternalLink
              className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity"
              aria-hidden="true"
            />
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-gray-200 dark:border-gray-600">
            <QuickStat
              label="Qdrant"
              value={stats.qdrant_total_chunks.toLocaleString()}
              sublabel="chunks"
            />
            <QuickStat
              label="Neo4j"
              value={(stats.neo4j_total_entities ?? 0).toLocaleString()}
              sublabel="entities"
            />
            <QuickStat
              label="BM25"
              value={(stats.bm25_corpus_size ?? 0).toLocaleString()}
              sublabel="docs"
            />
          </div>
        </div>
      )}
    </AdminSection>
  );
}

/**
 * Quick stat display
 */
interface QuickStatProps {
  label: string;
  value: string | number;
  sublabel: string;
}

function QuickStat({ label, value, sublabel }: QuickStatProps) {
  return (
    <div className="text-center" data-testid={`quick-stat-${label.toLowerCase()}`}>
      <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
      <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">{value}</div>
      <div className="text-xs text-gray-400 dark:text-gray-500">{sublabel}</div>
    </div>
  );
}

export default IndexingSection;

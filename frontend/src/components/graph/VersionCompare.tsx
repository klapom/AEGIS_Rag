/**
 * VersionCompare Component
 * Sprint 39 Feature 39.7: Version Comparison View (6 SP)
 *
 * Features:
 * - Side-by-side diff view
 * - Version selectors (dropdowns)
 * - Highlight added/removed/changed fields
 * - Summary line (e.g., "1 field changed, 1 relationship added")
 * - Revert to Version X button
 * - Export Diff button
 */

import { useState, useEffect } from 'react';
import { X, Download, RotateCcw, GitCompare, Plus, Minus, ArrowRight } from 'lucide-react';
import type { FieldChange } from '../../types/graph';
import { useVersionDiff } from '../../hooks/useVersionDiff';
import { revertToVersion } from '../../api/graphViz';

interface VersionCompareProps {
  entityId: string;
  initialVersionA?: number;
  initialVersionB?: number;
  onClose: () => void;
  onRevert?: () => void;
}

export function VersionCompare({
  entityId,
  initialVersionA,
  initialVersionB,
  onClose,
  onRevert,
}: VersionCompareProps) {
  const [versionA, setVersionA] = useState<number | null>(initialVersionA ?? null);
  const [versionB, setVersionB] = useState<number | null>(initialVersionB ?? null);
  const [isReverting, setIsReverting] = useState(false);

  const { data: diff, versions, loading, error } = useVersionDiff(entityId, versionA, versionB);

  // Auto-select latest two versions if available
  useEffect(() => {
    if (versions && versions.length >= 2 && !versionA && !versionB) {
      setVersionB(versions[0].version); // Latest
      setVersionA(versions[1].version); // Previous
    }
  }, [versions, versionA, versionB]);

  const handleRevert = async () => {
    if (!versionA) return;

    const reason = prompt('Please provide a reason for reverting:');
    if (!reason) return;

    setIsReverting(true);
    try {
      await revertToVersion(entityId, versionA, reason);
      alert(`Successfully reverted to version ${versionA}`);
      onRevert?.();
      onClose();
    } catch (err) {
      alert(`Failed to revert: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsReverting(false);
    }
  };

  const handleExportDiff = () => {
    if (!diff) return;

    const dataStr = JSON.stringify(diff, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);

    const exportFileDefaultName = `version-diff-${versionA}-${versionB}.json`;

    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  const formatValue = (value: unknown): string => {
    if (value === null || value === undefined) return 'null';
    if (typeof value === 'string') return value;
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    return String(value);
  };

  return (
    <div className="version-compare" data-testid="version-compare">
      {/* Header */}
      <div className="flex justify-between items-center mb-6 pb-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <GitCompare className="w-5 h-5 text-blue-600" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Compare Versions
          </h2>
        </div>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
          data-testid="close-button"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Version Selectors */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <label className="text-sm text-gray-600 dark:text-gray-400 mb-2 block font-medium">
            Version A (Base):
          </label>
          <select
            value={versionA ?? ''}
            onChange={(e) => setVersionA(Number(e.target.value))}
            className="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            data-testid="version-a-select"
          >
            <option value="">Select version...</option>
            {versions?.map((v) => (
              <option key={v.version} value={v.version}>
                v{v.version} - {new Date(v.timestamp).toLocaleDateString('de-DE')} (by{' '}
                {v.changedBy})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-sm text-gray-600 dark:text-gray-400 mb-2 block font-medium">
            Version B (Compare):
          </label>
          <select
            value={versionB ?? ''}
            onChange={(e) => setVersionB(Number(e.target.value))}
            className="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            data-testid="version-b-select"
          >
            <option value="">Select version...</option>
            {versions?.map((v) => (
              <option key={v.version} value={v.version}>
                v{v.version} - {new Date(v.timestamp).toLocaleDateString('de-DE')} (by{' '}
                {v.changedBy})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-4">
          <p className="text-red-800 dark:text-red-200 text-sm">
            Error loading diff: {error.message}
          </p>
        </div>
      )}

      {/* Side-by-Side Comparison */}
      {diff && !loading && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden mb-4">
            {/* Version A */}
            <div className="bg-gray-50 dark:bg-gray-800 p-4">
              <h4 className="font-semibold mb-3 text-gray-900 dark:text-gray-100">
                Version {diff.versionA.version}
                <span className="text-sm font-normal text-gray-500 ml-2">
                  ({new Date(diff.versionA.timestamp).toLocaleDateString('de-DE')})
                </span>
              </h4>
              <VersionContent
                version={diff.versionA}
                changes={diff.changes}
                side="left"
                formatValue={formatValue}
              />
            </div>

            {/* Version B */}
            <div className="bg-gray-50 dark:bg-gray-800 p-4">
              <h4 className="font-semibold mb-3 text-gray-900 dark:text-gray-100">
                Version {diff.versionB.version}
                <span className="text-sm font-normal text-gray-500 ml-2">
                  ({new Date(diff.versionB.timestamp).toLocaleDateString('de-DE')})
                </span>
              </h4>
              <VersionContent
                version={diff.versionB}
                changes={diff.changes}
                side="right"
                formatValue={formatValue}
              />
            </div>
          </div>

          {/* Summary */}
          <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded text-sm">
            <strong className="text-gray-900 dark:text-gray-100">Summary:</strong>{' '}
            <span className="text-gray-700 dark:text-gray-300">{diff.summary}</span>
          </div>

          {/* Change Details */}
          {(diff.changes.added.length > 0 ||
            diff.changes.removed.length > 0 ||
            diff.changes.changed.length > 0) && (
            <div className="mb-6 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <h4 className="font-semibold mb-3 text-gray-900 dark:text-gray-100">
                Change Details
              </h4>
              {diff.changes.added.length > 0 && (
                <ChangeList
                  title="Added"
                  changes={diff.changes.added}
                  icon={<Plus className="w-4 h-4" />}
                  color="green"
                  formatValue={formatValue}
                />
              )}
              {diff.changes.removed.length > 0 && (
                <ChangeList
                  title="Removed"
                  changes={diff.changes.removed}
                  icon={<Minus className="w-4 h-4" />}
                  color="red"
                  formatValue={formatValue}
                />
              )}
              {diff.changes.changed.length > 0 && (
                <ChangeList
                  title="Changed"
                  changes={diff.changes.changed}
                  icon={<ArrowRight className="w-4 h-4" />}
                  color="blue"
                  formatValue={formatValue}
                />
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-between">
            <button
              onClick={handleRevert}
              disabled={isReverting || !versionA}
              className="px-4 py-2 bg-amber-500 text-white rounded hover:bg-amber-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              data-testid="revert-button"
            >
              <RotateCcw className="w-4 h-4" />
              {isReverting ? 'Reverting...' : `Revert to Version ${versionA}`}
            </button>
            <div className="flex gap-2">
              <button
                onClick={handleExportDiff}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
                data-testid="export-diff-button"
              >
                <Download className="w-4 h-4" />
                Export Diff
              </button>
              <button
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

interface VersionContentProps {
  version: { properties: Record<string, unknown>; relationships: Array<{ type: string; target: string; weight?: number }> };
  changes: { added: FieldChange[]; removed: FieldChange[]; changed: FieldChange[] };
  side: 'left' | 'right';
  formatValue: (value: unknown) => string;
}

function VersionContent({ version, changes, side, formatValue }: VersionContentProps) {
  const allChangedFields = [
    ...changes.added.map((c) => c.field),
    ...changes.removed.map((c) => c.field),
    ...changes.changed.map((c) => c.field),
  ];

  return (
    <div className="space-y-3 text-sm">
      {/* Properties */}
      <div>
        <h5 className="font-medium text-gray-700 dark:text-gray-300 mb-2">Properties:</h5>
        <div className="bg-white dark:bg-gray-900 rounded p-3 space-y-1 max-h-64 overflow-y-auto font-mono text-xs">
          {Object.entries(version.properties).map(([key, value]) => {
            const isChanged = allChangedFields.includes(key);
            const change = changes.changed.find((c) => c.field === key);
            const isAdded = side === 'right' && changes.added.some((c) => c.field === key);
            const isRemoved = side === 'left' && changes.removed.some((c) => c.field === key);

            return (
              <div
                key={key}
                className={`${
                  isChanged || isAdded || isRemoved
                    ? isAdded
                      ? 'bg-green-100 dark:bg-green-900/30'
                      : isRemoved
                        ? 'bg-red-100 dark:bg-red-900/30'
                        : 'bg-blue-100 dark:bg-blue-900/30'
                    : ''
                } px-2 py-1 rounded`}
              >
                <span className="text-gray-500 dark:text-gray-400">{key}:</span>{' '}
                <span className="text-gray-900 dark:text-gray-100">
                  {formatValue(value)}
                </span>
                {isChanged && change && (
                  <span className="ml-2 text-blue-600 dark:text-blue-400 text-xs">[CHANGED]</span>
                )}
                {isAdded && <span className="ml-2 text-green-600 dark:text-green-400 text-xs">[ADDED]</span>}
                {isRemoved && <span className="ml-2 text-red-600 dark:text-red-400 text-xs">[REMOVED]</span>}
              </div>
            );
          })}
        </div>
      </div>

      {/* Relationships */}
      <div>
        <h5 className="font-medium text-gray-700 dark:text-gray-300 mb-2">
          Relationships: {version.relationships.length}
        </h5>
        {version.relationships.length > 0 && (
          <div className="bg-white dark:bg-gray-900 rounded p-3 space-y-1 max-h-40 overflow-y-auto text-xs">
            {version.relationships.map((rel, idx) => (
              <div key={idx} className="text-gray-700 dark:text-gray-300">
                {rel.type} → {rel.target}
                {rel.weight && ` (weight: ${rel.weight})`}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface ChangeListProps {
  title: string;
  changes: FieldChange[];
  icon: React.ReactNode;
  color: 'green' | 'red' | 'blue';
  formatValue: (value: unknown) => string;
}

function ChangeList({ title, changes, icon, color, formatValue }: ChangeListProps) {
  const colorClasses = {
    green: 'text-green-600 dark:text-green-400',
    red: 'text-red-600 dark:text-red-400',
    blue: 'text-blue-600 dark:text-blue-400',
  };

  return (
    <div className="mb-3 last:mb-0">
      <div className={`flex items-center gap-2 mb-2 ${colorClasses[color]} font-medium`}>
        {icon}
        <span>{title}</span>
      </div>
      <div className="ml-6 space-y-1 text-sm">
        {changes.map((change, idx) => (
          <div key={idx} className="font-mono text-xs">
            <span className="text-gray-600 dark:text-gray-400">{change.field}:</span>{' '}
            {change.oldValue !== undefined && (
              <span className={colorClasses.red}>{formatValue(change.oldValue)}</span>
            )}
            {change.oldValue !== undefined && change.newValue !== undefined && (
              <span className="mx-2">→</span>
            )}
            {change.newValue !== undefined && (
              <span className={colorClasses.green}>{formatValue(change.newValue)}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

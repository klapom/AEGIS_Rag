/**
 * AuditExport Component
 * Sprint 98 Feature 98.4: Audit Trail Viewer
 *
 * Export audit logs to CSV or JSON formats.
 */

import { useState } from 'react';
import { Download, FileJson, FileText } from 'lucide-react';
import type { AuditEventFilters } from '../../types/audit';

interface AuditExportProps {
  filters: AuditEventFilters;
  onExport: (format: 'json' | 'csv', includeMetadata: boolean) => void;
}

export function AuditExport({ filters, onExport }: AuditExportProps) {
  const [format, setFormat] = useState<'json' | 'csv'>('csv');
  const [includeMetadata, setIncludeMetadata] = useState(true);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Download className="w-5 h-5 text-blue-600 dark:text-blue-400" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Export Audit Log
        </h3>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 space-y-4">
        {/* Format Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Export Format
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => setFormat('csv')}
              className={`flex items-center justify-center gap-2 px-4 py-3 border-2 rounded-lg transition-colors ${
                format === 'csv'
                  ? 'border-blue-600 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-gray-400'
              }`}
            >
              <FileText className="w-5 h-5" />
              <span className="font-medium">CSV</span>
            </button>
            <button
              onClick={() => setFormat('json')}
              className={`flex items-center justify-center gap-2 px-4 py-3 border-2 rounded-lg transition-colors ${
                format === 'json'
                  ? 'border-blue-600 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                  : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-gray-400'
              }`}
            >
              <FileJson className="w-5 h-5" />
              <span className="font-medium">JSON</span>
            </button>
          </div>
        </div>

        {/* Options */}
        <div className="space-y-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={includeMetadata}
              onChange={(e) => setIncludeMetadata(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              Include event metadata
            </span>
          </label>
        </div>

        {/* Current Filters Info */}
        <div className="text-xs text-gray-600 dark:text-gray-400 p-3 bg-gray-50 dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600">
          <div className="font-medium mb-1">Export will include:</div>
          <ul className="list-disc list-inside space-y-0.5">
            {filters.eventType && <li>Event Type: {filters.eventType}</li>}
            {filters.outcome && <li>Outcome: {filters.outcome}</li>}
            {filters.actorId && <li>Actor: {filters.actorId}</li>}
            {filters.startTime && (
              <li>From: {new Date(filters.startTime).toLocaleString()}</li>
            )}
            {filters.endTime && <li>To: {new Date(filters.endTime).toLocaleString()}</li>}
            {!filters.eventType &&
              !filters.outcome &&
              !filters.actorId &&
              !filters.startTime &&
              !filters.endTime && <li>All events (no filters applied)</li>}
          </ul>
        </div>

        {/* Export Button */}
        <button
          onClick={() => onExport(format, includeMetadata)}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          <Download className="w-4 h-4" />
          Export {format.toUpperCase()}
        </button>
      </div>
    </div>
  );
}

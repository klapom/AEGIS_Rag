/**
 * GraphExportButton Component
 * Sprint 29 Feature 29.3: Admin Graph Analytics View
 *
 * Features:
 * - Dropdown with 3 export format options (JSON, GraphML, Cytoscape/GEXF)
 * - Downloads graph data as file with timestamp
 * - Calls backend /export endpoint with current filters
 * - Visual feedback during download
 */

import { useState } from 'react';
import type { GraphFilters } from '../../types/graph';

interface GraphExportButtonProps {
  filters: GraphFilters;
  disabled?: boolean;
}

type ExportFormat = 'json' | 'graphml' | 'gexf';

interface ExportFormatOption {
  value: ExportFormat;
  label: string;
  extension: string;
  description: string;
}

const EXPORT_FORMATS: ExportFormatOption[] = [
  {
    value: 'json',
    label: 'JSON',
    extension: 'json',
    description: 'Compatible with D3.js, Cytoscape.js, react-force-graph',
  },
  {
    value: 'graphml',
    label: 'GraphML',
    extension: 'graphml',
    description: 'Compatible with Gephi, yEd, Neo4j',
  },
  {
    value: 'gexf',
    label: 'Cytoscape (GEXF)',
    extension: 'gexf',
    description: 'Compatible with Cytoscape Desktop',
  },
];

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Component for exporting graph data in various formats
 *
 * @param filters Current graph filters to apply to export
 * @param disabled Whether the export button is disabled
 */
export function GraphExportButton({ filters, disabled = false }: GraphExportButtonProps) {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('json');
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async (format: ExportFormat) => {
    setIsExporting(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/graph/viz/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          format,
          max_nodes: filters.maxNodes || 100,
          entity_types: filters.entityTypes,
          include_communities: true,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Export failed: ${errorText}`);
      }

      // Get response as text/blob depending on format
      let data: string;
      let contentType: string;

      if (format === 'json') {
        const jsonData = await response.json();
        data = JSON.stringify(jsonData, null, 2);
        contentType = 'application/json';
      } else {
        data = await response.text();
        contentType = 'application/xml';
      }

      // Create blob and download
      const blob = new Blob([data], { type: contentType });
      const url = window.URL.createObjectURL(blob);
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      const extension = EXPORT_FORMATS.find((f) => f.value === format)?.extension || format;
      const filename = `aegis-graph-${timestamp}.${extension}`;

      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Export failed';
      setError(errorMessage);
      console.error('Graph export error:', err);
    } finally {
      setIsExporting(false);
    }
  };

  const selectedFormatOption = EXPORT_FORMATS.find((f) => f.value === selectedFormat);

  return (
    <div className="space-y-2">
      {/* Format Selection */}
      <div>
        <label htmlFor="export-format" className="block text-sm font-semibold text-gray-900 mb-2">
          Export Format
        </label>
        <select
          id="export-format"
          value={selectedFormat}
          onChange={(e) => setSelectedFormat(e.target.value as ExportFormat)}
          disabled={disabled || isExporting}
          className="w-full px-3 py-2 text-sm bg-white border-2 border-gray-300 rounded-lg
                     focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20
                     hover:border-gray-400 transition-all duration-200 cursor-pointer
                     disabled:bg-gray-100 disabled:cursor-not-allowed"
          aria-label="Select export format"
        >
          {EXPORT_FORMATS.map((format) => (
            <option key={format.value} value={format.value}>
              {format.label}
            </option>
          ))}
        </select>
        {selectedFormatOption && (
          <p className="mt-1.5 text-xs text-gray-500">{selectedFormatOption.description}</p>
        )}
      </div>

      {/* Export Button */}
      <button
        onClick={() => handleExport(selectedFormat)}
        disabled={disabled || isExporting}
        className="w-full px-4 py-2.5 text-sm font-semibold text-white bg-primary
                   hover:bg-primary-hover active:bg-primary-active
                   disabled:bg-gray-300 disabled:cursor-not-allowed
                   rounded-lg transition-colors duration-200
                   flex items-center justify-center space-x-2"
        aria-label={`Export graph as ${selectedFormatOption?.label}`}
      >
        {isExporting ? (
          <>
            <svg
              className="animate-spin h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span>Exporting...</span>
          </>
        ) : (
          <>
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            <span>Export Graph</span>
          </>
        )}
      </button>

      {/* Error Message */}
      {error && (
        <div className="p-3 bg-red-50 border-2 border-red-200 rounded-lg">
          <div className="flex items-start space-x-2">
            <svg
              className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <div className="flex-grow">
              <p className="text-sm font-medium text-red-800">Export Failed</p>
              <p className="text-xs text-red-700 mt-1">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-red-500 hover:text-red-700"
              aria-label="Dismiss error"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Export Info */}
      <div className="p-3 bg-blue-50 border-2 border-blue-200 rounded-lg">
        <div className="text-xs text-blue-800 space-y-1">
          <p className="font-semibold">Export includes:</p>
          <ul className="list-disc list-inside space-y-0.5 ml-2">
            <li>Nodes with metadata</li>
            <li>Edges with relationships</li>
            <li>Community assignments</li>
            <li>Current filter settings</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

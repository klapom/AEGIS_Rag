/**
 * NamespaceSelector Component
 * Sprint 42: Project/Namespace selection for search filtering
 *
 * Displays available namespaces as checkboxes to filter search results.
 * Fetches namespaces from backend and allows multi-select.
 */

import { useState, useEffect } from 'react';
import { getNamespaces, type NamespaceInfo } from '../../api/admin';

interface NamespaceSelectorProps {
  selectedNamespaces: string[];
  onSelectionChange: (namespaces: string[]) => void;
}

// Display-friendly labels for namespace types
const NAMESPACE_TYPE_LABELS: Record<string, string> = {
  general: 'Allgemein',
  project: 'Projekt',
  evaluation: 'Evaluation',
  test: 'Test',
};

// Icons for namespace types
const NAMESPACE_TYPE_ICONS: Record<string, string> = {
  general: '📁',
  project: '📂',
  evaluation: '📊',
  test: '🧪',
};

export function NamespaceSelector({
  selectedNamespaces,
  onSelectionChange,
}: NamespaceSelectorProps) {
  const [namespaces, setNamespaces] = useState<NamespaceInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    const fetchNamespaces = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await getNamespaces();
        setNamespaces(response.namespaces);

        // If no namespaces selected, select all by default
        if (selectedNamespaces.length === 0 && response.namespaces.length > 0) {
          onSelectionChange(response.namespaces.map(ns => ns.namespace_id));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load namespaces');
        console.error('Failed to fetch namespaces:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchNamespaces();
  }, []);

  const handleToggle = (namespaceId: string) => {
    if (selectedNamespaces.includes(namespaceId)) {
      // Don't allow deselecting all namespaces
      if (selectedNamespaces.length > 1) {
        onSelectionChange(selectedNamespaces.filter(id => id !== namespaceId));
      }
    } else {
      onSelectionChange([...selectedNamespaces, namespaceId]);
    }
  };

  const handleSelectAll = () => {
    onSelectionChange(namespaces.map(ns => ns.namespace_id));
  };

  const handleSelectNone = () => {
    // Keep at least one selected (first one)
    if (namespaces.length > 0) {
      onSelectionChange([namespaces[0].namespace_id]);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-2 text-sm text-gray-500">
        <svg className="animate-spin h-4 w-4 mr-2" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        Projekte laden...
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-sm text-red-500 py-2">
        Fehler: {error}
      </div>
    );
  }

  if (namespaces.length === 0) {
    return (
      <div className="text-sm text-gray-500 py-2">
        Keine Projekte verfügbar
      </div>
    );
  }

  const selectedCount = selectedNamespaces.length;
  const totalCount = namespaces.length;

  return (
    <div className="w-full">
      {/* Collapsed view - clickable header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg border border-gray-200 transition-colors"
        data-testid="namespace-selector-toggle"
      >
        <div className="flex items-center space-x-2">
          <span className="text-gray-500">📂</span>
          <span className="text-sm font-medium text-gray-700">
            Projekte ({selectedCount}/{totalCount} ausgewählt)
          </span>
        </div>
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded view - namespace list */}
      {isExpanded && (
        <div className="mt-2 p-3 bg-white border border-gray-200 rounded-lg shadow-sm">
          {/* Quick actions */}
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-gray-100">
            <span className="text-xs text-gray-500 uppercase tracking-wider">Schnellauswahl</span>
            <div className="flex space-x-2">
              <button
                onClick={handleSelectAll}
                className="text-xs text-primary hover:text-primary-hover transition-colors"
                data-testid="namespace-select-all"
              >
                Alle
              </button>
              <span className="text-gray-300">|</span>
              <button
                onClick={handleSelectNone}
                className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
                data-testid="namespace-select-none"
              >
                Nur erstes
              </button>
            </div>
          </div>

          {/* Namespace checkboxes */}
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {namespaces.map((ns) => {
              const isSelected = selectedNamespaces.includes(ns.namespace_id);
              const icon = NAMESPACE_TYPE_ICONS[ns.namespace_type] || '📁';
              const typeLabel = NAMESPACE_TYPE_LABELS[ns.namespace_type] || ns.namespace_type;

              return (
                <label
                  key={ns.namespace_id}
                  className={`
                    flex items-center justify-between p-2 rounded-lg cursor-pointer
                    transition-colors
                    ${isSelected
                      ? 'bg-primary/10 border border-primary/30'
                      : 'bg-gray-50 border border-transparent hover:bg-gray-100'
                    }
                  `}
                  data-testid={`namespace-${ns.namespace_id}`}
                >
                  <div className="flex items-center space-x-3">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => handleToggle(ns.namespace_id)}
                      className="w-4 h-4 text-primary rounded border-gray-300 focus:ring-primary"
                    />
                    <span className="text-lg" role="img" aria-label={typeLabel}>
                      {icon}
                    </span>
                    <div className="flex flex-col">
                      <span className={`text-sm ${isSelected ? 'font-medium text-gray-900' : 'text-gray-700'}`}>
                        {ns.namespace_id}
                      </span>
                      <span className="text-xs text-gray-500">
                        {typeLabel} · {ns.document_count} Dokumente
                      </span>
                    </div>
                  </div>
                </label>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

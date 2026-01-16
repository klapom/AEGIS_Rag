/**
 * MemoryManagementPage Component
 * Sprint 72 Feature 72.3: Memory Management UI
 *
 * Main admin page for memory debugging and management.
 * Features:
 * - Tab layout: Stats | Search | Consolidation
 * - Real-time memory statistics for all layers
 * - Memory search with filters
 * - Manual consolidation trigger and history
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { BarChart3, Search, Layers, ArrowLeft } from 'lucide-react';
import { MemoryStatsCard } from '../../components/admin/MemoryStatsCard';
import { MemorySearchPanel } from '../../components/admin/MemorySearchPanel';
import { ConsolidationControl } from '../../components/admin/ConsolidationControl';
import { AdminNavigationBar } from '../../components/admin/AdminNavigationBar';

/**
 * Tab type for the memory management page
 */
type MemoryTab = 'stats' | 'search' | 'consolidation';

/**
 * Tab button configuration
 */
interface TabConfig {
  id: MemoryTab;
  label: string;
  icon: typeof BarChart3;
  description: string;
}

const tabs: TabConfig[] = [
  {
    id: 'stats',
    label: 'Statistics',
    icon: BarChart3,
    description: 'View memory layer statistics',
  },
  {
    id: 'search',
    label: 'Search',
    icon: Search,
    description: 'Search across memory layers',
  },
  {
    id: 'consolidation',
    label: 'Consolidation',
    icon: Layers,
    description: 'Manage memory consolidation',
  },
];

/**
 * Tab button component
 */
function TabButton({
  tab,
  isActive,
  onClick,
}: {
  tab: TabConfig;
  isActive: boolean;
  onClick: () => void;
}) {
  const Icon = tab.icon;

  return (
    <button
      role="tab"
      aria-selected={isActive}
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
        isActive
          ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
          : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
      }`}
      data-testid={`tab-${tab.id}`}
    >
      <Icon className="w-4 h-4" />
      {tab.label}
    </button>
  );
}

/**
 * MemoryManagementPage - Main memory management admin page
 */
export function MemoryManagementPage() {
  const [activeTab, setActiveTab] = useState<MemoryTab>('stats');
  const [sessionId] = useState<string>('');

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900" data-testid="memory-management-page">
      {/* Admin Navigation */}
      <div className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <AdminNavigationBar />
      </div>

      {/* Page Header */}
      <div className="bg-white dark:bg-gray-800 border-b-2 border-gray-200 dark:border-gray-700 px-6 py-6">
        <Link
          to="/admin"
          className="inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Admin
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Memory Management</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Debug and manage the 3-layer memory system (Redis, Qdrant, Graphiti)
            </p>
          </div>
          <div
            className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1"
            role="tablist"
            data-testid="memory-tabs-container"
          >
            {tabs.map((tab) => (
              <TabButton
                key={tab.id}
                tab={tab}
                isActive={activeTab === tab.id}
                onClick={() => setActiveTab(tab.id)}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Tab Content */}
      <div className="p-6" data-testid="tab-content-wrapper">
        <div className="max-w-7xl mx-auto">
          {/* Tab Description */}
          <div className="mb-6">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {tabs.find((t) => t.id === activeTab)?.description}
            </p>
          </div>

          {/* Stats Tab */}
          {activeTab === 'stats' && (
            <div data-testid="stats-tab-content">
              <MemoryStatsCard />

              {/* Additional Info Section */}
              <div
                className="mt-6 bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-800 rounded-xl p-6"
                data-testid="memory-layers-info"
              >
                <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">About the Memory Layers</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <h4 className="font-medium text-blue-800 dark:text-blue-300 mb-1">Redis (Layer 1)</h4>
                    <p className="text-blue-700 dark:text-blue-400">
                      Short-term session cache. Stores recent conversation context with fast access times.
                      Hit rate indicates cache effectiveness.
                    </p>
                  </div>
                  <div>
                    <h4 className="font-medium text-blue-800 dark:text-blue-300 mb-1">Qdrant (Layer 2)</h4>
                    <p className="text-blue-700 dark:text-blue-400">
                      Vector store for semantic search. Contains embedded memories for similarity-based retrieval.
                      Lower latency means faster searches.
                    </p>
                  </div>
                  <div>
                    <h4 className="font-medium text-blue-800 dark:text-blue-300 mb-1">Graphiti (Layer 3)</h4>
                    <p className="text-blue-700 dark:text-blue-400">
                      Temporal memory graph. Stores entities and episodes with temporal relationships
                      for long-term knowledge retention.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Search Tab */}
          {activeTab === 'search' && (
            <div data-testid="search-tab-content">
              <MemorySearchPanel />

              {/* Search Tips */}
              <div
                className="mt-6 bg-gray-50 dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 rounded-xl p-6"
                data-testid="memory-search-tips"
              >
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">Search Tips</h3>
                <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                  <li className="flex items-start gap-2">
                    <span className="text-blue-500 font-bold">*</span>
                    <span>Use the query field for semantic search across all memory content</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-blue-500 font-bold">*</span>
                    <span>Filter by User ID to see all memories for a specific user</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-blue-500 font-bold">*</span>
                    <span>Session ID filter shows conversation-specific memories</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-blue-500 font-bold">*</span>
                    <span>Results show which layer the memory is stored in (Redis, Qdrant, or Graphiti)</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-blue-500 font-bold">*</span>
                    <span>Export a session to download all its memories as JSON</span>
                  </li>
                </ul>
              </div>
            </div>
          )}

          {/* Consolidation Tab */}
          {activeTab === 'consolidation' && (
            <div data-testid="consolidation-tab-content">
              <ConsolidationControl sessionId={sessionId} />

              {/* Consolidation Info */}
              <div
                className="mt-6 bg-gray-50 dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 rounded-xl p-6"
                data-testid="consolidation-info"
              >
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">What is Memory Consolidation?</h3>
                <div className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
                  <p>
                    Memory consolidation is the process of transferring short-term memories from Redis
                    into long-term storage in Qdrant and Graphiti. This mimics how human memory works,
                    moving important information from working memory to long-term memory.
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                    <div className="bg-white dark:bg-gray-700 rounded-lg p-4">
                      <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">Step 1: Extraction</h4>
                      <p className="text-xs">
                        Important memories are identified from Redis based on relevance, frequency, and recency.
                      </p>
                    </div>
                    <div className="bg-white dark:bg-gray-700 rounded-lg p-4">
                      <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">Step 2: Embedding</h4>
                      <p className="text-xs">
                        Extracted memories are converted to vector embeddings and stored in Qdrant
                        for semantic search.
                      </p>
                    </div>
                    <div className="bg-white dark:bg-gray-700 rounded-lg p-4">
                      <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">Step 3: Graphing</h4>
                      <p className="text-xs">
                        Entities and relationships are extracted and added to the Graphiti temporal graph.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default MemoryManagementPage;

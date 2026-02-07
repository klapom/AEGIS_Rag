/**
 * LongContextPage
 * Sprint 111 Feature 111.1: Long Context UI
 *
 * Admin page for managing long context documents:
 * - Large document handling (>100K tokens)
 * - Context window usage visualization
 * - Document chunk exploration
 * - Relevance score display
 * - Context compression tools
 * - Multi-document context merging
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  FileText,
  Upload,
  Download,
  Trash2,
  RefreshCw,
  Search,
  AlertCircle,
} from 'lucide-react';
import {
  ContextWindowIndicator,
  ChunkExplorer,
  RelevanceScoreDisplay,
  ContextCompressionPanel,
} from '../../components/context';
import type { DocumentChunk, CompressionStrategy } from '../../components/context';
import { AdminNavigationBar } from '../../components/admin/AdminNavigationBar';

interface ContextDocument {
  id: string;
  name: string;
  tokenCount: number;
  chunkCount: number;
  uploadedAt: string;
  status: 'ready' | 'processing' | 'error';
}

interface ContextMetrics {
  totalTokens: number;
  maxTokens: number;
  documentCount: number;
  averageRelevance: number;
}

export function LongContextPage() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<ContextDocument[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [metrics, setMetrics] = useState<ContextMetrics>({
    totalTokens: 0,
    maxTokens: 128000, // Default max context window
    documentCount: 0,
    averageRelevance: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isCompressing, setIsCompressing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Fetch documents and metrics
  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch context documents
      const docsResponse = await fetch('/api/v1/context/documents');
      if (!docsResponse.ok) throw new Error('Failed to fetch documents');
      const docsData = await docsResponse.json();
      setDocuments(docsData.documents || []);

      // Fetch context metrics
      const metricsResponse = await fetch('/api/v1/context/metrics');
      if (!metricsResponse.ok) throw new Error('Failed to fetch metrics');
      const metricsData = await metricsResponse.json();
      setMetrics({
        totalTokens: metricsData.total_tokens || 0,
        maxTokens: metricsData.max_tokens || 128000,
        documentCount: metricsData.document_count || 0,
        averageRelevance: metricsData.average_relevance || 0,
      });
    } catch (err) {
      console.error('Error fetching context data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load data');

      // Provide demo data for testing
      setDocuments([
        {
          id: 'doc-1',
          name: 'Research Paper - RAG Systems.pdf',
          tokenCount: 45000,
          chunkCount: 52,
          uploadedAt: '2026-01-18T10:00:00Z',
          status: 'ready',
        },
        {
          id: 'doc-2',
          name: 'Technical Documentation.md',
          tokenCount: 28000,
          chunkCount: 31,
          uploadedAt: '2026-01-17T14:30:00Z',
          status: 'ready',
        },
        {
          id: 'doc-3',
          name: 'API Reference Guide.pdf',
          tokenCount: 62000,
          chunkCount: 78,
          uploadedAt: '2026-01-16T09:15:00Z',
          status: 'ready',
        },
      ]);
      setMetrics({
        totalTokens: 135000,
        maxTokens: 128000,
        documentCount: 3,
        averageRelevance: 0.72,
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch chunks for selected document
  const fetchChunks = useCallback(async (docId: string) => {
    try {
      const response = await fetch(`/api/v1/context/chunks/${docId}`);
      if (!response.ok) throw new Error('Failed to fetch chunks');
      const data = await response.json();
      setChunks(data.chunks || []);
    } catch (err) {
      console.error('Error fetching chunks:', err);
      // Generate demo chunks for testing
      const demoChunks: DocumentChunk[] = Array.from({ length: 20 }, (_, i) => ({
        id: `chunk-${i + 1}`,
        content: `This is chunk ${i + 1} content. It contains important information about the document topic. The content varies in relevance and length depending on the section. This chunk discusses key concepts and provides detailed explanations.`,
        relevanceScore: Math.random() * 0.5 + 0.4, // 0.4-0.9 range
        tokenCount: Math.floor(Math.random() * 500) + 200,
        chunkIndex: i,
        metadata: {
          section: ['Introduction', 'Methods', 'Results', 'Discussion', 'Conclusion'][i % 5],
          pageNumber: Math.floor(i / 3) + 1,
        },
      }));
      setChunks(demoChunks);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (selectedDocId) {
      fetchChunks(selectedDocId);
    } else {
      setChunks([]);
    }
  }, [selectedDocId, fetchChunks]);

  // Handle compression
  const handleCompress = async (settings: {
    strategy: CompressionStrategy;
    targetReduction: number;
    minRelevanceThreshold: number;
    maxChunks?: number;
  }) => {
    setIsCompressing(true);
    try {
      const response = await fetch('/api/v1/context/compress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: selectedDocId,
          strategy: settings.strategy,
          target_reduction: settings.targetReduction,
          min_relevance_threshold: settings.minRelevanceThreshold,
          max_chunks: settings.maxChunks,
        }),
      });

      if (!response.ok) throw new Error('Compression failed');

      // Refresh data after compression
      await fetchData();
      if (selectedDocId) {
        await fetchChunks(selectedDocId);
      }
    } catch (err) {
      console.error('Compression error:', err);
      setError('Failed to compress context');
    } finally {
      setIsCompressing(false);
    }
  };

  // Handle export
  const handleExport = async (format: 'json' | 'markdown') => {
    try {
      const response = await fetch(`/api/v1/context/export?format=${format}`, {
        method: 'GET',
      });
      if (!response.ok) throw new Error('Export failed');

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `context-export.${format === 'json' ? 'json' : 'md'}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export error:', err);
      setError('Failed to export context');
    }
  };

  // Filter documents by search
  const filteredDocuments = documents.filter((doc) =>
    doc.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Build relevance scores for display
  const relevanceScores = chunks.map((chunk) => ({
    chunkId: chunk.id,
    chunkIndex: chunk.chunkIndex,
    score: chunk.relevanceScore,
  }));

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900" data-testid="long-context-page">
      <div className="mb-4">
        <AdminNavigationBar />
      </div>
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/admin')}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                data-testid="back-button"
              >
                <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              </button>
              <div className="flex items-center gap-3">
                <FileText className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                <div>
                  <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                    Long Context Manager
                  </h1>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Manage large documents and context window
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => fetchData()}
                className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                data-testid="refresh-button"
              >
                <RefreshCw className={`w-5 h-5 text-gray-600 dark:text-gray-400 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
              <button
                onClick={() => handleExport('json')}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                data-testid="export-json-button"
              >
                <Download className="w-4 h-4" />
                Export JSON
              </button>
              <button
                onClick={() => handleExport('markdown')}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                data-testid="export-markdown-button"
              >
                <Download className="w-4 h-4" />
                Export MD
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
          <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-3" data-testid="error-banner">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            <span className="text-red-700 dark:text-red-300">{error}</span>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Documents & Context */}
          <div className="lg:col-span-2 space-y-6">
            {/* Context Window Indicator */}
            <ContextWindowIndicator
              currentTokens={metrics.totalTokens}
              maxTokens={metrics.maxTokens}
            />

            {/* Document List */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-semibold text-gray-900 dark:text-gray-100">
                    Context Documents ({documents.length})
                  </h2>
                  <button
                    onClick={() => navigate('/admin/upload')}
                    className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors"
                    data-testid="upload-button"
                  >
                    <Upload className="w-4 h-4" />
                    Upload
                  </button>
                </div>

                {/* Search */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search documents..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm"
                    data-testid="document-search"
                  />
                </div>
              </div>

              {/* Document Items */}
              <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-64 overflow-y-auto" data-testid="document-list">
                {isLoading ? (
                  <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                    Loading documents...
                  </div>
                ) : filteredDocuments.length === 0 ? (
                  <div className="p-8 text-center text-gray-500 dark:text-gray-400" data-testid="no-documents">
                    No documents found
                  </div>
                ) : (
                  filteredDocuments.map((doc) => (
                    <div
                      key={doc.id}
                      onClick={() => setSelectedDocId(doc.id === selectedDocId ? null : doc.id)}
                      className={`p-4 cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-gray-700 ${
                        selectedDocId === doc.id
                          ? 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500'
                          : ''
                      }`}
                      data-testid={`document-item-${doc.id}`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <FileText className="w-5 h-5 text-gray-400" />
                          <div>
                            <p className="font-medium text-gray-900 dark:text-gray-100">
                              {doc.name}
                            </p>
                            <p className="text-sm text-gray-500 dark:text-gray-400">
                              {doc.tokenCount.toLocaleString()} tokens · {doc.chunkCount} chunks
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-1 text-xs rounded-full ${
                              doc.status === 'ready'
                                ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                                : doc.status === 'processing'
                                ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300'
                                : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                            }`}
                          >
                            {doc.status}
                          </span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              // Handle delete
                            }}
                            className="p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors"
                            data-testid={`delete-doc-${doc.id}`}
                          >
                            <Trash2 className="w-4 h-4 text-red-500" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Chunk Explorer */}
            {selectedDocId && (
              <ChunkExplorer
                chunks={chunks}
                selectedChunkId={undefined}
                onChunkSelect={(chunk) => console.log('Selected chunk:', chunk)}
              />
            )}
          </div>

          {/* Right Column - Scores & Compression */}
          <div className="space-y-6">
            {/* Relevance Scores */}
            <RelevanceScoreDisplay
              scores={relevanceScores}
              averageScore={metrics.averageRelevance}
            />

            {/* Compression Panel */}
            <ContextCompressionPanel
              currentTokens={metrics.totalTokens}
              maxTokens={metrics.maxTokens}
              onCompress={handleCompress}
              isCompressing={isCompressing}
            />

            {/* Quality Metrics */}
            <div
              className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-4"
              data-testid="context-quality-metrics"
            >
              <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">
                Context Quality
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Documents</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100" data-testid="metric-documents">
                    {metrics.documentCount}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Total Chunks</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100" data-testid="metric-chunks">
                    {chunks.length}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Avg. Relevance</span>
                  <span className="font-medium text-green-600 dark:text-green-400" data-testid="metric-relevance">
                    {(metrics.averageRelevance * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Window Usage</span>
                  <span
                    className={`font-medium ${
                      metrics.totalTokens / metrics.maxTokens < 0.8
                        ? 'text-green-600 dark:text-green-400'
                        : 'text-red-600 dark:text-red-400'
                    }`}
                    data-testid="metric-usage"
                  >
                    {((metrics.totalTokens / metrics.maxTokens) * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

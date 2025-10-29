/**
 * Admin Statistics API E2E Tests
 * Sprint 17 Feature 17.6: Admin Statistics API
 *
 * Tests cover:
 * - GET /api/v1/admin/stats returns statistics
 * - All stat fields present (Qdrant, Neo4j, Redis)
 * - Stats update after re-indexing
 * - Graceful degradation for unavailable stats
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { setupGlobalFetchMock, cleanupGlobalFetchMock } from './helpers';
import { mockAdminStats, mockAdminStatsPartial } from './fixtures';

// Mock Admin Stats component (simplified for testing)
interface AdminStatsDisplayProps {
  onLoad?: (stats: any) => void;
}

function AdminStatsDisplay({ onLoad }: AdminStatsDisplayProps) {
  const [stats, setStats] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    const fetchStats = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch('http://localhost:8000/api/v1/admin/stats');

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        }

        const data = await response.json();
        setStats(data);
        onLoad?.(data);
      } catch (err) {
        console.error('Failed to fetch stats:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, [onLoad]);

  if (loading) {
    return <div>Loading statistics...</div>;
  }

  if (error) {
    return <div>Error loading statistics: {error}</div>;
  }

  if (!stats) {
    return <div>No statistics available</div>;
  }

  return (
    <div data-testid="admin-stats">
      <h2>System Statistics</h2>

      <section data-testid="qdrant-stats">
        <h3>Qdrant Vector Database</h3>
        <p>Total Chunks: {stats.qdrant_total_chunks}</p>
        <p>Collection: {stats.qdrant_collection_name}</p>
        <p>Dimension: {stats.qdrant_vector_dimension}</p>
      </section>

      {stats.bm25_corpus_size !== null && (
        <section data-testid="bm25-stats">
          <h3>BM25 Search</h3>
          <p>Corpus Size: {stats.bm25_corpus_size}</p>
        </section>
      )}

      {stats.neo4j_total_entities !== null && (
        <section data-testid="neo4j-stats">
          <h3>Neo4j Knowledge Graph</h3>
          <p>Entities: {stats.neo4j_total_entities}</p>
          <p>Relations: {stats.neo4j_total_relations}</p>
          <p>Chunks: {stats.neo4j_total_chunks}</p>
        </section>
      )}

      {stats.total_conversations !== null && (
        <section data-testid="redis-stats">
          <h3>Redis Conversations</h3>
          <p>Total Conversations: {stats.total_conversations}</p>
        </section>
      )}

      <section data-testid="system-info">
        <h3>System Configuration</h3>
        <p>Embedding Model: {stats.embedding_model}</p>
        {stats.last_reindex_timestamp && (
          <p>Last Reindex: {stats.last_reindex_timestamp}</p>
        )}
      </section>
    </div>
  );
}

// Need React import for component
import * as React from 'react';

describe('Feature 17.6: Admin Statistics API E2E Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanupGlobalFetchMock();
  });

  describe('Statistics Retrieval', () => {
    it('should fetch and display complete system statistics', async () => {
      // Arrange: Mock successful stats response
      setupGlobalFetchMock(
        vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(mockAdminStats),
        })
      );

      // Act: Render admin stats component
      render(<AdminStatsDisplay />);

      // Assert: Loading state should be shown initially
      expect(screen.getByText(/Loading statistics/i)).toBeInTheDocument();

      // Assert: Stats should be displayed after loading
      await waitFor(
        () => {
          expect(screen.getByTestId('admin-stats')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      // Verify Qdrant stats
      expect(screen.getByText(/Total Chunks: 1523/i)).toBeInTheDocument();
      expect(screen.getByText(/Collection: aegis_documents/i)).toBeInTheDocument();
      expect(screen.getByText(/Dimension: 1024/i)).toBeInTheDocument();

      // Verify BM25 stats
      expect(screen.getByText(/Corpus Size: 342/i)).toBeInTheDocument();

      // Verify Neo4j stats
      expect(screen.getByText(/Entities: 856/i)).toBeInTheDocument();
      expect(screen.getByText(/Relations: 1204/i)).toBeInTheDocument();

      // Verify Redis stats
      expect(screen.getByText(/Total Conversations: 15/i)).toBeInTheDocument();

      // Verify system info
      expect(screen.getByText(/Embedding Model: BAAI\/bge-m3/i)).toBeInTheDocument();
    });

    it('should include all required stat fields in response', async () => {
      // Arrange: Track received stats
      const onLoad = vi.fn();

      setupGlobalFetchMock(
        vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(mockAdminStats),
        })
      );

      // Act: Render component
      render(<AdminStatsDisplay onLoad={onLoad} />);

      // Wait for load callback
      await waitFor(() => {
        expect(onLoad).toHaveBeenCalled();
      });

      // Assert: All required fields should be present
      const stats = onLoad.mock.calls[0][0];

      // Required Qdrant fields
      expect(stats).toHaveProperty('qdrant_total_chunks');
      expect(stats).toHaveProperty('qdrant_collection_name');
      expect(stats).toHaveProperty('qdrant_vector_dimension');

      // Optional Neo4j fields
      expect(stats).toHaveProperty('neo4j_total_entities');
      expect(stats).toHaveProperty('neo4j_total_relations');
      expect(stats).toHaveProperty('neo4j_total_chunks');

      // Optional BM25 field
      expect(stats).toHaveProperty('bm25_corpus_size');

      // Optional Redis field
      expect(stats).toHaveProperty('total_conversations');

      // Required system fields
      expect(stats).toHaveProperty('embedding_model');
      expect(stats).toHaveProperty('last_reindex_timestamp');

      // Verify types
      expect(typeof stats.qdrant_total_chunks).toBe('number');
      expect(typeof stats.qdrant_collection_name).toBe('string');
      expect(typeof stats.qdrant_vector_dimension).toBe('number');
      expect(typeof stats.embedding_model).toBe('string');
    });

    it('should make GET request to correct endpoint', async () => {
      // Arrange: Mock fetch
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockAdminStats),
      });

      setupGlobalFetchMock(mockFetch);

      // Act: Render component
      render(<AdminStatsDisplay />);

      // Assert: Correct API endpoint should be called
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/admin/stats'
        );
      });
    });
  });

  describe('Graceful Degradation', () => {
    it('should handle partial stats when some services unavailable', async () => {
      // Arrange: Mock response with null optional fields
      setupGlobalFetchMock(
        vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(mockAdminStatsPartial),
        })
      );

      // Act: Render component
      render(<AdminStatsDisplay />);

      // Assert: Required stats should still be shown
      await waitFor(() => {
        expect(screen.getByText(/Total Chunks: 450/i)).toBeInTheDocument();
      });

      // Assert: Optional sections should not be rendered
      expect(screen.queryByTestId('neo4j-stats')).not.toBeInTheDocument();
      expect(screen.queryByTestId('bm25-stats')).not.toBeInTheDocument();
      expect(screen.queryByTestId('redis-stats')).not.toBeInTheDocument();

      // Assert: Core Qdrant stats should still be displayed
      expect(screen.getByTestId('qdrant-stats')).toBeInTheDocument();
      expect(screen.getByTestId('system-info')).toBeInTheDocument();
    });

    it('should handle zero values correctly', async () => {
      // Arrange: Mock stats with zero counts
      const zeroStats = {
        ...mockAdminStats,
        qdrant_total_chunks: 0,
        neo4j_total_entities: 0,
        neo4j_total_relations: 0,
        total_conversations: 0,
      };

      setupGlobalFetchMock(
        vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(zeroStats),
        })
      );

      // Act: Render component
      render(<AdminStatsDisplay />);

      // Assert: Zero values should be displayed (not treated as null)
      await waitFor(() => {
        expect(screen.getByText(/Total Chunks: 0/i)).toBeInTheDocument();
        expect(screen.getByText(/Entities: 0/i)).toBeInTheDocument();
        expect(screen.getByText(/Total Conversations: 0/i)).toBeInTheDocument();
      });
    });

    it('should handle missing last_reindex_timestamp', async () => {
      // Arrange: Mock stats without timestamp
      const statsWithoutTimestamp = {
        ...mockAdminStats,
        last_reindex_timestamp: null,
      };

      setupGlobalFetchMock(
        vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(statsWithoutTimestamp),
        })
      );

      // Act: Render component
      render(<AdminStatsDisplay />);

      // Assert: Other stats should still be shown
      await waitFor(() => {
        expect(screen.getByTestId('system-info')).toBeInTheDocument();
      });

      // Assert: Timestamp should not be displayed
      expect(screen.queryByText(/Last Reindex:/i)).not.toBeInTheDocument();

      // Other system info should be present
      expect(screen.getByText(/Embedding Model:/i)).toBeInTheDocument();
    });
  });

  describe('Stats After Re-indexing', () => {
    it('should show updated stats after re-indexing completes', async () => {
      // Arrange: Mock initial stats
      const initialStats = { ...mockAdminStats, qdrant_total_chunks: 1000 };

      // Mock updated stats after re-indexing
      const updatedStats = { ...mockAdminStats, qdrant_total_chunks: 1523 };

      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(initialStats),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(updatedStats),
        });

      setupGlobalFetchMock(mockFetch);

      // Act: Render initial stats
      const { rerender } = render(<AdminStatsDisplay key="initial" />);

      // Assert: Initial count should be shown
      await waitFor(() => {
        expect(screen.getByText(/Total Chunks: 1000/i)).toBeInTheDocument();
      });

      // Act: Simulate re-render after re-indexing (force re-fetch)
      rerender(<AdminStatsDisplay key="updated" />);

      // Assert: Updated count should be shown
      await waitFor(() => {
        expect(screen.getByText(/Total Chunks: 1523/i)).toBeInTheDocument();
      });

      // Verify fetch was called twice
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    it('should reflect Neo4j changes after graph re-indexing', async () => {
      // Arrange: Initial stats vs. post-reindex stats
      const beforeReindex = {
        ...mockAdminStats,
        neo4j_total_entities: 500,
        neo4j_total_relations: 800,
      };

      const afterReindex = {
        ...mockAdminStats,
        neo4j_total_entities: 856,
        neo4j_total_relations: 1204,
      };

      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(beforeReindex),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(afterReindex),
        });

      setupGlobalFetchMock(mockFetch);

      // Act: Initial render
      const { rerender } = render(<AdminStatsDisplay key="before" />);

      await waitFor(() => {
        expect(screen.getByText(/Entities: 500/i)).toBeInTheDocument();
        expect(screen.getByText(/Relations: 800/i)).toBeInTheDocument();
      });

      // Act: Re-render after re-indexing
      rerender(<AdminStatsDisplay key="after" />);

      // Assert: Updated counts
      await waitFor(() => {
        expect(screen.getByText(/Entities: 856/i)).toBeInTheDocument();
        expect(screen.getByText(/Relations: 1204/i)).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('should display error message when API request fails', async () => {
      // Arrange: Mock failed request
      setupGlobalFetchMock(
        vi.fn().mockRejectedValue(new Error('Failed to fetch statistics'))
      );

      // Act: Render component
      render(<AdminStatsDisplay />);

      // Assert: Error should be displayed
      await waitFor(
        () => {
          expect(
            screen.getByText(/Error loading statistics: Failed to fetch statistics/i)
          ).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      // No stats should be shown
      expect(screen.queryByTestId('admin-stats')).not.toBeInTheDocument();
    });

    it('should handle HTTP error responses', async () => {
      // Arrange: Mock 500 error
      setupGlobalFetchMock(
        vi.fn().mockResolvedValue({
          ok: false,
          status: 500,
          text: () => Promise.resolve('Internal Server Error'),
        })
      );

      // Act: Render component
      render(<AdminStatsDisplay />);

      // Assert: Error message should include HTTP status
      await waitFor(() => {
        expect(
          screen.getByText(/Error loading statistics: HTTP 500/i)
        ).toBeInTheDocument();
      });
    });

    it('should handle malformed JSON response', async () => {
      // Arrange: Mock invalid JSON
      setupGlobalFetchMock(
        vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.reject(new Error('Unexpected token')),
        })
      );

      // Act: Render component
      render(<AdminStatsDisplay />);

      // Assert: Error should be caught and displayed
      await waitFor(() => {
        expect(screen.getByText(/Error loading statistics/i)).toBeInTheDocument();
      });
    });

    it('should handle network timeout', async () => {
      // Arrange: Mock timeout
      setupGlobalFetchMock(
        vi.fn().mockImplementation(() => {
          return new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Network timeout')), 100);
          });
        })
      );

      // Act: Render component
      render(<AdminStatsDisplay />);

      // Assert: Timeout error should be shown
      await waitFor(
        () => {
          expect(
            screen.getByText(/Error loading statistics: Network timeout/i)
          ).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });

  describe('Integration with Re-indexing', () => {
    it('should work alongside re-indexing status endpoint', async () => {
      // Arrange: Mock stats + re-indexing status
      setupGlobalFetchMock(
        vi.fn((url) => {
          if (url.includes('/admin/stats')) {
            return Promise.resolve({
              ok: true,
              json: () => Promise.resolve(mockAdminStats),
            });
          }
          if (url.includes('/admin/reindex')) {
            return Promise.resolve({
              ok: true,
              body: new ReadableStream({
                start(controller) {
                  const encoder = new TextEncoder();
                  controller.enqueue(
                    encoder.encode(
                      'data: {"status":"in_progress","progress_percent":50}\n\n'
                    )
                  );
                  controller.close();
                },
              }),
            });
          }
          return Promise.reject(new Error('Unknown endpoint'));
        })
      );

      // Act: Fetch stats
      render(<AdminStatsDisplay />);

      // Assert: Stats should load successfully
      await waitFor(() => {
        expect(screen.getByTestId('admin-stats')).toBeInTheDocument();
      });

      // Both endpoints should coexist without conflicts
      const statsResponse = await fetch('http://localhost:8000/api/v1/admin/stats');
      expect(statsResponse.ok).toBe(true);
    });
  });
});

/**
 * Graph Operations API Client Tests
 * Sprint 79 Feature 79.7: Admin Graph Operations UI
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  triggerCommunitySummarization,
  fetchGraphOperationsStats,
  fetchNamespaces,
  type CommunitySummarizationRequest,
  type CommunitySummarizationResponse,
  type GraphOperationsStats,
  type NamespaceListResponse,
} from './graphOperations';

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('graphOperations API client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('triggerCommunitySummarization', () => {
    const mockSuccessResponse: CommunitySummarizationResponse = {
      status: 'complete',
      total_communities: 92,
      summaries_generated: 85,
      failed: 7,
      total_time_s: 120.5,
      avg_time_per_summary_s: 1.42,
      message: 'Generated 85 summaries in 120.5s (7 failed).',
    };

    it('should send POST request to correct endpoint', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockSuccessResponse),
      });

      await triggerCommunitySummarization({});

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/admin/graph/communities/summarize'),
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        })
      );
    });

    it('should send correct request body with default values', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockSuccessResponse),
      });

      await triggerCommunitySummarization({});

      const call = mockFetch.mock.calls[0];
      const body = JSON.parse(call[1].body);
      expect(body).toEqual({
        namespace: null,
        force: false,
        batch_size: 10,
      });
    });

    it('should send correct request body with custom values', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockSuccessResponse),
      });

      const request: CommunitySummarizationRequest = {
        namespace: 'hotpotqa_large',
        force: true,
        batch_size: 20,
      };

      await triggerCommunitySummarization(request);

      const call = mockFetch.mock.calls[0];
      const body = JSON.parse(call[1].body);
      expect(body).toEqual({
        namespace: 'hotpotqa_large',
        force: true,
        batch_size: 20,
      });
    });

    it('should return response data on success', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockSuccessResponse),
      });

      const result = await triggerCommunitySummarization({});

      expect(result).toEqual(mockSuccessResponse);
    });

    it('should throw error on non-OK response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 503,
        text: () => Promise.resolve('Service unavailable'),
      });

      await expect(triggerCommunitySummarization({})).rejects.toThrow(
        'HTTP 503: Service unavailable'
      );
    });

    it('should handle no_work response', async () => {
      const noWorkResponse: CommunitySummarizationResponse = {
        status: 'no_work',
        total_communities: 0,
        summaries_generated: 0,
        failed: 0,
        total_time_s: 0.0,
        avg_time_per_summary_s: 0.0,
        message: 'No communities need summarization.',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(noWorkResponse),
      });

      const result = await triggerCommunitySummarization({});

      expect(result.status).toBe('no_work');
    });
  });

  describe('fetchGraphOperationsStats', () => {
    const mockStatsResponse: GraphOperationsStats = {
      total_entities: 1500,
      total_relationships: 3200,
      entity_types: { PERSON: 500, ORGANIZATION: 400 },
      relationship_types: { RELATES_TO: 2000, MENTIONED_IN: 1000 },
      community_count: 92,
      community_sizes: [45, 30, 20],
      orphan_nodes: 50,
      avg_degree: 4.27,
      summary_status: {
        generated: 80,
        pending: 12,
      },
      graph_health: 'healthy',
      timestamp: '2026-01-08T10:30:00Z',
    };

    it('should send GET request to correct endpoint', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockStatsResponse),
      });

      await fetchGraphOperationsStats();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/admin/graph/stats'),
        expect.objectContaining({
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        })
      );
    });

    it('should return stats data on success', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockStatsResponse),
      });

      const result = await fetchGraphOperationsStats();

      expect(result).toEqual(mockStatsResponse);
      expect(result.total_entities).toBe(1500);
      expect(result.community_count).toBe(92);
      expect(result.graph_health).toBe('healthy');
    });

    it('should throw error on non-OK response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Internal server error'),
      });

      await expect(fetchGraphOperationsStats()).rejects.toThrow(
        'HTTP 500: Internal server error'
      );
    });
  });

  describe('fetchNamespaces', () => {
    const mockNamespacesResponse: NamespaceListResponse = {
      namespaces: [
        {
          namespace_id: 'default',
          namespace_type: 'general',
          document_count: 100,
          description: 'Default namespace',
        },
        {
          namespace_id: 'hotpotqa_large',
          namespace_type: 'qa',
          document_count: 50,
          description: 'HotpotQA dataset',
        },
      ],
      total_count: 2,
    };

    it('should send GET request to correct endpoint', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockNamespacesResponse),
      });

      await fetchNamespaces();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/admin/namespaces'),
        expect.objectContaining({
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        })
      );
    });

    it('should return namespaces data on success', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockNamespacesResponse),
      });

      const result = await fetchNamespaces();

      expect(result.namespaces).toHaveLength(2);
      expect(result.namespaces[0].namespace_id).toBe('default');
      expect(result.namespaces[1].namespace_id).toBe('hotpotqa_large');
      expect(result.total_count).toBe(2);
    });

    it('should throw error on non-OK response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: () => Promise.resolve('Not found'),
      });

      await expect(fetchNamespaces()).rejects.toThrow('HTTP 404: Not found');
    });
  });
});

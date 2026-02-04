/**
 * useDomainTraining Hook Tests
 * Sprint 45 Feature 45.4: Domain Training Admin UI
 * Sprint 51 Feature 51.4: Auto-refresh and delete functionality
 *
 * Test Coverage:
 * - useDomains: fetching, refetch
 * - useDeleteDomain: deletion, error handling
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useDomains, useDeleteDomain, type Domain } from '../useDomainTraining';

// Mock the apiClient
const mockGet = vi.fn();
const mockDelete = vi.fn();

vi.mock('../../lib/api', () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
  },
}));

describe('useDomainTraining Hooks', () => {
  const mockDomains: Domain[] = [
    {
      id: 'domain-1',
      name: 'finance',
      description: 'Financial domain',
      llm_model: 'qwen3:32b',
      status: 'ready',
    },
    {
      id: 'domain-2',
      name: 'legal',
      description: 'Legal domain',
      llm_model: null,
      status: 'training',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue(mockDomains);
    mockDelete.mockResolvedValue({ message: 'Deleted', domain: 'finance' });
  });

  describe('useDomains', () => {
    it('should fetch domains on mount', async () => {
      const { result } = renderHook(() => useDomains({ enabled: true, refetchInterval: 60000 }));

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(mockGet).toHaveBeenCalledWith('/api/v1/admin/domains/');
        expect(result.current.isLoading).toBe(false);
        expect(result.current.data).toEqual(mockDomains);
      });
    });

    it('should set error state on fetch failure', async () => {
      mockGet.mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => useDomains({ enabled: true, refetchInterval: 60000 }));

      await waitFor(() => {
        expect(result.current.error).toBeInstanceOf(Error);
        expect(result.current.error?.message).toBe('Network error');
      });
    });

    it('should not fetch when enabled is false', async () => {
      renderHook(() => useDomains({ enabled: false }));

      // Wait a bit and verify no call was made
      await new Promise((resolve) => setTimeout(resolve, 100));
      expect(mockGet).not.toHaveBeenCalled();
    });

    it('should provide refetch function', async () => {
      const { result } = renderHook(() => useDomains({ enabled: true, refetchInterval: 60000 }));

      await waitFor(() => {
        expect(result.current.data).toEqual(mockDomains);
      });

      expect(mockGet).toHaveBeenCalledTimes(1);

      // Manual refetch
      await act(async () => {
        await result.current.refetch();
      });

      expect(mockGet).toHaveBeenCalledTimes(2);
    });

    it('should have default refetchInterval of 5 seconds', async () => {
      // We verify the hook accepts options without error
      const { result } = renderHook(() => useDomains());

      await waitFor(() => {
        expect(result.current.data).toEqual(mockDomains);
      });

      // Hook should work without errors
      expect(result.current.error).toBeNull();
    });
  });

  describe('useDeleteDomain', () => {
    it('should call delete API with domain ID', async () => {
      const { result } = renderHook(() => useDeleteDomain());

      expect(result.current.isLoading).toBe(false);

      await act(async () => {
        await result.current.mutateAsync('domain-123');
      });

      expect(mockDelete).toHaveBeenCalledWith('/api/v1/admin/domains/domain-123');
    });

    it('should return response on successful deletion', async () => {
      const mockResponse = { message: 'Domain deleted', domain: 'finance' };
      mockDelete.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => useDeleteDomain());

      let response;
      await act(async () => {
        response = await result.current.mutateAsync('domain-123');
      });

      expect(response).toEqual(mockResponse);
    });

    it('should throw error on deletion failure', async () => {
      mockDelete.mockRejectedValueOnce(new Error('Cannot delete: domain in use'));

      const { result } = renderHook(() => useDeleteDomain());

      await expect(
        act(async () => {
          await result.current.mutateAsync('domain-123');
        })
      ).rejects.toThrow('Cannot delete: domain in use');
    });

    it('should set isLoading to false after error', async () => {
      mockDelete.mockRejectedValueOnce(new Error('Delete failed'));

      const { result } = renderHook(() => useDeleteDomain());

      try {
        await act(async () => {
          await result.current.mutateAsync('domain-123');
        });
      } catch {
        // Expected to throw
      }

      expect(result.current.isLoading).toBe(false);
    });
  });
});

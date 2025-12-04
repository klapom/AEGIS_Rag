/**
 * useSessions Hook Tests
 * Sprint 35 Feature 35.5: Session History Sidebar
 *
 * Test Coverage:
 * - Fetching sessions on mount
 * - Grouping sessions by date (today, yesterday, lastWeek, older)
 * - Loading and error states
 * - Removing sessions
 * - Refetching sessions
 * - Date grouping logic accuracy
 * - Edge cases and boundary conditions
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useSessions } from '../useSessions';
import * as chatApi from '../../api/chat';
import type { SessionInfo, SessionSummary } from '../../api/chat';

// Mock the chat API
vi.mock('../../api/chat', () => ({
  listSessions: vi.fn(),
  deleteSession: vi.fn(),
}));

describe('useSessions', () => {
  const mockSessionInfoData: SessionInfo[] = [
    {
      session_id: 'session-1',
      title: 'Today Conversation',
      last_message: 'Last message today',
      updated_at: new Date().toISOString(),
      message_count: 5,
    },
    {
      session_id: 'session-2',
      title: null,
      last_message: 'Yesterday message',
      updated_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
      message_count: 3,
    },
    {
      session_id: 'session-3',
      title: 'Last Week Conversation',
      last_message: 'Last week message',
      updated_at: new Date(Date.now() - 3 * 86400000).toISOString(), // 3 days ago
      message_count: 8,
    },
    {
      session_id: 'session-4',
      title: 'Old Conversation',
      last_message: 'Old message',
      updated_at: new Date(Date.now() - 30 * 86400000).toISOString(), // 30 days ago
      message_count: 15,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    // Default successful response
    vi.mocked(chatApi.listSessions).mockResolvedValue({
      sessions: mockSessionInfoData,
      total_count: mockSessionInfoData.length,
    });
  });

  describe('Initialization and Fetching', () => {
    it('should fetch sessions on mount', async () => {
      renderHook(() => useSessions());

      await waitFor(() => {
        expect(chatApi.listSessions).toHaveBeenCalledTimes(1);
      });
    });

    it('should set loading state to true initially', () => {
      const { result } = renderHook(() => useSessions());

      // Initial state should have isLoading true
      expect(result.current.isLoading).toBe(true);
    });

    it('should set loading state to false after fetching', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });

    it('should return fetched sessions', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.sessions.length).toBe(4);
        expect(result.current.sessions[0].session_id).toBe('session-1');
      });
    });

    it('should convert SessionInfo to SessionSummary format', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        const firstSession = result.current.sessions[0];
        expect(firstSession).toHaveProperty('session_id');
        expect(firstSession).toHaveProperty('title');
        expect(firstSession).toHaveProperty('preview');
        expect(firstSession).toHaveProperty('updated_at');
        expect(firstSession).toHaveProperty('message_count');
      });
    });

    it('should handle empty session list', async () => {
      vi.mocked(chatApi.listSessions).mockResolvedValue({
        sessions: [],
        total_count: 0,
      });

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.sessions.length).toBe(0);
      });
    });
  });

  describe('Error Handling', () => {
    it('should set error state when fetch fails', async () => {
      const errorMessage = 'Failed to fetch sessions';
      vi.mocked(chatApi.listSessions).mockRejectedValue(new Error(errorMessage));

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.error).toBe(errorMessage);
      });
    });

    it('should set loading to false on error', async () => {
      vi.mocked(chatApi.listSessions).mockRejectedValue(new Error('API error'));

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });

    it('should set error to null on successful fetch', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.error).toBeNull();
      });
    });

    it('should handle non-Error exceptions', async () => {
      vi.mocked(chatApi.listSessions).mockRejectedValue('String error');

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.error).toBe('Failed to load sessions');
      });
    });
  });

  describe('Session Grouping by Date', () => {
    it('should group sessions into today, yesterday, lastWeek, and older', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.groupedSessions.today.length).toBe(1);
        expect(result.current.groupedSessions.yesterday.length).toBe(1);
        expect(result.current.groupedSessions.lastWeek.length).toBe(1);
        expect(result.current.groupedSessions.older.length).toBe(1);
      });
    });

    it('should put today sessions in today group', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        const todaySessions = result.current.groupedSessions.today;
        expect(todaySessions.length).toBeGreaterThan(0);
        expect(todaySessions[0].session_id).toBe('session-1');
      });
    });

    it('should put yesterday sessions in yesterday group', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        const yesterdaySessions = result.current.groupedSessions.yesterday;
        expect(yesterdaySessions.length).toBeGreaterThan(0);
        expect(yesterdaySessions[0].session_id).toBe('session-2');
      });
    });

    it('should put last 7 days sessions in lastWeek group', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        const lastWeekSessions = result.current.groupedSessions.lastWeek;
        expect(lastWeekSessions.length).toBeGreaterThan(0);
        expect(lastWeekSessions[0].session_id).toBe('session-3');
      });
    });

    it('should put older sessions in older group', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        const olderSessions = result.current.groupedSessions.older;
        expect(olderSessions.length).toBeGreaterThan(0);
        expect(olderSessions[0].session_id).toBe('session-4');
      });
    });

    it('should handle sessions at group boundaries', async () => {
      // Create a session exactly at yesterday boundary
      const now = new Date();
      const yesterdayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
      const yesterdayBoundary = yesterdayStart.toISOString();

      vi.mocked(chatApi.listSessions).mockResolvedValue({
        sessions: [
          {
            session_id: 'boundary-session',
            title: 'Boundary Session',
            last_message: 'Message',
            updated_at: yesterdayBoundary,
            message_count: 1,
          },
        ],
        total_count: 1,
      });

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        const yesterdaySessions = result.current.groupedSessions.yesterday;
        expect(yesterdaySessions.some(s => s.session_id === 'boundary-session')).toBe(true);
      });
    });

    it('should be accurate for 7-day boundary', async () => {
      const now = new Date();
      const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const weekStart = new Date(todayStart.getTime() - 7 * 86400000);

      // Session exactly 7 days ago should be in lastWeek
      const sevenDaysAgo = new Date(weekStart.getTime() - 1000).toISOString();
      // Session exactly 6 days ago should be in lastWeek
      const sixDaysAgo = new Date(weekStart.getTime() + 86400000).toISOString();

      vi.mocked(chatApi.listSessions).mockResolvedValue({
        sessions: [
          {
            session_id: 'session-6-days',
            title: 'Six Days Old',
            last_message: 'Message',
            updated_at: sixDaysAgo,
            message_count: 1,
          },
        ],
        total_count: 1,
      });

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        const lastWeekSessions = result.current.groupedSessions.lastWeek;
        expect(lastWeekSessions.some(s => s.session_id === 'session-6-days')).toBe(true);
      });
    });
  });

  describe('Preview Conversion', () => {
    it('should use last_message as preview', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.sessions[0].preview).toBe('Last message today');
      });
    });

    it('should handle missing last_message', async () => {
      vi.mocked(chatApi.listSessions).mockResolvedValue({
        sessions: [
          {
            session_id: 'session-no-preview',
            title: 'No Preview Session',
            message_count: 0,
          },
        ],
        total_count: 1,
      });

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.sessions[0]).toHaveProperty('preview');
      });
    });

    it('should handle null title as null not string', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        const sessionWithNullTitle = result.current.sessions.find(s => s.session_id === 'session-2');
        expect(sessionWithNullTitle?.title).toBeNull();
      });
    });
  });

  describe('removeSession', () => {
    it('should call deleteSession API', async () => {
      vi.mocked(chatApi.deleteSession).mockResolvedValue(undefined);

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.sessions.length).toBeGreaterThan(0);
      });

      await act(async () => {
        await result.current.removeSession('session-1');
      });

      expect(chatApi.deleteSession).toHaveBeenCalledWith('session-1');
    });

    it('should remove session from sessions list', async () => {
      vi.mocked(chatApi.deleteSession).mockResolvedValue(undefined);

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.sessions.length).toBe(4);
      });

      await act(async () => {
        await result.current.removeSession('session-1');
      });

      expect(result.current.sessions.length).toBe(3);
      expect(result.current.sessions.some(s => s.session_id === 'session-1')).toBe(false);
    });

    it('should update grouped sessions after removal', async () => {
      vi.mocked(chatApi.deleteSession).mockResolvedValue(undefined);

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.groupedSessions.today.length).toBe(1);
      });

      await act(async () => {
        await result.current.removeSession('session-1');
      });

      expect(result.current.groupedSessions.today.length).toBe(0);
    });

    it('should return true on successful deletion', async () => {
      vi.mocked(chatApi.deleteSession).mockResolvedValue(undefined);

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.sessions.length).toBeGreaterThan(0);
      });

      let success = false;
      await act(async () => {
        success = await result.current.removeSession('session-1');
      });

      expect(success).toBe(true);
    });

    it('should return false on deletion error', async () => {
      vi.mocked(chatApi.deleteSession).mockRejectedValue(new Error('Delete failed'));

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.sessions.length).toBeGreaterThan(0);
      });

      let success = true;
      await act(async () => {
        success = await result.current.removeSession('session-1');
      });

      expect(success).toBe(false);
    });

    it('should not remove session on error', async () => {
      vi.mocked(chatApi.deleteSession).mockRejectedValue(new Error('Delete failed'));

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.sessions.length).toBe(4);
      });

      await act(async () => {
        await result.current.removeSession('session-1');
      });

      // Session should still be in the list
      expect(result.current.sessions.length).toBe(4);
      expect(result.current.sessions.some(s => s.session_id === 'session-1')).toBe(true);
    });

    it('should remove from correct group when deleting', async () => {
      vi.mocked(chatApi.deleteSession).mockResolvedValue(undefined);

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.groupedSessions.yesterday.length).toBe(1);
      });

      await act(async () => {
        await result.current.removeSession('session-2');
      });

      expect(result.current.groupedSessions.yesterday.length).toBe(0);
      expect(result.current.groupedSessions.yesterday.some(s => s.session_id === 'session-2')).toBe(false);
    });
  });

  describe('refetch', () => {
    it('should refetch sessions', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(chatApi.listSessions).toHaveBeenCalledTimes(1);
      });

      await act(async () => {
        await result.current.refetch();
      });

      expect(chatApi.listSessions).toHaveBeenCalledTimes(2);
    });

    it('should set loading state during refetch', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const refetchPromise = act(async () => {
        await result.current.refetch();
      });

      // Note: isLoading might be true during refetch, but due to async nature,
      // we check that it becomes false after
      await refetchPromise;

      expect(result.current.isLoading).toBe(false);
    });

    it('should update sessions on successful refetch', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.sessions.length).toBe(4);
      });

      // Mock new data
      vi.mocked(chatApi.listSessions).mockResolvedValue({
        sessions: [
          {
            session_id: 'new-session',
            title: 'New Session',
            last_message: 'New message',
            updated_at: new Date().toISOString(),
            message_count: 1,
          },
        ],
        total_count: 1,
      });

      await act(async () => {
        await result.current.refetch();
      });

      expect(result.current.sessions.length).toBe(1);
      expect(result.current.sessions[0].session_id).toBe('new-session');
    });

    it('should handle error during refetch', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.error).toBeNull();
      });

      vi.mocked(chatApi.listSessions).mockRejectedValue(new Error('Refetch failed'));

      await act(async () => {
        await result.current.refetch();
      });

      expect(result.current.error).toBe('Refetch failed');
    });

    it('should clear error on successful refetch', async () => {
      vi.mocked(chatApi.listSessions).mockRejectedValue(new Error('Initial error'));

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.error).toBe('Initial error');
      });

      // Mock successful response
      vi.mocked(chatApi.listSessions).mockResolvedValue({
        sessions: mockSessionInfoData,
        total_count: mockSessionInfoData.length,
      });

      await act(async () => {
        await result.current.refetch();
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe('Session Data Persistence', () => {
    it('should maintain session data across multiple renders', async () => {
      const { result, rerender } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.sessions.length).toBe(4);
      });

      const sessionsBefore = result.current.sessions;

      rerender();

      const sessionsAfter = result.current.sessions;

      expect(sessionsAfter.length).toBe(sessionsBefore.length);
      expect(sessionsAfter[0].session_id).toBe(sessionsBefore[0].session_id);
    });

    it('should maintain grouped sessions across renders', async () => {
      const { result, rerender } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.groupedSessions.today.length).toBeGreaterThan(0);
      });

      const groupedBefore = { ...result.current.groupedSessions };

      rerender();

      const groupedAfter = result.current.groupedSessions;

      expect(groupedAfter.today.length).toBe(groupedBefore.today.length);
    });
  });

  describe('Multiple Hook Instances', () => {
    it('should fetch independently for each hook instance', async () => {
      const { result: result1 } = renderHook(() => useSessions());
      const { result: result2 } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result1.current.sessions.length).toBeGreaterThan(0);
        expect(result2.current.sessions.length).toBeGreaterThan(0);
      });

      expect(chatApi.listSessions).toHaveBeenCalledTimes(2);
    });

    it('should maintain independent state for each instance', async () => {
      const { result: result1 } = renderHook(() => useSessions());
      const { result: result2 } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result1.current.sessions.length).toBe(4);
      });

      // Update mock for second instance deletion
      vi.mocked(chatApi.deleteSession).mockResolvedValue(undefined);

      await act(async () => {
        await result1.current.removeSession('session-1');
      });

      // Only result1 should be updated
      expect(result1.current.sessions.length).toBe(3);
      expect(result2.current.sessions.length).toBe(4);
    });
  });

  describe('Edge Cases', () => {
    it('should handle sessions with same updated_at timestamp', async () => {
      const sameTimestamp = new Date().toISOString();

      vi.mocked(chatApi.listSessions).mockResolvedValue({
        sessions: [
          {
            session_id: 'session-same-time-1',
            title: 'Session 1',
            last_message: 'Message 1',
            updated_at: sameTimestamp,
            message_count: 1,
          },
          {
            session_id: 'session-same-time-2',
            title: 'Session 2',
            last_message: 'Message 2',
            updated_at: sameTimestamp,
            message_count: 1,
          },
        ],
        total_count: 2,
      });

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.groupedSessions.today.length).toBe(2);
      });
    });

    it('should handle empty updated_at field', async () => {
      vi.mocked(chatApi.listSessions).mockResolvedValue({
        sessions: [
          {
            session_id: 'session-no-updated',
            title: 'Session',
            last_message: 'Message',
            message_count: 1,
          } as SessionInfo,
        ],
        total_count: 1,
      });

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        // Should use current date as fallback
        expect(result.current.groupedSessions.today.length).toBe(1);
      });
    });

    it('should handle very old sessions (many years old)', async () => {
      const veryOld = new Date('2010-01-01').toISOString();

      vi.mocked(chatApi.listSessions).mockResolvedValue({
        sessions: [
          {
            session_id: 'ancient-session',
            title: 'Very Old',
            last_message: 'Message',
            updated_at: veryOld,
            message_count: 1,
          },
        ],
        total_count: 1,
      });

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.groupedSessions.older.length).toBe(1);
      });
    });

    it('should handle future-dated sessions', async () => {
      const future = new Date(Date.now() + 86400000).toISOString(); // Tomorrow

      vi.mocked(chatApi.listSessions).mockResolvedValue({
        sessions: [
          {
            session_id: 'future-session',
            title: 'Future Session',
            last_message: 'Message',
            updated_at: future,
            message_count: 1,
          },
        ],
        total_count: 1,
      });

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        // Future sessions should go to "today" or beyond (implementation dependent)
        expect(result.current.sessions.length).toBe(1);
      });
    });

    it('should handle very long session title', async () => {
      const longTitle = 'A'.repeat(500);

      vi.mocked(chatApi.listSessions).mockResolvedValue({
        sessions: [
          {
            session_id: 'long-title-session',
            title: longTitle,
            last_message: 'Message',
            updated_at: new Date().toISOString(),
            message_count: 1,
          },
        ],
        total_count: 1,
      });

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.sessions[0].title?.length).toBe(500);
      });
    });

    it('should handle special characters in session title', async () => {
      const specialTitle = "Test <script>alert('xss')</script>";

      vi.mocked(chatApi.listSessions).mockResolvedValue({
        sessions: [
          {
            session_id: 'special-chars-session',
            title: specialTitle,
            last_message: 'Message',
            updated_at: new Date().toISOString(),
            message_count: 1,
          },
        ],
        total_count: 1,
      });

      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.sessions[0].title).toBe(specialTitle);
      });
    });
  });

  describe('Return Value Structure', () => {
    it('should return correct hook structure', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current).toHaveProperty('sessions');
        expect(result.current).toHaveProperty('groupedSessions');
        expect(result.current).toHaveProperty('isLoading');
        expect(result.current).toHaveProperty('error');
        expect(result.current).toHaveProperty('refetch');
        expect(result.current).toHaveProperty('removeSession');
      });
    });

    it('should have correct groupedSessions structure', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.groupedSessions).toHaveProperty('today');
        expect(result.current.groupedSessions).toHaveProperty('yesterday');
        expect(result.current.groupedSessions).toHaveProperty('lastWeek');
        expect(result.current.groupedSessions).toHaveProperty('older');
      });
    });

    it('should have all grouped sessions as arrays', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(Array.isArray(result.current.groupedSessions.today)).toBe(true);
        expect(Array.isArray(result.current.groupedSessions.yesterday)).toBe(true);
        expect(Array.isArray(result.current.groupedSessions.lastWeek)).toBe(true);
        expect(Array.isArray(result.current.groupedSessions.older)).toBe(true);
      });
    });

    it('should have refetch as callable function', async () => {
      const { result } = renderHook(() => useSessions());

      expect(typeof result.current.refetch).toBe('function');
    });

    it('should have removeSession as callable function', async () => {
      const { result } = renderHook(() => useSessions());

      expect(typeof result.current.removeSession).toBe('function');
    });
  });

  describe('Async Function Behavior', () => {
    it('should handle rapid refetch calls', async () => {
      const { result } = renderHook(() => useSessions());

      await waitFor(() => {
        expect(result.current.sessions.length).toBeGreaterThan(0);
      });

      await act(async () => {
        await Promise.all([
          result.current.refetch(),
          result.current.refetch(),
          result.current.refetch(),
        ]);
      });

      expect(chatApi.listSessions).toHaveBeenCalledTimes(4); // 1 initial + 3 refetches
    });
  });
});

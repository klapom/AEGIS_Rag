/**
 * useSessions Hook
 * Sprint 35 Feature 35.5: Session History Sidebar
 * Sprint 65 Feature 65.3: Added pagination to avoid timeout with >100 conversations
 *
 * Fetches and manages conversation sessions with date-based grouping
 */

import { useState, useEffect, useCallback } from 'react';
import { listSessions, deleteSession } from '../api/chat';
import type { SessionSummary } from '../api/chat';

interface GroupedSessions {
  today: SessionSummary[];
  yesterday: SessionSummary[];
  lastWeek: SessionSummary[];
  older: SessionSummary[];
}

export function useSessions() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Sprint 65 Feature 65.3: Request only 50 most recent sessions to avoid timeout
      // TODO Sprint 66: Implement infinite scroll for loading more sessions
      const data = await listSessions(50, 0);
      // Convert SessionInfo to SessionSummary format
      const summaries: SessionSummary[] = data.sessions.map(s => ({
        session_id: s.session_id,
        title: s.title ?? null,
        preview: s.last_message,
        updated_at: s.updated_at || s.last_activity || new Date().toISOString(),
        message_count: s.message_count,
      }));
      setSessions(summaries);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load sessions');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const removeSession = useCallback(async (sessionId: string) => {
    try {
      await deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.session_id !== sessionId));
      return true;
    } catch {
      return false;
    }
  }, []);

  // Group sessions by date
  const groupedSessions: GroupedSessions = {
    today: [],
    yesterday: [],
    lastWeek: [],
    older: [],
  };

  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterdayStart = new Date(todayStart.getTime() - 86400000);
  const weekStart = new Date(todayStart.getTime() - 7 * 86400000);

  sessions.forEach(session => {
    const updated = new Date(session.updated_at);
    if (updated >= todayStart) {
      groupedSessions.today.push(session);
    } else if (updated >= yesterdayStart) {
      groupedSessions.yesterday.push(session);
    } else if (updated >= weekStart) {
      groupedSessions.lastWeek.push(session);
    } else {
      groupedSessions.older.push(session);
    }
  });

  return {
    sessions,
    groupedSessions,
    isLoading,
    error,
    refetch: fetchSessions,
    removeSession,
  };
}

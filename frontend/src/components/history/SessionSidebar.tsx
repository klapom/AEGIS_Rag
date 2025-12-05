/**
 * SessionSidebar Component
 * Sprint 15 Feature 15.5: Conversation history sidebar
 *
 * Features:
 * - Session list with grouping (Today, Yesterday, Last 7 days)
 * - Load session on click
 * - Delete session button
 * - Search within sessions
 * - Collapsible sidebar
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { listSessions } from '../../api/chat';
import type { SessionInfo } from '../../types/chat';
import { SessionGroup } from './SessionGroup';

interface SessionSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

export function SessionSidebar({ isOpen, onToggle }: SessionSidebarProps) {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadSessions();
    }
  }, [isOpen]);

  const loadSessions = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listSessions();
      setSessions(data.sessions);
    } catch (err) {
      console.error('Failed to load sessions:', err);
      setError('Fehler beim Laden der Sitzungen');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteSession = (sessionId: string) => {
    setSessions(sessions.filter((s) => s.session_id !== sessionId));
  };

  // Sprint 19: Search by conversation title/name
  const getSessionTitle = (session: SessionInfo): string => {
    if (session.title) return session.title;
    if (session.last_message) return session.last_message;
    // Try to extract first user message from messages array
    if (session.messages && session.messages.length > 0) {
      const firstUserMsg = session.messages.find(m => m.role === 'user');
      if (firstUserMsg?.content) {
        return firstUserMsg.content.length > 60
          ? firstUserMsg.content.substring(0, 60) + '...'
          : firstUserMsg.content;
      }
    }
    return 'Neue Konversation';
  };

  const filteredSessions = sessions.filter((session) => {
    if (!searchQuery) return true;
    const title = getSessionTitle(session);
    return title.toLowerCase().includes(searchQuery.toLowerCase());
  });

  const groupedSessions = groupSessionsByDate(filteredSessions);

  return (
    <>
      {/* Backdrop for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 lg:hidden"
          onClick={onToggle}
        />
      )}

      {/* Sidebar */}
      <div
        className={`
          fixed lg:relative inset-y-0 left-0 z-50
          transition-all duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          ${isOpen ? 'w-80' : 'w-0 lg:w-0'}
          bg-white border-r border-gray-200 overflow-hidden
          flex flex-col
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 flex-shrink-0">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
            <span>📚</span>
            <span>History</span>
          </h2>
          <button
            onClick={onToggle}
            className="p-2 hover:bg-gray-100 rounded-lg transition"
            title="Sidebar schließen"
          >
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Search */}
        <div className="p-4 flex-shrink-0">
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Suchen..."
              className="w-full px-4 py-2 pl-10 border border-gray-300 rounded-lg
                         focus:border-primary focus:ring-2 focus:ring-primary/20
                         transition-all outline-none text-sm"
            />
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
        </div>

        {/* Session List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {isLoading ? (
            <LoadingState />
          ) : error ? (
            <ErrorState error={error} onRetry={loadSessions} />
          ) : filteredSessions.length === 0 ? (
            <EmptyState hasSearch={!!searchQuery} />
          ) : (
            Object.entries(groupedSessions).map(([group, groupSessions]) => (
              <SessionGroup
                key={group}
                title={group}
                sessions={groupSessions}
                onDelete={handleDeleteSession}
              />
            ))
          )}
        </div>

        {/* Admin Section */}
        <div className="pt-4 border-t border-gray-200 px-4">
          <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">
            Admin
          </h3>
          <div className="space-y-1">
            <button
              onClick={() => navigate('/admin/indexing')}
              className="w-full py-2 px-3 text-sm text-gray-700 hover:bg-gray-100 rounded-lg flex items-center space-x-2"
            >
              <span>📄</span>
              <span>Indexing</span>
            </button>
            <button
              onClick={() => navigate('/admin/graph')}
              className="w-full py-2 px-3 text-sm text-gray-700 hover:bg-gray-100 rounded-lg flex items-center space-x-2"
            >
              <span>🕸️</span>
              <span>Graph Analytics</span>
            </button>
            <button
              onClick={() => navigate('/admin/costs')}
              className="w-full py-2 px-3 text-sm text-gray-700 hover:bg-gray-100 rounded-lg flex items-center space-x-2"
            >
              <span>💰</span>
              <span>Cost Dashboard</span>
            </button>
            <button
              onClick={() => navigate('/admin/llm-config')}
              className="w-full py-2 px-3 text-sm text-gray-700 hover:bg-gray-100 rounded-lg flex items-center space-x-2"
              data-testid="sidebar-llm-config-link"
            >
              <span>🤖</span>
              <span>LLM Configuration</span>
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

function groupSessionsByDate(sessions: SessionInfo[]): Record<string, SessionInfo[]> {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const lastWeek = new Date(today);
  lastWeek.setDate(lastWeek.getDate() - 7);

  const groups: Record<string, SessionInfo[]> = {
    'Heute': [],
    'Gestern': [],
    'Letzte 7 Tage': [],
    'Älter': [],
  };

  sessions.forEach((session) => {
    if (!session.updated_at) {
      groups['Älter'].push(session);
      return;
    }

    const sessionDate = new Date(session.updated_at);
    if (sessionDate >= today) {
      groups['Heute'].push(session);
    } else if (sessionDate >= yesterday) {
      groups['Gestern'].push(session);
    } else if (sessionDate >= lastWeek) {
      groups['Letzte 7 Tage'].push(session);
    } else {
      groups['Älter'].push(session);
    }
  });

  // Remove empty groups
  Object.keys(groups).forEach((key) => {
    if (groups[key].length === 0) {
      delete groups[key];
    }
  });

  return groups;
}

function LoadingState() {
  return (
    <div className="space-y-3">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="animate-pulse space-y-2">
          <div className="h-4 bg-gray-200 rounded w-3/4" />
          <div className="h-3 bg-gray-200 rounded w-1/2" />
        </div>
      ))}
    </div>
  );
}

function ErrorState({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className="text-center space-y-3 py-8">
      <div className="text-red-500 text-sm">{error}</div>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary-hover transition"
      >
        Erneut versuchen
      </button>
    </div>
  );
}

function EmptyState({ hasSearch }: { hasSearch: boolean }) {
  return (
    <div className="text-center py-12 text-gray-500 text-sm">
      {hasSearch ? (
        <>
          <div className="text-3xl mb-2">🔍</div>
          <p>Keine Ergebnisse gefunden</p>
        </>
      ) : (
        <>
          <div className="text-3xl mb-2">💭</div>
          <p>Noch keine Konversationen</p>
        </>
      )}
    </div>
  );
}

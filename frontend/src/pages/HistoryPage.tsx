/**
 * HistoryPage Component
 * Sprint 119 Feature 119.3: Conversation History Page
 *
 * Dedicated page for browsing and managing conversation history.
 * Features:
 * - Display all conversations with metadata (title, date, message count)
 * - Search conversations by title/content
 * - Delete conversations with confirmation dialog
 * - Export conversations as JSON
 * - Date-based grouping (Today, Yesterday, Last 7 Days, Older)
 * - Empty state when no conversations exist
 * - Responsive design with mobile support
 */

import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { History, Search, Trash2, Download, MessageSquare, Calendar, Hash, X } from 'lucide-react';
import { useSessions } from '../hooks/useSessions';
import { getConversationHistory } from '../api/chat';
import type { SessionSummary } from '../api/chat';

export function HistoryPage() {
  const navigate = useNavigate();
  const { groupedSessions, isLoading, removeSession } = useSessions();
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Filter sessions based on search query
  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) {
      return groupedSessions;
    }

    const query = searchQuery.toLowerCase();
    const filterGroup = (sessions: SessionSummary[]) =>
      sessions.filter(
        (session) =>
          session.title?.toLowerCase().includes(query) ||
          session.preview?.toLowerCase().includes(query)
      );

    return {
      today: filterGroup(groupedSessions.today),
      yesterday: filterGroup(groupedSessions.yesterday),
      lastWeek: filterGroup(groupedSessions.lastWeek),
      older: filterGroup(groupedSessions.older),
    };
  }, [groupedSessions, searchQuery]);

  // Calculate total conversation count
  const totalCount =
    filteredSessions.today.length +
    filteredSessions.yesterday.length +
    filteredSessions.lastWeek.length +
    filteredSessions.older.length;

  const handleConversationClick = (sessionId: string) => {
    // Navigate to home page with session ID in state
    // The SessionSidebar in HomePage will handle loading the session
    navigate('/', { state: { sessionId } });
  };

  const handleDeleteClick = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteConfirmId(sessionId);
  };

  const handleDeleteConfirm = async () => {
    if (deleteConfirmId) {
      await removeSession(deleteConfirmId);
      setDeleteConfirmId(null);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmId(null);
  };

  const handleExportClick = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const conversation = await getConversationHistory(sessionId);
      const dataStr = JSON.stringify(conversation, null, 2);
      const dataUri = `data:application/json;charset=utf-8,${encodeURIComponent(dataStr)}`;

      const exportFileDefaultName = `conversation-${sessionId}-${new Date().toISOString().slice(0, 10)}.json`;

      const linkElement = document.createElement('a');
      linkElement.setAttribute('href', dataUri);
      linkElement.setAttribute('download', exportFileDefaultName);
      linkElement.click();
    } catch (error) {
      console.error('Failed to export conversation:', error);
    }
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterdayStart = new Date(todayStart.getTime() - 86400000);

    if (date >= todayStart) {
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } else if (date >= yesterdayStart) {
      return 'Yesterday';
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <History className="w-6 h-6 text-gray-700" />
              <h1 className="text-2xl font-semibold text-gray-900">Conversation History</h1>
            </div>
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Back to Chat
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search Bar */}
        <div className="mb-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search conversations by title or content..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-3 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              data-testid="search-history"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 p-1 hover:bg-gray-100 rounded-full transition-colors"
              >
                <X className="w-4 h-4 text-gray-400" />
              </button>
            )}
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading conversations...</p>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && totalCount === 0 && (
          <div className="text-center py-12" data-testid="empty-history">
            <MessageSquare className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-700 mb-2">
              {searchQuery ? 'No conversations found' : 'No conversations yet'}
            </h2>
            <p className="text-gray-500 mb-6">
              {searchQuery
                ? 'Try a different search query'
                : 'Start a conversation to see it here'}
            </p>
            {!searchQuery && (
              <button
                onClick={() => navigate('/')}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                Start New Conversation
              </button>
            )}
          </div>
        )}

        {/* Conversation List */}
        {!isLoading && totalCount > 0 && (
          <div data-testid="conversation-list" className="space-y-6">
            {/* Today */}
            {filteredSessions.today.length > 0 && (
              <ConversationGroup
                title="Today"
                sessions={filteredSessions.today}
                onConversationClick={handleConversationClick}
                onDeleteClick={handleDeleteClick}
                onExportClick={handleExportClick}
                formatDate={formatDate}
              />
            )}

            {/* Yesterday */}
            {filteredSessions.yesterday.length > 0 && (
              <ConversationGroup
                title="Yesterday"
                sessions={filteredSessions.yesterday}
                onConversationClick={handleConversationClick}
                onDeleteClick={handleDeleteClick}
                onExportClick={handleExportClick}
                formatDate={formatDate}
              />
            )}

            {/* Last 7 Days */}
            {filteredSessions.lastWeek.length > 0 && (
              <ConversationGroup
                title="Last 7 Days"
                sessions={filteredSessions.lastWeek}
                onConversationClick={handleConversationClick}
                onDeleteClick={handleDeleteClick}
                onExportClick={handleExportClick}
                formatDate={formatDate}
              />
            )}

            {/* Older */}
            {filteredSessions.older.length > 0 && (
              <ConversationGroup
                title="Older"
                sessions={filteredSessions.older}
                onConversationClick={handleConversationClick}
                onDeleteClick={handleDeleteClick}
                onExportClick={handleExportClick}
                formatDate={formatDate}
              />
            )}
          </div>
        )}
      </main>

      {/* Delete Confirmation Dialog */}
      {deleteConfirmId && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={handleDeleteCancel}
        >
          <div
            className="bg-white rounded-lg p-6 max-w-md w-full"
            onClick={(e) => e.stopPropagation()}
            data-testid="confirm-delete"
          >
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Delete Conversation?</h2>
            <p className="text-gray-600 mb-6">
              This action cannot be undone. The conversation and all its messages will be permanently deleted.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={handleDeleteCancel}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface ConversationGroupProps {
  title: string;
  sessions: SessionSummary[];
  onConversationClick: (sessionId: string) => void;
  onDeleteClick: (sessionId: string, e: React.MouseEvent) => void;
  onExportClick: (sessionId: string, e: React.MouseEvent) => void;
  formatDate: (dateString: string) => string;
}

function ConversationGroup({
  title,
  sessions,
  onConversationClick,
  onDeleteClick,
  onExportClick,
  formatDate,
}: ConversationGroupProps) {
  return (
    <div>
      <h2 className="text-sm font-semibold text-gray-500 uppercase mb-3 px-2">{title}</h2>
      <div className="space-y-2">
        {sessions.map((session) => (
          <ConversationItem
            key={session.session_id}
            session={session}
            onClick={() => onConversationClick(session.session_id)}
            onDelete={(e) => onDeleteClick(session.session_id, e)}
            onExport={(e) => onExportClick(session.session_id, e)}
            formatDate={formatDate}
          />
        ))}
      </div>
    </div>
  );
}

interface ConversationItemProps {
  session: SessionSummary;
  onClick: () => void;
  onDelete: (e: React.MouseEvent) => void;
  onExport: (e: React.MouseEvent) => void;
  formatDate: (dateString: string) => string;
}

function ConversationItem({ session, onClick, onDelete, onExport, formatDate }: ConversationItemProps) {
  const [showActions, setShowActions] = useState(false);

  return (
    <div
      className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
      data-testid="conversation-item"
    >
      <div className="flex items-start justify-between gap-4">
        {/* Left: Main Content */}
        <div className="flex-1 min-w-0">
          <h3
            className="text-lg font-semibold text-gray-900 mb-1 truncate"
            data-testid="conversation-title"
          >
            {session.title || 'Untitled Conversation'}
          </h3>
          {session.preview && (
            <p className="text-sm text-gray-600 mb-2 line-clamp-2">{session.preview}</p>
          )}
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <div className="flex items-center gap-1" data-testid="conversation-created">
              <Calendar className="w-3 h-3" />
              <span>{formatDate(session.updated_at)}</span>
            </div>
            <div className="flex items-center gap-1" data-testid="conversation-message-count">
              <Hash className="w-3 h-3" />
              <span>{session.message_count} {session.message_count === 1 ? 'message' : 'messages'}</span>
            </div>
          </div>
        </div>

        {/* Right: Actions */}
        {showActions && (
          <div className="flex items-center gap-2">
            <button
              onClick={onExport}
              className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
              title="Export conversation"
              data-testid="export-conversation"
            >
              <Download className="w-4 h-4" />
            </button>
            <button
              onClick={onDelete}
              className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              title="Delete conversation"
              data-testid="delete-conversation"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

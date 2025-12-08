/**
 * SessionSidebar Component
 * Sprint 35 Feature 35.5: Session History Sidebar
 * Sprint 38 Feature 38.2: Conversation Search Integration
 *
 * Features:
 * - Conversation search at the top
 * - List conversation history with titles and previews
 * - Date-based grouping (Today, Yesterday, Last Week, Older)
 * - New Chat button
 * - Delete session functionality
 * - Mobile responsive with hamburger menu
 * - Active session highlighting
 */

import { useState } from 'react';
import { Plus, Trash2, MessageSquare, Menu, X, Share2 } from 'lucide-react';
import { ShareModal } from './ShareModal';
import { useSessions } from '../../hooks/useSessions';
import { ConversationSearch } from './ConversationSearch';
import type { SessionSummary } from '../../api/chat';

interface SessionSidebarProps {
  currentSessionId: string | null;
  onNewChat: () => void;
  onSelectSession: (sessionId: string) => void;
  isOpen: boolean;
  onToggle: () => void;
}

interface SessionGroupProps {
  title: string;
  sessions: SessionSummary[];
  currentSessionId: string | null;
  onSelect: (sessionId: string) => void;
  onDelete: (sessionId: string) => void;
  onShare: (sessionId: string) => void;
}

function SessionGroup({ title, sessions, currentSessionId, onSelect, onDelete, onShare }: SessionGroupProps) {
  if (sessions.length === 0) return null;

  return (
    <div className="mb-4">
      <h3 className="px-3 py-1 text-xs font-semibold text-gray-400 uppercase">
        {title}
      </h3>
      <div className="space-y-1">
        {sessions.map(session => (
          <SessionItem
            key={session.session_id}
            session={session}
            isActive={session.session_id === currentSessionId}
            onSelect={() => onSelect(session.session_id)}
            onDelete={() => onDelete(session.session_id)}
            onShare={() => onShare(session.session_id)}
          />
        ))}
      </div>
    </div>
  );
}

interface SessionItemProps {
  session: SessionSummary;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onShare: () => void;
}

function SessionItem({ session, isActive, onSelect, onDelete, onShare }: SessionItemProps) {
  const [showActions, setShowActions] = useState(false);

  return (
    <div
      className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
        isActive
          ? 'bg-gray-700 text-white'
          : 'text-gray-300 hover:bg-gray-800'
      }`}
      onClick={onSelect}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
      data-testid="session-item"
    >
      <MessageSquare className="w-4 h-4 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="text-sm truncate" data-testid="session-title">
          {session.title || 'New Conversation'}
        </div>
        {session.preview && (
          <div className="text-xs text-gray-500 truncate">
            {session.preview}
          </div>
        )}
      </div>
      {showActions && (
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onShare();
            }}
            className="p-1 text-gray-400 hover:text-blue-400 transition-colors"
            data-testid="share-session"
            title="Share conversation"
          >
            <Share2 className="w-4 h-4" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1 text-gray-400 hover:text-red-400 transition-colors"
            data-testid="delete-session"
            title="Delete conversation"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}

export function SessionSidebar({
  currentSessionId,
  onNewChat,
  onSelectSession,
  isOpen,
  onToggle,
}: SessionSidebarProps) {
  const { groupedSessions, isLoading, removeSession } = useSessions();
  const [shareModalOpen, setShareModalOpen] = useState(false);
  const [shareSessionId, setShareSessionId] = useState<string | null>(null);

  const handleDelete = async (sessionId: string) => {
    if (confirm('Delete this conversation?')) {
      await removeSession(sessionId);
      if (sessionId === currentSessionId) {
        onNewChat();
      }
    }
  };

  const handleShare = (sessionId: string) => {
    setShareSessionId(sessionId);
    setShareModalOpen(true);
  };

  const handleCloseShareModal = () => {
    setShareModalOpen(false);
    setShareSessionId(null);
  };

  return (
    <>
      {/* Mobile toggle button */}
      <button
        onClick={onToggle}
        className="md:hidden fixed top-4 left-4 z-50 p-2 bg-gray-800 text-white rounded-lg"
        data-testid="sidebar-toggle"
      >
        {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Sidebar */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 w-64 bg-gray-900 text-white transform transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
        data-testid="session-sidebar"
      >
        <div className="flex flex-col h-full">
          {/* New Chat Button */}
          <div className="p-4 border-b border-gray-700">
            <button
              onClick={() => {
                onNewChat();
                onToggle();
              }}
              className="flex items-center justify-center gap-2 w-full px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
              data-testid="new-chat-button"
            >
              <Plus className="w-4 h-4" />
              <span>New Chat</span>
            </button>
          </div>

          {/* Conversation Search - Sprint 38 Feature 38.2 */}
          <div className="p-4 border-b border-gray-700">
            <ConversationSearch
              onSelectResult={(sessionId) => {
                onSelectSession(sessionId);
                onToggle();
              }}
              placeholder="Search conversations..."
            />
          </div>

          {/* Session List */}
          <div className="flex-1 overflow-y-auto p-2">
            {isLoading ? (
              <div className="text-center text-gray-500 py-4">Loading...</div>
            ) : (
              <>
                <SessionGroup
                  title="Today"
                  sessions={groupedSessions.today}
                  currentSessionId={currentSessionId}
                  onSelect={(id) => {
                    onSelectSession(id);
                    onToggle();
                  }}
                  onDelete={handleDelete}
                  onShare={handleShare}
                />
                <SessionGroup
                  title="Yesterday"
                  sessions={groupedSessions.yesterday}
                  currentSessionId={currentSessionId}
                  onSelect={(id) => {
                    onSelectSession(id);
                    onToggle();
                  }}
                  onDelete={handleDelete}
                  onShare={handleShare}
                />
                <SessionGroup
                  title="Last 7 Days"
                  sessions={groupedSessions.lastWeek}
                  currentSessionId={currentSessionId}
                  onSelect={(id) => {
                    onSelectSession(id);
                    onToggle();
                  }}
                  onDelete={handleDelete}
                  onShare={handleShare}
                />
                <SessionGroup
                  title="Older"
                  sessions={groupedSessions.older}
                  currentSessionId={currentSessionId}
                  onSelect={(id) => {
                    onSelectSession(id);
                    onToggle();
                  }}
                  onDelete={handleDelete}
                  onShare={handleShare}
                />
              </>
            )}
          </div>

          {/* Settings (optional) */}
          <div className="p-4 border-t border-gray-700">
            <div className="text-xs text-gray-500 text-center">
              AegisRAG v0.35
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black bg-opacity-50 z-30"
          onClick={onToggle}
        />
      )}

      {/* Share Modal - Sprint 38 Feature 38.3 */}
      {shareSessionId && (
        <ShareModal
          sessionId={shareSessionId}
          isOpen={shareModalOpen}
          onClose={handleCloseShareModal}
        />
      )}
    </>
  );
}

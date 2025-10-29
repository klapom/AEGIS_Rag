/**
 * SessionItem Component
 * Sprint 15 Feature 15.5: Individual session item
 * Sprint 17 Feature 17.3: Inline title editing
 */

import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { SessionInfo } from '../../types/chat';
import { deleteSession, updateConversationTitle } from '../../api/chat';

interface SessionItemProps {
  session: SessionInfo;
  onDelete: (sessionId: string) => void;
  onTitleUpdate?: (sessionId: string, newTitle: string) => void;  // Sprint 17 Feature 17.3
}

export function SessionItem({ session, onDelete, onTitleUpdate }: SessionItemProps) {
  const navigate = useNavigate();
  const [showDelete, setShowDelete] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Sprint 17 Feature 17.3: Title editing state
  const [isEditing, setIsEditing] = useState(false);
  const [editedTitle, setEditedTitle] = useState(session.title || session.last_message || 'Neue Konversation');
  const [isSaving, setIsSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus input when entering edit mode
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleClick = () => {
    if (!isEditing) {
      navigate(`/search?session_id=${session.session_id}`);
    }
  };

  // Sprint 17 Feature 17.3: Title editing handlers
  const handleTitleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsEditing(true);
  };

  const handleTitleSave = async () => {
    if (!editedTitle.trim() || editedTitle === (session.title || session.last_message)) {
      setIsEditing(false);
      return;
    }

    setIsSaving(true);
    try {
      await updateConversationTitle(session.session_id, editedTitle.trim());
      onTitleUpdate?.(session.session_id, editedTitle.trim());
      setIsEditing(false);
    } catch (err) {
      console.error('Failed to update title:', err);
      alert('Fehler beim Aktualisieren des Titels');
      setEditedTitle(session.title || session.last_message || 'Neue Konversation');
    } finally {
      setIsSaving(false);
    }
  };

  const handleTitleCancel = () => {
    setEditedTitle(session.title || session.last_message || 'Neue Konversation');
    setIsEditing(false);
  };

  const handleTitleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleTitleSave();
    } else if (e.key === 'Escape') {
      handleTitleCancel();
    }
  };

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();

    if (!confirm('Möchten Sie diese Konversation wirklich löschen?')) {
      return;
    }

    setIsDeleting(true);
    try {
      await deleteSession(session.session_id);
      onDelete(session.session_id);
    } catch (err) {
      console.error('Failed to delete session:', err);
      alert('Fehler beim Löschen der Sitzung');
    } finally {
      setIsDeleting(false);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '';

    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Gerade eben';
    if (diffMins < 60) return `vor ${diffMins} Min`;
    if (diffHours < 24) return `vor ${diffHours} Std`;
    if (diffDays < 7) return `vor ${diffDays} Tag${diffDays > 1 ? 'en' : ''}`;

    return date.toLocaleDateString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
    });
  };

  return (
    <div
      className="group relative p-3 hover:bg-gray-50 rounded-lg cursor-pointer transition"
      onClick={handleClick}
      onMouseEnter={() => setShowDelete(true)}
      onMouseLeave={() => setShowDelete(false)}
    >
      {/* Content - Sprint 17 Feature 17.3: Inline title editing */}
      <div className="pr-8 flex-1">
        {isEditing ? (
          <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <input
              ref={inputRef}
              type="text"
              value={editedTitle}
              onChange={(e) => setEditedTitle(e.target.value)}
              onKeyDown={handleTitleKeyDown}
              onBlur={handleTitleSave}
              disabled={isSaving}
              className="flex-1 text-sm font-medium text-gray-900 px-2 py-1 border border-blue-500 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              maxLength={100}
            />
            {isSaving && (
              <svg className="w-4 h-4 animate-spin text-blue-500" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            )}
          </div>
        ) : (
          <>
            <div
              className="text-sm font-medium text-gray-900 line-clamp-2 mb-1 cursor-text hover:text-blue-600 transition"
              onClick={handleTitleClick}
              title="Klicken zum Bearbeiten"
            >
              {session.title || session.last_message || 'Neue Konversation'}
            </div>
            <div className="text-xs text-gray-500 flex items-center space-x-2">
              <span>{session.message_count || 0} Nachricht{(session.message_count || 0) !== 1 ? 'en' : ''}</span>
              <span>•</span>
              <span>{formatDate(session.last_activity || session.updated_at)}</span>
            </div>
          </>
        )}
      </div>

      {/* Delete Button */}
      {showDelete && (
        <button
          onClick={handleDelete}
          disabled={isDeleting}
          className="absolute right-3 top-1/2 -translate-y-1/2
                     p-1.5 bg-red-500 text-white rounded-md
                     opacity-0 group-hover:opacity-100
                     hover:bg-red-600
                     disabled:opacity-50 disabled:cursor-not-allowed
                     transition-all"
          title="Löschen"
        >
          {isDeleting ? (
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          )}
        </button>
      )}
    </div>
  );
}

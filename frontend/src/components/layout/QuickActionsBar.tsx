/**
 * QuickActionsBar Component
 * Sprint 27 Feature 27.9: Quick action buttons for common tasks
 *
 * Features:
 * - New Chat with Ctrl+N shortcut
 * - Clear History with confirmation
 * - Settings button (placeholder)
 */

import { useState, useEffect } from 'react';

interface QuickActionsBarProps {
  onNewChat: () => void;
  onClearHistory: () => void;
  onSettings?: () => void;
}

export function QuickActionsBar({ onNewChat, onClearHistory, onSettings }: QuickActionsBarProps) {
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  // Keyboard shortcut: Ctrl+N for New Chat
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'n') {
        e.preventDefault();
        onNewChat();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onNewChat]);

  const handleClearHistory = () => {
    setShowClearConfirm(true);
  };

  const confirmClearHistory = () => {
    onClearHistory();
    setShowClearConfirm(false);
  };

  const cancelClearHistory = () => {
    setShowClearConfirm(false);
  };

  return (
    <div className="space-y-2 mb-4">
      {/* Action Buttons Row */}
      <div className="flex items-center space-x-2">
        {/* New Chat Button */}
        <button
          onClick={onNewChat}
          className="flex-1 py-2 px-3 bg-primary text-white rounded-lg
                     hover:bg-primary-hover transition-colors
                     flex items-center justify-center space-x-1 text-sm"
          title="Neuer Chat (Ctrl+N)"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          <span>Neu</span>
        </button>

        {/* Clear History Button */}
        <button
          onClick={handleClearHistory}
          className="flex-1 py-2 px-3 bg-gray-100 text-gray-700 rounded-lg
                     hover:bg-gray-200 transition-colors
                     flex items-center justify-center space-x-1 text-sm"
          title="Verlauf löschen"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          <span>Löschen</span>
        </button>

        {/* Settings Button */}
        <button
          onClick={onSettings}
          className="py-2 px-3 bg-gray-100 text-gray-700 rounded-lg
                     hover:bg-gray-200 transition-colors
                     flex items-center justify-center"
          title="Einstellungen"
          disabled={!onSettings}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>

      {/* Confirmation Dialog for Clear History */}
      {showClearConfirm && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-2">
          <p className="text-sm text-amber-800">
            Verlauf wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.
          </p>
          <div className="flex space-x-2">
            <button
              onClick={confirmClearHistory}
              className="flex-1 py-1.5 px-3 bg-red-600 text-white rounded text-sm
                         hover:bg-red-700 transition-colors"
            >
              Löschen
            </button>
            <button
              onClick={cancelClearHistory}
              className="flex-1 py-1.5 px-3 bg-gray-200 text-gray-700 rounded text-sm
                         hover:bg-gray-300 transition-colors"
            >
              Abbrechen
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

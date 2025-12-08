/**
 * SharedConversationPage Component
 * Sprint 38 Feature 38.3: Share Conversation Links
 *
 * Features:
 * - Display shared conversation (read-only)
 * - No authentication required (public link)
 * - Yellow banner indicating read-only view
 * - Handle expired/not found links
 * - Display conversation title and messages
 * - Format timestamps
 */

import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { AlertCircle, Clock, MessageSquare, Home, Share2 } from 'lucide-react';
import { getSharedConversation, type SharedConversationResponse } from '../api/chat';
import { ChatMessage } from '../components/chat/ChatMessage';

export function SharedConversationPage() {
  const { shareToken } = useParams<{ shareToken: string }>();
  const [conversation, setConversation] = useState<SharedConversationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!shareToken) {
      setError('Invalid share link');
      setIsLoading(false);
      return;
    }

    loadSharedConversation();
  }, [shareToken]);

  const loadSharedConversation = async () => {
    if (!shareToken) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await getSharedConversation(shareToken);
      setConversation(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load shared conversation';

      if (errorMessage.includes('404') || errorMessage.includes('not found')) {
        setError('This shared link is invalid or has expired.');
      } else {
        setError(errorMessage);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (isoString: string): string => {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading shared conversation...</p>
        </div>
      </div>
    );
  }

  if (error || !conversation) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 text-center">
            <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Link Not Found
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {error || 'This shared conversation could not be found.'}
            </p>
            <Link
              to="/"
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
            >
              <Home className="w-4 h-4" />
              Go to Home
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header with read-only banner */}
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border-b border-yellow-200 dark:border-yellow-800">
        <div className="max-w-4xl mx-auto px-4 py-3">
          <div className="flex items-center gap-2 text-yellow-800 dark:text-yellow-300">
            <Share2 className="w-5 h-5" />
            <p className="text-sm font-medium">
              This is a shared conversation (read-only)
            </p>
          </div>
        </div>
      </div>

      {/* Conversation header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                {conversation.title || 'Shared Conversation'}
              </h1>
              <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                <div className="flex items-center gap-1">
                  <MessageSquare className="w-4 h-4" />
                  <span>{conversation.message_count} messages</span>
                </div>
                {conversation.created_at && (
                  <div className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    <span>Created {formatDate(conversation.created_at)}</span>
                  </div>
                )}
              </div>
            </div>
            <Link
              to="/"
              className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
            >
              <Home className="w-4 h-4" />
              Home
            </Link>
          </div>

          {/* Expiry information */}
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
            <p className="text-xs text-gray-600 dark:text-gray-400">
              Shared on {formatDate(conversation.shared_at)} · Expires on {formatDate(conversation.expires_at)}
            </p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="space-y-6">
          {conversation.messages.map((msg, index) => (
            <div key={index} className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
              <ChatMessage
                message={{
                  role: msg.role as 'user' | 'assistant',
                  content: msg.content,
                  timestamp: msg.timestamp,
                  citations: msg.sources,
                }}
              />
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-12 pt-6 border-t border-gray-200 dark:border-gray-700 text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Want to chat with AEGIS RAG yourself?
          </p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors font-medium"
          >
            <MessageSquare className="w-4 h-4" />
            Start Your Own Conversation
          </Link>
        </div>
      </div>
    </div>
  );
}

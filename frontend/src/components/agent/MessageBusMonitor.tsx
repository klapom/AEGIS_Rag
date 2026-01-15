/**
 * MessageBusMonitor Component
 * Sprint 98 Feature 98.1: Agent Communication Dashboard
 *
 * Real-time monitoring of agent-to-agent messages via MessageBus.
 *
 * Features:
 * - Auto-refresh every 2 seconds
 * - Message filtering by type and agent
 * - Pause/resume stream
 * - View message details modal
 * - Compact and detailed view modes
 */

import { useState, useEffect, useCallback } from 'react';
import { MessageSquare, Pause, Play, Trash2, AlertCircle } from 'lucide-react';
import {
  fetchAgentMessages,
  type AgentMessage,
  type MessageQueryParams,
} from '../../api/agentCommunication';

interface MessageBusMonitorProps {
  className?: string;
}

/**
 * Message type display colors
 */
const MESSAGE_TYPE_COLORS: Record<string, string> = {
  SKILL_REQUEST: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  SKILL_RESPONSE: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  BROADCAST: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  EVENT: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  ERROR: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

export function MessageBusMonitor({ className = '' }: MessageBusMonitorProps) {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [selectedMessage, setSelectedMessage] = useState<AgentMessage | null>(null);

  // Filters
  const [messageTypeFilter, setMessageTypeFilter] = useState<string>('all');
  const [agentFilter, setAgentFilter] = useState<string>('');

  /**
   * Load messages from API
   */
  const loadMessages = useCallback(async () => {
    if (isPaused) return;

    setLoading(true);
    setError(null);

    try {
      const params: MessageQueryParams = {
        timeRange: '1h',
        limit: 50,
      };

      if (messageTypeFilter !== 'all') {
        params.messageType = messageTypeFilter;
      }

      if (agentFilter) {
        params.agentId = agentFilter;
      }

      const response = await fetchAgentMessages(params);
      setMessages(response.messages);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch messages'));
    } finally {
      setLoading(false);
    }
  }, [isPaused, messageTypeFilter, agentFilter]);

  // Initial load
  useEffect(() => {
    void loadMessages();
  }, [loadMessages]);

  // Auto-refresh every 2 seconds
  useEffect(() => {
    if (isPaused) return;

    const interval = setInterval(() => {
      void loadMessages();
    }, 2000);

    return () => clearInterval(interval);
  }, [loadMessages, isPaused]);

  /**
   * Format timestamp for display
   */
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  /**
   * Handle pause/resume
   */
  const togglePause = () => {
    setIsPaused(!isPaused);
  };

  /**
   * Clear messages
   */
  const clearMessages = () => {
    setMessages([]);
  };

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
            <MessageSquare className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              MessageBus (Live)
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {messages.length} messages in last hour
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={togglePause}
            className="px-3 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors flex items-center gap-2"
            data-testid="pause-resume-button"
          >
            {isPaused ? (
              <>
                <Play className="w-4 h-4" />
                Resume
              </>
            ) : (
              <>
                <Pause className="w-4 h-4" />
                Pause
              </>
            )}
          </button>
          <button
            onClick={clearMessages}
            className="px-3 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors flex items-center gap-2"
            data-testid="clear-messages-button"
          >
            <Trash2 className="w-4 h-4" />
            Clear
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <select
          value={messageTypeFilter}
          onChange={(e) => setMessageTypeFilter(e.target.value)}
          className="px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
          data-testid="message-type-filter"
        >
          <option value="all">All Types</option>
          <option value="SKILL_REQUEST">Skill Request</option>
          <option value="SKILL_RESPONSE">Skill Response</option>
          <option value="BROADCAST">Broadcast</option>
          <option value="EVENT">Event</option>
          <option value="ERROR">Error</option>
        </select>

        <input
          type="text"
          placeholder="Filter by agent..."
          value={agentFilter}
          onChange={(e) => setAgentFilter(e.target.value)}
          className="flex-1 px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
          data-testid="agent-filter"
        />
      </div>

      {/* Messages List */}
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {loading && messages.length === 0 && (
          <div className="text-center py-8 text-gray-500">Loading messages...</div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            <span className="text-red-700 dark:text-red-300">{error.message}</span>
          </div>
        )}

        {!loading && !error && messages.length === 0 && (
          <div className="text-center py-8 text-gray-500">No messages found</div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-600 transition-colors cursor-pointer"
            onClick={() => setSelectedMessage(message)}
            data-testid={`message-${message.id}`}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-gray-500 dark:text-gray-400">
                  {formatTime(message.timestamp)}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded font-medium ${MESSAGE_TYPE_COLORS[message.message_type] || 'bg-gray-100 text-gray-700'}`}
                >
                  {message.message_type}
                </span>
              </div>
              {message.duration_ms && (
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {message.duration_ms}ms
                </span>
              )}
            </div>

            <div className="text-sm text-gray-900 dark:text-gray-100">
              <span className="font-medium">{message.sender}</span>
              <span className="text-gray-500 dark:text-gray-400 mx-2">→</span>
              <span className="font-medium">{message.receiver}</span>
            </div>

            <div className="mt-2 text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
              {JSON.stringify(message.payload, null, 2).slice(0, 100)}...
            </div>

            <button
              className="mt-2 text-xs text-blue-600 dark:text-blue-400 hover:underline"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedMessage(message);
              }}
            >
              View Details
            </button>
          </div>
        ))}
      </div>

      {/* Message Details Modal */}
      {selectedMessage && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedMessage(null)}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Message Details
              </h3>
              <button
                onClick={() => setSelectedMessage(null)}
                className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-sm">
              <div>
                <span className="font-medium text-gray-700 dark:text-gray-300">ID:</span>
                <span className="ml-2 font-mono text-gray-600 dark:text-gray-400">
                  {selectedMessage.id}
                </span>
              </div>
              <div>
                <span className="font-medium text-gray-700 dark:text-gray-300">Timestamp:</span>
                <span className="ml-2 text-gray-600 dark:text-gray-400">
                  {new Date(selectedMessage.timestamp).toLocaleString()}
                </span>
              </div>
              <div>
                <span className="font-medium text-gray-700 dark:text-gray-300">Type:</span>
                <span className="ml-2 text-gray-600 dark:text-gray-400">
                  {selectedMessage.message_type}
                </span>
              </div>
              <div>
                <span className="font-medium text-gray-700 dark:text-gray-300">Sender:</span>
                <span className="ml-2 text-gray-600 dark:text-gray-400">
                  {selectedMessage.sender}
                </span>
              </div>
              <div>
                <span className="font-medium text-gray-700 dark:text-gray-300">Receiver:</span>
                <span className="ml-2 text-gray-600 dark:text-gray-400">
                  {selectedMessage.receiver}
                </span>
              </div>
              {selectedMessage.duration_ms && (
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">Duration:</span>
                  <span className="ml-2 text-gray-600 dark:text-gray-400">
                    {selectedMessage.duration_ms}ms
                  </span>
                </div>
              )}
              <div>
                <span className="font-medium text-gray-700 dark:text-gray-300 block mb-2">
                  Payload:
                </span>
                <pre className="bg-gray-100 dark:bg-gray-900 p-3 rounded-lg overflow-x-auto text-xs">
                  {JSON.stringify(selectedMessage.payload, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

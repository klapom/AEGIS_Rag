/**
 * HomePage Component (Chat Interface)
 * Sprint 15 Feature 15.3: Landing page with SearchInput component
 * Sprint 31: Transformed into full chat interface for E2E test compatibility
 * Sprint 35 Feature 35.5: Session History Sidebar
 * Sprint 46 Feature 46.1: ConversationView Integration
 * Sprint 46 Feature 46.2: ReasoningPanel Integration
 * Sprint 47: Fixed infinite re-render loop with stable callbacks
 * Sprint 48 Feature 48.6: Phase event display integration
 * Sprint 48 Feature 48.10: Request timeout and cancel integration
 *
 * Features:
 * - Chat-style conversation layout with ConversationView
 * - Message input with inline chat responses
 * - Conversation history display with MessageBubble
 * - Session management with sidebar
 * - Citations and follow-up questions
 * - Welcome screen with quick prompts
 * - Transparent reasoning panel for assistant messages
 * - Real-time phase progress display (Sprint 48)
 * - Timeout warning and request cancellation (Sprint 48)
 */

import { useState, useCallback, useMemo, useRef } from 'react';
import { type SearchMode } from '../components/search';
import { ConversationView, SessionSidebar, type MessageData } from '../components/chat';
import { getConversation } from '../api/chat';
import type { Source } from '../types/chat';
import type { ReasoningData } from '../types/reasoning';
import { useStreamChat, buildReasoningData } from '../hooks/useStreamChat';

/**
 * Internal message format for conversation history
 */
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  query?: string;
  mode?: SearchMode;
  namespaces?: string[];
  sources?: Source[];
  reasoningData?: ReasoningData | null;
  timestamp?: string;
}

/**
 * Generate a unique message ID
 */
function generateMessageId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

export function HomePage() {
  // Conversation state
  const [conversationHistory, setConversationHistory] = useState<Message[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | undefined>();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Current query state for streaming
  const [currentQuery, setCurrentQuery] = useState<string | null>(null);
  const [currentMode, setCurrentMode] = useState<SearchMode>('hybrid');
  const [currentNamespaces, setCurrentNamespaces] = useState<string[]>([]);

  // Sprint 47 Fix: Use ref to track activeSessionId for the callback
  // This avoids needing activeSessionId in the callback's dependencies
  const activeSessionIdRef = useRef(activeSessionId);
  activeSessionIdRef.current = activeSessionId;

  // Sprint 47 Fix: Stable callbacks using useCallback with minimal dependencies
  // These callbacks use refs internally to access current state without
  // needing to include that state in dependency arrays
  const handleSessionIdReceived = useCallback((sessionId: string) => {
    // Use ref to check current value without dependency
    if (!activeSessionIdRef.current && sessionId) {
      setActiveSessionId(sessionId);
    }
  }, []);

  const handleStreamComplete = useCallback((answer: string, sources: Source[], reasoningData: ReasoningData | null) => {
    // Add completed assistant message to history
    setConversationHistory((prev) => [
      ...prev,
      {
        id: generateMessageId(),
        role: 'assistant',
        content: answer,
        sources,
        reasoningData,
        timestamp: new Date().toISOString(),
      },
    ]);
    // Clear current query after completion (keep answer visible in history)
    // Note: We don't clear immediately to allow the streaming message to be replaced by history
  }, []);

  // Use streaming hook for SSE
  const streamingState = useStreamChat({
    query: currentQuery,
    mode: currentMode,
    namespaces: currentNamespaces,
    sessionId: activeSessionId,
    onSessionIdReceived: handleSessionIdReceived,
    onComplete: handleStreamComplete,
  });

  /**
   * Handle new message submission
   */
  const handleSearch = useCallback((query: string, mode: SearchMode, namespaces: string[]) => {
    // Add user message to history
    setConversationHistory((prev) => [
      ...prev,
      {
        id: generateMessageId(),
        role: 'user',
        content: query,
        query,
        mode,
        namespaces,
        timestamp: new Date().toISOString(),
      },
    ]);

    // Trigger streaming response
    setCurrentQuery(query);
    setCurrentMode(mode);
    setCurrentNamespaces(namespaces);
  }, []);

  /**
   * Handle quick prompt click
   */
  const handleQuickPrompt = useCallback((prompt: string) => {
    handleSearch(prompt, 'hybrid', currentNamespaces);
  }, [handleSearch, currentNamespaces]);

  /**
   * Handle new chat creation
   */
  const handleNewChat = useCallback(() => {
    setActiveSessionId(undefined);
    setConversationHistory([]);
    setCurrentQuery(null);
  }, []);

  /**
   * Handle session selection from sidebar
   */
  const handleSelectSession = useCallback(async (sessionId: string) => {
    try {
      const conversation = await getConversation(sessionId);
      setActiveSessionId(sessionId);

      // Convert messages to Message format
      const messages: Message[] = conversation.messages.map(
        (m: { role: 'user' | 'assistant'; content: string }) => ({
          id: generateMessageId(),
          role: m.role,
          content: m.content,
          mode: 'hybrid' as SearchMode,
        })
      );

      setConversationHistory(messages);
      setCurrentQuery(null);
    } catch (error) {
      console.error('Failed to load conversation:', error);
      alert('Failed to load conversation');
    }
  }, []);

  // Sprint 47 Fix: Use a stable ID for the streaming message to prevent
  // unnecessary re-renders and potential infinite loops
  const streamingMessageIdRef = useRef<string>('streaming-0');

  /**
   * Build messages array for ConversationView
   * Combines history with current streaming message
   */
  const messages = useMemo((): MessageData[] => {
    // Convert history to MessageData format
    const historyMessages: MessageData[] = conversationHistory.map((msg) => ({
      id: msg.id,
      role: msg.role,
      content: msg.content,
      sources: msg.sources,
      timestamp: msg.timestamp,
      isStreaming: false,
      reasoningData: msg.reasoningData,
    }));

    // If streaming, add current streaming message (but only if we have content)
    if (streamingState.isStreaming || (currentQuery && streamingState.answer)) {
      // Check if this streaming message is already in history (completed)
      const lastHistoryMessage = historyMessages[historyMessages.length - 1];
      const isAlreadyInHistory =
        lastHistoryMessage?.role === 'assistant' &&
        lastHistoryMessage?.content === streamingState.answer;

      if (!isAlreadyInHistory && streamingState.answer) {
        // Build reasoning data from metadata if available
        // Sprint 51: Include phaseEvents to persist phases after answer appears
        const reasoningData = buildReasoningData(
          streamingState.metadata,
          streamingState.intent,
          streamingState.phaseEvents
        );

        // Sprint 51 Fix: Use citationMap as fallback for sources
        // Backend sends citation_map instead of individual source events
        let sources = streamingState.sources;
        if ((!sources || sources.length === 0) && streamingState.citationMap) {
          // Convert citationMap (Record<number, Source>) to Source[]
          sources = Object.entries(streamingState.citationMap)
            .sort(([a], [b]) => Number(a) - Number(b))
            .map(([, source]) => source);
        }

        // Sprint 47 Fix: Use stable streaming ID from ref instead of Date.now()
        // This prevents unnecessary re-renders caused by new IDs on each render
        historyMessages.push({
          id: streamingMessageIdRef.current,
          role: 'assistant',
          content: streamingState.answer,
          sources,
          isStreaming: streamingState.isStreaming,
          reasoningData,
        });
      }
    }

    return historyMessages;
  }, [conversationHistory, streamingState, currentQuery]);

  // Sprint 47 Fix: Generate new streaming ID when a new query starts
  // This ensures the streaming message has a unique but stable ID during streaming
  const prevQueryRef = useRef<string | null>(null);
  if (currentQuery !== prevQueryRef.current) {
    prevQueryRef.current = currentQuery;
    if (currentQuery) {
      streamingMessageIdRef.current = `streaming-${Date.now()}`;
    }
  }

  // Show welcome screen if no conversation yet
  const showWelcome = messages.length === 0;

  /**
   * Welcome screen component with quick prompts
   */
  const welcomeContent = (
    <div className="space-y-12 max-w-4xl mx-auto px-6">
      {/* Welcome Text */}
      <div className="text-center space-y-3">
        <h1 className="text-5xl font-bold text-gray-900">Was möchten Sie wissen?</h1>
        <p className="text-xl text-gray-600">
          Durchsuchen Sie Ihre Dokumente mit KI-gestützter Hybrid-Retrieval
        </p>
      </div>

      {/* Quick Prompts */}
      <div className="space-y-4">
        <h2 className="text-center text-sm font-semibold text-gray-500 uppercase tracking-wide">
          Beispiel-Fragen
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            'Erkläre mir das Konzept von RAG',
            'Was ist ein Knowledge Graph?',
            'Wie funktioniert Hybrid Search?',
            'Zeige mir die Systemarchitektur',
          ].map((prompt) => (
            <button
              key={prompt}
              onClick={() => handleQuickPrompt(prompt)}
              data-testid={`quick-prompt-${prompt.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}
              aria-label={`Quick prompt: ${prompt}`}
              className="p-4 text-left border-2 border-gray-200 rounded-xl
                         hover:border-primary hover:shadow-md hover:bg-gray-50
                         transition-all text-sm text-gray-700 font-medium"
            >
              <span className="text-gray-400 mr-2">-&gt;</span>
              {prompt}
            </button>
          ))}
        </div>
      </div>

      {/* Features Overview */}
      <div className="grid grid-cols-4 gap-6 pt-8 border-t border-gray-200">
        <FeatureCard icon="magnifying-glass" title="Vector Search" description="Semantische Ähnlichkeit" />
        <FeatureCard icon="network" title="Graph RAG" description="Entity-Beziehungen" />
        <FeatureCard icon="chat" title="Memory" description="Kontext-Awareness" />
        <FeatureCard icon="shuffle" title="Hybrid" description="Best of All" />
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Session Sidebar */}
      <SessionSidebar
        currentSessionId={activeSessionId || null}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Session ID Badge */}
        {activeSessionId && (
          <div className="flex-shrink-0 bg-white border-b border-gray-200 px-6 py-2">
            <div className="text-xs text-gray-500">
              <span>Session: </span>
              <span data-testid="session-id" data-session-id={activeSessionId} className="font-mono">
                {activeSessionId.slice(0, 8)}...
              </span>
            </div>
          </div>
        )}

        {/* Conversation View */}
        <ConversationView
          messages={messages}
          isStreaming={streamingState.isStreaming}
          onSendMessage={handleSearch}
          placeholder={showWelcome ? 'Fragen Sie alles über Ihre Dokumente...' : 'Neue Frage...'}
          showTypingIndicator={streamingState.isStreaming && !streamingState.answer}
          typingText="AegisRAG denkt nach..."
          emptyStateContent={welcomeContent}
          currentPhase={streamingState.currentPhase}
          phaseEvents={streamingState.phaseEvents}
          showTimeoutWarning={streamingState.showTimeoutWarning}
          onCancel={streamingState.cancelRequest}
        />
      </div>
    </div>
  );
}

interface FeatureCardProps {
  icon: string;
  title: string;
  description: string;
}

function FeatureCard({ icon, title, description }: FeatureCardProps) {
  // Map icon names to emoji for simplicity (could be replaced with Lucide icons)
  const iconMap: Record<string, string> = {
    'magnifying-glass': '\uD83D\uDD0D',
    'network': '\uD83D\uDD78\uFE0F',
    'chat': '\uD83D\uDCAD',
    'shuffle': '\uD83D\uDD00',
  };

  return (
    <div className="text-center space-y-2">
      <div className="text-3xl">{iconMap[icon] || icon}</div>
      <h3 className="font-semibold text-gray-900 text-sm">{title}</h3>
      <p className="text-xs text-gray-500">{description}</p>
    </div>
  );
}

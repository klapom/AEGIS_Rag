/**
 * HomePage Component (Chat Interface)
 * Sprint 15 Feature 15.3: Landing page with SearchInput component
 * Sprint 31: Transformed into full chat interface for E2E test compatibility
 * Sprint 35 Feature 35.5: Session History Sidebar
 *
 * Features:
 * - Message input with inline chat responses
 * - Conversation history display
 * - Session management with sidebar
 * - Citations and follow-up questions
 * - Welcome screen with quick prompts
 */

import { useState, useCallback } from 'react';
import { SearchInput, type SearchMode } from '../components/search';
import { StreamingAnswer, SessionSidebar } from '../components/chat';
import { getConversation } from '../api/chat';
import type { Source } from '../types/chat';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  query?: string;
  mode?: SearchMode;
  namespaces?: string[];
}

export function HomePage() {
  const [conversationHistory, setConversationHistory] = useState<Message[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | undefined>();
  const [currentQuery, setCurrentQuery] = useState<string | null>(null);
  const [currentMode, setCurrentMode] = useState<SearchMode>('hybrid');
  const [currentNamespaces, setCurrentNamespaces] = useState<string[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleSearch = (query: string, mode: SearchMode, namespaces: string[]) => {
    // Add user message to history
    setConversationHistory(prev => [...prev, { role: 'user', content: query, query, mode, namespaces }]);

    // Trigger streaming response
    setCurrentQuery(query);
    setCurrentMode(mode);
    setCurrentNamespaces(namespaces);
  };

  const handleQuickPrompt = (prompt: string) => {
    // Use current namespaces for quick prompts (or all if none selected)
    handleSearch(prompt, 'hybrid', currentNamespaces);
  };

  const handleSessionIdReceived = (sessionId: string) => {
    if (!activeSessionId && sessionId) {
      setActiveSessionId(sessionId);
    }
  };

  const handleFollowUpQuestion = (question: string) => {
    handleSearch(question, currentMode, currentNamespaces);
  };

  // Sprint 32: Save completed answer to history
  // Sprint 32 Fix: DON'T clear currentQuery - keep StreamingAnswer rendered so citations remain visible
  const handleAnswerComplete = useCallback((answer: string, _sources: Source[]) => {
    // Add assistant message to history (for when new question is asked and this one moves to history)
    setConversationHistory(prev => [...prev, { role: 'assistant', content: answer }]);
    // NOTE: Don't clear currentQuery! StreamingAnswer must stay rendered to show citations.
    // It will be replaced when user asks a new question via handleSearch.
  }, []);

  // Sprint 35 Feature 35.5: Session management handlers
  const handleNewChat = () => {
    setActiveSessionId(undefined);
    setConversationHistory([]);
    setCurrentQuery(null);
  };

  const handleSelectSession = async (sessionId: string) => {
    try {
      const conversation = await getConversation(sessionId);
      setActiveSessionId(sessionId);

      // Convert messages to Message format
      const messages: Message[] = conversation.messages.map((m: { role: 'user' | 'assistant'; content: string }) => ({
        role: m.role,
        content: m.content,
        mode: 'hybrid' as SearchMode, // Default mode for loaded conversations
      }));

      setConversationHistory(messages);
      setCurrentQuery(null); // Clear any active streaming
    } catch (error) {
      console.error('Failed to load conversation:', error);
      alert('Failed to load conversation');
    }
  };

  // Show welcome screen if no conversation yet
  const showWelcome = conversationHistory.length === 0;

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
        {/* Top Search Bar (Sticky) */}
        <div className="flex-shrink-0 bg-white border-b border-gray-200 shadow-sm">
          <div className="max-w-5xl mx-auto py-4 px-6">
            {activeSessionId && (
              <div className="mb-2 text-xs text-gray-500">
                <span>Session: </span>
                <span data-testid="session-id" data-session-id={activeSessionId} className="font-mono">
                  {activeSessionId.slice(0, 8)}...
                </span>
              </div>
            )}
            <SearchInput
              onSubmit={handleSearch}
              placeholder={showWelcome ? "Fragen Sie alles über Ihre Dokumente..." : "Neue Frage..."}
              autoFocus={showWelcome}
            />
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-5xl mx-auto py-8 px-6">
        {showWelcome ? (
          /* Welcome Screen with Quick Prompts */
          <div className="space-y-12">
            {/* Welcome Text */}
            <div className="text-center space-y-3">
              <h1 className="text-5xl font-bold text-gray-900">
                Was möchten Sie wissen?
              </h1>
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
                    <span className="text-gray-400 mr-2">→</span>
                    {prompt}
                  </button>
                ))}
              </div>
            </div>

            {/* Features Overview */}
            <div className="grid grid-cols-4 gap-6 pt-8 border-t border-gray-200">
              <FeatureCard
                icon="🔍"
                title="Vector Search"
                description="Semantische Ähnlichkeit"
              />
              <FeatureCard
                icon="🕸️"
                title="Graph RAG"
                description="Entity-Beziehungen"
              />
              <FeatureCard
                icon="💭"
                title="Memory"
                description="Kontext-Awareness"
              />
              <FeatureCard
                icon="🔀"
                title="Hybrid"
                description="Best of All"
              />
            </div>
          </div>
        ) : (
          /* Conversation View */
          <div className="space-y-6">
            {/* Conversation History */}
            {conversationHistory.map((message, index) => (
              <div
                key={index}
                data-testid="message"
                className={`p-6 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-blue-50 border-2 border-blue-200'
                    : 'bg-white border-2 border-gray-200'
                }`}
              >
                <div className="text-xs font-semibold text-gray-500 uppercase mb-2">
                  {message.role === 'user' ? 'Frage' : 'Antwort'}
                </div>
                <div className="text-gray-900 whitespace-pre-wrap">{message.content}</div>
              </div>
            ))}

            {/* Streaming Answer (Latest Query) */}
            {currentQuery && (
              <StreamingAnswer
                query={currentQuery}
                mode={currentMode}
                namespaces={currentNamespaces}
                sessionId={activeSessionId}
                onSessionIdReceived={handleSessionIdReceived}
                onFollowUpQuestion={handleFollowUpQuestion}
                onComplete={handleAnswerComplete}
              />
            )}
          </div>
        )}
          </div>
        </div>
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
  return (
    <div className="text-center space-y-2">
      <div className="text-3xl">{icon}</div>
      <h3 className="font-semibold text-gray-900 text-sm">{title}</h3>
      <p className="text-xs text-gray-500">{description}</p>
    </div>
  );
}

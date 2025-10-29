/**
 * HomePage Component
 * Sprint 15 Feature 15.3: Landing page with SearchInput component
 *
 * Perplexity-inspired homepage with centered search input
 */

import { useNavigate } from 'react-router-dom';
import { SearchInput, type SearchMode } from '../components/search';

export function HomePage() {
  const navigate = useNavigate();

  const handleSearch = (query: string, mode: SearchMode) => {
    // Navigate to search results page (Feature 15.4)
    navigate(`/search?q=${encodeURIComponent(query)}&mode=${mode}`);
  };

  const handleQuickPrompt = (prompt: string) => {
    handleSearch(prompt, 'hybrid');
  };

  return (
    <div className="flex items-center justify-center min-h-full px-6 py-12">
      <div className="max-w-4xl w-full space-y-12">
        {/* Welcome Text */}
        <div className="text-center space-y-3">
          <h1 className="text-5xl font-bold text-gray-900">
            Was möchten Sie wissen?
          </h1>
          <p className="text-xl text-gray-600">
            Durchsuchen Sie Ihre Dokumente mit KI-gestützter Hybrid-Retrieval
          </p>
        </div>

        {/* Search Input with Mode Selector */}
        <SearchInput onSubmit={handleSearch} autoFocus />

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
                data-testid={`quick-prompt-${prompt.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`} // TD-38: Add testid for E2E tests
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

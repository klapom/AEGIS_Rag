/**
 * HomePage Component
 * Sprint 15 Feature 15.2: Landing page with large centered search
 *
 * Perplexity-inspired homepage with centered search input
 */

export function HomePage() {
  return (
    <div className="flex items-center justify-center min-h-full px-6">
      <div className="max-w-3xl w-full space-y-8">
        {/* Welcome Text */}
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-3">
            Was möchten Sie wissen?
          </h1>
          <p className="text-lg text-gray-600">
            Durchsuchen Sie Ihre Dokumente mit KI-gestützter Retrieval
          </p>
        </div>

        {/* Search Input Placeholder */}
        <div className="relative">
          <input
            type="text"
            placeholder="Fragen Sie alles. Tippen Sie @ für Erwähnungen."
            className="w-full h-28 px-6 pr-48 text-lg border-2 border-gray-200 rounded-3xl
                       focus:border-primary focus:ring-2 focus:ring-primary/20
                       transition-all outline-none"
          />

          {/* Action Buttons (right side) */}
          <div className="absolute right-4 bottom-4 flex items-center space-x-2">
            <button
              className="w-10 h-10 rounded-full bg-primary text-white
                         hover:bg-primary-hover transition-colors
                         flex items-center justify-center"
              aria-label="Send Query"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
            </button>
          </div>
        </div>

        {/* Mode Chips Placeholder */}
        <div className="flex justify-center space-x-3">
          {['Hybrid', 'Vektor', 'Graph', 'Gedächtnis'].map((mode) => (
            <button
              key={mode}
              className="px-4 py-2 rounded-full border-2 border-gray-200
                         text-sm font-medium text-gray-700
                         hover:border-primary hover:text-primary
                         transition-colors"
            >
              {mode}
            </button>
          ))}
        </div>

        {/* Quick Prompts */}
        <div className="grid grid-cols-2 gap-3">
          {[
            'Erkläre mir das Konzept von RAG',
            'Was ist ein Knowledge Graph?',
            'Wie funktioniert Hybrid Search?',
            'Zeige mir die Systemarchitektur',
          ].map((prompt) => (
            <button
              key={prompt}
              className="p-4 text-left border border-gray-200 rounded-xl
                         hover:border-primary hover:shadow-md
                         transition-all text-sm text-gray-700"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * FollowUpQuestions Component
 * Sprint 28 Feature 28.1: Display follow-up questions below answers
 *
 * Features:
 * - Fetch follow-up questions from backend API
 * - Display as clickable cards (Perplexity-inspired)
 * - Loading/error states
 * - Auto-fetch when answer completes
 */

import { useState, useEffect } from 'react';
import { getFollowUpQuestions } from '../../api/chat';

interface FollowUpQuestionsProps {
  sessionId: string;
  onQuestionClick: (question: string) => void;
}

export function FollowUpQuestions({ sessionId, onQuestionClick }: FollowUpQuestionsProps) {
  const [questions, setQuestions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchQuestions = async () => {
      if (!sessionId) {
        console.log('[FollowUpQuestions] No session ID provided');
        return;
      }

      console.log('[FollowUpQuestions] Fetching questions for session:', sessionId);
      setIsLoading(true);
      setError(null);

      try {
        const fetchedQuestions = await getFollowUpQuestions(sessionId);
        console.log('[FollowUpQuestions] Received questions:', fetchedQuestions);
        setQuestions(Array.isArray(fetchedQuestions) ? fetchedQuestions : []);
      } catch (err) {
        console.error('[FollowUpQuestions] Failed to fetch follow-up questions:', err);
        setError('Keine Fragen verfugbar');
        // Don't show empty state - just silently fail
        setQuestions([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchQuestions();
  }, [sessionId]);

  // Don't render if no questions and not loading
  if (!isLoading && (!questions || questions.length === 0)) {
    return null;
  }

  return (
    <div className="space-y-3 mt-6 pt-6 border-t border-gray-200">
      {/* Header */}
      <h3 className="text-sm font-semibold text-gray-700 flex items-center space-x-2">
        <span className="text-lg">?</span>
        <span>Verwandte Fragen</span>
      </h3>

      {/* Loading State: Skeleton Cards */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="followup-loading">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <div className="text-sm text-gray-500 italic">
          {error}
        </div>
      )}

      {/* Questions Grid */}
      {!isLoading && questions && questions.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {questions.map((question, index) => (
            <QuestionCard
              key={index}
              question={question}
              onClick={() => onQuestionClick(question)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface QuestionCardProps {
  question: string;
  onClick: () => void;
}

function QuestionCard({ question, onClick }: QuestionCardProps) {
  return (
    <button
      onClick={onClick}
      className="group p-4 bg-white border-2 border-gray-200 rounded-xl
                 hover:shadow-md hover:border-primary/50
                 transition-all duration-200 text-left
                 flex items-start space-x-3 w-full"
      data-testid="followup-question"
    >
      {/* Question Icon */}
      <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center
                      text-primary/70 group-hover:text-primary transition-colors">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </div>

      {/* Question Text */}
      <p className="text-sm text-gray-700 group-hover:text-gray-900 leading-relaxed">
        {question}
      </p>
    </button>
  );
}

function SkeletonCard() {
  return (
    <div className="p-4 bg-white border-2 border-gray-200 rounded-xl flex items-start space-x-3">
      <div className="flex-shrink-0 w-6 h-6 bg-gray-200 rounded animate-pulse" />
      <div className="flex-1 space-y-2">
        <div className="h-3 bg-gray-200 rounded animate-pulse w-full" />
        <div className="h-3 bg-gray-200 rounded animate-pulse w-3/4" />
      </div>
    </div>
  );
}

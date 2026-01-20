/**
 * IntermediateResults Component
 * Sprint 116.10: Deep Research Multi-Step (13 SP)
 *
 * Displays intermediate answers for each sub-question during multi-step research.
 * Shows partial results as they become available with confidence scores and sources.
 *
 * Features:
 * - Expandable sections for each sub-question
 * - Confidence score indicators
 * - Context count display
 * - Source preview
 * - Progress indicators
 */

import { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  AlertCircle,
  FileText,
  TrendingUp,
} from 'lucide-react';
import type { IntermediateAnswer } from '../../types/research';

interface IntermediateResultsProps {
  /** List of intermediate answers for sub-questions */
  intermediateAnswers: IntermediateAnswer[];
  /** Callback when a sub-question is clicked */
  onSubQuestionClick?: (subQuestion: string) => void;
}

/**
 * Get confidence level and color based on score
 */
function getConfidenceLevel(confidence: number): {
  level: string;
  color: string;
  bgColor: string;
} {
  if (confidence >= 0.8) {
    return { level: 'High', color: 'text-green-700', bgColor: 'bg-green-100' };
  } else if (confidence >= 0.6) {
    return { level: 'Medium', color: 'text-blue-700', bgColor: 'bg-blue-100' };
  } else if (confidence >= 0.4) {
    return { level: 'Low', color: 'text-yellow-700', bgColor: 'bg-yellow-100' };
  } else {
    return { level: 'Very Low', color: 'text-red-700', bgColor: 'bg-red-100' };
  }
}

/**
 * Individual intermediate answer item
 */
interface IntermediateAnswerItemProps {
  answer: IntermediateAnswer;
  index: number;
  isExpanded: boolean;
  onToggle: () => void;
}

function IntermediateAnswerItem({
  answer,
  index,
  isExpanded,
  onToggle,
}: IntermediateAnswerItemProps) {
  const confidenceInfo = getConfidenceLevel(answer.confidence);

  return (
    <div
      className="border border-gray-200 rounded-lg overflow-hidden"
      data-testid={`intermediate-answer-${index}`}
    >
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full p-4 bg-gray-50 hover:bg-gray-100 transition-colors text-left flex items-start gap-3"
        aria-expanded={isExpanded}
        aria-label={`Sub-question ${index + 1}`}
      >
        {/* Expand icon */}
        <div className="flex-shrink-0 mt-1">
          {isExpanded ? (
            <ChevronDown className="w-5 h-5 text-gray-600" />
          ) : (
            <ChevronRight className="w-5 h-5 text-gray-600" />
          )}
        </div>

        {/* Content */}
        <div className="flex-grow min-w-0">
          <div className="flex items-start justify-between gap-4 mb-2">
            <h3 className="font-medium text-gray-900 text-sm flex-grow">
              {index + 1}. {answer.sub_question}
            </h3>

            {/* Confidence badge */}
            <div
              className={`px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${confidenceInfo.bgColor} ${confidenceInfo.color} flex-shrink-0`}
            >
              <TrendingUp className="w-3 h-3" />
              {confidenceInfo.level} ({(answer.confidence * 100).toFixed(0)}%)
            </div>
          </div>

          {/* Meta info */}
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <div className="flex items-center gap-1">
              <FileText className="w-3 h-3" />
              {answer.contexts_count} context{answer.contexts_count !== 1 ? 's' : ''}
            </div>
            <div className="flex items-center gap-1">
              {answer.sources.length > 0 ? (
                <>
                  <CheckCircle2 className="w-3 h-3 text-green-600" />
                  {answer.sources.length} source{answer.sources.length !== 1 ? 's' : ''}
                </>
              ) : (
                <>
                  <AlertCircle className="w-3 h-3 text-yellow-600" />
                  No sources yet
                </>
              )}
            </div>
          </div>
        </div>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="p-4 bg-white border-t border-gray-200">
          {/* Answer text */}
          <div className="mb-4">
            <h4 className="text-xs font-medium text-gray-700 uppercase tracking-wide mb-2">
              Answer
            </h4>
            <div className="text-sm text-gray-900 whitespace-pre-wrap">{answer.answer}</div>
          </div>

          {/* Sources preview */}
          {answer.sources.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-700 uppercase tracking-wide mb-2">
                Top Sources
              </h4>
              <div className="space-y-2">
                {answer.sources.slice(0, 3).map((source, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-gray-50 rounded border border-gray-200 text-sm"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-gray-600">
                        {source.source_type}
                      </span>
                      <span className="text-xs text-gray-500">
                        Score: {source.score.toFixed(3)}
                      </span>
                    </div>
                    <p className="text-gray-700 line-clamp-3">{source.text}</p>
                  </div>
                ))}
              </div>
              {answer.sources.length > 3 && (
                <p className="text-xs text-gray-500 mt-2">
                  +{answer.sources.length - 3} more source{answer.sources.length - 3 !== 1 ? 's' : ''}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * IntermediateResults Component
 */
export function IntermediateResults({
  intermediateAnswers,
  onSubQuestionClick,
}: IntermediateResultsProps) {
  const [expandedIndices, setExpandedIndices] = useState<Set<number>>(new Set([0])); // First item expanded by default

  const toggleExpanded = (index: number) => {
    setExpandedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });

    if (onSubQuestionClick) {
      onSubQuestionClick(intermediateAnswers[index].sub_question);
    }
  };

  // Calculate overall progress
  const totalQuestions = intermediateAnswers.length;
  const avgConfidence =
    intermediateAnswers.reduce((sum, a) => sum + a.confidence, 0) / totalQuestions;
  const totalContexts = intermediateAnswers.reduce((sum, a) => sum + a.contexts_count, 0);
  const totalSources = intermediateAnswers.reduce((sum, a) => sum + a.sources.length, 0);

  return (
    <div
      className="bg-white rounded-xl border border-gray-200 shadow-sm p-6"
      data-testid="intermediate-results"
    >
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-xl font-semibold text-gray-800 mb-2">Intermediate Findings</h2>
        <p className="text-sm text-gray-600">
          Research broken down into {totalQuestions} sub-question{totalQuestions !== 1 ? 's' : ''}{' '}
          with partial answers.
        </p>
      </div>

      {/* Overall stats */}
      <div className="grid grid-cols-3 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-900">
            {(avgConfidence * 100).toFixed(0)}%
          </div>
          <div className="text-xs text-gray-600 mt-1">Avg. Confidence</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-900">{totalContexts}</div>
          <div className="text-xs text-gray-600 mt-1">Total Contexts</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-900">{totalSources}</div>
          <div className="text-xs text-gray-600 mt-1">Total Sources</div>
        </div>
      </div>

      {/* Intermediate answers list */}
      <div className="space-y-3">
        {intermediateAnswers.map((answer, index) => (
          <IntermediateAnswerItem
            key={index}
            answer={answer}
            index={index}
            isExpanded={expandedIndices.has(index)}
            onToggle={() => toggleExpanded(index)}
          />
        ))}
      </div>
    </div>
  );
}

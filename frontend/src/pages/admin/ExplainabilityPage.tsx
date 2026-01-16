/**
 * ExplainabilityPage Component
 * Sprint 98 Feature 98.5: Explainability Dashboard
 *
 * EU AI Act Article 13 Compliance - Decision Transparency
 *
 * Features:
 * - Decision trace viewer with recent queries
 * - Multi-level explanations (User/Expert/Audit)
 * - Decision flow visualization
 * - Source attribution panel
 * - Confidence and hallucination metrics
 */

import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, FileText, AlertCircle, CheckCircle2 } from 'lucide-react';
import {
  getRecentTraces,
  getDecisionTrace,
  getExplanation,
  getSourceAttribution,
} from '../../api/admin';
import type {
  TraceListItem,
  DecisionTrace,
  ExplanationLevel,
  UserExplanation,
  ExpertExplanation,
  AuditExplanation,
  SourceDocument,
} from '../../types/admin';

/**
 * ExplainabilityPage - Main dashboard for decision transparency
 */
export function ExplainabilityPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // State
  const [recentTraces, setRecentTraces] = useState<TraceListItem[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<DecisionTrace | null>(null);
  const [explanation, setExplanation] = useState<
    UserExplanation | ExpertExplanation | AuditExplanation | null
  >(null);
  const [sources, setSources] = useState<SourceDocument[]>([]);
  const [explanationLevel, setExplanationLevel] = useState<ExplanationLevel>('user');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load recent traces on mount
  useEffect(() => {
    loadRecentTraces();

    // If trace ID in URL, load that trace
    const traceId = searchParams.get('traceId');
    if (traceId) {
      loadTrace(traceId);
    }
  }, []);

  // Load recent traces
  const loadRecentTraces = async () => {
    try {
      const traces = await getRecentTraces(undefined, 20);
      setRecentTraces(traces);
    } catch (err) {
      console.error('Failed to load recent traces:', err);
      setError('Failed to load recent traces. Please try again.');
    }
  };

  // Load specific trace
  const loadTrace = async (traceId: string) => {
    setLoading(true);
    setError(null);
    try {
      const trace = await getDecisionTrace(traceId);
      setSelectedTrace(trace);

      // Load explanation
      await loadExplanation(traceId, explanationLevel);

      // Load sources
      const sourceData = await getSourceAttribution(traceId);
      setSources(sourceData);

      // Update URL
      setSearchParams({ traceId });
    } catch (err) {
      console.error('Failed to load trace:', err);
      setError('Failed to load trace details. The trace may not exist or the backend is unavailable.');
    } finally {
      setLoading(false);
    }
  };

  // Load explanation at specified level
  const loadExplanation = async (traceId: string, level: ExplanationLevel) => {
    try {
      const explanationData = await getExplanation(traceId, level);
      setExplanation(explanationData);
    } catch (err) {
      console.error('Failed to load explanation:', err);
      setError('Failed to load explanation. Please try again.');
    }
  };

  // Handle trace selection
  const handleTraceSelect = (traceId: string) => {
    loadTrace(traceId);
  };

  // Handle explanation level change
  const handleLevelChange = (level: ExplanationLevel) => {
    setExplanationLevel(level);
    if (selectedTrace) {
      loadExplanation(selectedTrace.trace_id, level);
    }
  };

  // Get confidence color
  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'text-green-600 dark:text-green-400';
    if (confidence >= 0.5) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  // Get hallucination risk color
  const getHallucinationColor = (risk: number): string => {
    if (risk <= 0.2) return 'text-green-600 dark:text-green-400';
    if (risk <= 0.5) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <div
      className="min-h-screen bg-gray-50 dark:bg-gray-900"
      data-testid="explainability-page"
    >
      <div className="max-w-7xl mx-auto py-8 px-6 space-y-6">
        {/* Header */}
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/admin')}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200 transition-colors rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
              data-testid="back-to-admin-button"
              aria-label="Back to Admin Dashboard"
            >
              <ArrowLeft className="w-5 h-5" />
              <span>Back to Admin</span>
            </button>
          </div>
        </header>

        {/* Page Title */}
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/50 rounded-xl flex items-center justify-center">
              <FileText className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                Explainability Dashboard
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                EU AI Act Art. 13 - Decision Transparency & Source Attribution
              </p>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-red-900 dark:text-red-100">Error</p>
                <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Trace Selector */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Recent Queries
              </h2>
              <div className="space-y-2 max-h-[600px] overflow-y-auto" data-testid="decision-traces-list">
                {recentTraces.length === 0 ? (
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    No recent traces available. Submit queries to see traces here.
                  </p>
                ) : (
                  recentTraces.map((trace) => (
                    <button
                      key={trace.trace_id}
                      onClick={() => handleTraceSelect(trace.trace_id)}
                      className={`w-full text-left p-3 rounded-lg border-2 transition-colors ${
                        selectedTrace?.trace_id === trace.trace_id
                          ? 'bg-purple-50 dark:bg-purple-900/20 border-purple-300 dark:border-purple-700'
                          : 'bg-gray-50 dark:bg-gray-700/50 border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                      data-testid={`trace-item-${trace.trace_id}`}
                    >
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate" data-testid={`trace-query-${trace.trace_id}`}>
                        {trace.query}
                      </p>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(trace.timestamp).toLocaleString()}
                        </span>
                        <span className={`text-xs font-semibold ${getConfidenceColor(trace.confidence)}`} data-testid={`trace-confidence-${trace.trace_id}`}>
                          {(trace.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Trace Details */}
          <div className="lg:col-span-2 space-y-6">
            {!selectedTrace && (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-12 text-center">
                <FileText className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                <p className="text-lg font-medium text-gray-600 dark:text-gray-400">
                  Select a query trace to view details
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
                  Choose from the recent queries on the left to see decision transparency information
                </p>
              </div>
            )}

            {loading && (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-12 text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-4 border-purple-200 dark:border-purple-800 border-t-purple-600 dark:border-t-purple-400 mx-auto mb-4"></div>
                <p className="text-gray-600 dark:text-gray-400">Loading trace details...</p>
              </div>
            )}

            {selectedTrace && !loading && (
              <>
                {/* Query Info */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-6">
                  <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                    Query
                  </h3>
                  <p className="text-lg text-gray-900 dark:text-gray-100 mb-4">
                    {selectedTrace.query}
                  </p>
                  <div className="flex flex-wrap gap-4 text-sm">
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">Trace ID:</span>{' '}
                      <code className="text-gray-900 dark:text-gray-100 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                        {selectedTrace.trace_id}
                      </code>
                    </div>
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">Time:</span>{' '}
                      <span className="text-gray-900 dark:text-gray-100">
                        {new Date(selectedTrace.timestamp).toLocaleString()}
                      </span>
                    </div>
                    {selectedTrace.user_id && (
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">User:</span>{' '}
                        <span className="text-gray-900 dark:text-gray-100">
                          {selectedTrace.user_id}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Explanation Level Selector */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-6">
                  <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
                    Explanation Level
                  </h3>
                  <div className="flex gap-2">
                    {(['user', 'expert', 'audit'] as ExplanationLevel[]).map((level) => (
                      <button
                        key={level}
                        onClick={() => handleLevelChange(level)}
                        className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                          explanationLevel === level
                            ? 'bg-purple-600 dark:bg-purple-500 text-white'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                        }`}
                        data-testid={`level-${level}`}
                      >
                        {level.charAt(0).toUpperCase() + level.slice(1)} View
                      </button>
                    ))}
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                    {explanationLevel === 'user' && 'Simple explanation for end users'}
                    {explanationLevel === 'expert' && 'Technical details for developers'}
                    {explanationLevel === 'audit' && 'Complete trace for compliance audits'}
                  </p>
                </div>

                {/* Explanation Content */}
                {explanation && (
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-6" data-testid={`explanation-${explanationLevel}-${selectedTrace.trace_id}`}>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                      How this answer was generated
                    </h3>
                    <div className="prose dark:prose-invert max-w-none">
                      <p className="text-gray-700 dark:text-gray-300" data-testid={`explanation-summary-${selectedTrace.trace_id}`}>{explanation.summary}</p>

                      {explanation.capabilities_list && (
                        <div className="mt-4">
                          <p className="font-medium text-gray-900 dark:text-gray-100">
                            Capabilities used: {explanation.capabilities_used}
                          </p>
                          <ul className="list-disc list-inside mt-2 space-y-1">
                            {explanation.capabilities_list.map((cap, idx) => (
                              <li key={idx} className="text-gray-700 dark:text-gray-300">
                                {cap}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    {/* Expert/Audit Details */}
                    {explanationLevel !== 'user' && 'technical_details' in explanation && (
                      <div className="mt-6 space-y-4 border-t-2 border-gray-200 dark:border-gray-700 pt-4">
                        <h4 className="font-semibold text-gray-900 dark:text-gray-100">
                          Technical Details
                        </h4>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-gray-500 dark:text-gray-400">Retrieval Mode:</span>{' '}
                            <span className="text-gray-900 dark:text-gray-100 font-medium">
                              {explanation.technical_details.retrieval_mode}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-500 dark:text-gray-400">Chunks Retrieved:</span>{' '}
                            <span className="text-gray-900 dark:text-gray-100 font-medium">
                              {explanation.technical_details.chunks_retrieved}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-500 dark:text-gray-400">Chunks Used:</span>{' '}
                            <span className="text-gray-900 dark:text-gray-100 font-medium">
                              {explanation.technical_details.chunks_used}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-500 dark:text-gray-400">Duration:</span>{' '}
                            <span className="text-gray-900 dark:text-gray-100 font-medium">
                              {explanation.technical_details.performance_metrics.duration}ms
                            </span>
                          </div>
                        </div>

                        {/* Skills Considered */}
                        {explanation.technical_details.skills_considered.length > 0 && (
                          <div className="mt-4">
                            <p className="font-medium text-gray-900 dark:text-gray-100 mb-2">
                              Skills Considered:
                            </p>
                            <div className="space-y-2">
                              {explanation.technical_details.skills_considered.map((skill, idx) => (
                                <div
                                  key={idx}
                                  className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700/50 rounded"
                                >
                                  <div className="flex items-center gap-2">
                                    {skill.selected ? (
                                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                                    ) : (
                                      <div className="w-4 h-4 border-2 border-gray-300 dark:border-gray-600 rounded-full" />
                                    )}
                                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                      {skill.name}
                                    </span>
                                    {skill.trigger && (
                                      <span className="text-xs text-gray-500 dark:text-gray-400">
                                        (trigger: {skill.trigger})
                                      </span>
                                    )}
                                  </div>
                                  <span className="text-sm text-gray-600 dark:text-gray-400">
                                    {(skill.confidence * 100).toFixed(0)}%
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Audit Full Trace */}
                    {explanationLevel === 'audit' && 'full_trace' in explanation && (
                      <div className="mt-6 border-t-2 border-gray-200 dark:border-gray-700 pt-4">
                        <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
                          Complete Trace (for compliance)
                        </h4>
                        <pre className="bg-gray-100 dark:bg-gray-900 p-4 rounded-lg overflow-x-auto text-xs text-gray-800 dark:text-gray-200">
                          {JSON.stringify(explanation.full_trace, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}

                {/* Decision Flow */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-6" data-testid="decision-flow-section">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                    Decision Flow
                  </h3>
                  <div className="space-y-3" data-testid={`decision-flow-${selectedTrace.trace_id}`}>
                    {selectedTrace.decision_flow.map((stage, idx) => (
                      <div key={idx} className="flex items-start gap-3" data-testid={`decision-step-${idx}`}>
                        <div className="flex-shrink-0 mt-1">
                          {stage.status === 'completed' ? (
                            <CheckCircle2 className="w-5 h-5 text-green-500" />
                          ) : stage.status === 'error' ? (
                            <AlertCircle className="w-5 h-5 text-red-500" />
                          ) : (
                            <div className="w-5 h-5 border-2 border-gray-300 dark:border-gray-600 rounded-full animate-pulse" />
                          )}
                        </div>
                        <div className="flex-1">
                          <p className="font-medium text-gray-900 dark:text-gray-100" data-testid={`decision-step-name-${idx}`}>
                            {idx + 1}. {stage.stage.charAt(0).toUpperCase() + stage.stage.slice(1)}
                          </p>
                          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1" data-testid={`decision-step-details-${idx}`}>
                            {stage.details}
                          </p>
                          {stage.timestamp && (
                            <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                              {new Date(stage.timestamp).toLocaleTimeString()}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Source Attribution */}
                {sources.length > 0 && (
                  <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-6" data-testid="source-attribution-section">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                      Source Attribution
                    </h3>
                    <div className="space-y-3" data-testid={`sources-${selectedTrace.trace_id}`}>
                      {sources.map((source, idx) => (
                        <div
                          key={idx}
                          className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                          data-testid={`source-${idx}`}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <p className="font-medium text-gray-900 dark:text-gray-100" data-testid={`source-name-${idx}`}>
                                {source.name}
                                {source.page && (
                                  <span className="text-sm text-gray-500 dark:text-gray-400 ml-2">
                                    Page {source.page}
                                  </span>
                                )}
                              </p>
                              {source.snippet && (
                                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1" data-testid={`source-snippet-${idx}`}>
                                  "{source.snippet}"
                                </p>
                              )}
                            </div>
                            <div className="flex-shrink-0 ml-4 text-right">
                              <p className="text-sm font-semibold text-purple-600 dark:text-purple-400" data-testid={`source-relevance-${idx}`}>
                                {(source.relevance * 100).toFixed(0)}%
                              </p>
                              {source.confidence && (
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                  {source.confidence}
                                </p>
                              )}
                            </div>
                          </div>
                          {/* Relevance bar */}
                          <div className="mt-2 w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                            <div
                              className="bg-purple-600 dark:bg-purple-500 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${source.relevance * 100}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Confidence & Hallucination Metrics */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-6" data-testid="confidence-metrics-section">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                    Confidence Metrics
                  </h3>
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                        Overall Confidence
                      </p>
                      <p className={`text-4xl font-bold ${getConfidenceColor(selectedTrace.confidence_overall)}`} data-testid={`confidence-score-${selectedTrace.trace_id}`}>
                        {(selectedTrace.confidence_overall * 100).toFixed(0)}%
                      </p>
                      <div className="mt-2 w-full bg-gray-200 dark:bg-gray-600 rounded-full h-3">
                        <div
                          className="bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 h-3 rounded-full transition-all duration-300"
                          style={{ width: `${selectedTrace.confidence_overall * 100}%` }}
                        />
                      </div>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                        Hallucination Risk
                      </p>
                      <p className={`text-4xl font-bold ${getHallucinationColor(selectedTrace.hallucination_risk)}`} data-testid={`hallucination-risk-${selectedTrace.trace_id}`}>
                        {(selectedTrace.hallucination_risk * 100).toFixed(0)}%
                      </p>
                      <div className="mt-2 w-full bg-gray-200 dark:bg-gray-600 rounded-full h-3">
                        <div
                          className="bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 h-3 rounded-full transition-all duration-300"
                          style={{ width: `${selectedTrace.hallucination_risk * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Info Section */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-800 rounded-xl p-6">
          <div className="flex gap-3">
            <div className="flex-shrink-0">
              <svg
                className="w-6 h-6 text-blue-600 dark:text-blue-400"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div>
              <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                About Explainability (EU AI Act Art. 13)
              </h4>
              <p className="text-sm text-blue-800 dark:text-blue-200 mb-3">
                This dashboard provides transparency into AI decision-making processes as required
                by EU AI Act Article 13. It shows how the system arrived at its responses, which
                sources were used, and the confidence levels.
              </p>
              <ul className="space-y-1 text-sm text-blue-800 dark:text-blue-200">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                  <span>User View: Simplified explanations for end users</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                  <span>Expert View: Technical details for developers and data scientists</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                  <span>Audit View: Complete trace data for compliance audits</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ExplainabilityPage;

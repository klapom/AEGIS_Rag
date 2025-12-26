/**
 * ResearchResponseDisplay Component
 * Sprint 63 Feature 63.8: Full Research UI with Progress Tracking
 *
 * Displays the research synthesis result with collapsible research plan,
 * quality metrics, and source list.
 *
 * Features:
 * - Synthesis display in main area
 * - Collapsible research plan section
 * - Quality metrics display (iterations, sources used)
 * - Source list with scores
 * - Loading state
 */

import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  FileText,
  Target,
  CheckCircle,
  ExternalLink,
  Loader2,
} from 'lucide-react';
import type { ResearchResponseDisplayProps, ResearchSource } from '../../types/research';

/**
 * Quality metric badge component
 */
interface MetricBadgeProps {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
}

function MetricBadge({ label, value, icon }: MetricBadgeProps) {
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 rounded-lg">
      {icon && <span className="text-gray-500">{icon}</span>}
      <span className="text-xs text-gray-500">{label}:</span>
      <span className="text-sm font-medium text-gray-700">{value}</span>
    </div>
  );
}

/**
 * Collapsible section component
 */
interface CollapsibleSectionProps {
  title: string;
  icon: React.ReactNode;
  defaultExpanded?: boolean;
  children: React.ReactNode;
  testId?: string;
}

function CollapsibleSection({
  title,
  icon,
  defaultExpanded = false,
  children,
  testId,
}: CollapsibleSectionProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div
      className="border border-gray-200 rounded-lg overflow-hidden"
      data-testid={testId}
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-3 px-4 py-3 bg-gray-50 hover:bg-gray-100
                   transition-colors text-left"
        aria-expanded={isExpanded}
      >
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-gray-500" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-500" />
        )}
        <span className="text-gray-600">{icon}</span>
        <span className="font-medium text-gray-700">{title}</span>
      </button>

      {isExpanded && (
        <div className="px-4 py-3 bg-white border-t border-gray-100">
          {children}
        </div>
      )}
    </div>
  );
}

/**
 * Single source item display
 */
interface SourceItemProps {
  source: ResearchSource;
  index: number;
}

function SourceItem({ source, index }: SourceItemProps) {
  const hasEntitiesOrRelationships =
    (source.entities?.length || 0) > 0 || (source.relationships?.length || 0) > 0;

  return (
    <div
      className="p-3 bg-white border border-gray-200 rounded-lg hover:shadow-sm transition-shadow"
      data-testid={`source-item-${index}`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span className="flex items-center justify-center w-5 h-5 text-xs font-medium
                          bg-blue-100 text-blue-700 rounded-full">
            {index + 1}
          </span>
          <span className="text-xs font-medium text-gray-500 uppercase">
            {source.source_type}
          </span>
        </div>
        <span className="text-xs text-gray-400">
          Score: {(source.score * 100).toFixed(1)}%
        </span>
      </div>

      <p className="text-sm text-gray-700 line-clamp-3 mb-2">
        {source.text}
      </p>

      {/* Entities and relationships */}
      {hasEntitiesOrRelationships && (
        <div className="flex flex-wrap gap-1">
          {source.entities?.slice(0, 5).map((entity, idx) => (
            <span
              key={`entity-${idx}`}
              className="px-2 py-0.5 text-xs bg-green-50 text-green-700 rounded"
            >
              {entity}
            </span>
          ))}
          {(source.entities?.length || 0) > 5 && (
            <span className="px-2 py-0.5 text-xs text-gray-400">
              +{(source.entities?.length || 0) - 5} more
            </span>
          )}
        </div>
      )}

      {/* Metadata link if available */}
      {source.metadata?.url && (
        <a
          href={source.metadata.url as string}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 mt-2 text-xs text-blue-600 hover:underline"
        >
          <ExternalLink className="w-3 h-3" />
          View source
        </a>
      )}
    </div>
  );
}

/**
 * ResearchResponseDisplay Component
 */
export function ResearchResponseDisplay({
  synthesis,
  sources,
  researchPlan,
  qualityMetrics,
  isLoading,
}: ResearchResponseDisplayProps) {
  // Loading state
  if (isLoading && !synthesis) {
    return (
      <div
        className="flex flex-col items-center justify-center py-12 text-gray-500"
        data-testid="research-response-loading"
      >
        <Loader2 className="w-8 h-8 animate-spin mb-4" />
        <p className="text-sm">Recherche wird durchgefuehrt...</p>
      </div>
    );
  }

  // No content state
  if (!synthesis && sources.length === 0) {
    return null;
  }

  return (
    <div
      className="space-y-4"
      data-testid="research-response-display"
    >
      {/* Quality Metrics Bar */}
      <div className="flex flex-wrap items-center gap-3 pb-4 border-b border-gray-200">
        <MetricBadge
          label="Iterationen"
          value={qualityMetrics.iterations}
          icon={<Target className="w-4 h-4" />}
        />
        <MetricBadge
          label="Quellen"
          value={qualityMetrics.totalSources}
          icon={<FileText className="w-4 h-4" />}
        />
        {qualityMetrics.overall_score !== undefined && (
          <MetricBadge
            label="Qualitaet"
            value={`${(qualityMetrics.overall_score * 100).toFixed(0)}%`}
            icon={<CheckCircle className="w-4 h-4" />}
          />
        )}
        {qualityMetrics.webSources > 0 && (
          <MetricBadge
            label="Web-Quellen"
            value={qualityMetrics.webSources}
            icon={<ExternalLink className="w-4 h-4" />}
          />
        )}
      </div>

      {/* Synthesis / Main Answer */}
      {synthesis && (
        <div className="prose prose-sm max-w-none" data-testid="research-synthesis">
          <p className="text-gray-800 whitespace-pre-wrap leading-relaxed">
            {synthesis}
          </p>
        </div>
      )}

      {/* Research Plan (Collapsible) */}
      {researchPlan.length > 0 && (
        <CollapsibleSection
          title={`Recherche-Plan (${researchPlan.length} Schritte)`}
          icon={<Target className="w-4 h-4" />}
          defaultExpanded={false}
          testId="research-plan-section"
        >
          <ol className="list-decimal list-inside space-y-2">
            {researchPlan.map((step, idx) => (
              <li
                key={idx}
                className="text-sm text-gray-700 pl-2"
              >
                {step}
              </li>
            ))}
          </ol>
        </CollapsibleSection>
      )}

      {/* Sources (Collapsible) */}
      {sources.length > 0 && (
        <CollapsibleSection
          title={`Quellen (${sources.length})`}
          icon={<FileText className="w-4 h-4" />}
          defaultExpanded={true}
          testId="research-sources-section"
        >
          <div className="space-y-3">
            {sources.slice(0, 10).map((source, idx) => (
              <SourceItem key={idx} source={source} index={idx} />
            ))}

            {sources.length > 10 && (
              <p className="text-xs text-gray-400 text-center pt-2">
                +{sources.length - 10} weitere Quellen
              </p>
            )}
          </div>
        </CollapsibleSection>
      )}

      {/* Additional Metrics (if available) */}
      {(qualityMetrics.coverage !== undefined ||
        qualityMetrics.diversity !== undefined ||
        qualityMetrics.completeness !== undefined) && (
        <div className="grid grid-cols-3 gap-3 pt-4 border-t border-gray-200">
          {qualityMetrics.coverage !== undefined && (
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {(qualityMetrics.coverage * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-gray-500">Abdeckung</div>
            </div>
          )}
          {qualityMetrics.diversity !== undefined && (
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {(qualityMetrics.diversity * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-gray-500">Diversitaet</div>
            </div>
          )}
          {qualityMetrics.completeness !== undefined && (
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {(qualityMetrics.completeness * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-gray-500">Vollstaendigkeit</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

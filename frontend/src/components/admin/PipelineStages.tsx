/**
 * PipelineStages Component
 * Sprint 35 Feature 35.2: Admin Indexing Side-by-Side Layout
 *
 * Visual indicator of the document processing pipeline stages:
 * Parsing → VLM → Chunking → Embedding → Graph → Validation
 *
 * Features:
 * - Highlights current stage
 * - Shows completed stages in green
 * - Shows pending stages in gray
 * - Arrow separators between stages
 */

import React from 'react';

const STAGES = ['Parsing', 'VLM', 'Chunking', 'Embedding', 'Graph', 'Validation'] as const;

interface PipelineStagesProps {
  current?: string;
}

export function PipelineStages({ current }: PipelineStagesProps) {
  // Find the index of the current stage (case-insensitive)
  const currentIndex = STAGES.findIndex(
    (stage) => stage.toLowerCase() === current?.toLowerCase()
  );

  return (
    <div className="flex items-center gap-1 mt-1 flex-wrap" data-testid="pipeline-stages">
      {STAGES.map((stage, i) => {
        // Determine the style based on stage status
        const isCompleted = currentIndex > i;
        const isCurrent = i === currentIndex;

        let stageClass = 'bg-gray-100 text-gray-500'; // default: pending
        if (isCompleted) {
          stageClass = 'bg-green-100 text-green-800';
        } else if (isCurrent) {
          stageClass = 'bg-blue-100 text-blue-800 font-medium';
        }

        return (
          <React.Fragment key={stage}>
            <div className={`px-2 py-1 rounded text-xs ${stageClass}`}>
              {stage}
            </div>
            {i < STAGES.length - 1 && (
              <div className="text-gray-300 text-xs">→</div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

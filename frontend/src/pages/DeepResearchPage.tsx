/**
 * DeepResearchPage Component
 * Sprint 116.10: Deep Research Multi-Step (13 SP)
 *
 * Dedicated page for deep research with multi-step workflow.
 * Provides comprehensive research capabilities with intermediate results.
 */

import { DeepResearchUI } from '../components/research';
import type { DeepResearchResponse } from '../types/research';

/**
 * DeepResearchPage Component
 */
export function DeepResearchPage() {
  /**
   * Handle research completion
   */
  const handleComplete = (result: DeepResearchResponse) => {
    console.log('Research completed:', result);
    // Could trigger notifications, save to history, etc.
  };

  /**
   * Handle research error
   */
  const handleError = (error: string) => {
    console.error('Research error:', error);
    // Could show global error notification
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <DeepResearchUI
        defaultNamespace="default"
        onComplete={handleComplete}
        onError={handleError}
      />
    </div>
  );
}

export default DeepResearchPage;

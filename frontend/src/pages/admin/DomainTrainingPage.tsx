/**
 * DomainTrainingPage Component
 * Sprint 45 Feature 45.4: Domain Training Admin UI
 * Sprint 64 Feature 64.2: Frontend validation improvements
 * Sprint 65 Feature 65.2: Lazy loading for performance optimization
 *
 * Admin page for managing domain training with DSPy integration
 */

import { useState, lazy, Suspense } from 'react';
import { useDomains } from '../../hooks/useDomainTraining';
import { DomainList } from '../../components/admin/DomainList';
import { AdminNavigationBar } from '../../components/admin/AdminNavigationBar';

// Sprint 65 Feature 65.2.1: Lazy load NewDomainWizard to reduce initial bundle size
// This component is only loaded when user clicks "New Domain" button
const NewDomainWizard = lazy(() =>
  import('../../components/admin/NewDomainWizard').then((module) => ({
    default: module.NewDomainWizard,
  }))
);

export function DomainTrainingPage() {
  const { data: domains, isLoading, refetch } = useDomains();
  const [showNewDomain, setShowNewDomain] = useState(false);

  const handleCloseWizard = () => {
    setShowNewDomain(false);
    // Refetch domains to show the newly created domain
    refetch();
  };

  return (
    <div className="p-6 max-w-6xl mx-auto" data-testid="domain-training-page">
      {/* Admin Navigation */}
      <div className="mb-4">
        <AdminNavigationBar />
      </div>

      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Domain Training</h1>
          <p className="text-gray-600 mt-1">
            Train domain-specific models with DSPy for improved query understanding
          </p>
        </div>
        <button
          onClick={() => setShowNewDomain(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold"
          data-testid="new-domain-button"
        >
          + New Domain
        </button>
      </div>

      {/* Domain List */}
      <DomainList domains={domains} isLoading={isLoading} onRefresh={refetch} />

      {/* New Domain Wizard Dialog */}
      {/* Sprint 65 Feature 65.2.1: Lazy loaded with Suspense for faster page load */}
      {showNewDomain && (
        <Suspense
          fallback={
            <div
              className="fixed inset-0 bg-black/50 flex items-center justify-center"
              data-testid="wizard-loading"
            >
              <div className="bg-white rounded-lg p-6 shadow-xl">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
                <p className="text-sm text-gray-600 mt-4">Loading wizard...</p>
              </div>
            </div>
          }
        >
          <NewDomainWizard onClose={handleCloseWizard} />
        </Suspense>
      )}
    </div>
  );
}

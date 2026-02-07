/**
 * DomainTrainingPage Component
 * Sprint 45 Feature 45.4: Domain Training Admin UI
 * Sprint 64 Feature 64.2: Frontend validation improvements
 * Sprint 65 Feature 65.2: Lazy loading for performance optimization
 *
 * Admin page for managing domain training with DSPy integration
 */

import { useState, lazy, Suspense } from 'react';
import { Info } from 'lucide-react';
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

      {/* Under Development Banner (Feature 64.2) */}
      <div
        className="p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-start gap-3 mb-6"
        data-testid="development-banner"
        role="status"
      >
        <Info className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
        <div>
          <h4 className="text-sm font-semibold text-blue-800">Feature Status</h4>
          <p className="text-sm text-blue-700 mt-1">
            DSPy domain training is currently in active development.
            Core functionality is operational but metrics may be simulated during optimization.
            Full production-ready implementation expected in next release.
          </p>
        </div>
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

/**
 * DomainTrainingPage Component
 * Sprint 45 Feature 45.4: Domain Training Admin UI
 *
 * Admin page for managing domain training with DSPy integration
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useDomains } from '../../hooks/useDomainTraining';
import { DomainList } from '../../components/admin/DomainList';
import { NewDomainWizard } from '../../components/admin/NewDomainWizard';

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
      {/* Back Link */}
      <Link
        to="/admin"
        className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 mb-4"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Back to Admin
      </Link>

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
      {showNewDomain && <NewDomainWizard onClose={handleCloseWizard} />}
    </div>
  );
}

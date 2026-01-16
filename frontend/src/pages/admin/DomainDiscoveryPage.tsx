/**
 * DomainDiscoveryPage
 * Sprint 106: Route wrapper for DomainAutoDiscovery component
 *
 * Provides the /admin/domain-discovery route for E2E tests
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DomainAutoDiscovery, type DomainSuggestion } from '../../components/admin/DomainAutoDiscovery';

export function DomainDiscoveryPage() {
  const navigate = useNavigate();
  const [lastSuggestion, setLastSuggestion] = useState<DomainSuggestion | null>(null);

  const handleDomainSuggested = (suggestion: DomainSuggestion) => {
    setLastSuggestion(suggestion);
    console.log('[DomainDiscoveryPage] Suggestion received:', suggestion);
  };

  const handleAccept = (title: string, description: string) => {
    console.log('[DomainDiscoveryPage] Accepted:', { title, description });
    // Navigate to domain training with pre-filled values
    navigate('/admin/domain-training', {
      state: {
        prefillTitle: title,
        prefillDescription: description
      }
    });
  };

  const handleCancel = () => {
    console.log('[DomainDiscoveryPage] Cancelled');
    navigate('/admin/domain-training');
  };

  return (
    <div className="p-6" data-testid="domain-discovery-page">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Domain Auto-Discovery
        </h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Upload sample documents to automatically generate domain configuration
        </p>
      </div>

      <DomainAutoDiscovery
        onDomainSuggested={handleDomainSuggested}
        onAccept={handleAccept}
        onCancel={handleCancel}
      />

      {lastSuggestion && (
        <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <p className="text-sm text-blue-800 dark:text-blue-200">
            Last suggestion: {lastSuggestion.title} (Confidence: {Math.round(lastSuggestion.confidence * 100)}%)
          </p>
        </div>
      )}
    </div>
  );
}

export default DomainDiscoveryPage;

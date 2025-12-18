/**
 * DomainSection Component
 * Sprint 46 Feature 46.8: Admin Area Consolidation
 *
 * Compact domain list section for the admin dashboard.
 * Shows domains with their status and provides a button to create new domains.
 */

import { useState, useCallback } from 'react';
import { Book, Plus, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { AdminSection } from './AdminSection';
import { useDomains, type Domain } from '../../hooks/useDomainTraining';

/**
 * Domain status badge component
 */
function DomainStatusBadge({ status }: { status: Domain['status'] }) {
  const statusConfig: Record<Domain['status'], { color: string; label: string }> = {
    ready: { color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200', label: 'ready' },
    training: { color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200', label: 'training...' },
    pending: { color: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300', label: 'pending' },
    failed: { color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200', label: 'failed' },
  };

  const config = statusConfig[status] || statusConfig.pending;

  return (
    <span
      className={`px-2 py-0.5 text-xs font-medium rounded-full ${config.color}`}
      data-testid={`domain-status-badge-${status}`}
    >
      {config.label}
    </span>
  );
}

/**
 * Compact domain list item
 */
interface DomainItemProps {
  domain: Domain;
  onClick: () => void;
}

function DomainItem({ domain, onClick }: DomainItemProps) {
  return (
    <div
      className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors group"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      data-testid={`domain-item-${domain.name}`}
    >
      <div className="flex items-center gap-3 min-w-0">
        <span className="text-gray-400 dark:text-gray-500">--</span>
        <span className="font-medium text-gray-900 dark:text-gray-100 truncate">
          {domain.name}
        </span>
        <DomainStatusBadge status={domain.status} />
      </div>
      <ExternalLink
        className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity"
        aria-hidden="true"
      />
    </div>
  );
}

/**
 * Empty state when no domains exist
 */
function EmptyDomainsState() {
  return (
    <div
      className="text-center py-6 text-gray-500 dark:text-gray-400"
      data-testid="domains-empty-state"
    >
      <Book className="w-8 h-8 mx-auto mb-2 opacity-50" />
      <p className="text-sm">No domains configured yet.</p>
      <p className="text-xs mt-1">Create a new domain to get started.</p>
    </div>
  );
}

/**
 * New Domain Button component
 */
interface NewDomainButtonProps {
  onClick: () => void;
}

function NewDomainButton({ onClick }: NewDomainButtonProps) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
      data-testid="new-domain-button"
    >
      <Plus className="w-4 h-4" />
      <span>New Domain</span>
    </button>
  );
}

/**
 * DomainSection Props
 */
export interface DomainSectionProps {
  /** Whether the section is expanded by default (default: true) */
  defaultExpanded?: boolean;
}

/**
 * DomainSection - Compact domain list for admin dashboard
 */
export function DomainSection({ defaultExpanded = true }: DomainSectionProps) {
  const navigate = useNavigate();
  const { data: domains, isLoading, error } = useDomains();
  const [, setShowNewDomainDialog] = useState(false);

  const handleNewDomain = useCallback(() => {
    // Navigate to the domain training page which has the wizard
    navigate('/admin/domain-training');
    setShowNewDomainDialog(true);
  }, [navigate]);

  const handleDomainClick = useCallback(
    (domain: Domain) => {
      // Navigate to domain training page with the domain selected
      navigate('/admin/domain-training', { state: { selectedDomain: domain.name } });
    },
    [navigate]
  );

  // Get error message string
  const errorMessage = error ? error.message : null;

  return (
    <AdminSection
      title="Domains"
      icon={<Book className="w-5 h-5" />}
      action={<NewDomainButton onClick={handleNewDomain} />}
      defaultExpanded={defaultExpanded}
      testId="admin-domain-section"
      isLoading={isLoading}
      error={errorMessage}
    >
      {domains && domains.length > 0 ? (
        <div className="space-y-1" data-testid="domain-list">
          {domains.map((domain) => (
            <DomainItem
              key={domain.id || domain.name}
              domain={domain}
              onClick={() => handleDomainClick(domain)}
            />
          ))}
        </div>
      ) : (
        <EmptyDomainsState />
      )}
    </AdminSection>
  );
}

export default DomainSection;

/**
 * DomainList Component
 * Sprint 45 Feature 45.4: Domain Training Admin UI
 *
 * Displays a table of domains with status and actions
 */

import type { Domain } from '../../hooks/useDomainTraining';

interface DomainListProps {
  domains: Domain[] | null;
  isLoading: boolean;
}

export function DomainList({ domains, isLoading }: DomainListProps) {
  if (isLoading) {
    return (
      <div className="bg-white rounded-md border p-6 text-center" data-testid="domain-list-loading">
        <div className="inline-block w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
        <p className="mt-3 text-sm text-gray-600">Loading domains...</p>
      </div>
    );
  }

  if (!domains || domains.length === 0) {
    return (
      <div className="bg-white rounded-md border p-6 text-center" data-testid="domain-list-empty">
        <p className="text-sm text-gray-600">No domains found. Create a new domain to get started.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-md border" data-testid="domain-list">
      <table className="w-full">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Name</th>
            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Description</th>
            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Model</th>
            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Status</th>
            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Actions</th>
          </tr>
        </thead>
        <tbody>
          {domains.map((domain) => (
            <DomainRow key={domain.id || domain.name} domain={domain} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface DomainRowProps {
  domain: Domain;
}

function DomainRow({ domain }: DomainRowProps) {
  const statusColors: Record<Domain['status'], string> = {
    ready: 'bg-green-100 text-green-800',
    training: 'bg-yellow-100 text-yellow-800',
    pending: 'bg-gray-100 text-gray-800',
    failed: 'bg-red-100 text-red-800',
  };

  const statusColor = statusColors[domain.status] || 'bg-gray-100 text-gray-800';

  return (
    <tr className="border-t hover:bg-gray-50" data-testid={`domain-row-${domain.name}`}>
      <td className="px-3 py-2 text-sm font-medium text-gray-900">{domain.name}</td>
      <td className="px-3 py-2 text-xs text-gray-600 truncate max-w-xs" title={domain.description}>
        {domain.description}
      </td>
      <td className="px-3 py-2 text-xs text-gray-700">{domain.llm_model || '-'}</td>
      <td className="px-3 py-2">
        <span
          className={`px-1.5 py-0.5 rounded text-xs font-medium ${statusColor}`}
          data-testid={`domain-status-${domain.name}`}
        >
          {domain.status}
        </span>
      </td>
      <td className="px-3 py-2">
        <button
          className="text-blue-600 hover:underline text-xs font-medium"
          data-testid={`domain-view-${domain.name}`}
        >
          View
        </button>
      </td>
    </tr>
  );
}

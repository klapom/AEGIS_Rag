/**
 * ConsentRegistry Component
 * Sprint 98 Feature 98.3: GDPR Consent Manager UI
 *
 * Displays a list of all GDPR consents with filtering, search, and status indicators.
 * Shows active, expiring, expired, and withdrawn consents.
 */

import { useState } from 'react';
import { CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react';
import type {
  GDPRConsent,
  ConsentStatus,
  DataCategory,
  LegalBasis,
} from '../../types/gdpr';
import {
  getConsentStatusColor,
  getLegalBasisText,
  isConsentExpiringSoon,
} from '../../types/gdpr';

interface ConsentRegistryProps {
  consents: GDPRConsent[];
  onRevokeConsent: (consentId: string) => void;
  onEditConsent: (consent: GDPRConsent) => void;
  onViewDetails: (consent: GDPRConsent) => void;
  onRenewConsent: (consent: GDPRConsent) => void;
}

export function ConsentRegistry({
  consents,
  onRevokeConsent,
  onEditConsent,
  onViewDetails,
  onRenewConsent,
}: ConsentRegistryProps) {
  const [filterStatus, setFilterStatus] = useState<ConsentStatus | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Filter and search logic
  const filteredConsents = consents.filter((consent) => {
    const matchesStatus = filterStatus === 'all' || consent.status === filterStatus;
    const matchesSearch =
      searchQuery === '' ||
      consent.userId.toLowerCase().includes(searchQuery.toLowerCase()) ||
      consent.purpose.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  // Group consents by status
  const activeConsents = filteredConsents.filter((c) => c.status === 'active');
  const expiringConsents = activeConsents.filter(isConsentExpiringSoon);

  return (
    <div className="space-y-4">
      {/* Header with Summary */}
      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100">
              Consent Registry
            </h3>
            <p className="text-sm text-blue-700 dark:text-blue-300">
              {activeConsents.length} active consents
              {expiringConsents.length > 0 && (
                <span className="ml-2 text-yellow-700 dark:text-yellow-400">
                  • {expiringConsents.length} expiring soon
                </span>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <label htmlFor="consent-search" className="sr-only">
            Search consents
          </label>
          <input
            id="consent-search"
            type="text"
            placeholder="Search by user ID or purpose..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label htmlFor="status-filter" className="sr-only">
            Filter by status
          </label>
          <select
            id="status-filter"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as ConsentStatus | 'all')}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="expired">Expired</option>
            <option value="withdrawn">Withdrawn</option>
            <option value="pending">Pending</option>
          </select>
        </div>
      </div>

      {/* Consent List */}
      <div className="space-y-3">
        {filteredConsents.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No consents found matching your filters.
          </div>
        ) : (
          filteredConsents.map((consent) => (
            <ConsentCard
              key={consent.id}
              consent={consent}
              onRevoke={onRevokeConsent}
              onEdit={onEditConsent}
              onView={onViewDetails}
              onRenew={onRenewConsent}
            />
          ))
        )}
      </div>
    </div>
  );
}

/**
 * Single Consent Card Component
 */
interface ConsentCardProps {
  consent: GDPRConsent;
  onRevoke: (consentId: string) => void;
  onEdit: (consent: GDPRConsent) => void;
  onView: (consent: GDPRConsent) => void;
  onRenew: (consent: GDPRConsent) => void;
}

function ConsentCard({ consent, onRevoke, onEdit, onView, onRenew }: ConsentCardProps) {
  const statusColor = getConsentStatusColor(consent.status);
  const isExpiring = isConsentExpiringSoon(consent);

  // Calculate days until expiry
  const daysUntilExpiry = consent.expiresAt
    ? Math.ceil(
        (new Date(consent.expiresAt).getTime() - new Date().getTime()) /
          (1000 * 60 * 60 * 24)
      )
    : null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      {/* Header: Status Icon + User ID + Purpose */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <StatusIcon status={consent.status} />
          <div>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100">
              {consent.userId} - {consent.purpose}
            </h4>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Legal Basis: {getLegalBasisText(consent.legalBasis)}
            </p>
          </div>
        </div>
        <StatusBadge status={consent.status} isExpiring={isExpiring} />
      </div>

      {/* Data Categories */}
      <div className="flex flex-wrap gap-2">
        <span className="text-sm text-gray-700 dark:text-gray-300">Data Categories:</span>
        {consent.dataCategories.map((category) => (
          <span
            key={category}
            className="px-2 py-1 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded"
          >
            {category}
          </span>
        ))}
      </div>

      {/* Dates */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-600 dark:text-gray-400">Granted: </span>
          <span className="text-gray-900 dark:text-gray-100">
            {new Date(consent.grantedAt).toLocaleDateString()}
          </span>
        </div>
        <div>
          <span className="text-gray-600 dark:text-gray-400">Expires: </span>
          <span className="text-gray-900 dark:text-gray-100">
            {consent.expiresAt
              ? new Date(consent.expiresAt).toLocaleDateString()
              : 'Never'}
            {isExpiring && daysUntilExpiry && (
              <span className="ml-2 text-yellow-600 dark:text-yellow-400 font-medium">
                ({daysUntilExpiry} days left!)
              </span>
            )}
          </span>
        </div>
      </div>

      {/* Skill Restrictions */}
      {consent.skillRestrictions.length > 0 && (
        <div className="text-sm">
          <span className="text-gray-600 dark:text-gray-400">Skill Restrictions: </span>
          <span className="text-gray-900 dark:text-gray-100">
            {consent.skillRestrictions.join(', ')}
          </span>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
        {consent.status === 'active' && isExpiring && (
          <button
            onClick={() => onRenew(consent)}
            className="px-3 py-1.5 text-sm font-medium bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg transition-colors"
          >
            Renew
          </button>
        )}
        {consent.status === 'active' && (
          <button
            onClick={() => onRevoke(consent.id)}
            className="px-3 py-1.5 text-sm font-medium bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
          >
            Revoke
          </button>
        )}
        <button
          onClick={() => onEdit(consent)}
          className="px-3 py-1.5 text-sm font-medium bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
        >
          Edit
        </button>
        <button
          onClick={() => onView(consent)}
          className="px-3 py-1.5 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          View Details
        </button>
      </div>
    </div>
  );
}

/**
 * Status Icon Component
 */
function StatusIcon({ status }: { status: ConsentStatus }) {
  switch (status) {
    case 'active':
      return <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />;
    case 'expired':
      return <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />;
    case 'withdrawn':
      return <XCircle className="w-5 h-5 text-gray-600 dark:text-gray-400" />;
    case 'pending':
      return <Clock className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />;
  }
}

/**
 * Status Badge Component
 */
function StatusBadge({ status, isExpiring }: { status: ConsentStatus; isExpiring: boolean }) {
  const statusColor = getConsentStatusColor(status);

  if (status === 'active' && isExpiring) {
    return (
      <span className="flex items-center gap-1 px-3 py-1 text-xs font-semibold bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 rounded-full">
        <AlertTriangle className="w-3 h-3" />
        Expiring Soon
      </span>
    );
  }

  const colorClasses = {
    green: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300',
    red: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300',
    yellow: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300',
    gray: 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300',
  };

  return (
    <span
      className={`px-3 py-1 text-xs font-semibold rounded-full ${
        colorClasses[statusColor as keyof typeof colorClasses]
      }`}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

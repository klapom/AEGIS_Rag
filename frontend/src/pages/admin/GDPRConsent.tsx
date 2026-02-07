/**
 * GDPRConsent Page
 * Sprint 98 Feature 98.3: GDPR Consent Manager UI
 *
 * Main page for GDPR consent management.
 * Implements EU GDPR Articles 6, 7, 13-22, 30.
 */

import { useState, useEffect } from 'react';
import { Shield, Plus } from 'lucide-react';
import { AdminNavigationBar } from '../../components/admin/AdminNavigationBar';
import { ConsentRegistry } from '../../components/gdpr/ConsentRegistry';
import { ConsentForm } from '../../components/gdpr/ConsentForm';
import { DataSubjectRights } from '../../components/gdpr/DataSubjectRights';
import { ProcessingActivityLog } from '../../components/gdpr/ProcessingActivityLog';
import { PIIRedactionSettings } from '../../components/gdpr/PIIRedactionSettings';
import type {
  GDPRConsent,
  ConsentFormData,
  DataSubjectRightsRequest,
  DataSubjectRightType,
  ProcessingActivity,
  PIIRedactionSettings as PIISettings,
} from '../../types/gdpr';

type TabType = 'consents' | 'rights' | 'activities' | 'pii';

export function GDPRConsentPage() {
  const [activeTab, setActiveTab] = useState<TabType>('consents');
  const [consents, setConsents] = useState<GDPRConsent[]>([]);
  const [requests, setRequests] = useState<DataSubjectRightsRequest[]>([]);
  const [activities, setActivities] = useState<ProcessingActivity[]>([]);
  const [piiSettings, setPIISettings] = useState<PIISettings>({
    enabled: false,
    autoRedact: false,
    redactionChar: '*',
    detectionThreshold: 0.7,
    enabledCategories: ['identifier', 'contact', 'financial'],
  });

  const [showConsentForm, setShowConsentForm] = useState(false);
  const [editingConsent, setEditingConsent] = useState<GDPRConsent | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch data on mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch consents
      const consentsResponse = await fetch('/api/v1/gdpr/consents', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });
      if (consentsResponse.ok) {
        const consentsData = await consentsResponse.json();
        // Sprint 100 Fix #2: Use standardized "items" field (not "consents")
        const items = consentsData.items || [];

        // Transform snake_case API response to camelCase + Sprint 100 Fix #6 status mapping
        const mappedConsents = items.map((consent: any) => ({
          id: consent.id,
          userId: consent.user_id,
          purpose: consent.purpose,
          legalBasis: consent.legal_basis || 'consent',
          legalBasisText: consent.legal_basis_text || 'Art. 6(1)(a) Consent',
          dataCategories: consent.data_categories || [],
          skillRestrictions: consent.skill_restrictions || [],
          grantedAt: consent.granted_at,
          expiresAt: consent.expires_at || null,
          withdrawnAt: consent.withdrawn_at || null,
          // Sprint 100 Fix #6: Map backend "granted" status to frontend "active"
          status: consent.status === 'granted' ? 'active' : consent.status,
          version: consent.version || '1.0',
          metadata: consent.metadata || {},
        }));

        setConsents(mappedConsents);
      }

      // Fetch requests
      const requestsResponse = await fetch('/api/v1/gdpr/requests', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });
      if (requestsResponse.ok) {
        const requestsData = await requestsResponse.json();
        const requestsItems = requestsData.requests || [];

        // Transform snake_case to camelCase
        const mappedRequests = requestsItems.map((req: any) => ({
          id: req.id,
          userId: req.user_id,
          requestType: req.request_type,
          articleReference: req.article_reference || 'GDPR',
          submittedAt: req.submitted_at,
          status: req.status,
          scope: req.scope || [],
          reviewedBy: req.reviewed_by || null,
          reviewedAt: req.reviewed_at || null,
          completedAt: req.completed_at || null,
          rejectionReason: req.rejection_reason || null,
          metadata: req.metadata || {},
        }));

        setRequests(mappedRequests);
      }

      // Fetch activities
      const activitiesResponse = await fetch('/api/v1/gdpr/processing-activities?limit=50', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });
      if (activitiesResponse.ok) {
        const activitiesData = await activitiesResponse.json();
        const activitiesItems = activitiesData.activities || [];

        // Transform snake_case to camelCase
        const mappedActivities = activitiesItems.map((act: any) => ({
          id: act.id,
          userId: act.user_id || null,
          timestamp: act.timestamp,
          activity: act.activity,
          purpose: act.purpose,
          legalBasis: act.legal_basis,
          dataCategories: act.data_categories || [],
          skillName: act.skill_name || null,
          resourceId: act.resource_id,
          duration: act.duration || null,
          metadata: act.metadata || {},
        }));

        setActivities(mappedActivities);
      }

      // Fetch PII settings
      const piiResponse = await fetch('/api/v1/gdpr/pii-settings', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });
      if (piiResponse.ok) {
        const piiData = await piiResponse.json();
        setPIISettings(piiData);
      }
    } catch (err) {
      console.error('Failed to load GDPR data:', err);
      setError('Failed to load data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Consent handlers
  const handleCreateConsent = async (data: ConsentFormData) => {
    try {
      const response = await fetch('/api/v1/gdpr/consent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(data),
      });

      if (response.ok) {
        await loadData();
        setShowConsentForm(false);
      } else {
        throw new Error('Failed to create consent');
      }
    } catch (err) {
      console.error('Failed to create consent:', err);
      alert('Failed to create consent. Please try again.');
    }
  };

  const handleEditConsent = async (data: ConsentFormData) => {
    if (!editingConsent) return;

    try {
      const response = await fetch(`/api/v1/gdpr/consent/${editingConsent.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(data),
      });

      if (response.ok) {
        await loadData();
        setEditingConsent(undefined);
      } else {
        throw new Error('Failed to update consent');
      }
    } catch (err) {
      console.error('Failed to update consent:', err);
      alert('Failed to update consent. Please try again.');
    }
  };

  const handleRevokeConsent = async (consentId: string) => {
    if (!confirm('Are you sure you want to revoke this consent?')) return;

    try {
      const response = await fetch(`/api/v1/gdpr/consent/${consentId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (response.ok) {
        await loadData();
      } else {
        throw new Error('Failed to revoke consent');
      }
    } catch (err) {
      console.error('Failed to revoke consent:', err);
      alert('Failed to revoke consent. Please try again.');
    }
  };

  // Data subject rights handlers
  const handleCreateRequest = async (userId: string, requestType: DataSubjectRightType) => {
    try {
      const response = await fetch('/api/v1/gdpr/request', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ userId, requestType }),
      });

      if (response.ok) {
        await loadData();
      } else {
        throw new Error('Failed to create request');
      }
    } catch (err) {
      console.error('Failed to create request:', err);
      alert('Failed to create request. Please try again.');
    }
  };

  const handleApproveRequest = async (requestId: string) => {
    if (!confirm('Approve and execute this request?')) return;

    try {
      const response = await fetch(`/api/v1/gdpr/request/${requestId}/approve`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (response.ok) {
        await loadData();
      } else {
        throw new Error('Failed to approve request');
      }
    } catch (err) {
      console.error('Failed to approve request:', err);
      alert('Failed to approve request. Please try again.');
    }
  };

  const handleRejectRequest = async (requestId: string, reason: string) => {
    try {
      const response = await fetch(`/api/v1/gdpr/request/${requestId}/reject`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ reason }),
      });

      if (response.ok) {
        await loadData();
      } else {
        throw new Error('Failed to reject request');
      }
    } catch (err) {
      console.error('Failed to reject request:', err);
      alert('Failed to reject request. Please try again.');
    }
  };

  const handleSavePIISettings = async (settings: PIISettings) => {
    try {
      const response = await fetch('/api/v1/gdpr/pii-settings', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(settings),
      });

      if (response.ok) {
        setPIISettings(settings);
        alert('PII settings saved successfully.');
      } else {
        throw new Error('Failed to save PII settings');
      }
    } catch (err) {
      console.error('Failed to save PII settings:', err);
      alert('Failed to save PII settings. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-gray-600 dark:text-gray-400">Loading GDPR data...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900" data-testid="gdpr-page">
      <div className="max-w-6xl mx-auto py-8 px-6 space-y-6">
        {/* Navigation Bar */}
        <div className="mb-4">
          <AdminNavigationBar />
        </div>

        {/* Header */}
        <header className="space-y-2">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-600 dark:text-blue-400" />
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                GDPR Consent Management
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                EU GDPR Compliance - Articles 6, 7, 13-22, 30
              </p>
            </div>
          </div>
          {activeTab === 'consents' && (
            <button
              onClick={() => setShowConsentForm(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Consent
            </button>
          )}
        </header>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-red-700 dark:text-red-300">{error}</p>
          </div>
        )}

        {/* Tabs */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="flex gap-4">
            {[
              { id: 'consents' as TabType, label: 'Consents', count: consents.length },
              { id: 'rights' as TabType, label: 'Data Subject Rights', count: requests.length },
              { id: 'activities' as TabType, label: 'Processing Activities', count: activities.length },
              { id: 'pii' as TabType, label: 'PII Settings', count: undefined },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                data-testid={`tab-${tab.id}`}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                }`}
              >
                {tab.label}
                {tab.count !== undefined && (
                  <span className="ml-2 px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 rounded-full">
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div>
          {activeTab === 'consents' && (
            <ConsentRegistry
              consents={consents}
              onRevokeConsent={handleRevokeConsent}
              onEditConsent={(consent) => setEditingConsent(consent)}
              onViewDetails={(consent) => alert(`View details: ${consent.id}`)}
              onRenewConsent={(consent) => setEditingConsent(consent)}
            />
          )}
          {activeTab === 'rights' && (
            <DataSubjectRights
              requests={requests}
              onApproveRequest={handleApproveRequest}
              onRejectRequest={handleRejectRequest}
              onViewRequest={(request) => alert(`View request: ${request.id}`)}
              onCreateRequest={handleCreateRequest}
            />
          )}
          {activeTab === 'activities' && (
            <ProcessingActivityLog
              activities={activities}
              onLoadMore={() => {}}
              hasMore={false}
            />
          )}
          {activeTab === 'pii' && (
            <PIIRedactionSettings
              settings={piiSettings}
              onSave={handleSavePIISettings}
            />
          )}
        </div>

        {/* Consent Form Modal */}
        {(showConsentForm || editingConsent) && (
          <ConsentForm
            consent={editingConsent}
            onSubmit={editingConsent ? handleEditConsent : handleCreateConsent}
            onCancel={() => {
              setShowConsentForm(false);
              setEditingConsent(undefined);
            }}
          />
        )}
      </div>
    </div>
  );
}

export default GDPRConsentPage;

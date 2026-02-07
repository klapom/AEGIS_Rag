/**
 * DeploymentProfilePage Component
 * Sprint 125 Feature 125.9c: Deployment Profile Selection
 *
 * Admin page for selecting and managing deployment profiles.
 * Profiles activate relevant domains for the organization type.
 */

import { useState, useEffect } from 'react';
import { Check, Loader2, AlertTriangle } from 'lucide-react';
import { apiClient } from '../../lib/api';
import { AdminNavigationBar } from '../../components/admin/AdminNavigationBar';

interface Domain {
  domain_id: string;
  domain_name: string;
  ddc_code: string;
  description: string;
  status: string;
}

interface DeploymentProfile {
  profile_name: string;
  display_name: string;
  description: string;
  active_domains: string[];
}

const DEPLOYMENT_PROFILES: DeploymentProfile[] = [
  {
    profile_name: 'general',
    display_name: 'General (All Domains)',
    description: 'All domains active for maximum flexibility',
    active_domains: [], // Empty means all domains
  },
  {
    profile_name: 'software_company',
    display_name: 'Software Company',
    description: 'Technology and engineering domains',
    active_domains: ['computer_science', 'electrical_engineering', 'mathematics'],
  },
  {
    profile_name: 'pharma_company',
    display_name: 'Pharmaceutical Company',
    description: 'Medical and life sciences domains',
    active_domains: ['medicine', 'chemistry', 'biology'],
  },
  {
    profile_name: 'law_firm',
    display_name: 'Law Firm',
    description: 'Legal and business domains',
    active_domains: ['law', 'political_science', 'economics'],
  },
  {
    profile_name: 'university',
    display_name: 'University',
    description: 'All academic domains',
    active_domains: [], // All domains for educational institution
  },
  {
    profile_name: 'custom',
    display_name: 'Custom',
    description: 'Select specific domains manually',
    active_domains: [], // Will be customized by user
  },
];

export function DeploymentProfilePage() {
  const [selectedProfile, setSelectedProfile] = useState<string>('general');
  const [customDomains, setCustomDomains] = useState<string[]>([]);
  const [availableDomains, setAvailableDomains] = useState<Domain[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Load current profile and available domains
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);

      try {
        // Load current deployment profile (under retrieval router prefix)
        try {
          const profileData = await apiClient.get<{
            profile_name: string;
            active_domains: string[];
          }>('/api/v1/retrieval/admin/deployment-profile');
          setSelectedProfile(profileData.profile_name || 'general');
          if (profileData.profile_name === 'custom') {
            setCustomDomains(profileData.active_domains || []);
          }
        } catch {
          // No profile set yet — use default
        }

        // Load available domains
        // Sprint 117.8: API returns ApiResponse wrapper { success, data: [...] }
        interface ApiDomainResponse { success: boolean; data: Array<Record<string, string>> }
        const domainsData = await apiClient.get<ApiDomainResponse>('/api/v1/admin/domains/');
        const rawDomains = Array.isArray(domainsData) ? domainsData : (domainsData.data || []);
        const mapped: Domain[] = rawDomains.map((d: Record<string, string>) => ({
          domain_id: d.name || d.id,
          domain_name: d.name,
          ddc_code: d.ddc_code || '',
          description: d.description || '',
          status: d.status || 'active',
        }));
        setAvailableDomains(mapped);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const handleSaveProfile = async () => {
    setSaving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await apiClient.put('/api/v1/retrieval/admin/deployment-profile', {
        profile_name: selectedProfile,
      });

      setSuccessMessage('Deployment profile saved successfully!');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  const toggleCustomDomain = (domainId: string) => {
    setCustomDomains((prev) =>
      prev.includes(domainId)
        ? prev.filter((d) => d !== domainId)
        : [...prev, domainId]
    );
  };

  const getProfileDomains = (profileName: string): Domain[] => {
    const profile = DEPLOYMENT_PROFILES.find((p) => p.profile_name === profileName);
    if (!profile) return [];

    if (profileName === 'custom') {
      return availableDomains.filter((d) => customDomains.includes(d.domain_id));
    }

    if (profile.active_domains.length === 0) {
      return availableDomains; // All domains
    }

    return availableDomains.filter((d) =>
      profile.active_domains.includes(d.domain_id)
    );
  };

  if (loading) {
    return (
      <div className="p-6 max-w-5xl mx-auto">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto" data-testid="deployment-profile-page">
      {/* Navigation Bar */}
      <div className="mb-4">
        <AdminNavigationBar />
      </div>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Deployment Profile</h1>
        <p className="text-gray-600 mt-1">
          Select a profile to activate relevant domains for your organization
        </p>
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-red-600 mt-0.5" />
          <div className="text-sm text-red-800">{error}</div>
        </div>
      )}

      {successMessage && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-start gap-2">
          <Check className="w-4 h-4 text-green-600 mt-0.5" />
          <div className="text-sm text-green-800">{successMessage}</div>
        </div>
      )}

      {/* Profile Selection */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Select Deployment Profile
        </h2>
        <div className="space-y-3">
          {DEPLOYMENT_PROFILES.map((profile) => {
            const isSelected = selectedProfile === profile.profile_name;
            const domains = getProfileDomains(profile.profile_name);

            return (
              <div
                key={profile.profile_name}
                className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                  isSelected
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => setSelectedProfile(profile.profile_name)}
                data-testid={`profile-${profile.profile_name}`}
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <div
                      className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                        isSelected
                          ? 'border-blue-600 bg-blue-600'
                          : 'border-gray-300'
                      }`}
                    >
                      {isSelected && <Check className="w-3 h-3 text-white" />}
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-gray-900">
                      {profile.display_name}
                    </div>
                    <div className="text-sm text-gray-600 mt-1">
                      {profile.description}
                    </div>
                    {domains.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {domains.map((domain) => (
                          <span
                            key={domain.domain_id}
                            className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded"
                          >
                            {domain.domain_name}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Custom Domain Selection */}
      {selectedProfile === 'custom' && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Select Custom Domains
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {availableDomains.map((domain) => {
              const isSelected = customDomains.includes(domain.domain_id);
              return (
                <div
                  key={domain.domain_id}
                  className={`border rounded-lg p-3 cursor-pointer transition-colors ${
                    isSelected
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => toggleCustomDomain(domain.domain_id)}
                  data-testid={`domain-${domain.domain_id}`}
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleCustomDomain(domain.domain_id)}
                      className="mt-1 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">
                        {domain.domain_name}
                      </div>
                      <div className="text-xs text-gray-500">
                        DDC: {domain.ddc_code}
                      </div>
                      {domain.description && (
                        <div className="text-xs text-gray-600 mt-1">
                          {domain.description}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSaveProfile}
          disabled={saving || (selectedProfile === 'custom' && customDomains.length === 0)}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
          data-testid="save-profile-button"
        >
          {saving && <Loader2 className="w-4 h-4 animate-spin" />}
          {saving ? 'Saving...' : 'Save Profile'}
        </button>
      </div>
    </div>
  );
}

/**
 * SkillCertificationPage Component
 * Sprint 98 Feature 98.6: Certification Status Dashboard
 *
 * Features:
 * - Certification overview statistics
 * - Skill certification grid with levels (Enterprise/Standard/Basic)
 * - Expiring certifications alerts
 * - Validation report viewer
 * - Re-validation functionality
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Award, AlertTriangle, CheckCircle2, XCircle, Shield } from 'lucide-react';
import {
  getSkillCertifications,
  getCertificationOverview,
  getSkillValidationReport,
  validateSkill,
  getExpiringCertifications,
} from '../../api/admin';
import type {
  SkillCertification,
  CertificationOverview,
  ValidationReport,
  CertificationLevel,
  CertificationStatus,
} from '../../types/admin';

/**
 * SkillCertificationPage - Certification status dashboard
 */
export function SkillCertificationPage() {
  const navigate = useNavigate();

  // State
  const [overview, setOverview] = useState<CertificationOverview | null>(null);
  const [certifications, setCertifications] = useState<SkillCertification[]>([]);
  const [expiringCertifications, setExpiringCertifications] = useState<SkillCertification[]>([]);
  const [selectedReport, setSelectedReport] = useState<ValidationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [levelFilter, setLevelFilter] = useState<CertificationLevel | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<CertificationStatus | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Load data on mount
  useEffect(() => {
    loadData();
  }, []);

  // Load all certification data
  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [overviewData, certificationsData, expiringData] = await Promise.all([
        getCertificationOverview(),
        getSkillCertifications(),
        getExpiringCertifications(30),
      ]);
      setOverview(overviewData);
      setCertifications(certificationsData);
      setExpiringCertifications(expiringData);
    } catch (err) {
      console.error('Failed to load certification data:', err);
      setError('Failed to load certification data. The backend may be unavailable.');
    } finally {
      setLoading(false);
    }
  };

  // View validation report
  const handleViewReport = async (skillName: string) => {
    try {
      const report = await getSkillValidationReport(skillName);
      setSelectedReport(report);
    } catch (err) {
      console.error('Failed to load validation report:', err);
      setError(`Failed to load validation report for ${skillName}.`);
    }
  };

  // Re-validate skill
  const handleValidate = async (skillName: string) => {
    setValidating(skillName);
    setError(null);
    try {
      const report = await validateSkill(skillName);
      setSelectedReport(report);
      // Reload data to update certification list
      await loadData();
    } catch (err) {
      console.error('Failed to validate skill:', err);
      setError(`Failed to validate skill ${skillName}. Please try again.`);
    } finally {
      setValidating(null);
    }
  };

  // Get certification level badge
  const getCertificationBadge = (level: CertificationLevel) => {
    switch (level) {
      case 'enterprise':
        return {
          icon: <Shield className="w-4 h-4" />,
          color: 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300 border-green-300 dark:border-green-700',
          label: 'Enterprise',
        };
      case 'standard':
        return {
          icon: <Award className="w-4 h-4" />,
          color: 'bg-yellow-100 dark:bg-yellow-900/50 text-yellow-700 dark:text-yellow-300 border-yellow-300 dark:border-yellow-700',
          label: 'Standard',
        };
      case 'basic':
        return {
          icon: <CheckCircle2 className="w-4 h-4" />,
          color: 'bg-gray-100 dark:bg-gray-700/50 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600',
          label: 'Basic',
        };
      default:
        return {
          icon: <XCircle className="w-4 h-4" />,
          color: 'bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 border-red-300 dark:border-red-700',
          label: 'Uncertified',
        };
    }
  };

  // Filter certifications
  const filteredCertifications = certifications.filter((cert) => {
    if (levelFilter !== 'all' && cert.level !== levelFilter) return false;
    if (statusFilter !== 'all' && cert.status !== statusFilter) return false;
    if (searchQuery && !cert.skill_name.toLowerCase().includes(searchQuery.toLowerCase()))
      return false;
    return true;
  });

  // Get days until expiration
  const getDaysUntilExpiration = (validUntil?: string): number | null => {
    if (!validUntil) return null;
    const now = new Date();
    const expiry = new Date(validUntil);
    const diff = expiry.getTime() - now.getTime();
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  };

  return (
    <div
      className="min-h-screen bg-gray-50 dark:bg-gray-900"
      data-testid="skill-certification-page"
    >
      <div className="max-w-7xl mx-auto py-8 px-6 space-y-6">
        {/* Header */}
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/admin')}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200 transition-colors rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
              data-testid="back-to-admin-button"
              aria-label="Back to Admin Dashboard"
            >
              <ArrowLeft className="w-5 h-5" />
              <span>Back to Admin</span>
            </button>
          </div>
        </header>

        {/* Page Title */}
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-green-100 dark:bg-green-900/50 rounded-xl flex items-center justify-center">
              <Award className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                Skill Certification Dashboard
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Monitor skill certifications and validation status
              </p>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-red-900 dark:text-red-100">Error</p>
                <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
              </div>
            </div>
          </div>
        )}

        {loading ? (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-12 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-green-200 dark:border-green-800 border-t-green-600 dark:border-t-green-400 mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">Loading certification data...</p>
          </div>
        ) : (
          <>
            {/* Overview Statistics */}
            {overview && (
              <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
                <div className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-900/40 rounded-xl p-4 border-2 border-green-200 dark:border-green-800">
                  <div className="flex items-center gap-2 mb-2">
                    <Shield className="w-5 h-5 text-green-600 dark:text-green-400" />
                    <span className="text-sm font-medium text-green-700 dark:text-green-300">
                      Enterprise
                    </span>
                  </div>
                  <p className="text-3xl font-bold text-green-900 dark:text-green-100">
                    {overview.enterprise_count}
                  </p>
                </div>

                <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 dark:from-yellow-900/20 dark:to-yellow-900/40 rounded-xl p-4 border-2 border-yellow-200 dark:border-yellow-800">
                  <div className="flex items-center gap-2 mb-2">
                    <Award className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
                    <span className="text-sm font-medium text-yellow-700 dark:text-yellow-300">
                      Standard
                    </span>
                  </div>
                  <p className="text-3xl font-bold text-yellow-900 dark:text-yellow-100">
                    {overview.standard_count}
                  </p>
                </div>

                <div className="bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-700 rounded-xl p-4 border-2 border-gray-200 dark:border-gray-600">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle2 className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Basic
                    </span>
                  </div>
                  <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                    {overview.basic_count}
                  </p>
                </div>

                <div className="bg-gradient-to-br from-red-50 to-red-100 dark:from-red-900/20 dark:to-red-900/40 rounded-xl p-4 border-2 border-red-200 dark:border-red-800">
                  <div className="flex items-center gap-2 mb-2">
                    <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                    <span className="text-sm font-medium text-red-700 dark:text-red-300">
                      Uncertified
                    </span>
                  </div>
                  <p className="text-3xl font-bold text-red-900 dark:text-red-100">
                    {overview.uncertified_count}
                  </p>
                </div>

                <div className="bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-900/20 dark:to-orange-900/40 rounded-xl p-4 border-2 border-orange-200 dark:border-orange-800">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                    <span className="text-sm font-medium text-orange-700 dark:text-orange-300">
                      Expiring Soon
                    </span>
                  </div>
                  <p className="text-3xl font-bold text-orange-900 dark:text-orange-100">
                    {overview.expiring_soon_count}
                  </p>
                </div>

                <div className="bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-700 rounded-xl p-4 border-2 border-gray-200 dark:border-gray-600">
                  <div className="flex items-center gap-2 mb-2">
                    <XCircle className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Expired
                    </span>
                  </div>
                  <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                    {overview.expired_count}
                  </p>
                </div>
              </div>
            )}

            {/* Expiring Certifications Alert */}
            {expiringCertifications.length > 0 && (
              <div className="bg-orange-50 dark:bg-orange-900/20 border-2 border-orange-200 dark:border-orange-800 rounded-xl p-6">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-6 h-6 text-orange-600 dark:text-orange-400 flex-shrink-0" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-orange-900 dark:text-orange-100 mb-2">
                      Certifications Expiring Soon ({expiringCertifications.length})
                    </h3>
                    <div className="space-y-2">
                      {expiringCertifications.slice(0, 3).map((cert) => {
                        const daysLeft = getDaysUntilExpiration(cert.valid_until);
                        return (
                          <div
                            key={cert.skill_name}
                            className="flex items-center justify-between bg-white dark:bg-orange-900/20 p-3 rounded-lg"
                          >
                            <span className="font-medium text-orange-900 dark:text-orange-100">
                              {cert.skill_name}
                            </span>
                            <span className="text-sm text-orange-700 dark:text-orange-300">
                              {daysLeft} days left
                            </span>
                          </div>
                        );
                      })}
                    </div>
                    {expiringCertifications.length > 3 && (
                      <p className="text-sm text-orange-700 dark:text-orange-300 mt-2">
                        And {expiringCertifications.length - 3} more...
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Filters */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-6">
              <div className="flex flex-wrap gap-4 items-center">
                <div className="flex-1 min-w-[200px]">
                  <input
                    type="text"
                    placeholder="Search skills..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full px-4 py-2 border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-green-500 dark:focus:ring-green-400"
                    data-testid="search-input"
                  />
                </div>
                <select
                  value={levelFilter}
                  onChange={(e) => setLevelFilter(e.target.value as CertificationLevel | 'all')}
                  className="px-4 py-2 border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-green-500 dark:focus:ring-green-400"
                  data-testid="level-filter"
                >
                  <option value="all">All Levels</option>
                  <option value="enterprise">Enterprise</option>
                  <option value="standard">Standard</option>
                  <option value="basic">Basic</option>
                  <option value="uncertified">Uncertified</option>
                </select>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as CertificationStatus | 'all')}
                  className="px-4 py-2 border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-green-500 dark:focus:ring-green-400"
                  data-testid="status-filter"
                >
                  <option value="all">All Status</option>
                  <option value="valid">Valid</option>
                  <option value="expiring_soon">Expiring Soon</option>
                  <option value="expired">Expired</option>
                  <option value="pending">Pending</option>
                </select>
              </div>
            </div>

            {/* Certifications Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {filteredCertifications.length === 0 ? (
                <div className="col-span-2 bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-12 text-center">
                  <Award className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                  <p className="text-lg font-medium text-gray-600 dark:text-gray-400">
                    No skills found
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
                    Try adjusting your filters
                  </p>
                </div>
              ) : (
                filteredCertifications.map((cert) => {
                  const badge = getCertificationBadge(cert.level);
                  const daysLeft = getDaysUntilExpiration(cert.valid_until);

                  return (
                    <div
                      key={cert.skill_name}
                      className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-6"
                      data-testid={`cert-${cert.skill_name}`}
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex-1">
                          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                            {cert.skill_name}
                          </h3>
                          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            Version {cert.version}
                          </p>
                        </div>
                        <div
                          className={`flex items-center gap-2 px-3 py-1 rounded-full border-2 text-sm font-medium ${badge.color}`}
                        >
                          {badge.icon}
                          <span>{badge.label}</span>
                        </div>
                      </div>

                      <div className="space-y-2 text-sm mb-4">
                        {cert.valid_until && (
                          <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">Valid until:</span>
                            <span className="text-gray-900 dark:text-gray-100 font-medium">
                              {new Date(cert.valid_until).toLocaleDateString()}
                              {daysLeft !== null && daysLeft < 30 && (
                                <span className="ml-2 text-orange-600 dark:text-orange-400">
                                  ({daysLeft} days)
                                </span>
                              )}
                            </span>
                          </div>
                        )}
                        <div className="flex justify-between">
                          <span className="text-gray-500 dark:text-gray-400">Last validated:</span>
                          <span className="text-gray-900 dark:text-gray-100">
                            {new Date(cert.last_validated).toLocaleDateString()}
                          </span>
                        </div>
                      </div>

                      {/* Checks Summary */}
                      <div className="flex flex-wrap gap-2 mb-4">
                        {cert.checks.map((check, idx) => (
                          <div
                            key={idx}
                            className={`flex items-center gap-1 px-2 py-1 rounded text-xs ${
                              check.passed
                                ? 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300'
                                : 'bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300'
                            }`}
                          >
                            {check.passed ? (
                              <CheckCircle2 className="w-3 h-3" />
                            ) : (
                              <XCircle className="w-3 h-3" />
                            )}
                            <span>{check.check_name}</span>
                          </div>
                        ))}
                      </div>

                      {/* Issues */}
                      {cert.issues && cert.issues.length > 0 && (
                        <div className="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                          <p className="text-xs font-semibold text-yellow-900 dark:text-yellow-100 mb-1">
                            Issues:
                          </p>
                          <ul className="text-xs text-yellow-800 dark:text-yellow-200 space-y-1">
                            {cert.issues.map((issue, idx) => (
                              <li key={idx}>• {issue}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Actions */}
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleViewReport(cert.skill_name)}
                          className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
                          data-testid={`view-report-${cert.skill_name}`}
                        >
                          View Report
                        </button>
                        <button
                          onClick={() => handleValidate(cert.skill_name)}
                          disabled={validating === cert.skill_name}
                          className="flex-1 px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed rounded-lg transition-colors"
                          data-testid={`validate-${cert.skill_name}`}
                        >
                          {validating === cert.skill_name ? 'Validating...' : 'Re-validate'}
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </>
        )}

        {/* Validation Report Modal */}
        {selectedReport && (
          <div
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setSelectedReport(null)}
          >
            <div
              className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-3xl w-full max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6 space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      Validation Report
                    </h2>
                    <p className="text-gray-600 dark:text-gray-400 mt-1">
                      {selectedReport.skill_name}
                    </p>
                  </div>
                  <button
                    onClick={() => setSelectedReport(null)}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                  >
                    <XCircle className="w-6 h-6" />
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-4 py-4 border-y-2 border-gray-200 dark:border-gray-700">
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Checks Passed</p>
                    <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {selectedReport.passed_checks}/{selectedReport.total_checks}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Certification Level</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 capitalize">
                      {selectedReport.certification_level}
                    </p>
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">
                    Validation Checks
                  </h3>
                  <div className="space-y-2">
                    {selectedReport.checks.map((check, idx) => (
                      <div
                        key={idx}
                        className={`p-3 rounded-lg border-2 ${
                          check.passed
                            ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                            : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          {check.passed ? (
                            <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0" />
                          ) : (
                            <XCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
                          )}
                          <div className="flex-1">
                            <p
                              className={`font-medium ${
                                check.passed
                                  ? 'text-green-900 dark:text-green-100'
                                  : 'text-red-900 dark:text-red-100'
                              }`}
                            >
                              {check.check_name}
                            </p>
                            {check.details && (
                              <p
                                className={`text-sm mt-1 ${
                                  check.passed
                                    ? 'text-green-700 dark:text-green-300'
                                    : 'text-red-700 dark:text-red-300'
                                }`}
                              >
                                {check.details}
                              </p>
                            )}
                          </div>
                          <span
                            className={`text-xs font-semibold px-2 py-1 rounded ${
                              check.passed
                                ? 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300'
                                : 'bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300'
                            }`}
                          >
                            {check.category}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {selectedReport.recommendations.length > 0 && (
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">
                      Recommendations
                    </h3>
                    <ul className="space-y-2">
                      {selectedReport.recommendations.map((rec, idx) => (
                        <li
                          key={idx}
                          className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300"
                        >
                          <span className="text-blue-600 dark:text-blue-400 mt-1">•</span>
                          <span>{rec}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="flex justify-end gap-2 pt-4 border-t-2 border-gray-200 dark:border-gray-700">
                  <button
                    onClick={() => setSelectedReport(null)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Info Section */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-800 rounded-xl p-6">
          <div className="flex gap-3">
            <div className="flex-shrink-0">
              <svg
                className="w-6 h-6 text-blue-600 dark:text-blue-400"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div>
              <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                About Skill Certification
              </h4>
              <p className="text-sm text-blue-800 dark:text-blue-200 mb-3">
                Skills are certified at three levels based on compliance checks and validation:
              </p>
              <ul className="space-y-1 text-sm text-blue-800 dark:text-blue-200">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                  <span>
                    <strong>Basic:</strong> Syntax valid, no security issues
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                  <span>
                    <strong>Standard:</strong> Basic + GDPR compliance
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                  <span>
                    <strong>Enterprise:</strong> Standard + Audit + Explainability
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SkillCertificationPage;

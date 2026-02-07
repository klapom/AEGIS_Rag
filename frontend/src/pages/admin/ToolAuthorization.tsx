/**
 * ToolAuthorization Page Component
 * Sprint 97 Feature 97.3: Tool Authorization Manager (8 SP)
 *
 * Features:
 * - View tool authorizations per skill
 * - Add/remove tool permissions
 * - Configure access levels (standard/elevated/admin)
 * - Set rate limits
 * - Configure domain restrictions
 *
 * Route: /admin/skills/:skillName/tools
 */

import { useState, useEffect, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Plus, Trash2, Save, X } from 'lucide-react';
import {
  getToolAuthorizations,
  addToolAuthorization,
  removeToolAuthorization,
  updateToolAuthorization,
} from '../../api/skills';
import type { ToolAuthorization } from '../../types/skills';
import { AdminNavigationBar } from '../../components/admin/AdminNavigationBar';

export function ToolAuthorizationPage() {
  const { skillName } = useParams<{ skillName: string }>();

  // Data state
  const [authorizations, setAuthorizations] = useState<ToolAuthorization[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal state for adding/editing tools
  const [showModal, setShowModal] = useState(false);
  const [editingAuth, setEditingAuth] = useState<ToolAuthorization | null>(null);

  // Load authorizations
  const loadAuthorizations = useCallback(async () => {
    if (!skillName) return;

    setLoading(true);
    setError(null);

    try {
      const response = await getToolAuthorizations(skillName);
      setAuthorizations(response.authorizations);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tool authorizations');
    } finally {
      setLoading(false);
    }
  }, [skillName]);

  // Initial load
  useEffect(() => {
    void loadAuthorizations();
  }, [loadAuthorizations]);

  // Remove tool authorization
  const handleRemove = async (toolName: string) => {
    if (!skillName) return;

    if (!window.confirm(`Remove authorization for tool "${toolName}"?`)) {
      return;
    }

    try {
      await removeToolAuthorization(skillName, toolName);
      await loadAuthorizations();
    } catch (err) {
      alert(`Failed to remove authorization: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // Open modal for adding new tool
  const handleAddNew = () => {
    setEditingAuth({
      tool_name: '',
      access_level: 'standard',
      rate_limit: 60,
      allowed_domains: [],
      blocked_domains: [],
    });
    setShowModal(true);
  };

  // Open modal for editing existing tool
  const handleEdit = (auth: ToolAuthorization) => {
    setEditingAuth({ ...auth });
    setShowModal(true);
  };

  // Save tool authorization (add or update)
  const handleSave = async (auth: ToolAuthorization) => {
    if (!skillName) return;

    try {
      const existing = authorizations.find((a) => a.tool_name === auth.tool_name);
      if (existing) {
        await updateToolAuthorization(skillName, auth);
      } else {
        await addToolAuthorization(skillName, auth);
      }

      await loadAuthorizations();
      setShowModal(false);
      setEditingAuth(null);
    } catch (err) {
      alert(`Failed to save authorization: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  if (!skillName) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <p className="text-lg text-gray-600 dark:text-gray-400">Skill name is required</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="mb-4">
        <AdminNavigationBar />
      </div>
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b-2 border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <Link
            to="/admin/skills/registry"
            className="inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 mb-3"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Registry
          </Link>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Tool Authorization: {skillName}
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Manage tool permissions and access controls
              </p>
            </div>
            <button
              onClick={handleAddNew}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Tool
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Error Display */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
            <p className="text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-12 text-center">
            <p className="text-gray-600 dark:text-gray-400">Loading authorizations...</p>
          </div>
        )}

        {/* Authorizations Table */}
        {!loading && authorizations.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-gray-900 dark:text-gray-100">
                    Tool
                  </th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-gray-900 dark:text-gray-100">
                    Access Level
                  </th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-gray-900 dark:text-gray-100">
                    Rate Limit
                  </th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-gray-900 dark:text-gray-100">
                    Domains
                  </th>
                  <th className="text-right px-6 py-3 text-sm font-semibold text-gray-900 dark:text-gray-100">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {authorizations.map((auth) => (
                  <tr key={auth.tool_name} className="hover:bg-gray-50 dark:hover:bg-gray-900/50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-gray-100">
                      {auth.tool_name}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                          auth.access_level === 'admin'
                            ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                            : auth.access_level === 'elevated'
                            ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                            : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        }`}
                      >
                        {auth.access_level}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                      {auth.rate_limit ? `${auth.rate_limit}/min` : 'Unlimited'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                      {auth.allowed_domains.length > 0 || auth.blocked_domains.length > 0 ? (
                        <button
                          onClick={() => handleEdit(auth)}
                          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                        >
                          View ({auth.allowed_domains.length + auth.blocked_domains.length})
                        </button>
                      ) : (
                        'None'
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleEdit(auth)}
                          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 text-sm font-medium"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleRemove(auth.tool_name)}
                          className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Empty State */}
        {!loading && authorizations.length === 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-12 text-center">
            <p className="text-lg text-gray-600 dark:text-gray-400 mb-2">
              No tool authorizations configured
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-500 mb-4">
              Add tools to grant this skill access to external capabilities
            </p>
            <button
              onClick={handleAddNew}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add First Tool
            </button>
          </div>
        )}
      </main>

      {/* Edit Modal */}
      {showModal && editingAuth && (
        <AuthorizationModal
          authorization={editingAuth}
          onSave={handleSave}
          onCancel={() => {
            setShowModal(false);
            setEditingAuth(null);
          }}
        />
      )}
    </div>
  );
}

// ============================================================================
// Authorization Modal Component
// ============================================================================

interface AuthorizationModalProps {
  authorization: ToolAuthorization;
  onSave: (auth: ToolAuthorization) => void;
  onCancel: () => void;
}

function AuthorizationModal({ authorization, onSave, onCancel }: AuthorizationModalProps) {
  const [auth, setAuth] = useState<ToolAuthorization>(authorization);
  const [newDomain, setNewDomain] = useState('');

  const handleAddDomain = (type: 'allowed' | 'blocked') => {
    if (!newDomain.trim()) return;

    if (type === 'allowed') {
      setAuth({ ...auth, allowed_domains: [...auth.allowed_domains, newDomain.trim()] });
    } else {
      setAuth({ ...auth, blocked_domains: [...auth.blocked_domains, newDomain.trim()] });
    }

    setNewDomain('');
  };

  const handleRemoveDomain = (domain: string, type: 'allowed' | 'blocked') => {
    if (type === 'allowed') {
      setAuth({ ...auth, allowed_domains: auth.allowed_domains.filter((d) => d !== domain) });
    } else {
      setAuth({ ...auth, blocked_domains: auth.blocked_domains.filter((d) => d !== domain) });
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
            {authorization.tool_name ? 'Edit Tool Authorization' : 'Add Tool Authorization'}
          </h2>
          <button onClick={onCancel} className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Tool Name */}
          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
              Tool Name
            </label>
            <input
              type="text"
              value={auth.tool_name}
              onChange={(e) => setAuth({ ...auth, tool_name: e.target.value })}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="e.g., browser, python_exec, web_search"
            />
          </div>

          {/* Access Level */}
          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
              Access Level
            </label>
            <select
              value={auth.access_level}
              onChange={(e) =>
                setAuth({ ...auth, access_level: e.target.value as ToolAuthorization['access_level'] })
              }
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="standard">Standard</option>
              <option value="elevated">Elevated</option>
              <option value="admin">Admin</option>
            </select>
          </div>

          {/* Rate Limit */}
          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
              Rate Limit (requests per minute)
            </label>
            <input
              type="number"
              value={auth.rate_limit || ''}
              onChange={(e) => setAuth({ ...auth, rate_limit: e.target.value ? Number(e.target.value) : null })}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Leave empty for unlimited"
            />
          </div>

          {/* Allowed Domains */}
          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
              Allowed Domains
            </label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddDomain('allowed')}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="e.g., *.wikipedia.org"
              />
              <button
                onClick={() => handleAddDomain('allowed')}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
              >
                Add
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {auth.allowed_domains.map((domain) => (
                <span
                  key={domain}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-full text-sm"
                >
                  {domain}
                  <button
                    onClick={() => handleRemoveDomain(domain, 'allowed')}
                    className="hover:text-green-900 dark:hover:text-green-200"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Blocked Domains */}
          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
              Blocked Domains
            </label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddDomain('blocked')}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="e.g., *.malware.com"
              />
              <button
                onClick={() => handleAddDomain('blocked')}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
              >
                Add
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {auth.blocked_domains.map((domain) => (
                <span
                  key={domain}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded-full text-sm"
                >
                  {domain}
                  <button
                    onClick={() => handleRemoveDomain(domain, 'blocked')}
                    className="hover:text-red-900 dark:hover:text-red-200"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onCancel}
            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onSave(auth)}
            disabled={!auth.tool_name.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save className="w-4 h-4" />
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

export default ToolAuthorizationPage;

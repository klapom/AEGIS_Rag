/**
 * SkillRegistry Page Component
 * Sprint 97 Feature 97.1: Skill Registry Browser UI (10 SP)
 *
 * Features:
 * - Grid view of all skills (12 per page)
 * - Search by name/description
 * - Filter by status (active/inactive/all)
 * - Activation toggle
 * - Navigation to skill detail pages
 *
 * Route: /admin/skills/registry
 */

import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Search, Filter, Plus } from 'lucide-react';
import { AdminNavigationBar } from '../../components/admin/AdminNavigationBar';
import { listSkills, activateSkill, deactivateSkill } from '../../api/skills';
import type { SkillSummary } from '../../types/skills';

export function SkillRegistry() {
  // Search and filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [page, setPage] = useState(1);
  const [limit] = useState(12);

  // Data state
  const [skills, setSkills] = useState<SkillSummary[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load skills
  const loadSkills = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await listSkills({
        search: searchQuery || undefined,
        status: statusFilter,
        page,
        limit,
      });

      // Sprint 121 Fix: Use backend's total_pages instead of calculating locally
      setSkills(response.items);
      setTotalCount(response.total);
      setTotalPages(response.total_pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load skills');
    } finally {
      setLoading(false);
    }
  }, [searchQuery, statusFilter, page, limit]);

  // Initial load and refresh on filter changes
  useEffect(() => {
    void loadSkills();
  }, [loadSkills]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [searchQuery, statusFilter]);

  // Toggle skill activation
  const handleToggleActivation = async (skillName: string, currentActive: boolean) => {
    try {
      if (currentActive) {
        await deactivateSkill(skillName);
      } else {
        await activateSkill(skillName);
      }

      // Refresh skills list
      await loadSkills();
    } catch (err) {
      console.error('Failed to toggle skill activation:', err);
      alert(`Failed to ${currentActive ? 'deactivate' : 'activate'} skill: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // Pagination (totalPages comes from backend response)
  const hasNextPage = page < totalPages;
  const hasPrevPage = page > 1;

  return (
    <div data-testid="skills-page" className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b-2 border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <div className="mb-4">
            <AdminNavigationBar />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Skill Registry
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Browse and manage Anthropic Agent Skills
              </p>
            </div>
            <button
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              onClick={() => alert('Add Skill feature not yet implemented')}
            >
              <Plus className="w-4 h-4" />
              Add Skill
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Search and Filters */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Search Input */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                data-testid="skill-search-input"
                type="text"
                placeholder="Search skills by name or description..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-500" />
              <select
                data-testid="skill-filter-status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as 'all' | 'active' | 'inactive')}
                className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">All Skills</option>
                <option value="active">Active Only</option>
                <option value="inactive">Inactive Only</option>
              </select>
            </div>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
            <p className="text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div
                key={i}
                className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-6 animate-pulse"
              >
                <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded mb-4"></div>
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded mb-2"></div>
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3"></div>
              </div>
            ))}
          </div>
        )}

        {/* Skills Grid */}
        {!loading && skills.length > 0 && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
              {skills.map((skill) => (
                <SkillCard
                  key={skill.name}
                  skill={skill}
                  onToggle={handleToggleActivation}
                />
              ))}
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Showing {skills.length} of {totalCount} skills
              </p>
              <div className="flex items-center gap-2">
                <button
                  data-testid="skills-prev-page"
                  onClick={() => setPage(page - 1)}
                  disabled={!hasPrevPage}
                  className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                >
                  Previous
                </button>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Page {page} of {totalPages}
                </span>
                <button
                  data-testid="skills-next-page"
                  onClick={() => setPage(page + 1)}
                  disabled={!hasNextPage}
                  className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}

        {/* Empty State */}
        {!loading && skills.length === 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-12 text-center">
            <p className="text-lg text-gray-600 dark:text-gray-400 mb-2">No skills found</p>
            <p className="text-sm text-gray-500 dark:text-gray-500">
              {searchQuery || statusFilter !== 'all'
                ? 'Try adjusting your search or filters'
                : 'Get started by adding your first skill'}
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

// ============================================================================
// SkillCard Component
// ============================================================================

interface SkillCardProps {
  skill: SkillSummary;
  onToggle: (skillName: string, isActive: boolean) => void;
}

function SkillCard({ skill, onToggle }: SkillCardProps) {
  return (
    <div
      data-testid={`skill-card-${skill.name}`}
      className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-6 hover:shadow-lg transition-shadow"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-3xl" role="img" aria-label="skill icon">
          {skill.icon}
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400">v{skill.version}</span>
      </div>

      {/* Name and Description */}
      <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100 mb-2">
        {skill.name}
      </h3>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">
        {skill.description}
      </p>

      {/* Stats */}
      <div className="flex gap-4 text-xs text-gray-500 dark:text-gray-400 mb-4">
        <span>🔧 {skill.tools_count} tools</span>
        <span>🎯 {skill.triggers_count} triggers</span>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          data-testid={`skill-toggle-${skill.name}`}
          onClick={() => onToggle(skill.name, skill.is_active)}
          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
            skill.is_active
              ? 'bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400'
          }`}
        >
          <span data-testid={`skill-status-${skill.name}`}>
            {skill.is_active ? '🟢 Active' : '⚪ Inactive'}
          </span>
        </button>

        <div className="flex gap-2">
          <Link
            to={`/admin/skills/${skill.name}/config`}
            data-testid={`skill-edit-${skill.name}`}
            className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 text-sm font-medium"
          >
            Config
          </Link>
          <Link
            to={`/admin/skills/${skill.name}/logs`}
            data-testid={`skill-logs-link-${skill.name}`}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 text-sm font-medium"
          >
            Logs
          </Link>
        </div>
      </div>
    </div>
  );
}

export default SkillRegistry;

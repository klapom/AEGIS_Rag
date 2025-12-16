/**
 * AdminDashboard Component
 * Sprint 46 Feature 46.8: Admin Area Consolidation
 *
 * Consolidated admin dashboard with collapsible sections for:
 * - Domains: Domain list with status and creation
 * - Indexing: Document indexing status and controls
 * - Settings: System configuration overview
 *
 * This replaces the previous AdminPage as the main /admin route.
 */

import { DomainSection } from '../components/admin/DomainSection';
import { IndexingSection } from '../components/admin/IndexingSection';
import { SettingsSection } from '../components/admin/SettingsSection';

/**
 * AdminDashboard - Consolidated admin page with collapsible sections
 *
 * Layout:
 * ```
 * /admin          -> Single page with sections
 *   +-----------------------------------------+
 *   | Admin Dashboard                         |
 *   +-----------------------------------------+
 *   | Domains           [New Domain]          |
 *   | ├── omnitracker (ready)                 |
 *   | ├── legal (training...)                 |
 *   | └── general (fallback)                  |
 *   +-----------------------------------------+
 *   | Indexing          [Index Dir]           |
 *   | └── Last run: 2024-12-15 10:30          |
 *   |     Status: 450 documents indexed       |
 *   +-----------------------------------------+
 *   | Settings                                |
 *   | └── LLM: qwen3:8b | Embeddings: BGE     |
 *   +-----------------------------------------+
 * ```
 */
export function AdminDashboard() {
  return (
    <div
      className="min-h-screen bg-gray-50 dark:bg-gray-900"
      data-testid="admin-dashboard"
    >
      <div className="max-w-4xl mx-auto py-8 px-6 space-y-6">
        {/* Header */}
        <header className="space-y-2">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            Admin Dashboard
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage domains, indexing, and system configuration
          </p>
        </header>

        {/* Sections */}
        <div className="space-y-4">
          {/* Domains Section */}
          <DomainSection />

          {/* Indexing Section */}
          <IndexingSection />

          {/* Settings Section */}
          <SettingsSection />
        </div>

        {/* Footer with quick navigation */}
        <footer className="pt-6 border-t border-gray-200 dark:border-gray-700">
          <div className="flex flex-wrap gap-4 text-sm">
            <NavLink href="/admin/indexing" label="Full Indexing Page" />
            <NavLink href="/admin/domain-training" label="Domain Training" />
            <NavLink href="/admin/graph" label="Graph Analytics" />
            <NavLink href="/admin/costs" label="Cost Dashboard" />
            <NavLink href="/admin/llm-config" label="LLM Configuration" />
            <NavLink href="/health" label="System Health" />
          </div>
        </footer>
      </div>
    </div>
  );
}

/**
 * Navigation link component
 */
interface NavLinkProps {
  href: string;
  label: string;
}

function NavLink({ href, label }: NavLinkProps) {
  return (
    <a
      href={href}
      className="text-blue-600 dark:text-blue-400 hover:underline"
      data-testid={`nav-link-${label.toLowerCase().replace(/\s+/g, '-')}`}
    >
      {label}
    </a>
  );
}

export default AdminDashboard;

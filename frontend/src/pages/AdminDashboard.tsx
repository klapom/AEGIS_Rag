/**
 * AdminDashboard Component
 * Sprint 46 Feature 46.8: Admin Area Consolidation
 * Sprint 51: Navigation bar at top, Domains section at bottom collapsed
 *
 * Consolidated admin dashboard with collapsible sections for:
 * - Navigation: Quick links to admin subpages (TOP)
 * - Indexing: Document indexing status and controls
 * - Settings: System configuration overview
 * - Domains: Domain list with status and creation (BOTTOM, collapsed)
 *
 * This replaces the previous AdminPage as the main /admin route.
 */

import { AdminNavigationBar } from '../components/admin/AdminNavigationBar';
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
 *   | [Graph] [Costs] [LLM] [Health] [...]    | <- Navigation bar at TOP
 *   +-----------------------------------------+
 *   | Indexing          [Index Dir]           |
 *   | └── Last run: 2024-12-15 10:30          |
 *   |     Status: 450 documents indexed       |
 *   +-----------------------------------------+
 *   | Settings                                |
 *   | └── LLM: qwen3:8b | Embeddings: BGE     |
 *   +-----------------------------------------+
 *   | Domains (collapsed) [New Domain]        | <- At BOTTOM, collapsed
 *   | └── Click to expand...                  |
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

        {/* Navigation Bar - Quick links to admin subpages */}
        <AdminNavigationBar />

        {/* Main Sections */}
        <div className="space-y-4">
          {/* Indexing Section */}
          <IndexingSection />

          {/* Settings Section */}
          <SettingsSection />

          {/* Domains Section - at bottom, collapsed by default */}
          <DomainSection defaultExpanded={false} />
        </div>
      </div>
    </div>
  );
}

export default AdminDashboard;

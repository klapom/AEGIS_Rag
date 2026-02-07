/**
 * IngestionJobsPage Component
 * Sprint 71 Feature 71.8: Ingestion Job Monitoring UI
 *
 * Displays all ingestion jobs with real-time SSE progress updates.
 * Shows overall progress, current step, and parallel document processing.
 */

import { useNavigate } from 'react-router-dom';
import { IngestionJobList } from '../../components/admin/IngestionJobList';
import { AdminNavigationBar } from '../../components/admin/AdminNavigationBar';

/**
 * IngestionJobsPage - Main page for ingestion job monitoring
 *
 * Features:
 * - Back button to /admin
 * - Real-time job list with SSE updates
 * - Overall progress bars
 * - Current step display (parsing → chunking → embedding → graph)
 * - Parallel document status (up to 3 concurrent)
 */
export function IngestionJobsPage() {
  const navigate = useNavigate();

  return (
    <div
      className="min-h-screen bg-gray-50 dark:bg-gray-900"
      data-testid="ingestion-jobs-page"
    >
      <div className="max-w-6xl mx-auto py-8 px-6 space-y-6">
        {/* Admin Navigation */}
        <div className="mb-4">
          <AdminNavigationBar />
        </div>

        <div className="space-y-2">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            Ingestion Jobs
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Monitor document ingestion jobs with real-time progress updates
          </p>
        </div>

        {/* Job List */}
        <IngestionJobList />
      </div>
    </div>
  );
}

export default IngestionJobsPage;

/**
 * BashToolPage Component
 * Sprint 116 Feature 116.6: Bash Tool Execution UI (8 SP)
 *
 * Dedicated page for bash command execution with integrated UI.
 * Provides a standalone interface for executing bash commands
 * with command history and output visualization.
 */

import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Terminal } from 'lucide-react';
import { BashToolExecutor } from '../../components/admin/BashToolExecutor';

/**
 * BashToolPage - Standalone page for bash command execution
 *
 * Features:
 * - Back navigation to admin dashboard
 * - Full-width bash executor component
 * - Authentication token from localStorage
 */
export function BashToolPage() {
  const navigate = useNavigate();

  // Get auth token from localStorage (if available)
  const authToken = localStorage.getItem('auth_token') || undefined;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/admin')}
                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
                aria-label="Back to admin dashboard"
              >
                <ArrowLeft className="w-5 h-5" />
                <span className="text-sm font-medium">Admin Dashboard</span>
              </button>
              <div className="h-6 w-px bg-gray-300" />
              <div className="flex items-center gap-2">
                <Terminal className="w-5 h-5 text-blue-600" />
                <h1 className="text-lg font-semibold text-gray-900">Bash Tool</h1>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Execute Bash Commands
          </h2>
          <p className="text-gray-600">
            Run bash commands directly from the web interface. All commands are executed in
            a sandboxed environment with a 30-second timeout.
          </p>
        </div>

        {/* Bash Executor Component */}
        <BashToolExecutor
          authToken={authToken}
          onExecute={(command, result) => {
            console.log('Command executed:', { command, result });
          }}
        />

        {/* Help Section */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-3">Usage Tips</h3>
          <ul className="space-y-2 text-sm text-blue-800">
            <li className="flex items-start gap-2">
              <span className="font-bold">•</span>
              <span>
                Use <kbd className="px-1.5 py-0.5 bg-blue-100 rounded text-xs">Ctrl+Enter</kbd>{' '}
                or <kbd className="px-1.5 py-0.5 bg-blue-100 rounded text-xs">⌘+Enter</kbd> to
                quickly execute commands
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold">•</span>
              <span>
                Command history is stored locally in your browser and persists across sessions
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold">•</span>
              <span>
                Click on any command in the history to reload it into the input field
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold">•</span>
              <span>
                All commands have a 30-second timeout and are executed in a sandboxed environment
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold">•</span>
              <span>
                Exit code 0 indicates successful execution; non-zero indicates an error
              </span>
            </li>
          </ul>
        </div>

        {/* Security Notice */}
        <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <svg
                className="w-5 h-5 text-yellow-600"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div>
              <h4 className="text-sm font-medium text-yellow-800">Security Notice</h4>
              <p className="mt-1 text-sm text-yellow-700">
                Be cautious when executing commands. Destructive operations (rm, dd, etc.) may
                affect the system. Always verify commands before execution.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default BashToolPage;

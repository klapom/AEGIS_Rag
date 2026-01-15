/**
 * AgentCommunicationPage Component
 * Sprint 98 Feature 98.1: Agent Communication Dashboard
 *
 * Admin page for monitoring inter-agent communication.
 * Displays real-time MessageBus activity, Blackboard state,
 * active orchestrations, and performance metrics.
 *
 * Route: /admin/agent-communication
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Radio, Shield } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { MessageBusMonitor } from '../../components/agent/MessageBusMonitor';
import { BlackboardViewer } from '../../components/agent/BlackboardViewer';
import { OrchestrationTimeline } from '../../components/agent/OrchestrationTimeline';
import { CommunicationMetrics } from '../../components/agent/CommunicationMetrics';

/**
 * AgentCommunicationPage provides real-time monitoring of agent communication.
 *
 * Features:
 * - Admin-only access
 * - Real-time MessageBus monitoring with auto-refresh
 * - Blackboard state viewer for shared memory
 * - Active orchestration tracking with phase progress
 * - Performance metrics dashboard
 * - Responsive grid layout
 * - Dark mode support
 */
export function AgentCommunicationPage() {
  const { isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState<'all' | 'messages' | 'blackboard' | 'orchestrations'>(
    'all'
  );

  // Unauthorized state
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div
          className="text-center max-w-md p-8 bg-white dark:bg-gray-800 rounded-xl shadow-lg"
          data-testid="unauthorized-message"
        >
          <div className="w-16 h-16 mx-auto mb-4 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
            <Shield className="w-8 h-8 text-red-600 dark:text-red-400" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            Access Denied
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            You need to be logged in to access the Agent Communication Dashboard.
          </p>
          <Link
            to="/login"
            className="inline-block px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
          >
            Go to Login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b-2 border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <Link
            to="/admin"
            className="inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 mb-3"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Admin
          </Link>
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <Radio className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Agent Communication Dashboard
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Real-time monitoring of inter-agent messaging and orchestration
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* View Toggle Tabs */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-4">
            <button
              onClick={() => setActiveTab('all')}
              className={`px-4 py-3 font-medium border-b-2 transition-colors ${
                activeTab === 'all'
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
              data-testid="tab-all"
            >
              All Components
            </button>
            <button
              onClick={() => setActiveTab('messages')}
              className={`px-4 py-3 font-medium border-b-2 transition-colors ${
                activeTab === 'messages'
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
              data-testid="tab-messages"
            >
              MessageBus
            </button>
            <button
              onClick={() => setActiveTab('blackboard')}
              className={`px-4 py-3 font-medium border-b-2 transition-colors ${
                activeTab === 'blackboard'
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
              data-testid="tab-blackboard"
            >
              Blackboard
            </button>
            <button
              onClick={() => setActiveTab('orchestrations')}
              className={`px-4 py-3 font-medium border-b-2 transition-colors ${
                activeTab === 'orchestrations'
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
              data-testid="tab-orchestrations"
            >
              Orchestrations
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* All Components View */}
        {activeTab === 'all' && (
          <div className="space-y-8">
            {/* Performance Metrics - Full Width */}
            <CommunicationMetrics />

            {/* Two Column Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Left Column */}
              <div className="space-y-8">
                <MessageBusMonitor />
                <BlackboardViewer />
              </div>

              {/* Right Column */}
              <div>
                <OrchestrationTimeline />
              </div>
            </div>

            {/* Info Card */}
            <div className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                About Agent Communication
              </h3>
              <div className="space-y-4 text-sm text-gray-600 dark:text-gray-400">
                <div className="flex gap-3">
                  <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                    <span className="text-blue-600 dark:text-blue-400 font-bold">1</span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-gray-100">MessageBus</p>
                    <p>
                      The MessageBus enables asynchronous communication between agents via typed
                      messages (requests, responses, broadcasts, events).
                    </p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                    <span className="text-purple-600 dark:text-purple-400 font-bold">2</span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-gray-100">Blackboard</p>
                    <p>
                      The Blackboard provides shared memory across agents with namespaces for
                      different workflow stages (retrieval, synthesis, reflection).
                    </p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <div className="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                    <span className="text-green-600 dark:text-green-400 font-bold">3</span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-gray-100">
                      Skill Orchestrator
                    </p>
                    <p>
                      The Orchestrator coordinates multi-phase workflows with skill execution,
                      dependency management, and phase progress tracking.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* MessageBus Only View */}
        {activeTab === 'messages' && (
          <div className="space-y-8">
            <CommunicationMetrics />
            <MessageBusMonitor />
          </div>
        )}

        {/* Blackboard Only View */}
        {activeTab === 'blackboard' && (
          <div className="space-y-8">
            <CommunicationMetrics />
            <BlackboardViewer />
          </div>
        )}

        {/* Orchestrations Only View */}
        {activeTab === 'orchestrations' && (
          <div className="space-y-8">
            <CommunicationMetrics />
            <OrchestrationTimeline />
          </div>
        )}
      </main>
    </div>
  );
}

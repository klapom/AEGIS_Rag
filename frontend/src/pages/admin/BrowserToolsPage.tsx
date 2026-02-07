/**
 * BrowserToolsPage Component
 * Sprint 104 Feature 104.8: Browser Automation Tools UI
 *
 * Admin page for browser tool management and execution.
 * Integrates with Sprint 103 MCP Browser Backend.
 *
 * Route: /admin/browser-tools
 *
 * Features:
 * - Browser session management (Start/Stop/Status)
 * - Navigate tool (URL navigation with timeout)
 * - Screenshot tool (Full-page PNG capture)
 * - Evaluate JS tool (Execute JavaScript in browser context)
 * - Real-time session monitoring
 * - Error handling and loading states
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Globe, Camera, Code, PlayCircle, StopCircle, AlertCircle } from 'lucide-react';
import { AdminNavigationBar } from '../../components/admin/AdminNavigationBar';

interface BrowserSession {
  status: 'idle' | 'active' | 'error';
  currentUrl?: string;
  screenshot?: string; // base64 PNG
  lastAction?: string;
  executionTime?: number;
  error?: string;
}

interface ExecutionResult {
  success: boolean;
  result?: any;
  execution_time_ms?: number;
  error?: string;
}

/**
 * BrowserToolsPage - Main page for browser automation tools
 *
 * Layout:
 * - Header with back button and session controls
 * - Session status indicator
 * - Three-tool grid (Navigate, Screenshot, Evaluate JS)
 * - Session info panel with current URL, last action, execution time
 * - Screenshot preview panel
 */
export function BrowserToolsPage() {
  const navigate = useNavigate();
  const [session, setSession] = useState<BrowserSession>({ status: 'idle' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Tool-specific state
  const [url, setUrl] = useState('https://example.com');
  const [jsCode, setJsCode] = useState('document.title');
  const [evaluateResult, setEvaluateResult] = useState<string>('');

  /**
   * Start browser session (simulated - actual session managed by backend)
   */
  const handleStart = () => {
    setSession({
      status: 'active',
      currentUrl: 'about:blank',
      lastAction: 'Browser session started',
    });
    setError(null);
  };

  /**
   * Stop browser session (simulated - actual cleanup on backend)
   */
  const handleStop = () => {
    setSession({ status: 'idle' });
    setError(null);
    setEvaluateResult('');
  };

  /**
   * Navigate Tool - Navigate to specified URL
   */
  const handleNavigate = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/api/v1/mcp/tools/browser_navigate/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parameters: {
            url,
            timeout: 30000,
          },
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const result: ExecutionResult = await response.json();

      if (result.success) {
        setSession({
          status: 'active',
          currentUrl: result.result.url || url,
          lastAction: `Navigated to ${url}`,
          executionTime: result.execution_time_ms,
        });
      } else {
        throw new Error(result.error || 'Navigation failed');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Navigation failed';
      setError(errorMsg);
      setSession((prev) => ({ ...prev, status: 'error', error: errorMsg }));
    } finally {
      setLoading(false);
    }
  };

  /**
   * Screenshot Tool - Capture full-page screenshot
   */
  const handleScreenshot = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/api/v1/mcp/tools/browser_screenshot/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parameters: {
            fullPage: true,
            type: 'png',
          },
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const result: ExecutionResult = await response.json();

      if (result.success && result.result?.screenshot) {
        setSession((prev) => ({
          ...prev,
          status: 'active',
          screenshot: result.result.screenshot,
          lastAction: 'Screenshot captured',
          executionTime: result.execution_time_ms,
        }));
      } else {
        throw new Error(result.error || 'Screenshot capture failed');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Screenshot failed';
      setError(errorMsg);
      setSession((prev) => ({ ...prev, status: 'error', error: errorMsg }));
    } finally {
      setLoading(false);
    }
  };

  /**
   * Evaluate JS Tool - Execute JavaScript in browser context
   */
  const handleEvaluate = async () => {
    setLoading(true);
    setError(null);
    setEvaluateResult('');

    try {
      const response = await fetch('http://localhost:8000/api/v1/mcp/tools/browser_evaluate/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parameters: {
            function: `() => { return ${jsCode}; }`,
          },
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const result: ExecutionResult = await response.json();

      if (result.success) {
        const resultString = typeof result.result === 'object'
          ? JSON.stringify(result.result, null, 2)
          : String(result.result);

        setEvaluateResult(resultString);
        setSession((prev) => ({
          ...prev,
          status: 'active',
          lastAction: 'JavaScript executed',
          executionTime: result.execution_time_ms,
        }));
      } else {
        throw new Error(result.error || 'JavaScript execution failed');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Evaluation failed';
      setError(errorMsg);
      setEvaluateResult(`Error: ${errorMsg}`);
      setSession((prev) => ({ ...prev, status: 'error', error: errorMsg }));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen bg-gray-50 dark:bg-gray-900"
      data-testid="browser-tools-page"
    >
      <div className="max-w-7xl mx-auto py-8 px-6 space-y-6">
        {/* Admin Navigation */}
        <div className="mb-4">
          <AdminNavigationBar />
        </div>

        {/* Header */}
        <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
          </div>

          {/* Session Controls */}
          <div className="flex items-center gap-3">
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-800"
              data-testid="browser-session-status"
            >
              <div
                className={`w-2.5 h-2.5 rounded-full ${
                  session.status === 'active'
                    ? 'bg-green-500'
                    : session.status === 'error'
                    ? 'bg-red-500'
                    : 'bg-gray-400'
                }`}
              />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">
                {session.status}
              </span>
            </div>

            {session.status === 'idle' ? (
              <button
                onClick={handleStart}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="browser-start-btn"
                disabled={loading}
              >
                <PlayCircle className="w-4 h-4" />
                Start Browser
              </button>
            ) : (
              <button
                onClick={handleStop}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="browser-stop-btn"
                disabled={loading}
              >
                <StopCircle className="w-4 h-4" />
                Stop Browser
              </button>
            )}
          </div>
        </header>

        {/* Page Title and Description */}
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/50 rounded-xl flex items-center justify-center">
              <Globe className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                Browser Tools
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Automate browser actions with Playwright integration
              </p>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div
            className="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-xl p-4"
            data-testid="browser-error"
          >
            <div className="flex gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
              <div>
                <h4 className="font-semibold text-red-900 dark:text-red-100">
                  Error
                </h4>
                <p className="text-sm text-red-800 dark:text-red-200">
                  {error}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Tools Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Navigate Tool */}
          <div
            className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-6 space-y-4"
            data-testid="browser-tool-navigate"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/50 rounded-lg flex items-center justify-center">
                <Globe className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Navigate
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Navigate to a URL
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <label
                  htmlFor="navigate-url"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  URL
                </label>
                <input
                  id="navigate-url"
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="w-full px-3 py-2 border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="https://example.com"
                  data-testid="navigate-url-input"
                  disabled={session.status !== 'active' || loading}
                />
              </div>

              <button
                onClick={handleNavigate}
                className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="navigate-execute-btn"
                disabled={session.status !== 'active' || loading}
              >
                {loading ? 'Navigating...' : 'Navigate'}
              </button>
            </div>
          </div>

          {/* Screenshot Tool */}
          <div
            className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-6 space-y-4"
            data-testid="browser-tool-screenshot"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-100 dark:bg-green-900/50 rounded-lg flex items-center justify-center">
                <Camera className="w-5 h-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Screenshot
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Capture full-page screenshot
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Captures a full-page PNG screenshot of the current browser page.
              </p>

              <button
                onClick={handleScreenshot}
                className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="screenshot-execute-btn"
                disabled={session.status !== 'active' || loading}
              >
                {loading ? 'Capturing...' : 'Take Screenshot'}
              </button>
            </div>
          </div>

          {/* Evaluate JS Tool */}
          <div
            className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-6 space-y-4 md:col-span-2"
            data-testid="browser-tool-evaluate"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/50 rounded-lg flex items-center justify-center">
                <Code className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Evaluate JavaScript
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Execute JavaScript code in browser context
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <label
                  htmlFor="evaluate-js"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  JavaScript Expression
                </label>
                <textarea
                  id="evaluate-js"
                  value={jsCode}
                  onChange={(e) => setJsCode(e.target.value)}
                  className="w-full px-3 py-2 border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono text-sm"
                  placeholder="document.title"
                  rows={3}
                  data-testid="evaluate-js-input"
                  disabled={session.status !== 'active' || loading}
                />
              </div>

              <button
                onClick={handleEvaluate}
                className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="evaluate-execute-btn"
                disabled={session.status !== 'active' || loading}
              >
                {loading ? 'Executing...' : 'Execute JavaScript'}
              </button>

              {evaluateResult && (
                <div className="mt-4 p-3 bg-gray-100 dark:bg-gray-900 rounded-lg">
                  <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    Result:
                  </h4>
                  <pre className="text-sm text-gray-900 dark:text-gray-100 font-mono whitespace-pre-wrap">
                    {evaluateResult}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Session Info Panel */}
        {session.status === 'active' && (
          <div
            className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-6 space-y-4"
            data-testid="browser-session-info"
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Session Info
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                  Current URL
                </p>
                <p
                  className="text-sm font-mono text-gray-900 dark:text-gray-100 break-all"
                  data-testid="session-current-url"
                >
                  {session.currentUrl || 'N/A'}
                </p>
              </div>

              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                  Last Action
                </p>
                <p
                  className="text-sm text-gray-900 dark:text-gray-100"
                  data-testid="session-last-action"
                >
                  {session.lastAction || 'N/A'}
                </p>
              </div>

              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                  Execution Time
                </p>
                <p
                  className="text-sm text-gray-900 dark:text-gray-100"
                  data-testid="session-execution-time"
                >
                  {session.executionTime ? `${session.executionTime}ms` : 'N/A'}
                </p>
              </div>
            </div>

            {/* Screenshot Preview */}
            {session.screenshot && (
              <div className="mt-6 space-y-3">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                  Screenshot Preview
                </h4>
                <img
                  src={`data:image/png;base64,${session.screenshot}`}
                  alt="Browser screenshot"
                  className="w-full rounded-lg border-2 border-gray-200 dark:border-gray-700 shadow-md"
                  data-testid="browser-screenshot-image"
                />
              </div>
            )}
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
                About Browser Tools
              </h4>
              <p className="text-sm text-blue-800 dark:text-blue-200">
                Browser automation tools allow you to programmatically control a headless browser
                using Playwright. Navigate to web pages, capture screenshots, and execute JavaScript
                code in the browser context for testing, web scraping, and automation tasks.
              </p>
              <ul className="mt-3 space-y-1 text-sm text-blue-800 dark:text-blue-200">
                <li className="flex items-start gap-2">
                  <svg
                    className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span>Start a browser session to enable tool execution</span>
                </li>
                <li className="flex items-start gap-2">
                  <svg
                    className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span>Navigate to URLs with automatic timeout handling</span>
                </li>
                <li className="flex items-start gap-2">
                  <svg
                    className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span>Capture full-page screenshots for visual verification</span>
                </li>
                <li className="flex items-start gap-2">
                  <svg
                    className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span>Execute custom JavaScript to interact with page elements</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default BrowserToolsPage;

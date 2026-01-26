/**
 * MCP Custom Server Form Component
 * Sprint 120: Allow users to add MCP servers manually via JSON paste or form input.
 * Calls POST /api/v1/mcp/registry/custom endpoint.
 */

import React, { useState } from 'react';
import { Plus, Code, FormInput, Check, AlertCircle, Loader2, ExternalLink } from 'lucide-react';

interface CustomServerFormData {
  name: string;
  transport: 'stdio' | 'http';
  command: string;
  args: string;
  url: string;
  description: string;
  auto_connect: boolean;
}

interface MCPCustomServerFormProps {
  onServerAdded?: () => void;
}

type InputMode = 'form' | 'json';

export const MCPCustomServerForm: React.FC<MCPCustomServerFormProps> = ({ onServerAdded }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [inputMode, setInputMode] = useState<InputMode>('json');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ status: 'success' | 'error'; message: string } | null>(null);

  // JSON mode
  const [jsonInput, setJsonInput] = useState('');

  // Form mode
  const [formData, setFormData] = useState<CustomServerFormData>({
    name: '',
    transport: 'stdio',
    command: '',
    args: '',
    url: '',
    description: '',
    auto_connect: true,
  });

  const resetForm = () => {
    setJsonInput('');
    setFormData({
      name: '',
      transport: 'stdio',
      command: '',
      args: '',
      url: '',
      description: '',
      auto_connect: true,
    });
    setResult(null);
  };

  const parseJsonInput = (): Partial<CustomServerFormData> | null => {
    try {
      const parsed = JSON.parse(jsonInput);

      // Support PulseMCP server.json format
      const name = parsed.name || parsed.title || '';
      const description = parsed.description || parsed.short_description || '';
      const repoUrl = parsed.repository?.url || parsed.source_code_url || '';

      // Try to detect transport and command from common patterns
      let transport: 'stdio' | 'http' = 'stdio';
      let command = '';
      let args = '';
      let url = '';

      // Check for explicit transport config
      if (parsed.transport === 'http' || parsed.url) {
        transport = 'http';
        url = parsed.url || '';
      } else if (parsed.command) {
        command = parsed.command;
        args = Array.isArray(parsed.args) ? parsed.args.join(' ') : (parsed.args || '');
      } else if (parsed.package_name) {
        // PulseMCP format: has package_name like "mcp-filesystem-server"
        command = 'npx';
        args = `-y ${parsed.package_name}`;
      } else if (repoUrl && repoUrl.includes('github.com')) {
        // GitHub repo: suggest npx with package name derived from repo
        const repoName = repoUrl.split('/').pop()?.replace('.git', '') || '';
        command = repoUrl;
        args = '';
        // Leave for user to fill in
      }

      return {
        name: name.replace(/^com\.pulsemcp\.\w+\//, ''), // Strip PulseMCP prefix
        transport,
        command,
        args,
        url,
        description,
        auto_connect: true,
      };
    } catch {
      return null;
    }
  };

  const handleJsonParse = () => {
    const parsed = parseJsonInput();
    if (parsed) {
      setFormData((prev) => ({
        ...prev,
        ...parsed,
        name: parsed.name || prev.name,
        transport: parsed.transport || prev.transport,
      }));
      setInputMode('form');
      setResult({ status: 'success', message: 'JSON parsed! Please review and fill in missing fields.' });
    } else {
      setResult({ status: 'error', message: 'Invalid JSON. Please check format and try again.' });
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    setResult(null);

    try {
      const token = localStorage.getItem('token');
      const payload: Record<string, unknown> = {
        name: formData.name,
        transport: formData.transport,
        description: formData.description,
        auto_connect: formData.auto_connect,
      };

      if (formData.transport === 'stdio') {
        payload.command = formData.command;
        payload.args = formData.args.split(/\s+/).filter(Boolean);
      } else {
        payload.url = formData.url;
      }

      const response = await fetch('/api/v1/mcp/registry/custom', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error?.message || data.detail || 'Failed to add server');
      }

      const toolCount = data.tools?.length || 0;
      setResult({
        status: 'success',
        message: `Server "${formData.name}" added successfully! ${toolCount > 0 ? `${toolCount} tools discovered.` : 'Click "Connect Servers" to discover tools.'}`,
      });

      if (onServerAdded) {
        onServerAdded();
      }
    } catch (err) {
      setResult({
        status: 'error',
        message: err instanceof Error ? err.message : 'Failed to add server',
      });
    } finally {
      setLoading(false);
    }
  };

  const isFormValid = () => {
    if (!formData.name.trim()) return false;
    if (formData.transport === 'stdio' && !formData.command.trim()) return false;
    if (formData.transport === 'http' && !formData.url.trim()) return false;
    return true;
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => { setIsOpen(true); resetForm(); }}
        className="w-full flex items-center justify-center gap-2 p-4 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
        data-testid="add-custom-server-button"
      >
        <Plus className="h-5 w-5" />
        Add Custom Server (paste JSON or enter manually)
      </button>
    );
  }

  return (
    <div className="border border-gray-200 rounded-lg bg-white shadow-sm" data-testid="custom-server-form">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <h3 className="font-semibold text-gray-900">Add Custom MCP Server</h3>
        <button
          onClick={() => { setIsOpen(false); resetForm(); }}
          className="text-gray-400 hover:text-gray-600 text-xl leading-none"
        >
          ×
        </button>
      </div>

      {/* Input Mode Tabs */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setInputMode('json')}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
            inputMode === 'json'
              ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
              : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
          }`}
          data-testid="json-mode-tab"
        >
          <Code className="h-4 w-4" />
          Paste JSON
        </button>
        <button
          onClick={() => setInputMode('form')}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
            inputMode === 'form'
              ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
              : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
          }`}
          data-testid="form-mode-tab"
        >
          <FormInput className="h-4 w-4" />
          Manual Input
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* JSON Input Mode */}
        {inputMode === 'json' && (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Server JSON (from PulseMCP, GitHub, or registry)
              </label>
              <textarea
                value={jsonInput}
                onChange={(e) => setJsonInput(e.target.value)}
                placeholder={`Paste the server JSON here, e.g.:\n{\n  "name": "mcp-filesystem-server",\n  "description": "Read, write, and manipulate local files",\n  "repository": {\n    "url": "https://github.com/mark3labs/mcp-filesystem-server"\n  }\n}`}
                rows={8}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                data-testid="json-input"
              />
            </div>
            <button
              onClick={handleJsonParse}
              disabled={!jsonInput.trim()}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="parse-json-button"
            >
              Parse JSON → Fill Form
            </button>
          </>
        )}

        {/* Form Input Mode */}
        {inputMode === 'form' && (
          <>
            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Server Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData((p) => ({ ...p, name: e.target.value }))}
                placeholder="e.g. filesystem-tools"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                data-testid="server-name-input"
              />
            </div>

            {/* Transport */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Transport</label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="transport"
                    value="stdio"
                    checked={formData.transport === 'stdio'}
                    onChange={() => setFormData((p) => ({ ...p, transport: 'stdio' }))}
                    data-testid="transport-stdio"
                  />
                  <span className="text-sm">stdio (local binary)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="transport"
                    value="http"
                    checked={formData.transport === 'http'}
                    onChange={() => setFormData((p) => ({ ...p, transport: 'http' }))}
                    data-testid="transport-http"
                  />
                  <span className="text-sm">HTTP (remote endpoint)</span>
                </label>
              </div>
            </div>

            {/* stdio fields */}
            {formData.transport === 'stdio' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Command <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.command}
                    onChange={(e) => setFormData((p) => ({ ...p, command: e.target.value }))}
                    placeholder="e.g. npx, mcp-filesystem-server, /usr/local/bin/..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    data-testid="command-input"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Arguments (space-separated)
                  </label>
                  <input
                    type="text"
                    value={formData.args}
                    onChange={(e) => setFormData((p) => ({ ...p, args: e.target.value }))}
                    placeholder="e.g. -y mcp-filesystem-server /path/to/allowed/dir"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    data-testid="args-input"
                  />
                </div>
              </>
            )}

            {/* http fields */}
            {formData.transport === 'http' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Server URL <span className="text-red-500">*</span>
                </label>
                <input
                  type="url"
                  value={formData.url}
                  onChange={(e) => setFormData((p) => ({ ...p, url: e.target.value }))}
                  placeholder="e.g. http://localhost:3000/mcp"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  data-testid="url-input"
                />
              </div>
            )}

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData((p) => ({ ...p, description: e.target.value }))}
                placeholder="What does this server do?"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                data-testid="description-input"
              />
            </div>

            {/* Auto-connect */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.auto_connect}
                onChange={(e) => setFormData((p) => ({ ...p, auto_connect: e.target.checked }))}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                data-testid="auto-connect-checkbox"
              />
              <span className="text-sm text-gray-700">
                Auto-connect on startup and discover tools now
              </span>
            </label>

            {/* Submit */}
            <button
              onClick={handleSubmit}
              disabled={!isFormValid() || loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="add-server-button"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Adding Server...
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4" />
                  Add Server
                </>
              )}
            </button>
          </>
        )}

        {/* Result Message */}
        {result && (
          <div
            className={`flex items-start gap-2 p-3 rounded-lg ${
              result.status === 'success'
                ? 'bg-green-50 border border-green-200 text-green-800'
                : 'bg-red-50 border border-red-200 text-red-800'
            }`}
            data-testid="result-message"
          >
            {result.status === 'success' ? (
              <Check className="h-5 w-5 mt-0.5 flex-shrink-0" />
            ) : (
              <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
            )}
            <span className="text-sm">{result.message}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default MCPCustomServerForm;

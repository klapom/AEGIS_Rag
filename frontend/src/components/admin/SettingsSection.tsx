/**
 * SettingsSection Component
 * Sprint 46 Feature 46.8: Admin Area Consolidation
 *
 * Compact settings overview section for the admin dashboard.
 * Shows current LLM and embedding model configuration with quick navigation.
 */

import { useEffect, useState, useCallback } from 'react';
import { Settings, Cpu, Database, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { AdminSection } from './AdminSection';
import { getSystemStats } from '../../api/admin';
import type { SystemStats } from '../../types/admin';

// Storage key for LLM config (must match AdminLLMConfigPage)
const LLM_CONFIG_KEY = 'aegis-rag-llm-config';

interface LLMConfig {
  useCase: string;
  modelId: string;
  enabled: boolean;
}

/**
 * Get the primary LLM model from stored config
 */
function getPrimaryLLMModel(): string {
  try {
    const stored = localStorage.getItem(LLM_CONFIG_KEY);
    if (stored) {
      const config: LLMConfig[] = JSON.parse(stored);
      // Find the answer_generation use case as "primary"
      const answerGen = config.find((c) => c.useCase === 'answer_generation');
      if (answerGen) {
        // Extract model name from ID (e.g., "ollama/qwen3:32b" -> "qwen3:32b")
        const parts = answerGen.modelId.split('/');
        return parts.length > 1 ? parts[1] : answerGen.modelId;
      }
    }
  } catch (e) {
    console.error('Failed to read LLM config:', e);
  }
  return 'qwen3:8b'; // Default fallback
}

/**
 * Setting row component
 */
interface SettingRowProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  onClick?: () => void;
}

function SettingRow({ icon, label, value, onClick }: SettingRowProps) {
  const content = (
    <>
      <div className="flex items-center gap-2 text-sm">
        <span className="text-gray-400 dark:text-gray-500">{icon}</span>
        <span className="text-gray-600 dark:text-gray-400">{label}:</span>
        <span className="font-medium text-gray-900 dark:text-gray-100">{value}</span>
      </div>
      {onClick && (
        <ExternalLink
          className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity"
          aria-hidden="true"
        />
      )}
    </>
  );

  if (onClick) {
    return (
      <div
        className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors group"
        onClick={onClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onClick();
          }
        }}
        data-testid={`setting-row-${label.toLowerCase().replace(/\s+/g, '-')}`}
      >
        {content}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between py-2 px-3">
      {content}
    </div>
  );
}

/**
 * Configure Button
 */
interface ConfigureButtonProps {
  onClick: () => void;
}

function ConfigureButton({ onClick }: ConfigureButtonProps) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
      data-testid="configure-settings-button"
    >
      <Settings className="w-4 h-4" />
      <span>Configure</span>
    </button>
  );
}

/**
 * SettingsSection - Compact settings overview for admin dashboard
 */
export function SettingsSection() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [llmModel, setLlmModel] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch system stats and LLM config on mount
  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getSystemStats();
        setStats(data);
        setLlmModel(getPrimaryLLMModel());
      } catch (err) {
        console.error('Failed to fetch system stats:', err);
        setError(err instanceof Error ? err.message : 'Failed to load settings');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleConfigureClick = useCallback(() => {
    navigate('/admin/llm-config');
  }, [navigate]);

  const handleLLMClick = useCallback(() => {
    navigate('/admin/llm-config');
  }, [navigate]);

  const handleGraphClick = useCallback(() => {
    navigate('/admin/graph');
  }, [navigate]);

  // Extract embedding model name (e.g., "bge-m3" from full path)
  const embeddingModel = stats?.embedding_model
    ? stats.embedding_model.split('/').pop() || stats.embedding_model
    : 'BGE-M3';

  return (
    <AdminSection
      title="Settings"
      icon={<Settings className="w-5 h-5" />}
      action={<ConfigureButton onClick={handleConfigureClick} />}
      defaultExpanded={true}
      testId="admin-settings-section"
      isLoading={isLoading}
      error={error}
    >
      <div className="space-y-1">
        <SettingRow
          icon={<Cpu className="w-4 h-4" />}
          label="LLM"
          value={llmModel}
          onClick={handleLLMClick}
        />
        <SettingRow
          icon={<Database className="w-4 h-4" />}
          label="Embeddings"
          value={embeddingModel}
        />
        {stats && (
          <SettingRow
            icon={<Database className="w-4 h-4" />}
            label="Vector Dim"
            value={String(stats.qdrant_vector_dimension)}
          />
        )}

        {/* Additional Stats */}
        {stats && stats.total_conversations !== null && (
          <div className="pt-2 mt-2 border-t border-gray-200 dark:border-gray-600">
            <SettingRow
              icon={<Database className="w-4 h-4" />}
              label="Conversations"
              value={(stats.total_conversations ?? 0).toLocaleString()}
            />
          </div>
        )}

        {/* Quick Links */}
        <div className="pt-3 mt-3 border-t border-gray-200 dark:border-gray-600 flex gap-2">
          <QuickLink label="Graph Analytics" onClick={handleGraphClick} />
          <QuickLink label="LLM Config" onClick={handleLLMClick} />
        </div>
      </div>
    </AdminSection>
  );
}

/**
 * Quick link button
 */
interface QuickLinkProps {
  label: string;
  onClick: () => void;
}

function QuickLink({ label, onClick }: QuickLinkProps) {
  return (
    <button
      onClick={onClick}
      className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
      data-testid={`quick-link-${label.toLowerCase().replace(/\s+/g, '-')}`}
    >
      {label}
    </button>
  );
}

export default SettingsSection;

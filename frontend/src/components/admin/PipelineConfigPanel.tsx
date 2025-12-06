/**
 * PipelineConfigPanel Component
 * Sprint 37 Feature 37.7: Admin UI for Worker Pool Configuration
 *
 * Provides UI for configuring parallel worker pool settings:
 * - VLM Workers (1-2, GPU-bound)
 * - Embedding Workers (1-4)
 * - Extraction Workers (1-8, LLM calls)
 * - Resource limits and timeouts
 *
 * Features:
 * - Real-time configuration editing
 * - Preset configurations (Conservative, Balanced, Aggressive)
 * - Redis persistence for configuration
 * - Input validation with Pydantic ranges
 */

import React, { useState, useEffect } from "react";
import { WorkerConfigSlider } from "./WorkerConfigSlider";

export interface PipelineConfig {
  // Document Processing
  parallel_documents: number;
  max_queue_size: number;

  // VLM Workers
  vlm_workers: number;
  vlm_batch_size: number;
  vlm_timeout: number;

  // Embedding Workers
  embedding_workers: number;
  embedding_batch_size: number;
  embedding_timeout: number;

  // Extraction Workers
  extraction_workers: number;
  extraction_timeout: number;
  extraction_max_retries: number;

  // Resource Limits
  max_concurrent_llm: number;
  max_vram_mb: number;
}

interface PipelineConfigPanelProps {
  onConfigChange?: (config: PipelineConfig) => void;
}

const DEFAULT_CONFIG: PipelineConfig = {
  parallel_documents: 2,
  max_queue_size: 10,
  vlm_workers: 1,
  vlm_batch_size: 4,
  vlm_timeout: 180,
  embedding_workers: 2,
  embedding_batch_size: 8,
  embedding_timeout: 60,
  extraction_workers: 4,
  extraction_timeout: 120,
  extraction_max_retries: 2,
  max_concurrent_llm: 8,
  max_vram_mb: 5500,
};

type PresetType = "conservative" | "balanced" | "aggressive";

const PRESETS: Record<PresetType, Partial<PipelineConfig>> = {
  conservative: {
    parallel_documents: 1,
    extraction_workers: 2,
    embedding_workers: 1,
    vlm_workers: 1,
    max_concurrent_llm: 4,
    vlm_batch_size: 2,
    embedding_batch_size: 4,
  },
  balanced: {
    parallel_documents: 2,
    extraction_workers: 4,
    embedding_workers: 2,
    vlm_workers: 1,
    max_concurrent_llm: 8,
    vlm_batch_size: 4,
    embedding_batch_size: 8,
  },
  aggressive: {
    parallel_documents: 3,
    extraction_workers: 6,
    embedding_workers: 3,
    vlm_workers: 1,
    max_concurrent_llm: 12,
    vlm_batch_size: 6,
    embedding_batch_size: 16,
  },
};

export const PipelineConfigPanel: React.FC<PipelineConfigPanelProps> = ({
  onConfigChange,
}) => {
  const [config, setConfig] = useState<PipelineConfig>(DEFAULT_CONFIG);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [activePreset, setActivePreset] = useState<PresetType | null>(
    "balanced",
  );

  // Load config on mount
  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/v1/admin/pipeline/config");
      if (response.ok) {
        const data = await response.json();
        setConfig(data);
        detectActivePreset(data);
      } else {
        throw new Error("Failed to load configuration");
      }
    } catch (err) {
      console.error("Load config error:", err);
      setError("Fehler beim Laden der Konfiguration");
      // Use defaults on error
      setConfig(DEFAULT_CONFIG);
    } finally {
      setIsLoading(false);
    }
  };

  const saveConfig = async () => {
    setIsSaving(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const response = await fetch("/api/v1/admin/pipeline/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Save failed");
      }

      const savedConfig = await response.json();
      setConfig(savedConfig);
      setSuccessMessage("Konfiguration erfolgreich gespeichert");
      onConfigChange?.(savedConfig);

      // Auto-hide success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      console.error("Save config error:", err);
      setError(
        err instanceof Error
          ? err.message
          : "Fehler beim Speichern der Konfiguration",
      );
    } finally {
      setIsSaving(false);
    }
  };

  const resetConfig = () => {
    setConfig(DEFAULT_CONFIG);
    setActivePreset("balanced");
    setError(null);
    setSuccessMessage(null);
  };

  const applyPreset = (preset: PresetType) => {
    const presetConfig = { ...DEFAULT_CONFIG, ...PRESETS[preset] };
    setConfig(presetConfig);
    setActivePreset(preset);
    setError(null);
    setSuccessMessage(null);
  };

  const detectActivePreset = (currentConfig: PipelineConfig) => {
    for (const [presetName, presetValues] of Object.entries(PRESETS)) {
      const matches = Object.entries(presetValues).every(
        ([key, value]) => currentConfig[key as keyof PipelineConfig] === value,
      );
      if (matches) {
        setActivePreset(presetName as PresetType);
        return;
      }
    }
    setActivePreset(null); // Custom configuration
  };

  const updateConfigValue = <K extends keyof PipelineConfig>(
    key: K,
    value: PipelineConfig[K],
  ) => {
    const newConfig = { ...config, [key]: value };
    setConfig(newConfig);
    detectActivePreset(newConfig);
  };

  if (isLoading) {
    return (
      <div
        data-testid="config-loading"
        className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 flex items-center justify-center"
      >
        <div className="flex items-center space-x-3">
          <LoadingSpinner />
          <span className="text-gray-600">Lade Konfiguration...</span>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="config-panel-container"
      className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-6"
    >
      {/* Header */}
      <div className="border-b border-gray-200 pb-4">
        <h2 className="text-2xl font-bold text-gray-900">
          Worker Pool Configuration
        </h2>
        <p className="text-sm text-gray-600 mt-1">
          Konfigurieren Sie die parallelen Worker-Pools für optimale Performance
        </p>
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div
          data-testid="config-error"
          className="flex items-center space-x-2 p-4 bg-red-50 border border-red-200 rounded-lg"
        >
          <ErrorIcon />
          <span className="text-sm font-medium text-red-800">{error}</span>
        </div>
      )}

      {successMessage && (
        <div
          data-testid="config-success"
          className="flex items-center space-x-2 p-4 bg-green-50 border border-green-200 rounded-lg"
        >
          <SuccessIcon />
          <span className="text-sm font-medium text-green-800">
            {successMessage}
          </span>
        </div>
      )}

      {/* Preset Buttons */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700">
          Quick Presets
        </label>
        <div className="flex space-x-3">
          <PresetButton
            label="Conservative"
            description="Minimal resources, stable"
            isActive={activePreset === "conservative"}
            onClick={() => applyPreset("conservative")}
            testId="preset-conservative"
          />
          <PresetButton
            label="Balanced"
            description="Default, recommended"
            isActive={activePreset === "balanced"}
            onClick={() => applyPreset("balanced")}
            testId="preset-balanced"
          />
          <PresetButton
            label="Aggressive"
            description="Maximum performance"
            isActive={activePreset === "aggressive"}
            onClick={() => applyPreset("aggressive")}
            testId="preset-aggressive"
          />
        </div>
      </div>

      {/* Configuration Sections */}
      <div className="space-y-6">
        {/* Document Processing */}
        <ConfigSection title="Document Processing">
          <WorkerConfigSlider
            label="Parallel Documents"
            value={config.parallel_documents}
            min={1}
            max={4}
            description="Number of documents to process in parallel"
            onChange={(value) => updateConfigValue("parallel_documents", value)}
            testId="config-parallel-documents"
          />
          <WorkerConfigSlider
            label="Max Queue Size"
            value={config.max_queue_size}
            min={5}
            max={50}
            description="Maximum number of chunks in processing queue"
            onChange={(value) => updateConfigValue("max_queue_size", value)}
            testId="config-max-queue-size"
          />
        </ConfigSection>

        {/* VLM Workers */}
        <ConfigSection title="VLM Workers (GPU-bound)">
          <WorkerConfigSlider
            label="VLM Workers"
            value={config.vlm_workers}
            min={1}
            max={2}
            description="Number of parallel VLM workers (GPU memory limited)"
            onChange={(value) => updateConfigValue("vlm_workers", value)}
            testId="config-vlm-workers"
          />
          <WorkerConfigSlider
            label="VLM Batch Size"
            value={config.vlm_batch_size}
            min={1}
            max={8}
            description="Number of images processed per batch"
            onChange={(value) => updateConfigValue("vlm_batch_size", value)}
            testId="config-vlm-batch-size"
          />
          <WorkerConfigSlider
            label="VLM Timeout"
            value={config.vlm_timeout}
            min={60}
            max={300}
            unit="s"
            description="Timeout for VLM processing per image"
            onChange={(value) => updateConfigValue("vlm_timeout", value)}
            testId="config-vlm-timeout"
          />
        </ConfigSection>

        {/* Embedding Workers */}
        <ConfigSection title="Embedding Workers">
          <WorkerConfigSlider
            label="Embedding Workers"
            value={config.embedding_workers}
            min={1}
            max={4}
            description="Number of parallel embedding workers"
            onChange={(value) => updateConfigValue("embedding_workers", value)}
            testId="config-embedding-workers"
          />
          <WorkerConfigSlider
            label="Embedding Batch Size"
            value={config.embedding_batch_size}
            min={4}
            max={32}
            description="Number of chunks embedded per batch"
            onChange={(value) =>
              updateConfigValue("embedding_batch_size", value)
            }
            testId="config-embedding-batch-size"
          />
          <WorkerConfigSlider
            label="Embedding Timeout"
            value={config.embedding_timeout}
            min={30}
            max={120}
            unit="s"
            description="Timeout for embedding generation"
            onChange={(value) => updateConfigValue("embedding_timeout", value)}
            testId="config-embedding-timeout"
          />
        </ConfigSection>

        {/* Extraction Workers */}
        <ConfigSection title="Extraction Workers (LLM calls)">
          <WorkerConfigSlider
            label="Extraction Workers"
            value={config.extraction_workers}
            min={1}
            max={8}
            description="Number of parallel entity/relation extraction workers"
            onChange={(value) => updateConfigValue("extraction_workers", value)}
            testId="config-extraction-workers"
          />
          <WorkerConfigSlider
            label="Extraction Timeout"
            value={config.extraction_timeout}
            min={60}
            max={300}
            unit="s"
            description="Timeout for LLM extraction calls"
            onChange={(value) => updateConfigValue("extraction_timeout", value)}
            testId="config-extraction-timeout"
          />
          <WorkerConfigSlider
            label="Extraction Retries"
            value={config.extraction_max_retries}
            min={0}
            max={3}
            description="Maximum retry attempts for failed extractions"
            onChange={(value) =>
              updateConfigValue("extraction_max_retries", value)
            }
            testId="config-extraction-retries"
          />
        </ConfigSection>

        {/* Resource Limits */}
        <ConfigSection title="Resource Limits">
          <WorkerConfigSlider
            label="Max Concurrent LLM Calls"
            value={config.max_concurrent_llm}
            min={4}
            max={16}
            description="Global limit for concurrent LLM API calls"
            onChange={(value) => updateConfigValue("max_concurrent_llm", value)}
            testId="config-max-concurrent-llm"
          />
          <WorkerConfigSlider
            label="Max VRAM Usage"
            value={config.max_vram_mb}
            min={4000}
            max={8000}
            unit="MB"
            description="Maximum VRAM allocation for VLM workers"
            onChange={(value) => updateConfigValue("max_vram_mb", value)}
            testId="config-max-vram"
          />
        </ConfigSection>
      </div>

      {/* Action Buttons */}
      <div className="flex space-x-4 pt-4 border-t border-gray-200">
        <button
          data-testid="config-save-button"
          onClick={saveConfig}
          disabled={isSaving}
          className="
            flex-1 px-6 py-3 rounded-lg font-semibold
            bg-blue-600 text-white
            hover:bg-blue-700
            disabled:bg-gray-300 disabled:cursor-not-allowed
            transition-all
            flex items-center justify-center space-x-2
          "
        >
          {isSaving ? (
            <>
              <LoadingSpinner />
              <span>Speichern...</span>
            </>
          ) : (
            <span>Konfiguration speichern</span>
          )}
        </button>

        <button
          data-testid="config-reset-button"
          onClick={resetConfig}
          disabled={isSaving}
          className="
            px-6 py-3 rounded-lg font-semibold
            bg-gray-100 text-gray-700
            hover:bg-gray-200
            disabled:opacity-50 disabled:cursor-not-allowed
            transition-all
          "
        >
          Zurücksetzen
        </button>
      </div>
    </div>
  );
};

// ============================================================================
// Utility Components
// ============================================================================

interface ConfigSectionProps {
  title: string;
  children: React.ReactNode;
}

function ConfigSection({ title, children }: ConfigSectionProps) {
  return (
    <div className="bg-gray-50 rounded-lg p-4 space-y-4">
      <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
        {title}
      </h3>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

interface PresetButtonProps {
  label: string;
  description: string;
  isActive: boolean;
  onClick: () => void;
  testId: string;
}

function PresetButton({
  label,
  description,
  isActive,
  onClick,
  testId,
}: PresetButtonProps) {
  return (
    <button
      data-testid={testId}
      onClick={onClick}
      className={`
        flex-1 p-4 rounded-lg border-2 transition-all
        ${
          isActive
            ? "border-blue-600 bg-blue-50"
            : "border-gray-300 bg-white hover:border-blue-400"
        }
      `}
    >
      <div className="font-semibold text-gray-900">{label}</div>
      <div className="text-xs text-gray-600 mt-1">{description}</div>
    </button>
  );
}

function LoadingSpinner() {
  return (
    <svg
      className="w-5 h-5 animate-spin"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

function SuccessIcon() {
  return (
    <svg
      className="w-5 h-5 text-green-600 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 13l4 4L19 7"
      />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg
      className="w-5 h-5 text-red-600 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

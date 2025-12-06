/**
 * PipelineConfigPanel Component Tests
 * Sprint 37 Feature 37.7: Admin UI for Worker Pool Configuration
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PipelineConfigPanel } from './PipelineConfigPanel';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

const mockConfig = {
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

describe('PipelineConfigPanel', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('shows loading state initially', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockConfig,
      });

      render(<PipelineConfigPanel />);

      expect(screen.getByTestId('config-loading')).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.queryByTestId('config-loading')).not.toBeInTheDocument();
      });
    });

    it('loads and displays configuration', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockConfig,
      });

      render(<PipelineConfigPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('config-panel-container')).toBeInTheDocument();
      });

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/admin/pipeline/config');
    });

    it('displays all configuration sections', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockConfig,
      });

      render(<PipelineConfigPanel />);

      await waitFor(() => {
        // Check that all section titles are rendered (checking for section headers, not slider labels)
        expect(screen.getByTestId('config-panel-container')).toBeInTheDocument();
      });

      // Verify specific configuration sliders are present
      expect(screen.getByTestId('config-parallel-documents')).toBeInTheDocument();
      expect(screen.getByTestId('config-vlm-workers')).toBeInTheDocument();
      expect(screen.getByTestId('config-embedding-workers')).toBeInTheDocument();
      expect(screen.getByTestId('config-extraction-workers')).toBeInTheDocument();
      expect(screen.getByTestId('config-max-concurrent-llm')).toBeInTheDocument();
      expect(screen.getByTestId('config-max-vram')).toBeInTheDocument();
    });

    it('displays all preset buttons', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockConfig,
      });

      render(<PipelineConfigPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('preset-conservative')).toBeInTheDocument();
        expect(screen.getByTestId('preset-balanced')).toBeInTheDocument();
        expect(screen.getByTestId('preset-aggressive')).toBeInTheDocument();
      });
    });

    it('renders all required data-testid attributes', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockConfig,
      });

      render(<PipelineConfigPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('config-panel-container')).toBeInTheDocument();
        expect(screen.getByTestId('config-parallel-documents')).toBeInTheDocument();
        expect(screen.getByTestId('config-vlm-workers')).toBeInTheDocument();
        expect(screen.getByTestId('config-embedding-workers')).toBeInTheDocument();
        expect(screen.getByTestId('config-extraction-workers')).toBeInTheDocument();
        expect(screen.getByTestId('config-max-concurrent-llm')).toBeInTheDocument();
        expect(screen.getByTestId('config-max-vram')).toBeInTheDocument();
        expect(screen.getByTestId('config-save-button')).toBeInTheDocument();
        expect(screen.getByTestId('config-reset-button')).toBeInTheDocument();
      });
    });
  });

  describe('Presets', () => {
    it('applies conservative preset when clicked', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockConfig,
      });

      render(<PipelineConfigPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('preset-conservative')).toBeInTheDocument();
      });

      const conservativeButton = screen.getByTestId('preset-conservative');
      fireEvent.click(conservativeButton);

      // Conservative preset should set parallel_documents to 1
      // We can't directly check the state, but we can verify the button is highlighted
      expect(conservativeButton).toHaveClass('border-blue-600');
    });

    it('applies balanced preset when clicked', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockConfig,
      });

      render(<PipelineConfigPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('preset-balanced')).toBeInTheDocument();
      });

      const balancedButton = screen.getByTestId('preset-balanced');
      fireEvent.click(balancedButton);

      expect(balancedButton).toHaveClass('border-blue-600');
    });

    it('applies aggressive preset when clicked', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockConfig,
      });

      render(<PipelineConfigPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('preset-aggressive')).toBeInTheDocument();
      });

      const aggressiveButton = screen.getByTestId('preset-aggressive');
      fireEvent.click(aggressiveButton);

      expect(aggressiveButton).toHaveClass('border-blue-600');
    });
  });

  describe('Configuration Management', () => {
    it('saves configuration when save button clicked', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockConfig,
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockConfig,
        });

      render(<PipelineConfigPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('config-save-button')).toBeInTheDocument();
      });

      const saveButton = screen.getByTestId('config-save-button');
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/v1/admin/pipeline/config',
          expect.objectContaining({
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
          })
        );
      });
    });

    it('shows success message after successful save', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockConfig,
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockConfig,
        });

      render(<PipelineConfigPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('config-save-button')).toBeInTheDocument();
      });

      const saveButton = screen.getByTestId('config-save-button');
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByTestId('config-success')).toBeInTheDocument();
        expect(screen.getByText(/erfolgreich gespeichert/i)).toBeInTheDocument();
      });
    });

    it('shows error message on save failure', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockConfig,
        })
        .mockRejectedValueOnce(new Error('Network error'));

      render(<PipelineConfigPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('config-save-button')).toBeInTheDocument();
      });

      const saveButton = screen.getByTestId('config-save-button');
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByTestId('config-error')).toBeInTheDocument();
      });
    });

    it('resets configuration to defaults when reset clicked', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          ...mockConfig,
          parallel_documents: 3,
        }),
      });

      render(<PipelineConfigPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('config-reset-button')).toBeInTheDocument();
      });

      const resetButton = screen.getByTestId('config-reset-button');
      fireEvent.click(resetButton);

      // After reset, balanced preset should be active
      const balancedButton = screen.getByTestId('preset-balanced');
      expect(balancedButton).toHaveClass('border-blue-600');
    });
  });

  describe('Error Handling', () => {
    it('shows error message when initial load fails', async () => {
      mockFetch.mockRejectedValue(new Error('Failed to load'));

      render(<PipelineConfigPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('config-error')).toBeInTheDocument();
      });
    });

    it('uses default config when load fails', async () => {
      mockFetch.mockRejectedValue(new Error('Failed to load'));

      render(<PipelineConfigPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('config-panel-container')).toBeInTheDocument();
      });

      // Should still render the panel with defaults
      expect(screen.getByTestId('config-save-button')).toBeInTheDocument();
    });
  });

  describe('Callback Integration', () => {
    it('calls onConfigChange callback when config is saved', async () => {
      const onConfigChange = vi.fn();

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockConfig,
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockConfig,
        });

      render(<PipelineConfigPanel onConfigChange={onConfigChange} />);

      await waitFor(() => {
        expect(screen.getByTestId('config-save-button')).toBeInTheDocument();
      });

      const saveButton = screen.getByTestId('config-save-button');
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(onConfigChange).toHaveBeenCalledWith(mockConfig);
      });
    });
  });
});

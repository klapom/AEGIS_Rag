/**
 * Tests for AdminLLMConfigPage Component
 * Sprint 52 Feature 52.1: Community Summary Model Selection
 *
 * Tests:
 * - Page renders correctly with all sections
 * - Summary model selector is present
 * - Summary model save functionality
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AdminLLMConfigPage } from './AdminLLMConfigPage';

// Mock fetch
global.fetch = vi.fn();

// Helper to render with router
const renderWithRouter = (component: React.ReactNode) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('AdminLLMConfigPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();

    // Mock Ollama models response
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/llm/models')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              models: [
                {
                  name: 'qwen3:32b',
                  size: 20000000000,
                  digest: 'sha256:abc123',
                  modified_at: '2025-12-18T10:00:00Z',
                },
                {
                  name: 'llama3.2:8b',
                  size: 5000000000,
                  digest: 'sha256:def456',
                  modified_at: '2025-12-18T09:00:00Z',
                },
              ],
              ollama_available: true,
              error: null,
            }),
        });
      }

      if (url.includes('/llm/summary-model')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              model_id: 'ollama/qwen3:32b',
              updated_at: '2025-12-18T10:30:00Z',
            }),
        });
      }

      return Promise.reject(new Error('Unknown URL'));
    });
  });

  it('renders the page with correct title', async () => {
    renderWithRouter(<AdminLLMConfigPage />);

    expect(screen.getByText('LLM Configuration')).toBeInTheDocument();
    expect(screen.getByTestId('llm-config-page')).toBeInTheDocument();
  });

  it('displays all use case selectors', async () => {
    renderWithRouter(<AdminLLMConfigPage />);

    await waitFor(() => {
      expect(screen.getByTestId('usecase-selector-intent_classification')).toBeInTheDocument();
      expect(screen.getByTestId('usecase-selector-entity_extraction')).toBeInTheDocument();
      expect(screen.getByTestId('usecase-selector-answer_generation')).toBeInTheDocument();
      expect(screen.getByTestId('usecase-selector-followup_titles')).toBeInTheDocument();
      expect(screen.getByTestId('usecase-selector-query_decomposition')).toBeInTheDocument();
      expect(screen.getByTestId('usecase-selector-vision_vlm')).toBeInTheDocument();
    });
  });

  it('displays the community summary model section', async () => {
    renderWithRouter(<AdminLLMConfigPage />);

    await waitFor(() => {
      expect(screen.getByText('Graph Community Summary Model')).toBeInTheDocument();
      expect(screen.getByTestId('summary-model-selector')).toBeInTheDocument();
      expect(screen.getByTestId('model-dropdown-community_summary')).toBeInTheDocument();
    });
  });

  it('loads summary model config from backend', async () => {
    renderWithRouter(<AdminLLMConfigPage />);

    await waitFor(() => {
      // Verify the API was called
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/llm/summary-model')
      );
    });
  });

  it('displays save button for summary model', async () => {
    renderWithRouter(<AdminLLMConfigPage />);

    await waitFor(() => {
      const saveButton = screen.getByTestId('save-summary-model-button');
      expect(saveButton).toBeInTheDocument();
      expect(saveButton).toHaveTextContent('Save Summary Model');
    });
  });

  it('saves summary model config when save button clicked', async () => {
    // Mock both GET and PUT requests
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string, options?: RequestInit) => {
      if (url.includes('/llm/models')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              models: [
                { name: 'qwen3:32b', size: 20000000000, digest: 'sha256:abc', modified_at: '2025-12-18T10:00:00Z' },
              ],
              ollama_available: true,
              error: null,
            }),
        });
      }

      if (url.includes('/llm/summary-model')) {
        if (options?.method === 'PUT') {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                model_id: 'ollama/qwen3:32b',
                updated_at: '2025-12-18T11:00:00Z',
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              model_id: 'ollama/qwen3:32b',
              updated_at: '2025-12-18T10:30:00Z',
            }),
        });
      }

      return Promise.reject(new Error('Unknown URL'));
    });

    renderWithRouter(<AdminLLMConfigPage />);

    await waitFor(() => {
      expect(screen.getByTestId('save-summary-model-button')).toBeInTheDocument();
    });

    // Click save button
    const saveButton = screen.getByTestId('save-summary-model-button');
    fireEvent.click(saveButton);

    // Verify PUT request was made
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/llm/summary-model'),
        expect.objectContaining({
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
        })
      );
    });
  });

  it('displays success message after saving summary model', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string, options?: RequestInit) => {
      if (url.includes('/llm/models')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              models: [],
              ollama_available: false,
              error: 'Not available',
            }),
        });
      }

      if (url.includes('/llm/summary-model')) {
        if (options?.method === 'PUT') {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                model_id: 'alibaba/qwen-turbo',
                updated_at: '2025-12-18T11:00:00Z',
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              model_id: 'alibaba/qwen-turbo',
              updated_at: null,
            }),
        });
      }

      return Promise.reject(new Error('Unknown URL'));
    });

    renderWithRouter(<AdminLLMConfigPage />);

    await waitFor(() => {
      expect(screen.getByTestId('save-summary-model-button')).toBeInTheDocument();
    });

    // Click save button
    const saveButton = screen.getByTestId('save-summary-model-button');
    fireEvent.click(saveButton);

    // Wait for success message
    await waitFor(() => {
      expect(screen.getByText('Saved!')).toBeInTheDocument();
    });
  });

  it('shows Local badge for Ollama models', async () => {
    renderWithRouter(<AdminLLMConfigPage />);

    await waitFor(() => {
      // Find the summary model section
      const summarySection = screen.getByTestId('summary-model-selector');
      expect(summarySection).toHaveTextContent('Local');
    });
  });

  it('displays last updated timestamp when available', async () => {
    renderWithRouter(<AdminLLMConfigPage />);

    await waitFor(() => {
      // The timestamp should be displayed
      expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
    });
  });
});

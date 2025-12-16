/**
 * SettingsSection Component Tests
 * Sprint 46 Feature 46.8: Admin Area Consolidation
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { SettingsSection } from './SettingsSection';
import * as adminApi from '../../api/admin';
import type { SystemStats } from '../../types/admin';

// Mock the admin API
vi.mock('../../api/admin', () => ({
  getSystemStats: vi.fn(),
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Helper: Create mock SystemStats
function createMockStats(overrides?: Partial<SystemStats>): SystemStats {
  return {
    qdrant_total_chunks: 450,
    qdrant_collection_name: 'documents',
    qdrant_vector_dimension: 1024,
    bm25_corpus_size: 100,
    neo4j_total_entities: 500,
    neo4j_total_relations: 1200,
    last_reindex_timestamp: '2024-12-15T10:30:00Z',
    embedding_model: 'BAAI/bge-m3',
    total_conversations: 50,
    ...overrides,
  };
}

describe('SettingsSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (adminApi.getSystemStats as ReturnType<typeof vi.fn>).mockResolvedValue(createMockStats());
    localStorageMock.getItem.mockReturnValue(null);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = () => {
    return render(
      <BrowserRouter>
        <SettingsSection />
      </BrowserRouter>
    );
  };

  describe('loading state', () => {
    it('should show loading state initially', () => {
      (adminApi.getSystemStats as ReturnType<typeof vi.fn>).mockImplementation(
        () => new Promise(() => {})
      );

      renderComponent();

      expect(screen.getByTestId('admin-section-loading')).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('should show error message when API fails', async () => {
      (adminApi.getSystemStats as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('Failed to load settings')
      );

      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('admin-section-error')).toBeInTheDocument();
      });
      expect(screen.getByText('Failed to load settings')).toBeInTheDocument();
    });
  });

  describe('settings display', () => {
    it('should display embedding model', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('bge-m3')).toBeInTheDocument();
      });
    });

    it('should display vector dimension', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('1024')).toBeInTheDocument();
      });
    });

    it('should display LLM model from localStorage', async () => {
      const storedConfig = JSON.stringify([
        { useCase: 'answer_generation', modelId: 'ollama/qwen3:32b', enabled: true },
      ]);
      localStorageMock.getItem.mockReturnValue(storedConfig);

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('qwen3:32b')).toBeInTheDocument();
      });
    });

    it('should display default LLM model when no stored config', async () => {
      localStorageMock.getItem.mockReturnValue(null);

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('qwen3:8b')).toBeInTheDocument();
      });
    });

    it('should display conversation count when available', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('50')).toBeInTheDocument();
      });
    });
  });

  describe('navigation', () => {
    it('should navigate to LLM config page on Configure click', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('configure-settings-button')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('configure-settings-button'));

      expect(mockNavigate).toHaveBeenCalledWith('/admin/llm-config');
    });

    it('should navigate to LLM config page on LLM row click', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('setting-row-llm')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('setting-row-llm'));

      expect(mockNavigate).toHaveBeenCalledWith('/admin/llm-config');
    });

    it('should navigate to Graph Analytics on quick link click', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('quick-link-graph-analytics')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('quick-link-graph-analytics'));

      expect(mockNavigate).toHaveBeenCalledWith('/admin/graph');
    });

    it('should navigate to LLM Config on quick link click', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('quick-link-llm-config')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('quick-link-llm-config'));

      expect(mockNavigate).toHaveBeenCalledWith('/admin/llm-config');
    });
  });

  describe('section header', () => {
    it('should display Settings title', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Settings')).toBeInTheDocument();
      });
    });

    it('should render Configure button', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('configure-settings-button')).toBeInTheDocument();
        expect(screen.getByText('Configure')).toBeInTheDocument();
      });
    });
  });
});

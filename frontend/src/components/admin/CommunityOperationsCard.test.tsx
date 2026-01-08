/**
 * CommunityOperationsCard Component Tests
 * Sprint 79 Feature 79.7: Admin Graph Operations UI
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CommunityOperationsCard } from './CommunityOperationsCard';
import * as graphOperationsApi from '../../api/graphOperations';
import type { NamespaceInfo, CommunitySummarizationResponse } from '../../api/graphOperations';

// Mock the graph operations API
vi.mock('../../api/graphOperations', () => ({
  triggerCommunitySummarization: vi.fn(),
}));

// Helper: Create mock namespaces
function createMockNamespaces(): NamespaceInfo[] {
  return [
    {
      namespace_id: 'default',
      namespace_type: 'general',
      document_count: 100,
      description: 'Default namespace',
    },
    {
      namespace_id: 'hotpotqa_large',
      namespace_type: 'qa',
      document_count: 50,
      description: 'HotpotQA dataset',
    },
    {
      namespace_id: 'legal_docs',
      namespace_type: 'legal',
      document_count: 30,
      description: 'Legal documents',
    },
  ];
}

// Helper: Create mock success response
function createMockSuccessResponse(
  overrides?: Partial<CommunitySummarizationResponse>
): CommunitySummarizationResponse {
  return {
    status: 'complete',
    total_communities: 92,
    summaries_generated: 85,
    failed: 7,
    total_time_s: 120.5,
    avg_time_per_summary_s: 1.42,
    message: 'Generated 85 summaries in 120.5s (7 failed).',
    ...overrides,
  };
}

describe('CommunityOperationsCard', () => {
  const mockOnNamespaceChange = vi.fn();
  const mockOnOperationComplete = vi.fn();

  const defaultProps = {
    namespaces: createMockNamespaces(),
    selectedNamespace: null as string | null,
    onNamespaceChange: mockOnNamespaceChange,
    onOperationComplete: mockOnOperationComplete,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (graphOperationsApi.triggerCommunitySummarization as ReturnType<typeof vi.fn>).mockResolvedValue(
      createMockSuccessResponse()
    );
  });

  describe('initial rendering', () => {
    it('should render the card with title and description', () => {
      render(<CommunityOperationsCard {...defaultProps} />);

      expect(screen.getByTestId('community-operations-card')).toBeInTheDocument();
      expect(screen.getByText('Community Summarization')).toBeInTheDocument();
      expect(
        screen.getByText('Generate LLM-powered summaries for graph communities')
      ).toBeInTheDocument();
    });

    it('should render summarize button in idle state', () => {
      render(<CommunityOperationsCard {...defaultProps} />);

      expect(screen.getByTestId('summarize-button')).toBeInTheDocument();
      expect(screen.getByText('Summarize Communities')).toBeInTheDocument();
    });
  });

  describe('namespace selector', () => {
    it('should render namespace dropdown with all options', () => {
      render(<CommunityOperationsCard {...defaultProps} />);

      const select = screen.getByTestId('namespace-selector');
      expect(select).toBeInTheDocument();

      // Check default option
      expect(screen.getByRole('option', { name: 'All namespaces' })).toBeInTheDocument();

      // Check namespace options
      expect(screen.getByRole('option', { name: 'default (100 docs)' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'hotpotqa_large (50 docs)' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'legal_docs (30 docs)' })).toBeInTheDocument();
    });

    it('should call onNamespaceChange when selection changes', () => {
      render(<CommunityOperationsCard {...defaultProps} />);

      const select = screen.getByTestId('namespace-selector');
      fireEvent.change(select, { target: { value: 'hotpotqa_large' } });

      expect(mockOnNamespaceChange).toHaveBeenCalledWith('hotpotqa_large');
    });

    it('should call onNamespaceChange with null when "All namespaces" is selected', () => {
      render(
        <CommunityOperationsCard
          {...defaultProps}
          selectedNamespace="hotpotqa_large"
        />
      );

      const select = screen.getByTestId('namespace-selector');
      fireEvent.change(select, { target: { value: '' } });

      expect(mockOnNamespaceChange).toHaveBeenCalledWith(null);
    });

    it('should display selected namespace', () => {
      render(
        <CommunityOperationsCard
          {...defaultProps}
          selectedNamespace="hotpotqa_large"
        />
      );

      const select = screen.getByTestId('namespace-selector') as HTMLSelectElement;
      expect(select.value).toBe('hotpotqa_large');
    });
  });

  describe('force regenerate checkbox', () => {
    it('should render unchecked by default', () => {
      render(<CommunityOperationsCard {...defaultProps} />);

      const checkbox = screen.getByTestId('force-regenerate-checkbox');
      expect(checkbox).toBeInTheDocument();
      expect(checkbox).not.toBeChecked();
    });

    it('should toggle when clicked', () => {
      render(<CommunityOperationsCard {...defaultProps} />);

      const checkbox = screen.getByTestId('force-regenerate-checkbox');
      fireEvent.click(checkbox);
      expect(checkbox).toBeChecked();

      fireEvent.click(checkbox);
      expect(checkbox).not.toBeChecked();
    });
  });

  describe('summarization operation', () => {
    it('should show running state when operation starts', async () => {
      // Make the API call take time
      (graphOperationsApi.triggerCommunitySummarization as ReturnType<typeof vi.fn>).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(createMockSuccessResponse()), 100))
      );

      render(<CommunityOperationsCard {...defaultProps} />);

      fireEvent.click(screen.getByTestId('summarize-button'));

      await waitFor(() => {
        expect(screen.getByTestId('summarization-running')).toBeInTheDocument();
      });
    });

    it('should call API with correct parameters', async () => {
      render(
        <CommunityOperationsCard
          {...defaultProps}
          selectedNamespace="hotpotqa_large"
        />
      );

      // Enable force regenerate
      fireEvent.click(screen.getByTestId('force-regenerate-checkbox'));

      // Click summarize
      fireEvent.click(screen.getByTestId('summarize-button'));

      await waitFor(() => {
        expect(graphOperationsApi.triggerCommunitySummarization).toHaveBeenCalledWith({
          namespace: 'hotpotqa_large',
          force: true,
          batch_size: 10,
        });
      });
    });

    it('should show success state after operation completes', async () => {
      render(<CommunityOperationsCard {...defaultProps} />);

      fireEvent.click(screen.getByTestId('summarize-button'));

      await waitFor(() => {
        expect(screen.getByTestId('summarization-success')).toBeInTheDocument();
      });

      // Check success message
      expect(screen.getByText('Summarization Complete')).toBeInTheDocument();
      expect(
        screen.getByText('Generated 85 summaries in 120.5s (7 failed).')
      ).toBeInTheDocument();
    });

    it('should display result details after completion', async () => {
      render(<CommunityOperationsCard {...defaultProps} />);

      fireEvent.click(screen.getByTestId('summarize-button'));

      await waitFor(() => {
        expect(screen.getByTestId('summarization-success')).toBeInTheDocument();
      });

      // Check stats display
      expect(screen.getByText('92')).toBeInTheDocument(); // total communities
      expect(screen.getByText('85')).toBeInTheDocument(); // generated
      expect(screen.getByText('7')).toBeInTheDocument(); // failed
      expect(screen.getByText('120.5s')).toBeInTheDocument(); // time
    });

    it('should call onOperationComplete after successful operation', async () => {
      render(<CommunityOperationsCard {...defaultProps} />);

      fireEvent.click(screen.getByTestId('summarize-button'));

      await waitFor(() => {
        expect(mockOnOperationComplete).toHaveBeenCalledTimes(1);
      });
    });

    it('should show "no_work" message correctly', async () => {
      (graphOperationsApi.triggerCommunitySummarization as ReturnType<typeof vi.fn>).mockResolvedValue(
        createMockSuccessResponse({
          status: 'no_work',
          total_communities: 0,
          summaries_generated: 0,
          failed: 0,
          message: 'No communities need summarization. Use force=true to regenerate all summaries.',
        })
      );

      render(<CommunityOperationsCard {...defaultProps} />);

      fireEvent.click(screen.getByTestId('summarize-button'));

      await waitFor(() => {
        expect(screen.getByText('No Communities to Summarize')).toBeInTheDocument();
      });
    });
  });

  describe('error handling', () => {
    it('should show error state when operation fails', async () => {
      (graphOperationsApi.triggerCommunitySummarization as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('Connection failed: Service unavailable')
      );

      render(<CommunityOperationsCard {...defaultProps} />);

      fireEvent.click(screen.getByTestId('summarize-button'));

      await waitFor(() => {
        expect(screen.getByTestId('summarization-error')).toBeInTheDocument();
      });

      expect(screen.getByText('Summarization Failed')).toBeInTheDocument();
      expect(screen.getByText('Connection failed: Service unavailable')).toBeInTheDocument();
    });

    it('should allow retry after error', async () => {
      (graphOperationsApi.triggerCommunitySummarization as ReturnType<typeof vi.fn>)
        .mockRejectedValueOnce(new Error('First attempt failed'))
        .mockResolvedValueOnce(createMockSuccessResponse());

      render(<CommunityOperationsCard {...defaultProps} />);

      // First attempt - fails
      fireEvent.click(screen.getByTestId('summarize-button'));

      await waitFor(() => {
        expect(screen.getByTestId('summarization-error')).toBeInTheDocument();
      });

      // Retry - succeeds
      fireEvent.click(screen.getByTestId('retry-button'));

      await waitFor(() => {
        expect(screen.getByTestId('summarization-success')).toBeInTheDocument();
      });
    });
  });

  describe('reset functionality', () => {
    it('should reset to idle state when reset button is clicked', async () => {
      render(<CommunityOperationsCard {...defaultProps} />);

      // Complete operation
      fireEvent.click(screen.getByTestId('summarize-button'));

      await waitFor(() => {
        expect(screen.getByTestId('summarization-success')).toBeInTheDocument();
      });

      // Click reset
      fireEvent.click(screen.getByTestId('reset-button'));

      // Should be back to idle state
      expect(screen.getByTestId('summarize-button')).toBeInTheDocument();
    });
  });

  describe('disabled states during operation', () => {
    it('should disable namespace selector during operation', async () => {
      (graphOperationsApi.triggerCommunitySummarization as ReturnType<typeof vi.fn>).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(createMockSuccessResponse()), 100))
      );

      render(<CommunityOperationsCard {...defaultProps} />);

      fireEvent.click(screen.getByTestId('summarize-button'));

      await waitFor(() => {
        expect(screen.getByTestId('namespace-selector')).toBeDisabled();
      });
    });

    it('should disable force regenerate checkbox during operation', async () => {
      (graphOperationsApi.triggerCommunitySummarization as ReturnType<typeof vi.fn>).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(createMockSuccessResponse()), 100))
      );

      render(<CommunityOperationsCard {...defaultProps} />);

      fireEvent.click(screen.getByTestId('summarize-button'));

      await waitFor(() => {
        expect(screen.getByTestId('force-regenerate-checkbox')).toBeDisabled();
      });
    });
  });
});

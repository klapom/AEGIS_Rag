/**
 * DomainList Component Tests
 * Sprint 45 Feature 45.4: Domain Training Admin UI
 * Sprint 51 Feature 51.4: Domain deletion tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DomainList } from './DomainList';
import type { Domain } from '../../hooks/useDomainTraining';

// Mock the useDeleteDomain hook
const mockDeleteDomain = vi.fn();
vi.mock('../../hooks/useDomainTraining', async () => {
  const actual = await vi.importActual('../../hooks/useDomainTraining');
  return {
    ...actual,
    useDeleteDomain: () => ({
      mutateAsync: mockDeleteDomain,
      isLoading: false,
      error: null,
    }),
  };
});

// Helper: Create mock Domain
function createMockDomain(overrides?: Partial<Domain>): Domain {
  return {
    id: '1',
    name: 'finance',
    description: 'Financial domain for banking queries',
    llm_model: 'qwen3:32b',
    status: 'ready',
    ...overrides,
  };
}

describe('DomainList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  describe('loading state', () => {
    it('should show loading spinner when loading', () => {
      render(<DomainList domains={null} isLoading={true} />);
      expect(screen.getByTestId('domain-list-loading')).toBeInTheDocument();
      expect(screen.getByText(/loading domains/i)).toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('should show empty message when no domains', () => {
      render(<DomainList domains={[]} isLoading={false} />);
      expect(screen.getByTestId('domain-list-empty')).toBeInTheDocument();
      expect(screen.getByText(/no domains found/i)).toBeInTheDocument();
    });
  });

  describe('domain list rendering', () => {
    it('should render domain table with headers', () => {
      const domains = [createMockDomain()];
      render(<DomainList domains={domains} isLoading={false} />);

      expect(screen.getByTestId('domain-list')).toBeInTheDocument();
      expect(screen.getByText('Name')).toBeInTheDocument();
      expect(screen.getByText('Description')).toBeInTheDocument();
      expect(screen.getByText('Model')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
      expect(screen.getByText('Actions')).toBeInTheDocument();
    });

    it('should render domain rows', () => {
      const domains = [
        createMockDomain({ name: 'finance', description: 'Finance domain' }),
        createMockDomain({ name: 'legal', description: 'Legal domain', status: 'training' }),
      ];
      render(<DomainList domains={domains} isLoading={false} />);

      expect(screen.getByTestId('domain-row-finance')).toBeInTheDocument();
      expect(screen.getByTestId('domain-row-legal')).toBeInTheDocument();
      expect(screen.getByText('Finance domain')).toBeInTheDocument();
      expect(screen.getByText('Legal domain')).toBeInTheDocument();
    });

    it('should render domain status badges with correct colors', () => {
      const domains = [
        createMockDomain({ name: 'd1', status: 'ready' }),
        createMockDomain({ name: 'd2', status: 'training' }),
        createMockDomain({ name: 'd3', status: 'pending' }),
        createMockDomain({ name: 'd4', status: 'failed' }),
      ];
      render(<DomainList domains={domains} isLoading={false} />);

      const readyBadge = screen.getByTestId('domain-status-d1');
      expect(readyBadge).toHaveTextContent('ready');
      expect(readyBadge).toHaveClass('bg-green-100', 'text-green-800');

      const trainingBadge = screen.getByTestId('domain-status-d2');
      expect(trainingBadge).toHaveTextContent('training');
      expect(trainingBadge).toHaveClass('bg-yellow-100', 'text-yellow-800');

      const pendingBadge = screen.getByTestId('domain-status-d3');
      expect(pendingBadge).toHaveTextContent('pending');
      expect(pendingBadge).toHaveClass('bg-gray-100', 'text-gray-800');

      const failedBadge = screen.getByTestId('domain-status-d4');
      expect(failedBadge).toHaveTextContent('failed');
      expect(failedBadge).toHaveClass('bg-red-100', 'text-red-800');
    });

    it('should show "-" for null model', () => {
      const domains = [createMockDomain({ llm_model: null })];
      render(<DomainList domains={domains} isLoading={false} />);

      expect(screen.getByText('-')).toBeInTheDocument();
    });

    it('should render view button for each domain', () => {
      const domains = [createMockDomain({ name: 'finance' })];
      render(<DomainList domains={domains} isLoading={false} />);

      expect(screen.getByTestId('domain-view-finance')).toBeInTheDocument();
      expect(screen.getByTestId('domain-view-finance')).toHaveTextContent('View');
    });

    it('should render delete button for each domain', () => {
      const domains = [createMockDomain({ name: 'finance' })];
      render(<DomainList domains={domains} isLoading={false} />);

      expect(screen.getByTestId('domain-delete-finance')).toBeInTheDocument();
      expect(screen.getByTestId('domain-delete-finance')).toHaveTextContent('Delete');
    });
  });

  describe('delete functionality', () => {
    it('should show delete confirmation dialog when delete is clicked', async () => {
      const user = userEvent.setup();
      const domains = [createMockDomain({ name: 'finance' })];
      render(<DomainList domains={domains} isLoading={false} />);

      const deleteButton = screen.getByTestId('domain-delete-finance');
      await user.click(deleteButton);

      expect(screen.getByTestId('delete-confirm-dialog')).toBeInTheDocument();
      expect(screen.getByText(/are you sure you want to delete domain/i)).toBeInTheDocument();
      // Domain name appears in both row and dialog, so use getAllByText
      expect(screen.getAllByText('finance').length).toBeGreaterThan(0);
    });

    it('should close confirmation dialog when cancel is clicked', async () => {
      const user = userEvent.setup();
      const domains = [createMockDomain({ name: 'finance' })];
      render(<DomainList domains={domains} isLoading={false} />);

      // Open dialog
      await user.click(screen.getByTestId('domain-delete-finance'));
      expect(screen.getByTestId('delete-confirm-dialog')).toBeInTheDocument();

      // Cancel
      await user.click(screen.getByTestId('delete-cancel-button'));
      expect(screen.queryByTestId('delete-confirm-dialog')).not.toBeInTheDocument();
    });

    it('should call deleteDomain and onRefresh when confirmed', async () => {
      const user = userEvent.setup();
      const onRefresh = vi.fn();
      mockDeleteDomain.mockResolvedValueOnce({ message: 'Deleted', domain: 'finance' });

      const domains = [createMockDomain({ id: 'domain-123', name: 'finance' })];
      render(<DomainList domains={domains} isLoading={false} onRefresh={onRefresh} />);

      // Open dialog
      await user.click(screen.getByTestId('domain-delete-finance'));

      // Confirm deletion
      await user.click(screen.getByTestId('delete-confirm-button'));

      await waitFor(() => {
        expect(mockDeleteDomain).toHaveBeenCalledWith('domain-123');
        expect(onRefresh).toHaveBeenCalled();
      });

      // Dialog should close
      expect(screen.queryByTestId('delete-confirm-dialog')).not.toBeInTheDocument();
    });

    it('should display error message when deletion fails', async () => {
      const user = userEvent.setup();
      mockDeleteDomain.mockRejectedValueOnce(new Error('Failed to delete: domain in use'));

      const domains = [createMockDomain({ id: 'domain-123', name: 'finance' })];
      render(<DomainList domains={domains} isLoading={false} />);

      // Open dialog
      await user.click(screen.getByTestId('domain-delete-finance'));

      // Confirm deletion
      await user.click(screen.getByTestId('delete-confirm-button'));

      await waitFor(() => {
        expect(screen.getByText(/failed to delete: domain in use/i)).toBeInTheDocument();
      });

      // Dialog should remain open
      expect(screen.getByTestId('delete-confirm-dialog')).toBeInTheDocument();
    });

    it('should close dialog when clicking outside', async () => {
      const user = userEvent.setup();
      const domains = [createMockDomain({ name: 'finance' })];
      render(<DomainList domains={domains} isLoading={false} />);

      // Open dialog
      await user.click(screen.getByTestId('domain-delete-finance'));
      expect(screen.getByTestId('delete-confirm-dialog')).toBeInTheDocument();

      // Click on backdrop (the outer div)
      const backdrop = screen.getByTestId('delete-confirm-dialog');
      await user.click(backdrop);

      // Dialog should close
      expect(screen.queryByTestId('delete-confirm-dialog')).not.toBeInTheDocument();
    });
  });
});

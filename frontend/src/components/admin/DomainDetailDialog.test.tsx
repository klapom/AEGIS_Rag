/**
 * DomainDetailDialog Component Tests
 * Sprint 51 Feature: Domain View Dialog
 * Sprint 51 Feature 51.4: Domain deletion tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DomainDetailDialog } from './DomainDetailDialog';
import type { Domain } from '../../hooks/useDomainTraining';

// Mock the hooks
const mockDeleteDomain = vi.fn();
const mockTrainingStatus = {
  status: 'ready' as const,
  progress_percent: 100,
  current_step: 'completed',
  logs: ['Training completed successfully'],
  metrics: { accuracy: 0.95 },
};

vi.mock('../../hooks/useDomainTraining', async () => {
  const actual = await vi.importActual('../../hooks/useDomainTraining');
  return {
    ...actual,
    useDeleteDomain: () => ({
      mutateAsync: mockDeleteDomain,
      isLoading: false,
      error: null,
    }),
    useTrainingStatus: () => ({
      data: mockTrainingStatus,
      isLoading: false,
      error: null,
    }),
  };
});

// Helper: Create mock Domain
function createMockDomain(overrides?: Partial<Domain>): Domain {
  return {
    id: 'domain-123',
    name: 'finance',
    description: 'Financial domain for banking queries',
    llm_model: 'qwen3:32b',
    status: 'ready',
    created_at: '2024-01-15T10:30:00Z',
    updated_at: '2024-01-16T14:20:00Z',
    ...overrides,
  };
}

describe('DomainDetailDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('should not render when isOpen is false', () => {
      const { container } = render(
        <DomainDetailDialog domain={createMockDomain()} isOpen={false} onClose={vi.fn()} />
      );
      expect(container.firstChild).toBeNull();
    });

    it('should not render when domain is null', () => {
      const { container } = render(
        <DomainDetailDialog domain={null} isOpen={true} onClose={vi.fn()} />
      );
      expect(container.firstChild).toBeNull();
    });

    it('should render dialog when isOpen is true and domain exists', () => {
      render(
        <DomainDetailDialog domain={createMockDomain()} isOpen={true} onClose={vi.fn()} />
      );
      expect(screen.getByTestId('domain-detail-dialog')).toBeInTheDocument();
      // Domain name appears in header and info section
      expect(screen.getAllByText('finance').length).toBeGreaterThan(0);
    });

    it('should display domain information', () => {
      const domain = createMockDomain({
        name: 'legal',
        description: 'Legal domain for compliance',
        llm_model: 'gpt-4',
      });
      render(<DomainDetailDialog domain={domain} isOpen={true} onClose={vi.fn()} />);

      // Name appears multiple times (header and info section)
      expect(screen.getAllByText('legal').length).toBeGreaterThan(0);
      expect(screen.getByText('Legal domain for compliance')).toBeInTheDocument();
      expect(screen.getByText('gpt-4')).toBeInTheDocument();
    });

    it('should display status badge with correct color', () => {
      const domain = createMockDomain({ status: 'ready' });
      render(<DomainDetailDialog domain={domain} isOpen={true} onClose={vi.fn()} />);

      const statusBadges = screen.getAllByText('ready');
      expect(statusBadges.length).toBeGreaterThan(0);
      // At least one badge should have the green styling
      expect(statusBadges[0]).toHaveClass('bg-green-100', 'text-green-800');
    });

    it('should render Delete Domain button', () => {
      render(
        <DomainDetailDialog domain={createMockDomain()} isOpen={true} onClose={vi.fn()} />
      );
      expect(screen.getByTestId('dialog-delete-button')).toBeInTheDocument();
      expect(screen.getByTestId('dialog-delete-button')).toHaveTextContent('Delete Domain');
    });
  });

  describe('close functionality', () => {
    it('should call onClose when Close button is clicked', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      render(
        <DomainDetailDialog domain={createMockDomain()} isOpen={true} onClose={onClose} />
      );

      await user.click(screen.getByText('Close'));
      expect(onClose).toHaveBeenCalled();
    });

    it('should call onClose when clicking outside dialog', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      render(
        <DomainDetailDialog domain={createMockDomain()} isOpen={true} onClose={onClose} />
      );

      // Click on backdrop
      const backdrop = screen.getByTestId('domain-detail-dialog');
      await user.click(backdrop);
      expect(onClose).toHaveBeenCalled();
    });

    it('should call onClose when clicking X button', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      render(
        <DomainDetailDialog domain={createMockDomain()} isOpen={true} onClose={onClose} />
      );

      const closeButton = screen.getByLabelText('Close');
      await user.click(closeButton);
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('delete functionality', () => {
    it('should show inline delete confirmation when Delete Domain is clicked', async () => {
      const user = userEvent.setup();
      render(
        <DomainDetailDialog domain={createMockDomain()} isOpen={true} onClose={vi.fn()} />
      );

      await user.click(screen.getByTestId('dialog-delete-button'));

      expect(screen.getByText(/delete this domain\?/i)).toBeInTheDocument();
      expect(screen.getByText(/this will remove all indexed documents/i)).toBeInTheDocument();
      expect(screen.getByTestId('dialog-delete-confirm-button')).toBeInTheDocument();
      expect(screen.getByTestId('dialog-delete-cancel-button')).toBeInTheDocument();
    });

    it('should hide confirmation and show normal footer when Cancel is clicked', async () => {
      const user = userEvent.setup();
      render(
        <DomainDetailDialog domain={createMockDomain()} isOpen={true} onClose={vi.fn()} />
      );

      // Show confirmation
      await user.click(screen.getByTestId('dialog-delete-button'));
      expect(screen.getByTestId('dialog-delete-confirm-button')).toBeInTheDocument();

      // Cancel
      await user.click(screen.getByTestId('dialog-delete-cancel-button'));

      // Back to normal state
      expect(screen.queryByTestId('dialog-delete-confirm-button')).not.toBeInTheDocument();
      expect(screen.getByTestId('dialog-delete-button')).toBeInTheDocument();
    });

    it('should call deleteDomain and onDeleted when confirmed', async () => {
      const user = userEvent.setup();
      const onDeleted = vi.fn();
      mockDeleteDomain.mockResolvedValueOnce({ message: 'Deleted', domain: 'finance' });

      render(
        <DomainDetailDialog
          domain={createMockDomain({ id: 'domain-456' })}
          isOpen={true}
          onClose={vi.fn()}
          onDeleted={onDeleted}
        />
      );

      // Show confirmation
      await user.click(screen.getByTestId('dialog-delete-button'));

      // Confirm deletion
      await user.click(screen.getByTestId('dialog-delete-confirm-button'));

      await waitFor(() => {
        expect(mockDeleteDomain).toHaveBeenCalledWith('domain-456');
        expect(onDeleted).toHaveBeenCalled();
      });
    });

    it('should display error message when deletion fails', async () => {
      const user = userEvent.setup();
      mockDeleteDomain.mockRejectedValueOnce(new Error('Cannot delete: domain has active documents'));

      render(
        <DomainDetailDialog domain={createMockDomain()} isOpen={true} onClose={vi.fn()} />
      );

      // Show confirmation
      await user.click(screen.getByTestId('dialog-delete-button'));

      // Confirm deletion
      await user.click(screen.getByTestId('dialog-delete-confirm-button'));

      await waitFor(() => {
        expect(screen.getByText(/cannot delete: domain has active documents/i)).toBeInTheDocument();
      });

      // Confirmation should remain visible with error
      expect(screen.getByTestId('dialog-delete-confirm-button')).toBeInTheDocument();
    });

    it('should not call onDeleted if deletion fails', async () => {
      const user = userEvent.setup();
      const onDeleted = vi.fn();
      mockDeleteDomain.mockRejectedValueOnce(new Error('Delete failed'));

      render(
        <DomainDetailDialog
          domain={createMockDomain()}
          isOpen={true}
          onClose={vi.fn()}
          onDeleted={onDeleted}
        />
      );

      await user.click(screen.getByTestId('dialog-delete-button'));
      await user.click(screen.getByTestId('dialog-delete-confirm-button'));

      await waitFor(() => {
        expect(screen.getByText(/delete failed/i)).toBeInTheDocument();
      });

      expect(onDeleted).not.toHaveBeenCalled();
    });
  });
});

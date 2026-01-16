/**
 * DataSubjectRights Component Tests
 * Sprint 98 Feature 98.3: GDPR Consent Manager UI
 *
 * Tests for data subject rights request management.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DataSubjectRights } from './DataSubjectRights';
import type { DataSubjectRightsRequest } from '../../types/gdpr';

describe('DataSubjectRights', () => {
  const mockRequests: DataSubjectRightsRequest[] = [
    {
      id: 'request-1',
      userId: 'user-123',
      requestType: 'access',
      articleReference: 'GDPR Art. 15',
      submittedAt: '2024-01-20T10:00:00Z',
      status: 'pending',
      scope: ['Export all personal data', 'Include processing history'],
      reviewedBy: null,
      reviewedAt: null,
      completedAt: null,
      rejectionReason: null,
      metadata: {},
    },
    {
      id: 'request-2',
      userId: 'user-456',
      requestType: 'erasure',
      articleReference: 'GDPR Art. 17',
      submittedAt: '2024-01-18T10:00:00Z',
      status: 'completed',
      scope: ['Delete all user data'],
      reviewedBy: 'admin-1',
      reviewedAt: '2024-01-18T11:00:00Z',
      completedAt: '2024-01-18T12:00:00Z',
      rejectionReason: null,
      metadata: {},
    },
    {
      id: 'request-3',
      userId: 'user-789',
      requestType: 'portability',
      articleReference: 'GDPR Art. 20',
      submittedAt: '2024-01-19T10:00:00Z',
      status: 'rejected',
      scope: ['Export data in JSON format'],
      reviewedBy: 'admin-2',
      reviewedAt: '2024-01-19T11:00:00Z',
      completedAt: null,
      rejectionReason: 'Insufficient identity verification',
      metadata: {},
    },
  ];

  const mockHandlers = {
    onApproveRequest: vi.fn(),
    onRejectRequest: vi.fn(),
    onViewRequest: vi.fn(),
    onCreateRequest: vi.fn(),
  };

  it('renders header with title', () => {
    render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

    expect(screen.getByText('Data Subject Rights Requests')).toBeInTheDocument();
  });

  it('displays pending requests count', () => {
    render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

    expect(screen.getByText(/1 pending request/i)).toBeInTheDocument();
  });

  it('displays pending requests count with plural', () => {
    const pendingRequests = [
      { ...mockRequests[0] },
      { ...mockRequests[0], id: 'request-4', status: 'pending' as const },
    ];

    render(<DataSubjectRights {...mockHandlers} requests={pendingRequests} />);

    expect(screen.getByText(/2 pending requests/i)).toBeInTheDocument();
  });

  it('renders all request cards', () => {
    render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

    expect(screen.getByText(/Request #request-1/i)).toBeInTheDocument();
    expect(screen.getByText(/Request #request-2/i)).toBeInTheDocument();
    expect(screen.getByText(/Request #request-3/i)).toBeInTheDocument();
  });

  it('displays request details correctly', () => {
    render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

    expect(screen.getByText(/user-123/i)).toBeInTheDocument();
    expect(screen.getByText(/GDPR Art\. 15/i)).toBeInTheDocument();
    expect(screen.getByText(/Access/i)).toBeInTheDocument();
  });

  it('shows request scope items', () => {
    render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

    expect(screen.getByText('Export all personal data')).toBeInTheDocument();
    expect(screen.getByText('Include processing history')).toBeInTheDocument();
  });

  it('displays submission timestamp', () => {
    render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

    expect(screen.getAllByText(/Submitted:/i).length).toBeGreaterThan(0);
  });

  it('shows reviewed timestamp for processed requests', () => {
    render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

    expect(screen.getAllByText(/Reviewed:/i).length).toBe(2); // 2 completed/rejected
  });

  it('displays rejection reason for rejected requests', () => {
    render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

    expect(screen.getByText(/Rejection Reason:/i)).toBeInTheDocument();
    expect(screen.getByText('Insufficient identity verification')).toBeInTheDocument();
  });

  describe('Status Filtering', () => {
    it('filters requests by status', async () => {
      const user = userEvent.setup();
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      const statusFilter = screen.getByLabelText('Filter by status');
      await user.selectOptions(statusFilter, 'completed');

      // Only completed request should be visible
      expect(screen.queryByText(/Request #request-1/i)).not.toBeInTheDocument();
      expect(screen.getByText(/Request #request-2/i)).toBeInTheDocument();
      expect(screen.queryByText(/Request #request-3/i)).not.toBeInTheDocument();
    });

    it('shows all requests when filter is "all"', async () => {
      const user = userEvent.setup();
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      const statusFilter = screen.getByLabelText('Filter by status');
      await user.selectOptions(statusFilter, 'all');

      expect(screen.getByText(/Request #request-1/i)).toBeInTheDocument();
      expect(screen.getByText(/Request #request-2/i)).toBeInTheDocument();
      expect(screen.getByText(/Request #request-3/i)).toBeInTheDocument();
    });

    it('shows no results message when no requests match filter', async () => {
      const user = userEvent.setup();
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      const statusFilter = screen.getByLabelText('Filter by status');
      await user.selectOptions(statusFilter, 'failed');

      expect(screen.getByText(/No requests found matching your filters/i)).toBeInTheDocument();
    });
  });

  describe('Actions for Pending Requests', () => {
    it('shows Approve & Execute button for pending requests', () => {
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      expect(screen.getByRole('button', { name: /Approve & Execute/i })).toBeInTheDocument();
    });

    it('shows Reject button for pending requests', () => {
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      expect(screen.getByRole('button', { name: /Reject/i })).toBeInTheDocument();
    });

    it('calls onApproveRequest when approve button clicked', async () => {
      const user = userEvent.setup();
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      const approveButton = screen.getByRole('button', { name: /Approve & Execute/i });
      await user.click(approveButton);

      expect(mockHandlers.onApproveRequest).toHaveBeenCalledWith('request-1');
    });

    it('opens reject modal when reject button clicked', async () => {
      const user = userEvent.setup();
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      const rejectButton = screen.getByRole('button', { name: /Reject/i });
      await user.click(rejectButton);

      expect(screen.getByText('Reject Request')).toBeInTheDocument();
      expect(screen.getByLabelText('Rejection Reason')).toBeInTheDocument();
    });

    it('calls onRejectRequest with reason when reject modal submitted', async () => {
      const user = userEvent.setup();
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      const rejectButton = screen.getByRole('button', { name: /Reject/i });
      await user.click(rejectButton);

      const reasonInput = screen.getByLabelText('Rejection Reason');
      await user.type(reasonInput, 'Invalid request');

      const submitButton = screen.getByRole('button', { name: /Reject Request/i });
      await user.click(submitButton);

      expect(mockHandlers.onRejectRequest).toHaveBeenCalledWith('request-1', 'Invalid request');
    });

    it('closes reject modal when cancel clicked', async () => {
      const user = userEvent.setup();
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      const rejectButton = screen.getByRole('button', { name: /Reject/i });
      await user.click(rejectButton);

      const cancelButton = screen.getAllByRole('button', { name: /Cancel/i })[0];
      await user.click(cancelButton);

      expect(screen.queryByText('Reject Request')).not.toBeInTheDocument();
    });
  });

  describe('Actions for Non-Pending Requests', () => {
    it('shows View Details button for completed requests', () => {
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      const viewButtons = screen.getAllByRole('button', { name: /View Details/i });
      expect(viewButtons.length).toBeGreaterThan(0);
    });

    it('calls onViewRequest when view button clicked', async () => {
      const user = userEvent.setup();
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      const viewButtons = screen.getAllByRole('button', { name: /View Details/i });
      await user.click(viewButtons[0]);

      expect(mockHandlers.onViewRequest).toHaveBeenCalled();
    });

    it('does not show Approve button for completed requests', () => {
      const completedRequests = mockRequests.filter((r) => r.status === 'completed');
      render(<DataSubjectRights {...mockHandlers} requests={completedRequests} />);

      expect(screen.queryByRole('button', { name: /Approve & Execute/i })).not.toBeInTheDocument();
    });
  });

  describe('Create Request Modal', () => {
    it('shows New Request button', () => {
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      expect(screen.getByRole('button', { name: /New Request/i })).toBeInTheDocument();
    });

    it('opens create request modal when button clicked', async () => {
      const user = userEvent.setup();
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      const newRequestButton = screen.getByRole('button', { name: /New Request/i });
      await user.click(newRequestButton);

      expect(screen.getByText('Create Data Subject Rights Request')).toBeInTheDocument();
    });

    it('shows user ID and request type fields in modal', async () => {
      const user = userEvent.setup();
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      const newRequestButton = screen.getByRole('button', { name: /New Request/i });
      await user.click(newRequestButton);

      expect(screen.getByLabelText('User ID')).toBeInTheDocument();
      expect(screen.getByLabelText('Request Type')).toBeInTheDocument();
    });

    it('shows all request types in dropdown', async () => {
      const user = userEvent.setup();
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      const newRequestButton = screen.getByRole('button', { name: /New Request/i });
      await user.click(newRequestButton);

      const requestTypeSelect = screen.getByLabelText('Request Type');
      expect(requestTypeSelect).toBeInTheDocument();

      // Check options exist
      expect(screen.getByRole('option', { name: /Access \(Art\. 15\)/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /Erasure \(Art\. 17\)/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /Portability \(Art\. 20\)/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /Rectification \(Art\. 16\)/i })).toBeInTheDocument();
    });

    it('calls onCreateRequest when form submitted', async () => {
      const user = userEvent.setup();
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      const newRequestButton = screen.getByRole('button', { name: /New Request/i });
      await user.click(newRequestButton);

      const userIdInput = screen.getByLabelText('User ID');
      await user.type(userIdInput, 'user-999');

      const requestTypeSelect = screen.getByLabelText('Request Type');
      await user.selectOptions(requestTypeSelect, 'erasure');

      const submitButton = screen.getByRole('button', { name: /Create Request/i });
      await user.click(submitButton);

      expect(mockHandlers.onCreateRequest).toHaveBeenCalledWith('user-999', 'erasure');
    });

    it('closes modal when cancel clicked', async () => {
      const user = userEvent.setup();
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      const newRequestButton = screen.getByRole('button', { name: /New Request/i });
      await user.click(newRequestButton);

      const cancelButton = screen.getAllByRole('button', { name: /Cancel/i })[0];
      await user.click(cancelButton);

      expect(screen.queryByText('Create Data Subject Rights Request')).not.toBeInTheDocument();
    });

    it('requires user ID to submit form', async () => {
      const user = userEvent.setup();
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      const newRequestButton = screen.getByRole('button', { name: /New Request/i });
      await user.click(newRequestButton);

      const submitButton = screen.getByRole('button', { name: /Create Request/i });
      await user.click(submitButton);

      // Form should not submit without user ID
      expect(mockHandlers.onCreateRequest).not.toHaveBeenCalled();
    });
  });

  describe('Status Badges', () => {
    it('displays correct badge for pending status', () => {
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      expect(screen.getByText('Pending')).toBeInTheDocument();
    });

    it('displays correct badge for completed status', () => {
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      expect(screen.getByText('Completed')).toBeInTheDocument();
    });

    it('displays correct badge for rejected status', () => {
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      expect(screen.getByText('Rejected')).toBeInTheDocument();
    });
  });

  describe('Request Type Icons', () => {
    it('displays access icon for access requests', () => {
      render(<DataSubjectRights {...mockHandlers} requests={[mockRequests[0]]} />);

      // Icon should be present (Eye icon for access)
      expect(screen.getByText(/Access/i)).toBeInTheDocument();
    });

    it('displays erasure icon for erasure requests', () => {
      render(<DataSubjectRights {...mockHandlers} requests={[mockRequests[1]]} />);

      // Icon should be present (Trash icon for erasure)
      expect(screen.getByText(/Erasure/i)).toBeInTheDocument();
    });

    it('displays portability icon for portability requests', () => {
      render(<DataSubjectRights {...mockHandlers} requests={[mockRequests[2]]} />);

      // Icon should be present (Download icon for portability)
      expect(screen.getByText(/Portability/i)).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('shows empty message when no requests', () => {
      render(<DataSubjectRights {...mockHandlers} requests={[]} />);

      expect(screen.getByText(/No requests found matching your filters/i)).toBeInTheDocument();
    });

    it('shows 0 pending requests when all are processed', () => {
      const processedRequests = mockRequests.filter((r) => r.status !== 'pending');
      render(<DataSubjectRights {...mockHandlers} requests={processedRequests} />);

      expect(screen.getByText(/0 pending requests/i)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has accessible label for status filter', () => {
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      expect(screen.getByLabelText('Filter by status')).toBeInTheDocument();
    });

    it('has accessible labels in create modal', async () => {
      const user = userEvent.setup();
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      const newRequestButton = screen.getByRole('button', { name: /New Request/i });
      await user.click(newRequestButton);

      expect(screen.getByLabelText('User ID')).toBeInTheDocument();
      expect(screen.getByLabelText('Request Type')).toBeInTheDocument();
    });

    it('has accessible label in reject modal', async () => {
      const user = userEvent.setup();
      render(<DataSubjectRights {...mockHandlers} requests={mockRequests} />);

      const rejectButton = screen.getByRole('button', { name: /Reject/i });
      await user.click(rejectButton);

      expect(screen.getByLabelText('Rejection Reason')).toBeInTheDocument();
    });
  });
});

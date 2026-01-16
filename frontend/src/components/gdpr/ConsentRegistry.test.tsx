/**
 * ConsentRegistry Component Tests
 * Sprint 98 Feature 98.3: GDPR Consent Manager UI
 *
 * Tests for the consent list and filtering functionality.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConsentRegistry } from './ConsentRegistry';
import type { GDPRConsent } from '../../types/gdpr';

describe('ConsentRegistry', () => {
  const mockConsents: GDPRConsent[] = [
    {
      id: 'consent-1',
      userId: 'user-123',
      purpose: 'Data Processing',
      legalBasis: 'consent',
      legalBasisText: 'Art. 6(1)(a) Consent',
      dataCategories: ['identifier', 'contact'],
      skillRestrictions: [],
      grantedAt: '2024-01-15T10:00:00Z',
      expiresAt: '2025-01-15T10:00:00Z',
      withdrawnAt: null,
      status: 'active',
      version: '1.0',
      metadata: {},
    },
    {
      id: 'consent-2',
      userId: 'user-456',
      purpose: 'Marketing',
      legalBasis: 'consent',
      legalBasisText: 'Art. 6(1)(a) Consent',
      dataCategories: ['identifier', 'contact', 'behavioral'],
      skillRestrictions: ['marketing-agent'],
      grantedAt: '2023-06-01T10:00:00Z',
      expiresAt: null,
      withdrawnAt: '2024-01-10T10:00:00Z',
      status: 'withdrawn',
      version: '1.0',
      metadata: {},
    },
    {
      id: 'consent-3',
      userId: 'user-789',
      purpose: 'Analytics',
      legalBasis: 'legitimate_interests',
      legalBasisText: 'Art. 6(1)(f) Legitimate Interests',
      dataCategories: ['behavioral', 'location'],
      skillRestrictions: [],
      grantedAt: '2023-12-01T10:00:00Z',
      expiresAt: '2024-01-01T10:00:00Z',
      withdrawnAt: null,
      status: 'expired',
      version: '1.0',
      metadata: {},
    },
  ];

  const mockHandlers = {
    onRevokeConsent: vi.fn(),
    onEditConsent: vi.fn(),
    onViewDetails: vi.fn(),
    onRenewConsent: vi.fn(),
  };

  it('renders consent registry with header', () => {
    render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

    expect(screen.getByText('Consent Registry')).toBeInTheDocument();
  });

  it('displays total active consents count', () => {
    render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

    expect(screen.getByText(/1 active consent/i)).toBeInTheDocument();
  });

  it('renders all consent cards', () => {
    render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

    expect(screen.getByTestId('consent-row-consent-1')).toBeInTheDocument();
    expect(screen.getByTestId('consent-row-consent-2')).toBeInTheDocument();
    expect(screen.getByTestId('consent-row-consent-3')).toBeInTheDocument();
  });

  it('displays consent details correctly', () => {
    render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

    expect(screen.getByText('user-123')).toBeInTheDocument();
    expect(screen.getByText(/Data Processing/i)).toBeInTheDocument();
    expect(screen.getByText(/Art\. 6\(1\)\(a\) Consent/i)).toBeInTheDocument();
  });

  it('shows data categories as badges', () => {
    render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

    // Check for data categories in the first consent
    expect(screen.getByText('identifier')).toBeInTheDocument();
    expect(screen.getByText('contact')).toBeInTheDocument();
  });

  it('displays consent dates', () => {
    render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

    expect(screen.getByText(/Granted:/i)).toBeInTheDocument();
    expect(screen.getByText(/Expires:/i)).toBeInTheDocument();
  });

  it('shows "Never" for consents without expiration', () => {
    render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

    expect(screen.getByText('Never')).toBeInTheDocument();
  });

  it('displays skill restrictions when present', () => {
    render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

    expect(screen.getByText(/marketing-agent/i)).toBeInTheDocument();
  });

  describe('Filtering', () => {
    it('filters consents by status', async () => {
      const user = userEvent.setup();
      render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

      const statusFilter = screen.getByLabelText('Filter by status');
      await user.selectOptions(statusFilter, 'active');

      // Only active consent should be visible
      expect(screen.getByTestId('consent-row-consent-1')).toBeInTheDocument();
      expect(screen.queryByTestId('consent-row-consent-2')).not.toBeInTheDocument();
      expect(screen.queryByTestId('consent-row-consent-3')).not.toBeInTheDocument();
    });

    it('filters consents by search query (user ID)', async () => {
      const user = userEvent.setup();
      render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

      const searchInput = screen.getByPlaceholderText(/Search by user ID or purpose/i);
      await user.type(searchInput, 'user-456');

      // Only matching consent should be visible
      expect(screen.queryByTestId('consent-row-consent-1')).not.toBeInTheDocument();
      expect(screen.getByTestId('consent-row-consent-2')).toBeInTheDocument();
      expect(screen.queryByTestId('consent-row-consent-3')).not.toBeInTheDocument();
    });

    it('filters consents by search query (purpose)', async () => {
      const user = userEvent.setup();
      render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

      const searchInput = screen.getByPlaceholderText(/Search by user ID or purpose/i);
      await user.type(searchInput, 'Marketing');

      // Only matching consent should be visible
      expect(screen.queryByTestId('consent-row-consent-1')).not.toBeInTheDocument();
      expect(screen.getByTestId('consent-row-consent-2')).toBeInTheDocument();
      expect(screen.queryByTestId('consent-row-consent-3')).not.toBeInTheDocument();
    });

    it('shows "no results" message when no consents match filters', async () => {
      const user = userEvent.setup();
      render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

      const searchInput = screen.getByPlaceholderText(/Search by user ID or purpose/i);
      await user.type(searchInput, 'nonexistent');

      expect(screen.getByText(/No consents found matching your filters/i)).toBeInTheDocument();
    });

    it('combines status and search filters', async () => {
      const user = userEvent.setup();
      render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

      const statusFilter = screen.getByLabelText('Filter by status');
      await user.selectOptions(statusFilter, 'withdrawn');

      const searchInput = screen.getByPlaceholderText(/Search by user ID or purpose/i);
      await user.type(searchInput, 'user-456');

      expect(screen.getByTestId('consent-row-consent-2')).toBeInTheDocument();
      expect(screen.queryByTestId('consent-row-consent-1')).not.toBeInTheDocument();
      expect(screen.queryByTestId('consent-row-consent-3')).not.toBeInTheDocument();
    });
  });

  describe('Actions', () => {
    it('calls onRevokeConsent when Revoke button clicked', async () => {
      const user = userEvent.setup();
      render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

      const revokeButton = screen.getByRole('button', { name: /Revoke/i });
      await user.click(revokeButton);

      expect(mockHandlers.onRevokeConsent).toHaveBeenCalledWith('consent-1');
    });

    it('calls onEditConsent when Edit button clicked', async () => {
      const user = userEvent.setup();
      render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

      const editButtons = screen.getAllByRole('button', { name: /Edit/i });
      await user.click(editButtons[0]);

      expect(mockHandlers.onEditConsent).toHaveBeenCalledWith(mockConsents[0]);
    });

    it('calls onViewDetails when View Details button clicked', async () => {
      const user = userEvent.setup();
      render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

      const viewButtons = screen.getAllByRole('button', { name: /View Details/i });
      await user.click(viewButtons[0]);

      expect(mockHandlers.onViewDetails).toHaveBeenCalledWith(mockConsents[0]);
    });

    it('shows Revoke button only for active consents', () => {
      render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

      // Only one Revoke button (for active consent)
      const revokeButtons = screen.getAllByRole('button', { name: /Revoke/i });
      expect(revokeButtons).toHaveLength(1);
    });

    it('shows Edit and View Details for all consents', () => {
      render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

      const editButtons = screen.getAllByRole('button', { name: /Edit/i });
      expect(editButtons).toHaveLength(3);

      const viewButtons = screen.getAllByRole('button', { name: /View Details/i });
      expect(viewButtons).toHaveLength(3);
    });
  });

  describe('Status Indicators', () => {
    it('shows correct status badge for active consent', () => {
      render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

      expect(screen.getByText('Active')).toBeInTheDocument();
    });

    it('shows correct status badge for withdrawn consent', () => {
      render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

      expect(screen.getByText('Withdrawn')).toBeInTheDocument();
    });

    it('shows correct status badge for expired consent', () => {
      render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

      expect(screen.getByText('Expired')).toBeInTheDocument();
    });

    it('shows warning for expiring consents', () => {
      // Create consent expiring soon (10 days from now)
      const expiringConsent: GDPRConsent = {
        ...mockConsents[0],
        id: 'consent-expiring',
        expiresAt: new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString(),
      };

      render(
        <ConsentRegistry {...mockHandlers} consents={[expiringConsent, ...mockConsents]} />
      );

      expect(screen.getByText(/Expiring Soon/i)).toBeInTheDocument();
      expect(screen.getByText(/10 days left/i)).toBeInTheDocument();
    });

    it('shows Renew button for expiring consents', () => {
      const expiringConsent: GDPRConsent = {
        ...mockConsents[0],
        id: 'consent-expiring',
        expiresAt: new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString(),
      };

      render(
        <ConsentRegistry {...mockHandlers} consents={[expiringConsent, ...mockConsents]} />
      );

      expect(screen.getByRole('button', { name: /Renew/i })).toBeInTheDocument();
    });

    it('calls onRenewConsent when Renew button clicked', async () => {
      const user = userEvent.setup();
      const expiringConsent: GDPRConsent = {
        ...mockConsents[0],
        id: 'consent-expiring',
        expiresAt: new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString(),
      };

      render(
        <ConsentRegistry {...mockHandlers} consents={[expiringConsent, ...mockConsents]} />
      );

      const renewButton = screen.getByRole('button', { name: /Renew/i });
      await user.click(renewButton);

      expect(mockHandlers.onRenewConsent).toHaveBeenCalledWith(expiringConsent);
    });

    it('shows count of expiring consents in header', () => {
      const expiringConsent: GDPRConsent = {
        ...mockConsents[0],
        id: 'consent-expiring',
        expiresAt: new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString(),
      };

      render(
        <ConsentRegistry {...mockHandlers} consents={[expiringConsent, ...mockConsents]} />
      );

      expect(screen.getByText(/1 expiring soon/i)).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('shows empty message when no consents', () => {
      render(<ConsentRegistry {...mockHandlers} consents={[]} />);

      expect(screen.getByText(/No consents found matching your filters/i)).toBeInTheDocument();
    });

    it('shows 0 active consents when all are withdrawn', () => {
      const withdrawnConsents: GDPRConsent[] = [
        { ...mockConsents[0], status: 'withdrawn' },
        { ...mockConsents[1], status: 'withdrawn' },
      ];

      render(<ConsentRegistry {...mockHandlers} consents={withdrawnConsents} />);

      expect(screen.getByText(/0 active consent/i)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has accessible labels for filter controls', () => {
      render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

      expect(screen.getByLabelText('Search consents')).toBeInTheDocument();
      expect(screen.getByLabelText('Filter by status')).toBeInTheDocument();
    });

    it('uses semantic HTML for status filter', () => {
      render(<ConsentRegistry {...mockHandlers} consents={mockConsents} />);

      const select = screen.getByLabelText('Filter by status');
      expect(select.tagName).toBe('SELECT');
    });
  });
});

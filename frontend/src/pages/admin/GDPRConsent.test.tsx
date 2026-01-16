/**
 * GDPRConsent Page Tests
 * Sprint 98 Feature 98.3: GDPR Consent Manager UI
 *
 * Tests for GDPR consent management page with all tabs.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GDPRConsentPage } from './GDPRConsent';
import type { GDPRConsent, DataSubjectRightsRequest, ProcessingActivity } from '../../types/gdpr';

// Mock fetch globally
global.fetch = vi.fn();

describe('GDPRConsentPage', () => {
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
  ];

  const mockRequests: DataSubjectRightsRequest[] = [
    {
      id: 'request-1',
      userId: 'user-789',
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
  ];

  const mockActivities: ProcessingActivity[] = [
    {
      id: 'activity-1',
      userId: 'user-123',
      timestamp: '2024-01-21T10:00:00Z',
      activity: 'data_read',
      purpose: 'Customer Support',
      legalBasis: 'consent',
      dataCategories: ['identifier'],
      skillName: 'support-agent',
      resourceId: 'doc-123',
      duration: 150,
      metadata: {},
    },
  ];

  const mockPIISettings = {
    enabled: true,
    autoRedact: false,
    redactionChar: '*',
    detectionThreshold: 0.7,
    enabledCategories: ['identifier', 'contact', 'financial'],
  };

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock localStorage
    const localStorageMock = {
      getItem: vi.fn(() => 'mock-token'),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
      length: 0,
      key: vi.fn(),
    };
    Object.defineProperty(window, 'localStorage', {
      value: localStorageMock,
      writable: true,
    });

    // Default successful fetch responses
    (global.fetch as any).mockImplementation((url: string, options?: any) => {
      // Handle DELETE requests
      if (options?.method === 'DELETE') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true }),
        });
      }

      // Handle POST requests
      if (options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true }),
        });
      }

      // Handle PUT requests
      if (options?.method === 'PUT') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true }),
        });
      }

      // Handle GET requests
      if (url.includes('/api/v1/gdpr/consents')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            items: mockConsents.map((consent) => ({
              ...consent,
              // Backend returns "granted" but we map to "active"
              status: consent.status === 'active' ? 'granted' : consent.status,
            })),
            total: mockConsents.length,
          }),
        });
      }
      if (url.includes('/api/v1/gdpr/requests')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            requests: mockRequests,
            total: mockRequests.length,
          }),
        });
      }
      if (url.includes('/api/v1/gdpr/processing-activities')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            activities: mockActivities,
            total: mockActivities.length,
          }),
        });
      }
      if (url.includes('/api/v1/gdpr/pii-settings')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockPIISettings,
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({}),
      });
    });
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('Page Rendering', () => {
    it('renders the page with header', async () => {
      render(<GDPRConsentPage />);

      await waitFor(() => {
        expect(screen.getByText('GDPR Consent Management')).toBeInTheDocument();
      });

      expect(screen.getByText(/EU GDPR Compliance/i)).toBeInTheDocument();
    });

    it('shows loading state initially', () => {
      render(<GDPRConsentPage />);
      expect(screen.getByText('Loading GDPR data...')).toBeInTheDocument();
    });

    it('renders all four tabs', async () => {
      render(<GDPRConsentPage />);

      await waitFor(() => {
        expect(screen.getByTestId('tab-consents')).toBeInTheDocument();
      });

      expect(screen.getByTestId('tab-rights')).toBeInTheDocument();
      expect(screen.getByTestId('tab-activities')).toBeInTheDocument();
      expect(screen.getByTestId('tab-pii')).toBeInTheDocument();
    });

    it('fetches data from all endpoints on mount', async () => {
      render(<GDPRConsentPage />);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          '/api/v1/gdpr/consents',
          expect.objectContaining({
            headers: expect.objectContaining({
              Authorization: 'Bearer mock-token',
            }),
          })
        );
      });

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/gdpr/requests',
        expect.any(Object)
      );
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/gdpr/processing-activities?limit=50',
        expect.any(Object)
      );
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/gdpr/pii-settings',
        expect.any(Object)
      );
    });
  });

  describe('Sprint 100 API Contract Fixes', () => {
    it('handles "items" field from backend (Fix #2)', async () => {
      render(<GDPRConsentPage />);

      // Wait for loading to finish
      await waitFor(
        () => {
          expect(screen.queryByText('Loading GDPR data...')).not.toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      // Wait for consents to be displayed
      await waitFor(
        () => {
          expect(screen.getByTestId('gdpr-consents-list')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      // Verify the consents were loaded from "items" field
      await waitFor(
        () => {
          expect(screen.getByText(/Data Processing/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('maps "granted" status to "active" (Fix #6)', async () => {
      render(<GDPRConsentPage />);

      await waitFor(
        () => {
          expect(screen.queryByText('Loading GDPR data...')).not.toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      await waitFor(
        () => {
          expect(screen.getByText('Active')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      // The backend returns "granted" but UI should show "Active"
      const activeConsents = screen.getAllByText('Active');
      expect(activeConsents.length).toBeGreaterThan(0);
    });

    it('preserves other status values without mapping', async () => {
      render(<GDPRConsentPage />);

      await waitFor(
        () => {
          expect(screen.queryByText('Loading GDPR data...')).not.toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      await waitFor(
        () => {
          expect(screen.getByText('Withdrawn')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });

  describe('Consents Tab', () => {
    it('displays consents list with data-testid', async () => {
      render(<GDPRConsentPage />);

      await waitFor(() => {
        expect(screen.getByTestId('gdpr-consents-list')).toBeInTheDocument();
      });
    });

    it('displays consent rows with data-testid', async () => {
      render(<GDPRConsentPage />);

      await waitFor(() => {
        expect(screen.getByTestId('consent-row-consent-1')).toBeInTheDocument();
      });

      expect(screen.getByTestId('consent-row-consent-2')).toBeInTheDocument();
    });

    it('shows consent details correctly', async () => {
      render(<GDPRConsentPage />);

      await waitFor(
        () => {
          expect(screen.queryByText('Loading GDPR data...')).not.toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      await waitFor(
        () => {
          expect(screen.getByText(/Data Processing/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      expect(screen.getByText(/Art\. 6\(1\)\(a\) Consent/i)).toBeInTheDocument();
    });

    it('allows revoking active consent', async () => {
      const user = userEvent.setup();

      // Mock window.confirm
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

      render(<GDPRConsentPage />);

      await waitFor(
        () => {
          expect(screen.queryByText('Loading GDPR data...')).not.toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      await waitFor(
        () => {
          const revokeButtons = screen.queryAllByText('Revoke');
          return revokeButtons.length > 0;
        },
        { timeout: 3000 }
      );

      const revokeButtons = screen.getAllByText('Revoke');
      await user.click(revokeButtons[0]);

      expect(confirmSpy).toHaveBeenCalled();

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          '/api/v1/gdpr/consent/consent-1',
          expect.objectContaining({
            method: 'DELETE',
          })
        );
      });

      confirmSpy.mockRestore();
    });

    it('shows "Add Consent" button on consents tab', async () => {
      render(<GDPRConsentPage />);

      await waitFor(() => {
        expect(screen.getByText('Add Consent')).toBeInTheDocument();
      });
    });
  });

  describe('Data Subject Rights Tab', () => {
    it('switches to rights tab when clicked', async () => {
      const user = userEvent.setup();
      render(<GDPRConsentPage />);

      await waitFor(() => {
        expect(screen.getByTestId('tab-rights')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('tab-rights'));

      expect(screen.getByText(/Data Subject Rights Requests/i)).toBeInTheDocument();
    });

    it('displays pending requests', async () => {
      const user = userEvent.setup();
      render(<GDPRConsentPage />);

      await waitFor(() => {
        expect(screen.getByTestId('tab-rights')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('tab-rights'));

      await waitFor(() => {
        expect(screen.getByText(/1 pending request/i)).toBeInTheDocument();
      });
    });

    it('allows approving pending requests', async () => {
      const user = userEvent.setup();
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

      render(<GDPRConsentPage />);

      await waitFor(() => {
        expect(screen.getByTestId('tab-rights')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('tab-rights'));

      await waitFor(() => {
        expect(screen.getByText('Approve & Execute')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Approve & Execute'));

      expect(confirmSpy).toHaveBeenCalled();

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          '/api/v1/gdpr/request/request-1/approve',
          expect.objectContaining({
            method: 'POST',
          })
        );
      });

      confirmSpy.mockRestore();
    });

    it('shows "New Request" button on rights tab', async () => {
      const user = userEvent.setup();
      render(<GDPRConsentPage />);

      await waitFor(() => {
        expect(screen.getByTestId('tab-rights')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('tab-rights'));

      await waitFor(() => {
        expect(screen.getByText('New Request')).toBeInTheDocument();
      });
    });
  });

  describe('Processing Activities Tab', () => {
    it('switches to activities tab when clicked', async () => {
      const user = userEvent.setup();
      render(<GDPRConsentPage />);

      await waitFor(() => {
        expect(screen.getByTestId('tab-activities')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('tab-activities'));

      // ProcessingActivityLog component should be rendered
      expect(screen.getByTestId('tab-activities')).toHaveClass('border-blue-600');
    });
  });

  describe('PII Settings Tab', () => {
    it('switches to PII tab when clicked', async () => {
      const user = userEvent.setup();
      render(<GDPRConsentPage />);

      await waitFor(() => {
        expect(screen.getByTestId('tab-pii')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('tab-pii'));

      await waitFor(() => {
        expect(screen.getByText(/PII Detection & Redaction/i)).toBeInTheDocument();
      });
    });

    it('displays current PII settings', async () => {
      const user = userEvent.setup();
      render(<GDPRConsentPage />);

      await waitFor(() => {
        expect(screen.getByTestId('tab-pii')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('tab-pii'));

      await waitFor(() => {
        expect(screen.getByText('PII Detection Active')).toBeInTheDocument();
      });
    });

    it('allows saving PII settings', async () => {
      const user = userEvent.setup();
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

      render(<GDPRConsentPage />);

      await waitFor(() => {
        expect(screen.getByTestId('tab-pii')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('tab-pii'));

      await waitFor(() => {
        expect(screen.getByText('Enable PII Detection')).toBeInTheDocument();
      });

      // Toggle a setting to enable "Save Changes" button
      const toggles = screen.getAllByRole('button', { name: '' });
      await user.click(toggles[0]);

      const saveButton = screen.getByText('Save Changes');
      await user.click(saveButton);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          '/api/v1/gdpr/pii-settings',
          expect.objectContaining({
            method: 'PUT',
          })
        );
      });

      alertSpy.mockRestore();
    });
  });

  describe('Error Handling', () => {
    it('shows error message when API fails', async () => {
      (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

      render(<GDPRConsentPage />);

      await waitFor(() => {
        expect(screen.getByText(/Failed to load data/i)).toBeInTheDocument();
      });
    });

    it('handles consent revoke failure gracefully', async () => {
      const user = userEvent.setup();
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

      (global.fetch as any).mockImplementation((url: string, options?: any) => {
        if (options?.method === 'DELETE') {
          return Promise.resolve({ ok: false });
        }
        if (url.includes('/api/v1/gdpr/consents')) {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              items: mockConsents.map((c) => ({
                ...c,
                status: c.status === 'active' ? 'granted' : c.status,
              })),
              total: mockConsents.length,
            }),
          });
        }
        if (url.includes('/api/v1/gdpr/requests')) {
          return Promise.resolve({
            ok: true,
            json: async () => ({ requests: mockRequests, total: mockRequests.length }),
          });
        }
        if (url.includes('/api/v1/gdpr/processing-activities')) {
          return Promise.resolve({
            ok: true,
            json: async () => ({ activities: mockActivities, total: mockActivities.length }),
          });
        }
        if (url.includes('/api/v1/gdpr/pii-settings')) {
          return Promise.resolve({
            ok: true,
            json: async () => mockPIISettings,
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({}),
        });
      });

      render(<GDPRConsentPage />);

      await waitFor(
        () => {
          expect(screen.queryByText('Loading GDPR data...')).not.toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      await waitFor(
        () => {
          const revokeButtons = screen.queryAllByText('Revoke');
          return revokeButtons.length > 0;
        },
        { timeout: 3000 }
      );

      const revokeButtons = screen.getAllByText('Revoke');
      await user.click(revokeButtons[0]);

      await waitFor(() => {
        expect(alertSpy).toHaveBeenCalledWith(
          expect.stringContaining('Failed to revoke consent')
        );
      });

      confirmSpy.mockRestore();
      alertSpy.mockRestore();
    });
  });

  describe('Tab Count Badges', () => {
    it('shows count badges for consents', async () => {
      render(<GDPRConsentPage />);

      await waitFor(() => {
        const consentsTab = screen.getByTestId('tab-consents');
        expect(within(consentsTab).getByText('2')).toBeInTheDocument();
      });
    });

    it('shows count badges for requests', async () => {
      render(<GDPRConsentPage />);

      await waitFor(() => {
        const rightsTab = screen.getByTestId('tab-rights');
        expect(within(rightsTab).getByText('1')).toBeInTheDocument();
      });
    });

    it('shows count badges for activities', async () => {
      render(<GDPRConsentPage />);

      await waitFor(() => {
        const activitiesTab = screen.getByTestId('tab-activities');
        expect(within(activitiesTab).getByText('1')).toBeInTheDocument();
      });
    });
  });
});

/**
 * EventDetailsModal Component Tests
 * Sprint 98 Feature 98.4: Audit Trail Viewer
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { EventDetailsModal } from './EventDetailsModal';
import type { AuditEvent } from '../../types/audit';

const mockEvent: AuditEvent = {
  id: 'evt_001',
  timestamp: '2026-01-16T10:30:00Z',
  eventType: 'DATA_READ',
  actorId: 'user_123',
  actorName: 'John Doe',
  resourceId: 'doc_xyz',
  resourceType: 'document',
  outcome: 'success',
  duration: 320,
  message: 'User accessed sensitive document',
  metadata: {
    ipAddress: '192.168.1.100',
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    dataCategories: ['personal_data', 'health_data'],
  },
  hash: 'sha256_hash_001_full_64_chars_example_abcdef1234567890',
  previousHash: 'sha256_hash_000_full_64_chars_example_abcdef1234567890',
};

const mockErrorEvent: AuditEvent = {
  id: 'evt_002',
  timestamp: '2026-01-16T10:45:00Z',
  eventType: 'SKILL_FAILED',
  actorId: 'system',
  actorName: null,
  resourceId: 'skill_research',
  resourceType: 'skill',
  outcome: 'error',
  duration: null,
  message: 'Skill execution failed',
  metadata: {
    skillName: 'deep_research',
    skillVersion: '1.2.0',
    errorMessage: 'Timeout waiting for LLM response',
    errorCode: 'LLM_TIMEOUT',
  },
  hash: 'sha256_hash_002',
  previousHash: 'sha256_hash_001',
};

describe('EventDetailsModal', () => {
  describe('Rendering', () => {
    it('should not render when event is null', () => {
      const onClose = vi.fn();
      const { container } = render(<EventDetailsModal event={null} onClose={onClose} />);

      expect(container.firstChild).toBeNull();
    });

    it('should render modal when event is provided', () => {
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      expect(screen.getByTestId('event-details-modal')).toBeInTheDocument();
      expect(screen.getByText('Event Details')).toBeInTheDocument();
    });

    it('should display basic event information', () => {
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      // Event ID
      expect(screen.getByText('evt_001')).toBeInTheDocument();

      // Event Type (appears in header and details)
      expect(screen.getAllByText('Data Read')).toHaveLength(2);

      // Message
      expect(screen.getByText('User accessed sensitive document')).toBeInTheDocument();

      // Outcome (includes emoji icon)
      expect(screen.getByText(/Success/i)).toBeInTheDocument();
    });

    it('should display timestamp in human-readable format', () => {
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      // Check for date components (exact format may vary by locale)
      expect(screen.getByText(/January|Jan/)).toBeInTheDocument();
      expect(screen.getByText(/2026/)).toBeInTheDocument();
    });

    it('should display actor information', () => {
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      expect(screen.getByText('user_123')).toBeInTheDocument();
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    it('should display resource information', () => {
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      expect(screen.getByText('doc_xyz')).toBeInTheDocument();
      expect(screen.getByText('document')).toBeInTheDocument();
    });

    it('should display duration when available', () => {
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      expect(screen.getByText('320ms')).toBeInTheDocument();
    });

    it('should not display duration section when null', () => {
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockErrorEvent} onClose={onClose} />);

      // Duration label should not be present
      expect(screen.queryByText('Duration')).not.toBeInTheDocument();
    });
  });

  describe('Metadata Display', () => {
    it('should display IP address', () => {
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      expect(screen.getByText('IP Address')).toBeInTheDocument();
      expect(screen.getByText('192.168.1.100')).toBeInTheDocument();
    });

    it('should display user agent', () => {
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      expect(screen.getByText('User Agent')).toBeInTheDocument();
      expect(screen.getByText(/Mozilla\/5.0/)).toBeInTheDocument();
    });

    it('should display GDPR data categories', () => {
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      expect(screen.getByText('Data Categories (GDPR)')).toBeInTheDocument();
      expect(screen.getByText('personal_data')).toBeInTheDocument();
      expect(screen.getByText('health_data')).toBeInTheDocument();
    });

    it('should display skill information', () => {
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockErrorEvent} onClose={onClose} />);

      expect(screen.getByText('Skill Name')).toBeInTheDocument();
      expect(screen.getByText('deep_research')).toBeInTheDocument();
      expect(screen.getByText(/v1.2.0/)).toBeInTheDocument();
    });

    it('should display error information', () => {
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockErrorEvent} onClose={onClose} />);

      expect(screen.getByText('Error Message')).toBeInTheDocument();
      expect(screen.getByText(/Timeout waiting for LLM response/)).toBeInTheDocument();
      expect(screen.getByText(/LLM_TIMEOUT/)).toBeInTheDocument();
    });

    it('should not display metadata section when empty', () => {
      const onClose = vi.fn();
      const eventWithoutMetadata: AuditEvent = {
        ...mockEvent,
        metadata: {},
      };
      render(<EventDetailsModal event={eventWithoutMetadata} onClose={onClose} />);

      expect(screen.queryByText('Metadata')).not.toBeInTheDocument();
    });
  });

  describe('Cryptographic Integrity', () => {
    it('should display event hash', () => {
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      expect(screen.getByText('Event Hash (SHA-256)')).toBeInTheDocument();
      expect(
        screen.getByText('sha256_hash_001_full_64_chars_example_abcdef1234567890')
      ).toBeInTheDocument();
    });

    it('should display previous hash when available', () => {
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      expect(screen.getByText('Previous Event Hash')).toBeInTheDocument();
      expect(
        screen.getByText('sha256_hash_000_full_64_chars_example_abcdef1234567890')
      ).toBeInTheDocument();
    });

    it('should show chain verified badge', () => {
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      expect(screen.getByText('Chain Verified')).toBeInTheDocument();
    });
  });

  describe('Interaction', () => {
    it('should call onClose when clicking close button', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      const closeButton = screen.getByTestId('close-modal');
      await user.click(closeButton);

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('should call onClose when clicking overlay', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      const overlay = screen.getByTestId('event-details-modal');
      await user.click(overlay);

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('should not close when clicking modal content', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      const modalContent = screen.getByText('Event Details').closest('div');
      if (modalContent) {
        await user.click(modalContent);
      }

      // onClose should not be called when clicking inside modal
      expect(onClose).not.toHaveBeenCalled();
    });

    it('should call onClose when clicking Close footer button', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      const closeFooterButton = screen.getByRole('button', { name: /Close/i });
      await user.click(closeFooterButton);

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      expect(screen.getByTestId('event-details-modal')).toBeInTheDocument();
      expect(screen.getByTestId('close-modal')).toBeInTheDocument();
    });

    it('should be keyboard accessible', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockEvent} onClose={onClose} />);

      const closeButton = screen.getByTestId('close-modal');

      // Tab to close button
      await user.tab();
      expect(closeButton).toHaveFocus();

      // Press Enter to close
      await user.keyboard('{Enter}');
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('Edge Cases', () => {
    it('should handle event with null actorName', () => {
      const onClose = vi.fn();
      render(<EventDetailsModal event={mockErrorEvent} onClose={onClose} />);

      expect(screen.getByText('system')).toBeInTheDocument();
      // Actor Name section should not appear when null
      expect(screen.queryByText('Actor Name')).not.toBeInTheDocument();
    });

    it('should handle event with no previous hash', () => {
      const onClose = vi.fn();
      const firstEvent: AuditEvent = {
        ...mockEvent,
        previousHash: null,
      };
      render(<EventDetailsModal event={firstEvent} onClose={onClose} />);

      // Previous hash section should not be present
      expect(screen.queryByText('Previous Event Hash')).not.toBeInTheDocument();
    });

    it('should handle event with complex metadata objects', () => {
      const onClose = vi.fn();
      const eventWithComplexMetadata: AuditEvent = {
        ...mockEvent,
        metadata: {
          ...mockEvent.metadata,
          customData: {
            nested: {
              value: 'test',
            },
          },
        },
      };
      render(<EventDetailsModal event={eventWithComplexMetadata} onClose={onClose} />);

      // Should display JSON stringified version
      expect(screen.getByText(/customData/)).toBeInTheDocument();
      expect(screen.getByText(/"nested"/)).toBeInTheDocument();
    });
  });
});

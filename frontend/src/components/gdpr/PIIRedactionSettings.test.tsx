/**
 * PIIRedactionSettings Component Tests
 * Sprint 98 Feature 98.3: GDPR Consent Manager UI
 *
 * Tests for PII detection and redaction settings.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PIIRedactionSettings } from './PIIRedactionSettings';
import type { PIIRedactionSettings as PIISettings } from '../../types/gdpr';

describe('PIIRedactionSettings', () => {
  const mockSettings: PIISettings = {
    enabled: true,
    autoRedact: false,
    redactionChar: '*',
    detectionThreshold: 0.7,
    enabledCategories: ['identifier', 'contact', 'financial'],
  };

  const mockOnSave = vi.fn();

  it('renders header with title', () => {
    render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

    expect(screen.getByText('PII Detection & Redaction')).toBeInTheDocument();
  });

  it('displays PII detection toggle', () => {
    render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

    expect(screen.getByText('Enable PII Detection')).toBeInTheDocument();
    expect(screen.getByText(/Automatically detect personally identifiable information/i)).toBeInTheDocument();
  });

  it('displays auto-redact toggle', () => {
    render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

    expect(screen.getByText('Auto-Redact PII')).toBeInTheDocument();
    expect(screen.getByText(/Automatically redact detected PII in responses/i)).toBeInTheDocument();
  });

  it('displays redaction character input', () => {
    render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

    expect(screen.getByLabelText('Redaction Character')).toBeInTheDocument();
    expect(screen.getByDisplayValue('*')).toBeInTheDocument();
  });

  it('displays detection threshold slider', () => {
    render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

    expect(screen.getByText(/Detection Confidence Threshold: 70%/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Detection Confidence Threshold/i)).toBeInTheDocument();
  });

  it('displays category checkboxes', () => {
    render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

    expect(screen.getByText('Detect Categories')).toBeInTheDocument();
    expect(screen.getByText('identifier')).toBeInTheDocument();
    expect(screen.getByText('contact')).toBeInTheDocument();
    expect(screen.getByText('financial')).toBeInTheDocument();
    expect(screen.getByText('health')).toBeInTheDocument();
    expect(screen.getByText('biometric')).toBeInTheDocument();
    expect(screen.getByText('location')).toBeInTheDocument();
  });

  it('shows "PII Detection Active" when enabled', () => {
    render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

    expect(screen.getByText('PII Detection Active')).toBeInTheDocument();
  });

  it('shows "PII Detection Disabled" when disabled', () => {
    const disabledSettings: PIISettings = {
      ...mockSettings,
      enabled: false,
    };

    render(<PIIRedactionSettings settings={disabledSettings} onSave={mockOnSave} />);

    expect(screen.getByText('PII Detection Disabled')).toBeInTheDocument();
  });

  describe('Toggle Interactions', () => {
    it('shows Save Changes button when settings are modified', async () => {
      const user = userEvent.setup();
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      // Initially no Save button
      expect(screen.queryByText('Save Changes')).not.toBeInTheDocument();

      // Click enable toggle to trigger change
      const toggles = screen.getAllByRole('button', { name: '' });
      await user.click(toggles[0]);

      // Save button should appear
      expect(screen.getByText('Save Changes')).toBeInTheDocument();
    });

    it('toggles PII detection on/off', async () => {
      const user = userEvent.setup();
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      const toggles = screen.getAllByRole('button', { name: '' });
      await user.click(toggles[0]); // First toggle is "Enable PII Detection"

      await user.click(screen.getByText('Save Changes'));

      expect(mockOnSave).toHaveBeenCalledWith(
        expect.objectContaining({
          enabled: false, // Toggled from true to false
        })
      );
    });

    it('toggles auto-redact on/off', async () => {
      const user = userEvent.setup();
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      const toggles = screen.getAllByRole('button', { name: '' });
      await user.click(toggles[1]); // Second toggle is "Auto-Redact"

      await user.click(screen.getByText('Save Changes'));

      expect(mockOnSave).toHaveBeenCalledWith(
        expect.objectContaining({
          autoRedact: true, // Toggled from false to true
        })
      );
    });

    it('disables auto-redact toggle when PII detection is off', () => {
      const disabledSettings: PIISettings = {
        ...mockSettings,
        enabled: false,
      };

      render(<PIIRedactionSettings settings={disabledSettings} onSave={mockOnSave} />);

      const toggles = screen.getAllByRole('button', { name: '' });
      expect(toggles[1]).toBeDisabled();
    });
  });

  describe('Redaction Character Input', () => {
    it('changes redaction character', async () => {
      const user = userEvent.setup();
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      const input = screen.getByLabelText('Redaction Character');
      await user.clear(input);
      await user.type(input, '#');

      await user.click(screen.getByText('Save Changes'));

      expect(mockOnSave).toHaveBeenCalledWith(
        expect.objectContaining({
          redactionChar: '#',
        })
      );
    });

    it('limits input to 1 character', () => {
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      const input = screen.getByLabelText('Redaction Character') as HTMLInputElement;
      expect(input.maxLength).toBe(1);
    });

    it('disables redaction char input when PII detection is off', () => {
      const disabledSettings: PIISettings = {
        ...mockSettings,
        enabled: false,
      };

      render(<PIIRedactionSettings settings={disabledSettings} onSave={mockOnSave} />);

      const input = screen.getByLabelText('Redaction Character');
      expect(input).toBeDisabled();
    });

    it('shows example redaction', () => {
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      expect(screen.getByText(/Example: "John Doe" → ".*"/i)).toBeInTheDocument();
    });
  });

  describe('Detection Threshold Slider', () => {
    it('updates threshold value', async () => {
      const user = userEvent.setup();
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      const slider = screen.getByLabelText(/Detection Confidence Threshold/i);
      await user.click(slider);
      // Simulate changing slider value
      await user.type(slider, '{ArrowRight}');

      // Save button should appear
      expect(screen.getByText('Save Changes')).toBeInTheDocument();
    });

    it('displays threshold as percentage', () => {
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      expect(screen.getByText(/70%/i)).toBeInTheDocument();
    });

    it('shows threshold range labels', () => {
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      expect(screen.getByText('Less strict (0%)')).toBeInTheDocument();
      expect(screen.getByText('More strict (100%)')).toBeInTheDocument();
    });

    it('disables threshold slider when PII detection is off', () => {
      const disabledSettings: PIISettings = {
        ...mockSettings,
        enabled: false,
      };

      render(<PIIRedactionSettings settings={disabledSettings} onSave={mockOnSave} />);

      const slider = screen.getByLabelText(/Detection Confidence Threshold/i);
      expect(slider).toBeDisabled();
    });
  });

  describe('Category Checkboxes', () => {
    it('checks enabled categories', () => {
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      const identifierCheckbox = screen.getByRole('checkbox', { name: /identifier/i });
      const contactCheckbox = screen.getByRole('checkbox', { name: /contact/i });
      const financialCheckbox = screen.getByRole('checkbox', { name: /financial/i });

      expect(identifierCheckbox).toBeChecked();
      expect(contactCheckbox).toBeChecked();
      expect(financialCheckbox).toBeChecked();
    });

    it('unchecks disabled categories', () => {
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      const healthCheckbox = screen.getByRole('checkbox', { name: /health/i });
      const biometricCheckbox = screen.getByRole('checkbox', { name: /biometric/i });
      const locationCheckbox = screen.getByRole('checkbox', { name: /location/i });

      expect(healthCheckbox).not.toBeChecked();
      expect(biometricCheckbox).not.toBeChecked();
      expect(locationCheckbox).not.toBeChecked();
    });

    it('toggles category on/off', async () => {
      const user = userEvent.setup();
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      const healthCheckbox = screen.getByRole('checkbox', { name: /health/i });
      await user.click(healthCheckbox);

      await user.click(screen.getByText('Save Changes'));

      expect(mockOnSave).toHaveBeenCalledWith(
        expect.objectContaining({
          enabledCategories: expect.arrayContaining(['identifier', 'contact', 'financial', 'health']),
        })
      );
    });

    it('removes category when unchecked', async () => {
      const user = userEvent.setup();
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      const identifierCheckbox = screen.getByRole('checkbox', { name: /identifier/i });
      await user.click(identifierCheckbox);

      await user.click(screen.getByText('Save Changes'));

      expect(mockOnSave).toHaveBeenCalledWith(
        expect.objectContaining({
          enabledCategories: expect.not.arrayContaining(['identifier']),
        })
      );
    });

    it('disables category checkboxes when PII detection is off', () => {
      const disabledSettings: PIISettings = {
        ...mockSettings,
        enabled: false,
      };

      render(<PIIRedactionSettings settings={disabledSettings} onSave={mockOnSave} />);

      const identifierCheckbox = screen.getByRole('checkbox', { name: /identifier/i });
      expect(identifierCheckbox).toBeDisabled();
    });
  });

  describe('Save Functionality', () => {
    it('calls onSave with updated settings', async () => {
      const user = userEvent.setup();
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      // Make multiple changes
      const toggles = screen.getAllByRole('button', { name: '' });
      await user.click(toggles[0]); // Toggle PII detection off

      const redactionCharInput = screen.getByLabelText('Redaction Character');
      await user.clear(redactionCharInput);
      await user.type(redactionCharInput, '#');

      const healthCheckbox = screen.getByRole('checkbox', { name: /health/i });
      await user.click(healthCheckbox);

      await user.click(screen.getByText('Save Changes'));

      expect(mockOnSave).toHaveBeenCalledWith({
        enabled: false,
        autoRedact: false,
        redactionChar: '#',
        detectionThreshold: 0.7,
        enabledCategories: expect.arrayContaining(['identifier', 'contact', 'financial', 'health']),
      });
    });

    it('hides Save Changes button after save', async () => {
      const user = userEvent.setup();
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      const toggles = screen.getAllByRole('button', { name: '' });
      await user.click(toggles[0]);

      expect(screen.getByText('Save Changes')).toBeInTheDocument();

      await user.click(screen.getByText('Save Changes'));

      // Button should disappear after save
      expect(screen.queryByText('Save Changes')).not.toBeInTheDocument();
    });
  });

  describe('Initial State', () => {
    it('loads with correct initial values', () => {
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      expect(screen.getByText('PII Detection Active')).toBeInTheDocument();
      expect(screen.getByDisplayValue('*')).toBeInTheDocument();
      expect(screen.getByText(/70%/i)).toBeInTheDocument();

      const identifierCheckbox = screen.getByRole('checkbox', { name: /identifier/i });
      expect(identifierCheckbox).toBeChecked();
    });

    it('does not show Save Changes button initially', () => {
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      expect(screen.queryByText('Save Changes')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has accessible labels for all inputs', () => {
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      expect(screen.getByLabelText('Redaction Character')).toBeInTheDocument();
      expect(screen.getByLabelText(/Detection Confidence Threshold/i)).toBeInTheDocument();
    });

    it('uses semantic checkboxes for categories', () => {
      render(<PIIRedactionSettings settings={mockSettings} onSave={mockOnSave} />);

      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes.length).toBe(6); // 6 categories
    });

    it('disables controls appropriately when PII detection is off', () => {
      const disabledSettings: PIISettings = {
        ...mockSettings,
        enabled: false,
      };

      render(<PIIRedactionSettings settings={disabledSettings} onSave={mockOnSave} />);

      const toggles = screen.getAllByRole('button', { name: '' });
      const redactionCharInput = screen.getByLabelText('Redaction Character');
      const thresholdSlider = screen.getByLabelText(/Detection Confidence Threshold/i);
      const checkboxes = screen.getAllByRole('checkbox');

      // Auto-redact toggle should be disabled
      expect(toggles[1]).toBeDisabled();
      // Redaction char input should be disabled
      expect(redactionCharInput).toBeDisabled();
      // Threshold slider should be disabled
      expect(thresholdSlider).toBeDisabled();
      // All category checkboxes should be disabled
      checkboxes.forEach((checkbox) => {
        expect(checkbox).toBeDisabled();
      });
    });
  });
});

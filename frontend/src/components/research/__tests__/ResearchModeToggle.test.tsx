/**
 * ResearchModeToggle Component Tests
 * Sprint 63 Feature 63.8: Full Research UI with Progress Tracking
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ResearchModeToggle, ResearchModeToggleCompact } from '../ResearchModeToggle';

describe('ResearchModeToggle', () => {
  describe('rendering', () => {
    it('renders toggle switch with correct aria attributes when disabled', () => {
      const onToggle = vi.fn();

      render(
        <ResearchModeToggle
          isEnabled={false}
          onToggle={onToggle}
        />
      );

      const toggle = screen.getByRole('switch');
      expect(toggle).toBeInTheDocument();
      expect(toggle).toHaveAttribute('aria-checked', 'false');
      expect(toggle).toHaveAttribute('aria-label', 'Research Mode aktivieren/deaktivieren');
    });

    it('renders toggle switch with correct aria attributes when enabled', () => {
      const onToggle = vi.fn();

      render(
        <ResearchModeToggle
          isEnabled={true}
          onToggle={onToggle}
        />
      );

      const toggle = screen.getByRole('switch');
      expect(toggle).toHaveAttribute('aria-checked', 'true');
    });

    it('renders Research Mode label', () => {
      render(
        <ResearchModeToggle
          isEnabled={false}
          onToggle={() => {}}
        />
      );

      expect(screen.getByText('Research Mode')).toBeInTheDocument();
    });

    it('renders with data-testid', () => {
      render(
        <ResearchModeToggle
          isEnabled={false}
          onToggle={() => {}}
        />
      );

      expect(screen.getByTestId('research-mode-toggle')).toBeInTheDocument();
    });
  });

  describe('interaction', () => {
    it('calls onToggle when clicked', () => {
      const onToggle = vi.fn();

      render(
        <ResearchModeToggle
          isEnabled={false}
          onToggle={onToggle}
        />
      );

      fireEvent.click(screen.getByRole('switch'));
      expect(onToggle).toHaveBeenCalledTimes(1);
    });

    it('does not call onToggle when disabled', () => {
      const onToggle = vi.fn();

      render(
        <ResearchModeToggle
          isEnabled={false}
          onToggle={onToggle}
          disabled={true}
        />
      );

      const toggle = screen.getByRole('switch');
      expect(toggle).toBeDisabled();

      fireEvent.click(toggle);
      expect(onToggle).not.toHaveBeenCalled();
    });
  });

  describe('styling', () => {
    it('applies enabled styling when isEnabled is true', () => {
      render(
        <ResearchModeToggle
          isEnabled={true}
          onToggle={() => {}}
        />
      );

      const toggle = screen.getByRole('switch');
      expect(toggle.className).toContain('bg-blue-600');
    });

    it('applies disabled styling when isEnabled is false', () => {
      render(
        <ResearchModeToggle
          isEnabled={false}
          onToggle={() => {}}
        />
      );

      const toggle = screen.getByRole('switch');
      expect(toggle.className).toContain('bg-gray-300');
    });

    it('applies custom className', () => {
      render(
        <ResearchModeToggle
          isEnabled={false}
          onToggle={() => {}}
          className="custom-class"
        />
      );

      expect(screen.getByTestId('research-mode-toggle').className).toContain('custom-class');
    });
  });
});

describe('ResearchModeToggleCompact', () => {
  describe('rendering', () => {
    it('renders compact button with Research label', () => {
      render(
        <ResearchModeToggleCompact
          isEnabled={false}
          onToggle={() => {}}
        />
      );

      expect(screen.getByText('Research')).toBeInTheDocument();
    });

    it('renders with data-testid', () => {
      render(
        <ResearchModeToggleCompact
          isEnabled={false}
          onToggle={() => {}}
        />
      );

      expect(screen.getByTestId('research-mode-toggle-compact')).toBeInTheDocument();
    });

    it('renders pulse indicator when enabled', () => {
      const { container } = render(
        <ResearchModeToggleCompact
          isEnabled={true}
          onToggle={() => {}}
        />
      );

      // Check for the pulse indicator span
      const pulseIndicator = container.querySelector('.animate-pulse');
      expect(pulseIndicator).toBeInTheDocument();
    });

    it('does not render pulse indicator when disabled', () => {
      const { container } = render(
        <ResearchModeToggleCompact
          isEnabled={false}
          onToggle={() => {}}
        />
      );

      const pulseIndicator = container.querySelector('.animate-pulse');
      expect(pulseIndicator).not.toBeInTheDocument();
    });
  });

  describe('interaction', () => {
    it('calls onToggle when clicked', () => {
      const onToggle = vi.fn();

      render(
        <ResearchModeToggleCompact
          isEnabled={false}
          onToggle={onToggle}
        />
      );

      fireEvent.click(screen.getByTestId('research-mode-toggle-compact'));
      expect(onToggle).toHaveBeenCalledTimes(1);
    });

    it('has correct aria-pressed attribute', () => {
      render(
        <ResearchModeToggleCompact
          isEnabled={true}
          onToggle={() => {}}
        />
      );

      expect(screen.getByTestId('research-mode-toggle-compact')).toHaveAttribute('aria-pressed', 'true');
    });
  });

  describe('styling', () => {
    it('applies enabled styling when isEnabled is true', () => {
      render(
        <ResearchModeToggleCompact
          isEnabled={true}
          onToggle={() => {}}
        />
      );

      const button = screen.getByTestId('research-mode-toggle-compact');
      expect(button.className).toContain('bg-blue-100');
      expect(button.className).toContain('text-blue-700');
    });

    it('applies disabled styling when isEnabled is false', () => {
      render(
        <ResearchModeToggleCompact
          isEnabled={false}
          onToggle={() => {}}
        />
      );

      const button = screen.getByTestId('research-mode-toggle-compact');
      expect(button.className).toContain('bg-gray-100');
      expect(button.className).toContain('text-gray-600');
    });
  });
});

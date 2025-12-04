/**
 * ThemeToggle Component Tests
 * Sprint 35 Feature 35.7: Dark Mode Preparation
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ThemeToggle, ThemeToggleIcon } from '../ThemeToggle';
import * as useDarkModeModule from '../../../hooks/useDarkMode';

// Mock the useDarkMode hook
const mockToggle = vi.fn();
const mockSetDark = vi.fn();

vi.mock('../../../hooks/useDarkMode', () => ({
  useDarkMode: vi.fn(),
}));

describe('ThemeToggle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default to light mode
    vi.mocked(useDarkModeModule.useDarkMode).mockReturnValue({
      isDark: false,
      toggle: mockToggle,
      setDark: mockSetDark,
    });
  });

  describe('button variant', () => {
    it('should render moon icon in light mode', () => {
      render(<ThemeToggle />);
      const button = screen.getByTestId('theme-toggle-button');
      expect(button).toBeInTheDocument();
    });

    it('should render sun icon in dark mode', () => {
      vi.mocked(useDarkModeModule.useDarkMode).mockReturnValue({
        isDark: true,
        toggle: mockToggle,
        setDark: mockSetDark,
      });

      render(<ThemeToggle />);
      const button = screen.getByTestId('theme-toggle-button');
      expect(button).toBeInTheDocument();
    });

    it('should call toggle when clicked', () => {
      render(<ThemeToggle />);
      const button = screen.getByTestId('theme-toggle-button');

      fireEvent.click(button);

      expect(mockToggle).toHaveBeenCalledTimes(1);
    });

    it('should show label text when showLabel is true', () => {
      render(<ThemeToggle showLabel />);
      expect(screen.getByText('Dark Mode')).toBeInTheDocument();
    });

    it('should show "Light Mode" label in dark mode', () => {
      vi.mocked(useDarkModeModule.useDarkMode).mockReturnValue({
        isDark: true,
        toggle: mockToggle,
        setDark: mockSetDark,
      });

      render(<ThemeToggle showLabel />);
      expect(screen.getByText('Light Mode')).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      render(<ThemeToggle className="custom-class" />);
      const button = screen.getByTestId('theme-toggle-button');
      expect(button.className).toContain('custom-class');
    });

    it('should have proper aria-label', () => {
      render(<ThemeToggle />);
      const button = screen.getByTestId('theme-toggle-button');
      expect(button).toHaveAttribute('aria-label', 'Switch to dark mode');
    });

    it('should have proper aria-label in dark mode', () => {
      vi.mocked(useDarkModeModule.useDarkMode).mockReturnValue({
        isDark: true,
        toggle: mockToggle,
        setDark: mockSetDark,
      });

      render(<ThemeToggle />);
      const button = screen.getByTestId('theme-toggle-button');
      expect(button).toHaveAttribute('aria-label', 'Switch to light mode');
    });
  });

  describe('switch variant', () => {
    it('should render switch element', () => {
      render(<ThemeToggle variant="switch" />);
      const button = screen.getByTestId('theme-toggle-button');
      expect(button).toHaveAttribute('role', 'switch');
    });

    it('should render switch container', () => {
      render(<ThemeToggle variant="switch" />);
      const container = screen.getByTestId('theme-toggle-switch');
      expect(container).toBeInTheDocument();
    });

    it('should show label with icon when showLabel is true', () => {
      render(<ThemeToggle variant="switch" showLabel />);
      expect(screen.getByText('Light Mode')).toBeInTheDocument();
    });

    it('should show "Dark Mode" label in dark mode', () => {
      vi.mocked(useDarkModeModule.useDarkMode).mockReturnValue({
        isDark: true,
        toggle: mockToggle,
        setDark: mockSetDark,
      });

      render(<ThemeToggle variant="switch" showLabel />);
      expect(screen.getByText('Dark Mode')).toBeInTheDocument();
    });

    it('should have proper aria-checked attribute', () => {
      render(<ThemeToggle variant="switch" />);
      const button = screen.getByTestId('theme-toggle-button');
      expect(button).toHaveAttribute('aria-checked', 'false');
    });

    it('should have aria-checked="true" in dark mode', () => {
      vi.mocked(useDarkModeModule.useDarkMode).mockReturnValue({
        isDark: true,
        toggle: mockToggle,
        setDark: mockSetDark,
      });

      render(<ThemeToggle variant="switch" />);
      const button = screen.getByTestId('theme-toggle-button');
      expect(button).toHaveAttribute('aria-checked', 'true');
    });

    it('should call toggle when clicked', () => {
      render(<ThemeToggle variant="switch" />);
      const button = screen.getByTestId('theme-toggle-button');

      fireEvent.click(button);

      expect(mockToggle).toHaveBeenCalledTimes(1);
    });
  });

  describe('ThemeToggleIcon', () => {
    it('should render icon button', () => {
      render(<ThemeToggleIcon />);
      const button = screen.getByTestId('theme-toggle-icon');
      expect(button).toBeInTheDocument();
    });

    it('should call toggle when clicked', () => {
      render(<ThemeToggleIcon />);
      const button = screen.getByTestId('theme-toggle-icon');

      fireEvent.click(button);

      expect(mockToggle).toHaveBeenCalledTimes(1);
    });

    it('should apply custom className', () => {
      render(<ThemeToggleIcon className="custom-icon-class" />);
      const button = screen.getByTestId('theme-toggle-icon');
      expect(button.className).toContain('custom-icon-class');
    });

    it('should have proper aria-label', () => {
      render(<ThemeToggleIcon />);
      const button = screen.getByTestId('theme-toggle-icon');
      expect(button).toHaveAttribute('aria-label', 'Switch to dark mode');
    });
  });

  describe('accessibility', () => {
    it('should be keyboard accessible', () => {
      render(<ThemeToggle />);
      const button = screen.getByTestId('theme-toggle-button');

      // Focus the button
      button.focus();
      expect(document.activeElement).toBe(button);
    });

    it('should have focus ring styles', () => {
      render(<ThemeToggle />);
      const button = screen.getByTestId('theme-toggle-button');
      expect(button.className).toContain('focus:outline-none');
      expect(button.className).toContain('focus:ring');
    });

    it('should have proper role for switch variant', () => {
      render(<ThemeToggle variant="switch" />);
      const button = screen.getByTestId('theme-toggle-button');
      expect(button).toHaveAttribute('role', 'switch');
    });
  });
});

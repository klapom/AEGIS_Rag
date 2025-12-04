/**
 * useDarkMode Hook Tests
 * Sprint 35 Feature 35.7: Dark Mode Preparation
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useDarkMode } from '../useDarkMode';

describe('useDarkMode', () => {
  // Save original matchMedia
  const originalMatchMedia = window.matchMedia;

  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();

    // Mock matchMedia
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });

    // Clear document classes
    document.documentElement.classList.remove('dark');
  });

  afterEach(() => {
    // Restore matchMedia
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: originalMatchMedia,
    });
  });

  describe('initialization', () => {
    it('should default to light mode when no preference is set', () => {
      const { result } = renderHook(() => useDarkMode());
      expect(result.current.isDark).toBe(false);
    });

    it('should initialize from localStorage if preference exists', () => {
      localStorage.setItem('theme', 'dark');
      const { result } = renderHook(() => useDarkMode());
      expect(result.current.isDark).toBe(true);
    });

    it('should respect light mode preference from localStorage', () => {
      localStorage.setItem('theme', 'light');
      const { result } = renderHook(() => useDarkMode());
      expect(result.current.isDark).toBe(false);
    });

    it('should detect system preference when no localStorage value exists', () => {
      // Mock system dark mode preference
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query) => ({
          matches: query === '(prefers-color-scheme: dark)',
          media: query,
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        })),
      });

      const { result } = renderHook(() => useDarkMode());
      expect(result.current.isDark).toBe(true);
    });
  });

  describe('toggle functionality', () => {
    it('should toggle dark mode on and off', () => {
      const { result } = renderHook(() => useDarkMode());

      expect(result.current.isDark).toBe(false);

      act(() => {
        result.current.toggle();
      });

      expect(result.current.isDark).toBe(true);

      act(() => {
        result.current.toggle();
      });

      expect(result.current.isDark).toBe(false);
    });

    it('should update localStorage when toggled', () => {
      const { result } = renderHook(() => useDarkMode());

      act(() => {
        result.current.toggle();
      });

      expect(localStorage.getItem('theme')).toBe('dark');

      act(() => {
        result.current.toggle();
      });

      expect(localStorage.getItem('theme')).toBe('light');
    });

    it('should add/remove dark class from document element', () => {
      const { result } = renderHook(() => useDarkMode());

      expect(document.documentElement.classList.contains('dark')).toBe(false);

      act(() => {
        result.current.toggle();
      });

      expect(document.documentElement.classList.contains('dark')).toBe(true);

      act(() => {
        result.current.toggle();
      });

      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });
  });

  describe('setDark functionality', () => {
    it('should set dark mode explicitly to true', () => {
      const { result } = renderHook(() => useDarkMode());

      act(() => {
        result.current.setDark(true);
      });

      expect(result.current.isDark).toBe(true);
      expect(localStorage.getItem('theme')).toBe('dark');
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('should set dark mode explicitly to false', () => {
      localStorage.setItem('theme', 'dark');
      const { result } = renderHook(() => useDarkMode());

      act(() => {
        result.current.setDark(false);
      });

      expect(result.current.isDark).toBe(false);
      expect(localStorage.getItem('theme')).toBe('light');
      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });
  });

  describe('system preference tracking', () => {
    it('should listen for system preference changes', () => {
      const listeners: Array<(e: MediaQueryListEvent) => void> = [];

      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation(() => ({
          matches: false,
          media: '(prefers-color-scheme: dark)',
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn((event, listener) => {
            if (event === 'change') {
              listeners.push(listener);
            }
          }),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        })),
      });

      renderHook(() => useDarkMode());

      // Should have registered a listener
      expect(listeners.length).toBeGreaterThan(0);
    });

    it('should not update when user has explicit preference', () => {
      localStorage.setItem('theme', 'light');

      const listeners: Array<(e: MediaQueryListEvent) => void> = [];

      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation(() => ({
          matches: false,
          media: '(prefers-color-scheme: dark)',
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn((event, listener) => {
            if (event === 'change') {
              listeners.push(listener);
            }
          }),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        })),
      });

      const { result } = renderHook(() => useDarkMode());

      // Simulate system preference change
      if (listeners[0]) {
        act(() => {
          listeners[0]({ matches: true } as MediaQueryListEvent);
        });
      }

      // Should remain light because user set explicit preference
      expect(result.current.isDark).toBe(false);
    });
  });

  describe('persistence', () => {
    it('should persist dark mode preference across hook instances', () => {
      const { result: result1 } = renderHook(() => useDarkMode());

      act(() => {
        result1.current.setDark(true);
      });

      // Create new hook instance
      const { result: result2 } = renderHook(() => useDarkMode());

      expect(result2.current.isDark).toBe(true);
    });

    it('should persist light mode preference across hook instances', () => {
      localStorage.setItem('theme', 'dark');
      const { result: result1 } = renderHook(() => useDarkMode());

      act(() => {
        result1.current.setDark(false);
      });

      // Create new hook instance
      const { result: result2 } = renderHook(() => useDarkMode());

      expect(result2.current.isDark).toBe(false);
    });
  });
});

/**
 * useDarkMode Hook
 * Sprint 35 Feature 35.7: Dark Mode Preparation
 *
 * Provides dark mode toggle functionality with:
 * - localStorage persistence
 * - System preference detection (prefers-color-scheme)
 * - Automatic document class management
 */

import { useState, useEffect } from 'react';

/**
 * Hook return type
 */
export interface UseDarkModeReturn {
  /** Current dark mode state */
  isDark: boolean;
  /** Toggle dark mode on/off */
  toggle: () => void;
  /** Set dark mode explicitly */
  setDark: (value: boolean) => void;
}

/**
 * Custom hook for managing dark mode state
 *
 * @returns Dark mode state and control functions
 *
 * @example
 * ```tsx
 * function App() {
 *   const { isDark, toggle } = useDarkMode();
 *
 *   return (
 *     <button onClick={toggle}>
 *       {isDark ? 'Light Mode' : 'Dark Mode'}
 *     </button>
 *   );
 * }
 * ```
 */
export function useDarkMode(): UseDarkModeReturn {
  // Initialize state from localStorage or system preference
  const [isDark, setIsDark] = useState<boolean>(() => {
    // Check if we're in browser environment
    if (typeof window === 'undefined') {
      return false;
    }

    // First, check localStorage for user preference
    const storedTheme = localStorage.getItem('theme');
    if (storedTheme !== null) {
      return storedTheme === 'dark';
    }

    // If no stored preference, check system preference
    if (window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    // Default to light mode
    return false;
  });

  // Apply dark mode class to document and persist to localStorage
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    // Update document class
    const root = document.documentElement;
    if (isDark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }

    // Persist to localStorage
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  }, [isDark]);

  // Listen for system preference changes
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) {
      return;
    }

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e: MediaQueryListEvent) => {
      // Only update if user hasn't set explicit preference
      const storedTheme = localStorage.getItem('theme');
      if (storedTheme === null) {
        setIsDark(e.matches);
      }
    };

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
    // Legacy browsers
    else if (mediaQuery.addListener) {
      mediaQuery.addListener(handleChange);
      return () => mediaQuery.removeListener(handleChange);
    }
  }, []);

  // Toggle function
  const toggle = () => {
    setIsDark((prev) => !prev);
  };

  // Explicit setter
  const setDark = (value: boolean) => {
    setIsDark(value);
  };

  return {
    isDark,
    toggle,
    setDark,
  };
}

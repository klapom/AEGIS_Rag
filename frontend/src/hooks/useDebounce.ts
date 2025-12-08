/**
 * useDebounce Hook
 * Sprint 38 Feature 38.2: Conversation Search UI
 *
 * Generic debounce hook for delaying value updates
 */

import { useState, useEffect } from 'react';

/**
 * Debounce a value by delaying updates
 *
 * @param value Value to debounce
 * @param delay Delay in milliseconds (default: 300ms)
 * @returns Debounced value
 *
 * @example
 * ```tsx
 * const [searchQuery, setSearchQuery] = useState('');
 * const debouncedQuery = useDebounce(searchQuery, 300);
 *
 * useEffect(() => {
 *   // API call with debounced value
 *   searchAPI(debouncedQuery);
 * }, [debouncedQuery]);
 * ```
 */
export function useDebounce<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    // Set up timeout to update debounced value
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    // Clean up timeout on value change or unmount
    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

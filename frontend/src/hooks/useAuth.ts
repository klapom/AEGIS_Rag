/**
 * useAuth Hook
 * Sprint 38 Feature 38.1b: JWT Authentication Frontend
 */

import { useContext } from 'react';
import { AuthContext } from '../contexts/AuthContext';
import type { AuthContextType } from '../types/auth';

/**
 * Hook to access authentication context
 * @throws Error if used outside of AuthProvider
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
}

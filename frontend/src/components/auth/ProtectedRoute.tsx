/**
 * ProtectedRoute Component
 * Sprint 38 Feature 38.1b: JWT Authentication Frontend
 */

import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Loader2 } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

/**
 * Wrapper component that protects routes requiring authentication
 * Redirects to /login if not authenticated, preserving intended destination
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <div
        className="flex items-center justify-center min-h-screen"
        data-testid="protected-route-loading"
      >
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  // Redirect to login if not authenticated, preserving intended destination
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Render protected content
  return <>{children}</>;
}

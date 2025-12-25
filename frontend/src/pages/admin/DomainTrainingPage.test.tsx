/**
 * DomainTrainingPage Component Tests
 * Sprint 64 Feature 64.2: Frontend validation improvements
 *
 * Tests:
 * - Under Development banner display
 * - Page structure
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { DomainTrainingPage } from './DomainTrainingPage';

// Mock the hooks - include all exports used by child components
vi.mock('../../hooks/useDomainTraining', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../hooks/useDomainTraining')>();
  return {
    ...actual,
    useDomains: () => ({
      data: [],
      isLoading: false,
      refetch: vi.fn(),
    }),
    useDeleteDomain: () => ({
      mutateAsync: vi.fn(),
      isLoading: false,
      error: null,
    }),
  };
});

describe('DomainTrainingPage', () => {
  const renderWithRouter = () => {
    return render(
      <MemoryRouter>
        <DomainTrainingPage />
      </MemoryRouter>
    );
  };

  describe('page structure', () => {
    it('should render the page with test id', () => {
      renderWithRouter();
      expect(screen.getByTestId('domain-training-page')).toBeInTheDocument();
    });

    it('should display page title', () => {
      renderWithRouter();
      expect(screen.getByText('Domain Training')).toBeInTheDocument();
    });

    it('should display page description', () => {
      renderWithRouter();
      expect(
        screen.getByText('Train domain-specific models with DSPy for improved query understanding')
      ).toBeInTheDocument();
    });

    it('should have back link to admin page', () => {
      renderWithRouter();
      const backLink = screen.getByText('Back to Admin');
      expect(backLink).toBeInTheDocument();
      expect(backLink.closest('a')).toHaveAttribute('href', '/admin');
    });

    it('should have new domain button', () => {
      renderWithRouter();
      expect(screen.getByTestId('new-domain-button')).toBeInTheDocument();
      expect(screen.getByText('+ New Domain')).toBeInTheDocument();
    });
  });

  describe('Under Development banner (Feature 64.2)', () => {
    it('should display the development banner', () => {
      renderWithRouter();
      expect(screen.getByTestId('development-banner')).toBeInTheDocument();
    });

    it('should have Feature Status title in banner', () => {
      renderWithRouter();
      expect(screen.getByText('Feature Status')).toBeInTheDocument();
    });

    it('should explain that DSPy training is in development', () => {
      renderWithRouter();
      expect(
        screen.getByText(/DSPy domain training is currently in active development/)
      ).toBeInTheDocument();
    });

    it('should mention that metrics may be simulated', () => {
      renderWithRouter();
      expect(
        screen.getByText(/metrics may be simulated during optimization/)
      ).toBeInTheDocument();
    });

    it('should mention expected release timeline', () => {
      renderWithRouter();
      expect(
        screen.getByText(/Full production-ready implementation expected in next release/)
      ).toBeInTheDocument();
    });

    it('should have proper role for accessibility', () => {
      renderWithRouter();
      const banner = screen.getByTestId('development-banner');
      expect(banner).toHaveAttribute('role', 'status');
    });

    it('should have info icon with proper aria-hidden', () => {
      renderWithRouter();
      const banner = screen.getByTestId('development-banner');
      const icon = banner.querySelector('svg');
      expect(icon).toHaveAttribute('aria-hidden', 'true');
    });
  });
});

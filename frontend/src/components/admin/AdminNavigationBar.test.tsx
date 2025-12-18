/**
 * AdminNavigationBar Component Tests
 * Sprint 51: Admin Dashboard Navigation Improvement
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { AdminNavigationBar } from './AdminNavigationBar';

describe('AdminNavigationBar', () => {
  const renderComponent = (initialRoute = '/admin') => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <AdminNavigationBar />
      </MemoryRouter>
    );
  };

  describe('rendering', () => {
    it('should render the navigation bar container', () => {
      renderComponent();
      expect(screen.getByTestId('admin-navigation-bar')).toBeInTheDocument();
    });

    it('should render all navigation links', () => {
      renderComponent();

      expect(screen.getByTestId('admin-nav-graph')).toBeInTheDocument();
      expect(screen.getByTestId('admin-nav-costs')).toBeInTheDocument();
      expect(screen.getByTestId('admin-nav-llm')).toBeInTheDocument();
      expect(screen.getByTestId('admin-nav-health')).toBeInTheDocument();
      expect(screen.getByTestId('admin-nav-training')).toBeInTheDocument();
      expect(screen.getByTestId('admin-nav-indexing')).toBeInTheDocument();
    });

    it('should display correct link labels', () => {
      renderComponent();

      expect(screen.getByText('Graph')).toBeInTheDocument();
      expect(screen.getByText('Costs')).toBeInTheDocument();
      expect(screen.getByText('LLM')).toBeInTheDocument();
      expect(screen.getByText('Health')).toBeInTheDocument();
      expect(screen.getByText('Training')).toBeInTheDocument();
      expect(screen.getByText('Indexing')).toBeInTheDocument();
    });
  });

  describe('links', () => {
    it('should have correct href attributes', () => {
      renderComponent();

      expect(screen.getByTestId('admin-nav-graph')).toHaveAttribute('href', '/admin/graph');
      expect(screen.getByTestId('admin-nav-costs')).toHaveAttribute('href', '/admin/costs');
      expect(screen.getByTestId('admin-nav-llm')).toHaveAttribute('href', '/admin/llm-config');
      expect(screen.getByTestId('admin-nav-health')).toHaveAttribute('href', '/admin/health');
      expect(screen.getByTestId('admin-nav-training')).toHaveAttribute(
        'href',
        '/admin/domain-training'
      );
      expect(screen.getByTestId('admin-nav-indexing')).toHaveAttribute('href', '/admin/indexing');
    });
  });

  describe('active state', () => {
    it('should highlight graph link when on graph page', () => {
      renderComponent('/admin/graph');

      const graphLink = screen.getByTestId('admin-nav-graph');
      expect(graphLink).toHaveAttribute('aria-current', 'page');
    });

    it('should highlight costs link when on costs page', () => {
      renderComponent('/admin/costs');

      const costsLink = screen.getByTestId('admin-nav-costs');
      expect(costsLink).toHaveAttribute('aria-current', 'page');
    });

    it('should highlight llm link when on llm-config page', () => {
      renderComponent('/admin/llm-config');

      const llmLink = screen.getByTestId('admin-nav-llm');
      expect(llmLink).toHaveAttribute('aria-current', 'page');
    });

    it('should highlight health link when on health page', () => {
      renderComponent('/admin/health');

      const healthLink = screen.getByTestId('admin-nav-health');
      expect(healthLink).toHaveAttribute('aria-current', 'page');
    });

    it('should highlight training link when on domain-training page', () => {
      renderComponent('/admin/domain-training');

      const trainingLink = screen.getByTestId('admin-nav-training');
      expect(trainingLink).toHaveAttribute('aria-current', 'page');
    });

    it('should highlight indexing link when on indexing page', () => {
      renderComponent('/admin/indexing');

      const indexingLink = screen.getByTestId('admin-nav-indexing');
      expect(indexingLink).toHaveAttribute('aria-current', 'page');
    });

    it('should not highlight any link on main admin dashboard', () => {
      renderComponent('/admin');

      // None should have aria-current="page"
      expect(screen.getByTestId('admin-nav-graph')).not.toHaveAttribute('aria-current');
      expect(screen.getByTestId('admin-nav-costs')).not.toHaveAttribute('aria-current');
      expect(screen.getByTestId('admin-nav-llm')).not.toHaveAttribute('aria-current');
      expect(screen.getByTestId('admin-nav-health')).not.toHaveAttribute('aria-current');
      expect(screen.getByTestId('admin-nav-training')).not.toHaveAttribute('aria-current');
      expect(screen.getByTestId('admin-nav-indexing')).not.toHaveAttribute('aria-current');
    });
  });

  describe('accessibility', () => {
    it('should have navigation landmark role', () => {
      renderComponent();

      const nav = screen.getByRole('navigation', { name: /admin navigation/i });
      expect(nav).toBeInTheDocument();
    });

    it('should have accessible name for navigation', () => {
      renderComponent();

      const nav = screen.getByTestId('admin-navigation-bar');
      expect(nav).toHaveAttribute('aria-label', 'Admin navigation');
    });

    it('should render links as anchor elements', () => {
      renderComponent();

      const links = screen.getAllByRole('link');
      expect(links).toHaveLength(6);
    });
  });
});

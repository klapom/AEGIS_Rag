/**
 * AdminSection Component Tests
 * Sprint 46 Feature 46.8: Admin Area Consolidation
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AdminSection } from './AdminSection';
import { Book } from 'lucide-react';

describe('AdminSection', () => {
  const defaultProps = {
    title: 'Test Section',
    icon: <Book data-testid="test-icon" />,
    testId: 'test-section',
    children: <div data-testid="section-content">Content</div>,
  };

  describe('rendering', () => {
    it('should render with title and icon', () => {
      render(<AdminSection {...defaultProps} />);

      expect(screen.getByText('Test Section')).toBeInTheDocument();
      expect(screen.getByTestId('test-icon')).toBeInTheDocument();
    });

    it('should render children content when expanded', () => {
      render(<AdminSection {...defaultProps} defaultExpanded={true} />);

      expect(screen.getByTestId('section-content')).toBeInTheDocument();
      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('should not render children when collapsed', () => {
      render(<AdminSection {...defaultProps} defaultExpanded={false} />);

      expect(screen.queryByTestId('section-content')).not.toBeInTheDocument();
    });

    it('should render action button when provided', () => {
      const action = <button data-testid="action-button">Action</button>;
      render(<AdminSection {...defaultProps} action={action} />);

      expect(screen.getByTestId('action-button')).toBeInTheDocument();
    });
  });

  describe('expand/collapse behavior', () => {
    it('should toggle content on header click', () => {
      render(<AdminSection {...defaultProps} defaultExpanded={true} />);

      // Initially expanded
      expect(screen.getByTestId('section-content')).toBeInTheDocument();

      // Click to collapse
      const header = screen.getByRole('button', { name: /test section/i });
      fireEvent.click(header);

      // Should be collapsed
      expect(screen.queryByTestId('section-content')).not.toBeInTheDocument();

      // Click to expand again
      fireEvent.click(header);
      expect(screen.getByTestId('section-content')).toBeInTheDocument();
    });

    it('should toggle content on Enter key', () => {
      render(<AdminSection {...defaultProps} defaultExpanded={true} />);

      const header = screen.getByRole('button', { name: /test section/i });
      fireEvent.keyDown(header, { key: 'Enter' });

      expect(screen.queryByTestId('section-content')).not.toBeInTheDocument();
    });

    it('should toggle content on Space key', () => {
      render(<AdminSection {...defaultProps} defaultExpanded={true} />);

      const header = screen.getByRole('button', { name: /test section/i });
      fireEvent.keyDown(header, { key: ' ' });

      expect(screen.queryByTestId('section-content')).not.toBeInTheDocument();
    });

    it('should show correct expand/collapse icon', () => {
      const { container } = render(
        <AdminSection {...defaultProps} defaultExpanded={true} />
      );

      // ChevronDown when expanded
      expect(container.querySelector('svg.lucide-chevron-down')).toBeInTheDocument();

      // Click to collapse
      const header = screen.getByRole('button', { name: /test section/i });
      fireEvent.click(header);

      // ChevronRight when collapsed
      expect(container.querySelector('svg.lucide-chevron-right')).toBeInTheDocument();
    });
  });

  describe('action button behavior', () => {
    it('should not toggle section when clicking action button', () => {
      const actionClick = vi.fn();
      const action = (
        <button data-testid="action-button" onClick={actionClick}>
          Action
        </button>
      );
      render(<AdminSection {...defaultProps} action={action} defaultExpanded={true} />);

      fireEvent.click(screen.getByTestId('action-button'));

      // Section should still be expanded
      expect(screen.getByTestId('section-content')).toBeInTheDocument();
      expect(actionClick).toHaveBeenCalled();
    });
  });

  describe('loading state', () => {
    it('should show loading indicator when isLoading is true', () => {
      render(<AdminSection {...defaultProps} isLoading={true} />);

      expect(screen.getByTestId('admin-section-loading')).toBeInTheDocument();
      expect(screen.getByText('Loading...')).toBeInTheDocument();
      expect(screen.queryByTestId('section-content')).not.toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('should show error message when error is provided', () => {
      render(<AdminSection {...defaultProps} error="Test error message" />);

      expect(screen.getByTestId('admin-section-error')).toBeInTheDocument();
      expect(screen.getByText('Test error message')).toBeInTheDocument();
      expect(screen.queryByTestId('section-content')).not.toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('should have correct ARIA attributes', () => {
      render(<AdminSection {...defaultProps} defaultExpanded={true} />);

      const header = screen.getByRole('button', { name: /test section/i });
      expect(header).toHaveAttribute('aria-expanded', 'true');
      expect(header).toHaveAttribute('aria-controls', 'test-section-content');
    });

    it('should update aria-expanded when toggled', () => {
      render(<AdminSection {...defaultProps} defaultExpanded={true} />);

      const header = screen.getByRole('button', { name: /test section/i });
      expect(header).toHaveAttribute('aria-expanded', 'true');

      fireEvent.click(header);
      expect(header).toHaveAttribute('aria-expanded', 'false');
    });

    it('should have proper role on content region', () => {
      render(<AdminSection {...defaultProps} defaultExpanded={true} />);

      // There may be multiple regions (header button acts as implicit region)
      const regions = screen.getAllByRole('region');
      const contentRegion = regions.find(
        (r) => r.getAttribute('aria-labelledby') === 'test-section-title'
      );
      expect(contentRegion).toBeInTheDocument();
    });

    it('should be keyboard navigable', () => {
      render(<AdminSection {...defaultProps} />);

      const header = screen.getByRole('button', { name: /test section/i });
      expect(header).toHaveAttribute('tabIndex', '0');
    });
  });
});

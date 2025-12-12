/**
 * ConfidenceBadge Component Tests
 * Sprint 45 Feature 45.7: Upload Page Domain Suggestion
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConfidenceBadge } from './ConfidenceBadge';

describe('ConfidenceBadge', () => {
  describe('high confidence (> 0.8)', () => {
    it('should render green badge for score 0.9', () => {
      render(<ConfidenceBadge score={0.9} />);

      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveTextContent('High (90%)');
      expect(badge).toHaveClass('bg-green-100', 'text-green-800');
    });

    it('should render green badge for score 0.85', () => {
      render(<ConfidenceBadge score={0.85} />);

      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveTextContent('High (85%)');
      expect(badge).toHaveClass('bg-green-100', 'text-green-800');
    });
  });

  describe('medium confidence (0.5 - 0.8)', () => {
    it('should render yellow badge for score 0.7', () => {
      render(<ConfidenceBadge score={0.7} />);

      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveTextContent('Medium (70%)');
      expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800');
    });

    it('should render yellow badge for score 0.6', () => {
      render(<ConfidenceBadge score={0.6} />);

      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveTextContent('Medium (60%)');
      expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800');
    });
  });

  describe('low confidence (<= 0.5)', () => {
    it('should render red badge for score 0.5', () => {
      render(<ConfidenceBadge score={0.5} />);

      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveTextContent('Low (50%)');
      expect(badge).toHaveClass('bg-red-100', 'text-red-800');
    });

    it('should render red badge for score 0.3', () => {
      render(<ConfidenceBadge score={0.3} />);

      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveTextContent('Low (30%)');
      expect(badge).toHaveClass('bg-red-100', 'text-red-800');
    });

    it('should render red badge for score 0.1', () => {
      render(<ConfidenceBadge score={0.1} />);

      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveTextContent('Low (10%)');
      expect(badge).toHaveClass('bg-red-100', 'text-red-800');
    });
  });

  describe('edge cases', () => {
    it('should handle score 1.0', () => {
      render(<ConfidenceBadge score={1.0} />);

      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveTextContent('High (100%)');
    });

    it('should handle score 0.0', () => {
      render(<ConfidenceBadge score={0.0} />);

      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveTextContent('Low (0%)');
    });

    it('should have title attribute with percentage', () => {
      render(<ConfidenceBadge score={0.75} />);

      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveAttribute('title', 'Confidence: 75%');
    });
  });
});

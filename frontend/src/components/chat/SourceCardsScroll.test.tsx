/**
 * SourceCardsScroll Component Tests
 * Sprint 116 Feature 116.4: Citation Linking
 *
 * Tests for scroll-to-source and highlight animation functionality
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SourceCardsScroll } from './SourceCardsScroll';
import type { Source } from '../../types/chat';
import { createRef } from 'react';

describe('SourceCardsScroll', () => {
  const mockSources: Source[] = [
    {
      text: 'First source content',
      title: 'Document 1',
      source: '/path/to/doc1.pdf',
      score: 0.95,
      document_id: 'doc-1',
      context: 'Context for first document',
    },
    {
      text: 'Second source content',
      title: 'Document 2',
      source: '/path/to/doc2.pdf',
      score: 0.87,
      document_id: 'doc-2',
      context: 'Context for second document',
    },
    {
      text: 'Third source content',
      title: 'Document 3',
      source: '/path/to/doc3.pdf',
      score: 0.79,
      document_id: 'doc-3',
      context: 'Context for third document',
    },
  ];

  // Mock scrollIntoView
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Basic Rendering', () => {
    it('renders all source cards', () => {
      render(<SourceCardsScroll sources={mockSources} />);

      expect(screen.getByText('Document 1')).toBeInTheDocument();
      expect(screen.getByText('Document 2')).toBeInTheDocument();
      expect(screen.getByText('Document 3')).toBeInTheDocument();
    });

    it('displays source count in header', () => {
      render(<SourceCardsScroll sources={mockSources} />);

      expect(screen.getByText('Quellen (3)')).toBeInTheDocument();
    });

    it('renders nothing when sources array is empty', () => {
      const { container } = render(<SourceCardsScroll sources={[]} />);

      expect(container.firstChild).toBeNull();
    });

    it('applies horizontal scroll container classes', () => {
      render(<SourceCardsScroll sources={mockSources} />);

      const scrollContainer = screen.getByText('Quellen (3)').parentElement?.querySelector('.overflow-x-auto');
      expect(scrollContainer).toBeInTheDocument();
      expect(scrollContainer).toHaveClass('scroll-smooth');
    });
  });

  describe('Citation Linking (Sprint 116 Feature 116.4)', () => {
    it('exposes scrollToSource method via ref', () => {
      const ref = createRef<{ scrollToSource: (sourceId: string) => void }>();
      render(<SourceCardsScroll ref={ref} sources={mockSources} />);

      expect(ref.current).toBeDefined();
      expect(ref.current?.scrollToSource).toBeDefined();
      expect(typeof ref.current?.scrollToSource).toBe('function');
    });

    it('scrolls to source card when scrollToSource is called', () => {
      const ref = createRef<{ scrollToSource: (sourceId: string) => void }>();
      render(<SourceCardsScroll ref={ref} sources={mockSources} />);

      // Get the card element for doc-2
      const card = screen.getByText('Document 2').closest('[data-source-id]');
      expect(card).toBeInTheDocument();

      // Call scrollToSource
      ref.current?.scrollToSource('doc-2');

      // Verify scrollIntoView was called
      expect(card?.scrollIntoView).toHaveBeenCalledWith({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'center',
      });
    });

    it('adds highlight pulse animation class when scrolled to', () => {
      vi.useFakeTimers();
      const ref = createRef<{ scrollToSource: (sourceId: string) => void }>();
      render(<SourceCardsScroll ref={ref} sources={mockSources} />);

      const card = screen.getByText('Document 1').closest('[data-source-id]') as HTMLElement;

      ref.current?.scrollToSource('doc-1');

      // Check that the highlight class was added
      expect(card.classList.contains('citation-highlight-pulse')).toBe(true);

      vi.advanceTimersByTime(3000);

      // After 3 seconds, the class should be removed
      expect(card.classList.contains('citation-highlight-pulse')).toBe(false);

      vi.useRealTimers();
    });

    it('handles scrolling to source without document_id (uses fallback ID)', () => {
      const sourcesWithoutId: Source[] = [
        {
          text: 'Content',
          title: 'Document',
          score: 0.8,
        },
      ];

      const ref = createRef<{ scrollToSource: (sourceId: string) => void }>();
      render(<SourceCardsScroll ref={ref} sources={sourcesWithoutId} />);

      const card = screen.getByText('Document').closest('[data-source-id]');

      // Should use fallback ID 'source-1'
      ref.current?.scrollToSource('source-1');

      expect(card?.scrollIntoView).toHaveBeenCalled();
    });

    it('handles scrolling to non-existent source gracefully', () => {
      const ref = createRef<{ scrollToSource: (sourceId: string) => void }>();
      render(<SourceCardsScroll ref={ref} sources={mockSources} />);

      // Should not throw error
      expect(() => {
        ref.current?.scrollToSource('non-existent-id');
      }).not.toThrow();

      // scrollIntoView should not have been called
      const cards = screen.getAllByTestId('source-card-header');
      cards.forEach((card) => {
        expect(card.scrollIntoView).not.toHaveBeenCalled();
      });
    });

    it('maintains card refs map correctly', () => {
      const ref = createRef<{ scrollToSource: (sourceId: string) => void }>();
      const { rerender } = render(<SourceCardsScroll ref={ref} sources={mockSources} />);

      // Scroll to each source
      ref.current?.scrollToSource('doc-1');
      ref.current?.scrollToSource('doc-2');
      ref.current?.scrollToSource('doc-3');

      // All should have scrolled successfully
      const card1 = screen.getByText('Document 1').closest('[data-source-id]');
      const card2 = screen.getByText('Document 2').closest('[data-source-id]');
      const card3 = screen.getByText('Document 3').closest('[data-source-id]');

      expect(card1?.scrollIntoView).toHaveBeenCalled();
      expect(card2?.scrollIntoView).toHaveBeenCalled();
      expect(card3?.scrollIntoView).toHaveBeenCalled();

      // Update sources (remove one)
      rerender(<SourceCardsScroll ref={ref} sources={mockSources.slice(0, 2)} />);

      // Should not crash when scrolling to removed source
      expect(() => {
        ref.current?.scrollToSource('doc-3');
      }).not.toThrow();
    });
  });

  describe('Source with Citation Numbers (Sprint 51)', () => {
    it('supports sources with explicit citation numbers', () => {
      const sourcesWithCitations = [
        { source: mockSources[0], citationNumber: 1 },
        { source: mockSources[2], citationNumber: 3 }, // Note: skipping 2
      ];

      render(<SourceCardsScroll sources={sourcesWithCitations} />);

      // Should display citation numbers, not array indices
      expect(screen.getByText('Document 1')).toBeInTheDocument();
      expect(screen.getByText('Document 3')).toBeInTheDocument();
      expect(screen.queryByText('Document 2')).not.toBeInTheDocument();
    });

    it('uses citationNumber for source card index display', () => {
      const sourcesWithCitations = [
        { source: mockSources[0], citationNumber: 5 },
      ];

      const ref = createRef<{ scrollToSource: (sourceId: string) => void }>();
      render(<SourceCardsScroll ref={ref} sources={sourcesWithCitations} />);

      // Should be able to scroll using document_id
      ref.current?.scrollToSource('doc-1');

      const card = screen.getByText('Document 1').closest('[data-source-id]');
      expect(card?.scrollIntoView).toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('uses smooth scroll for better UX', () => {
      const ref = createRef<{ scrollToSource: (sourceId: string) => void }>();
      render(<SourceCardsScroll ref={ref} sources={mockSources} />);

      ref.current?.scrollToSource('doc-1');

      const card = screen.getByText('Document 1').closest('[data-source-id]');
      expect(card?.scrollIntoView).toHaveBeenCalledWith(
        expect.objectContaining({ behavior: 'smooth' })
      );
    });

    it('applies transition classes to cards for smooth animation', () => {
      render(<SourceCardsScroll sources={mockSources} />);

      const cards = screen.getAllByTestId('source-card-header').map((header) => header.parentElement);
      cards.forEach((card) => {
        expect(card).toHaveClass('transition-all', 'duration-300');
      });
    });
  });
});

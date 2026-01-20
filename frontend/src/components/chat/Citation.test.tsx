/**
 * Citation Component Tests
 * Sprint 62 Feature 62.4: Section-Aware Citations
 * Sprint 116 Feature 116.3: Enhanced Tooltip with Delay and Positioning
 *
 * Tests for the Citation component with section metadata display and intelligent tooltips
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { Citation } from './Citation';
import type { Source } from '../../types/chat';

describe('Citation', () => {
  const mockOnClickScrollTo = vi.fn();

  const baseSource: Source = {
    text: 'Sample source content',
    title: 'Sample Document',
    source: '/path/to/document.pdf',
    score: 0.95,
    document_id: 'doc-123',
    context: 'This is the context of the source',
  };

  beforeEach(() => {
    mockOnClickScrollTo.mockClear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Basic Rendering', () => {
    it('renders citation button with correct index', () => {
      render(
        <Citation
          sourceIndex={1}
          source={baseSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      const button = screen.getByTestId('citation');
      expect(button).toBeInTheDocument();
      expect(button).toHaveTextContent('[1]');
    });

    it('renders citation with correct styling', () => {
      render(
        <Citation
          sourceIndex={1}
          source={baseSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      const button = screen.getByTestId('citation');
      expect(button).toHaveClass('text-blue-600');
    });

    it('calls onClickScrollTo when clicked', () => {
      render(
        <Citation
          sourceIndex={1}
          source={baseSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      const button = screen.getByTestId('citation');
      fireEvent.click(button);

      expect(mockOnClickScrollTo).toHaveBeenCalledWith('doc-123');
    });

    it('sets correct aria-label', () => {
      render(
        <Citation
          sourceIndex={1}
          source={baseSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      const button = screen.getByTestId('citation');
      expect(button).toHaveAttribute('aria-label', 'Quelle 1: Sample Document');
    });
  });

  describe('Tooltip Display', () => {
    it('shows tooltip on hover after 300ms delay (Sprint 116.3)', () => {
      render(
        <Citation
          sourceIndex={1}
          source={baseSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      const button = screen.getByTestId('citation');
      fireEvent.mouseEnter(button);
      // Tooltip should not appear immediately
      expect(screen.queryByTestId('citation-tooltip')).not.toBeInTheDocument();

      // Advance timer by 300ms
      act(() => { vi.advanceTimersByTime(300); });

      const tooltip = screen.getByTestId('citation-tooltip');
      expect(tooltip).toBeInTheDocument();
    });

    it('cancels tooltip show if mouse leaves before 300ms', () => {
      render(
        <Citation
          sourceIndex={1}
          source={baseSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      const button = screen.getByTestId('citation');
      fireEvent.mouseEnter(button);
      act(() => { vi.advanceTimersByTime(0); });

      // Advance timer by 200ms (before the 300ms threshold)
      act(() => { vi.advanceTimersByTime(200); });

      // Mouse leaves before tooltip shows
      fireEvent.mouseLeave(button);

      // Advance timer past 300ms
      act(() => { vi.advanceTimersByTime(200); });

      // Tooltip should not have appeared
      expect(screen.queryByTestId('citation-tooltip')).not.toBeInTheDocument();
    });

    it('hides tooltip on mouse leave', () => {
      render(
        <Citation
          sourceIndex={1}
          source={baseSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      const button = screen.getByTestId('citation');
      act(() => { vi.advanceTimersByTime(300); });

      // Advance timer to show tooltip
      act(() => { vi.advanceTimersByTime(300); });

      // Verify tooltip is visible
      expect(screen.getByTestId('citation-tooltip')).toBeInTheDocument();

      fireEvent.mouseLeave(button);

      expect(screen.queryByTestId('citation-tooltip')).not.toBeInTheDocument();
    });

    it('displays document name in tooltip', () => {
      render(
        <Citation
          sourceIndex={1}
          source={baseSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      const button = screen.getByTestId('citation');
      fireEvent.mouseEnter(button);
      act(() => { vi.advanceTimersByTime(300); });

      vi.advanceTimersByTime(300);
      expect(screen.getByText('Sample Document')).toBeInTheDocument();
    });

    it('displays relevance score in tooltip', () => {
      render(
        <Citation
          sourceIndex={1}
          source={baseSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      const button = screen.getByTestId('citation');
      fireEvent.mouseEnter(button);
      act(() => { vi.advanceTimersByTime(300); });

      vi.advanceTimersByTime(300);
      expect(screen.getByText('95%')).toBeInTheDocument();
    });
  });

  describe('Document Type Badge (Sprint 62.4)', () => {
    it('displays PDF badge for PDF documents', () => {
      const pdfSource: Source = {
        ...baseSource,
        source: '/path/to/document.pdf',
      };

      render(
        <Citation
          sourceIndex={1}
          source={pdfSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      vi.advanceTimersByTime(300);
      const badge = screen.getByTestId('document-type-badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-red-100');
    });

    it('displays Word badge for DOCX documents', () => {
      const docxSource: Source = {
        ...baseSource,
        source: '/path/to/document.docx',
      };

      render(
        <Citation
          sourceIndex={1}
          source={docxSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      const badge = screen.getByTestId('document-type-badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-blue-100');
    });

    it('displays Markdown badge for MD documents', () => {
      const mdSource: Source = {
        ...baseSource,
        source: '/path/to/document.md',
      };

      render(
        <Citation
          sourceIndex={1}
          source={mdSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      const badge = screen.getByTestId('document-type-badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-purple-100');
    });

    it('uses document_type field when available', () => {
      const sourceWithType: Source = {
        ...baseSource,
        document_type: 'pdf',
        source: '/path/to/document.txt', // Different extension
      };

      render(
        <Citation
          sourceIndex={1}
          source={sourceWithType}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      const badge = screen.getByTestId('document-type-badge');
      expect(badge).toHaveClass('bg-red-100'); // PDF color, not TXT
    });

    it('does not display badge for unknown document type', () => {
      const unknownSource: Source = {
        ...baseSource,
        source: '/path/to/document.xyz',
      };

      render(
        <Citation
          sourceIndex={1}
          source={unknownSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      expect(screen.queryByTestId('document-type-badge')).not.toBeInTheDocument();
    });
  });

  describe('Section Display (Sprint 62.4)', () => {
    it('displays section info when section metadata is present', () => {
      const sourceWithSection: Source = {
        ...baseSource,
        section: {
          section_id: 'sec-1',
          section_title: 'Load Balancing',
          section_number: '1.2',
          section_level: 2,
        },
      };

      render(
        <Citation
          sourceIndex={1}
          source={sourceWithSection}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      const sectionInfo = screen.getByTestId('section-info');
      expect(sectionInfo).toBeInTheDocument();
      expect(sectionInfo).toHaveTextContent('Section 1.2: Load Balancing');
    });

    it('displays section level indicator', () => {
      const sourceWithSection: Source = {
        ...baseSource,
        section: {
          section_title: 'Introduction',
          section_level: 1,
        },
      };

      render(
        <Citation
          sourceIndex={1}
          source={sourceWithSection}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      const sectionInfo = screen.getByTestId('section-info');
      expect(sectionInfo).toHaveTextContent('(L1)');
    });

    it('displays section path in tooltip', () => {
      const sourceWithPath: Source = {
        ...baseSource,
        section: {
          section_title: 'Component Details',
          section_number: '1.2.1',
          section_path: ['1. Architecture', '1.2. Components', '1.2.1. Component Details'],
        },
      };

      render(
        <Citation
          sourceIndex={1}
          source={sourceWithPath}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      const sectionInfo = screen.getByTestId('section-info');
      expect(sectionInfo).toHaveAttribute(
        'title',
        '1. Architecture > 1.2. Components > 1.2.1. Component Details'
      );
    });

    it('does not display section info when no section metadata', () => {
      render(
        <Citation
          sourceIndex={1}
          source={baseSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      expect(screen.queryByTestId('section-info')).not.toBeInTheDocument();
    });

    it('extracts section from metadata field (backward compatibility)', () => {
      const legacySource: Source = {
        ...baseSource,
        metadata: {
          section_title: 'Legacy Section',
          section_number: '2.1',
        },
      };

      render(
        <Citation
          sourceIndex={1}
          source={legacySource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      const sectionInfo = screen.getByTestId('section-info');
      expect(sectionInfo).toBeInTheDocument();
      expect(sectionInfo).toHaveTextContent('Section 2.1: Legacy Section');
    });

    it('handles section with only section_number', () => {
      const sourceWithNumber: Source = {
        ...baseSource,
        section: {
          section_number: '3.1.2',
        },
      };

      render(
        <Citation
          sourceIndex={1}
          source={sourceWithNumber}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      const sectionInfo = screen.getByTestId('section-info');
      expect(sectionInfo).toHaveTextContent('Section 3.1.2');
    });

    it('handles section with only section_title', () => {
      const sourceWithTitle: Source = {
        ...baseSource,
        section: {
          section_title: 'Configuration',
        },
      };

      render(
        <Citation
          sourceIndex={1}
          source={sourceWithTitle}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      const sectionInfo = screen.getByTestId('section-info');
      expect(sectionInfo).toHaveTextContent('Configuration');
    });
  });

  describe('Backward Compatibility', () => {
    it('renders correctly without section metadata', () => {
      const simpleSource: Source = {
        text: 'Simple content',
        title: 'Simple Doc',
        score: 0.8,
      };

      render(
        <Citation
          sourceIndex={1}
          source={simpleSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      const button = screen.getByTestId('citation');
      expect(button).toBeInTheDocument();
      expect(button).toHaveTextContent('[1]');
    });

    it('handles empty metadata object', () => {
      const sourceWithEmptyMeta: Source = {
        ...baseSource,
        metadata: {},
      };

      render(
        <Citation
          sourceIndex={1}
          source={sourceWithEmptyMeta}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      expect(screen.queryByTestId('section-info')).not.toBeInTheDocument();
    });

    it('handles null score gracefully', () => {
      const sourceNoScore: Source = {
        ...baseSource,
        score: undefined,
      };

      render(
        <Citation
          sourceIndex={1}
          source={sourceNoScore}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      expect(screen.getByText('N/A')).toBeInTheDocument();
    });
  });

  describe('Document Name Extraction', () => {
    it('extracts filename from path', () => {
      const sourceWithPath: Source = {
        ...baseSource,
        title: '/long/path/to/my-document.pdf',
      };

      render(
        <Citation
          sourceIndex={1}
          source={sourceWithPath}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      expect(screen.getByText('my-document')).toBeInTheDocument();
    });

    it('uses source field when title is not available', () => {
      const sourceWithSource: Source = {
        text: 'Content',
        source: '/path/to/source-file.pdf',
        score: 0.9,
      };

      render(
        <Citation
          sourceIndex={1}
          source={sourceWithSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      expect(screen.getByText('source-file')).toBeInTheDocument();
    });

    it('uses document_id as fallback', () => {
      const sourceWithId: Source = {
        text: 'Content',
        document_id: 'unique-doc-id',
        score: 0.9,
      };

      render(
        <Citation
          sourceIndex={1}
          source={sourceWithId}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      expect(screen.getByText('unique-doc-id')).toBeInTheDocument();
    });
  });

  describe('Retrieval Modes Display', () => {
    it('displays retrieval mode badges', () => {
      const sourceWithModes: Source = {
        ...baseSource,
        retrieval_modes: ['vector', 'bm25'],
      };

      render(
        <Citation
          sourceIndex={1}
          source={sourceWithModes}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      fireEvent.mouseEnter(screen.getByTestId('citation'));
      act(() => { vi.advanceTimersByTime(300); });
      expect(screen.getByText('vector')).toBeInTheDocument();
      expect(screen.getByText('bm25')).toBeInTheDocument();
    });
  });

  describe('Citation Linking (Sprint 116 Feature 116.4)', () => {
    it('has hover state with underline', () => {
      render(
        <Citation
          sourceIndex={1}
          source={baseSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      const button = screen.getByTestId('citation');
      expect(button).toHaveClass('hover:underline');
      expect(button).toHaveClass('hover:bg-blue-50');
    });

    it('has cursor pointer to indicate clickability', () => {
      render(
        <Citation
          sourceIndex={1}
          source={baseSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      const button = screen.getByTestId('citation');
      expect(button).toHaveClass('cursor-pointer');
    });

    it('calls onClickScrollTo with correct source ID when clicked', () => {
      render(
        <Citation
          sourceIndex={3}
          source={{ ...baseSource, document_id: 'doc-456' }}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      const button = screen.getByTestId('citation');
      fireEvent.click(button);

      expect(mockOnClickScrollTo).toHaveBeenCalledTimes(1);
      expect(mockOnClickScrollTo).toHaveBeenCalledWith('doc-456');
    });

    it('falls back to source-{index} ID when document_id is missing', () => {
      const sourceWithoutId: Source = {
        text: 'Content',
        title: 'Document',
        score: 0.8,
      };

      render(
        <Citation
          sourceIndex={5}
          source={sourceWithoutId}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      const button = screen.getByTestId('citation');
      fireEvent.click(button);

      expect(mockOnClickScrollTo).toHaveBeenCalledWith('source-5');
    });

    it('shows tooltip with "Klicken zum Scrollen" hint', () => {
      render(
        <Citation
          sourceIndex={1}
          source={baseSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      const button = screen.getByTestId('citation');
      fireEvent.mouseEnter(button);
      act(() => { vi.advanceTimersByTime(300); });

      expect(screen.getByText('Klicken zum Scrollen')).toBeInTheDocument();
    });

    it('tooltip has pointer-events-auto to allow interaction', () => {
      render(
        <Citation
          sourceIndex={1}
          source={baseSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      const button = screen.getByTestId('citation');
      fireEvent.mouseEnter(button);
      act(() => { vi.advanceTimersByTime(300); });

      const tooltip = screen.getByTestId('citation-tooltip');
      expect(tooltip).toHaveClass('pointer-events-auto');
    });

    it('prevents default behavior on click', () => {
      render(
        <Citation
          sourceIndex={1}
          source={baseSource}
          onClickScrollTo={mockOnClickScrollTo}
        />
      );

      const button = screen.getByTestId('citation');
      const clickEvent = new MouseEvent('click', { bubbles: true, cancelable: true });
      const preventDefault = vi.spyOn(clickEvent, 'preventDefault');

      button.dispatchEvent(clickEvent);

      expect(preventDefault).toHaveBeenCalled();
    });
  });
});

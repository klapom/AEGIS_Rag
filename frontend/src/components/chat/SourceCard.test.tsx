/**
 * SourceCard Component Tests
 * Sprint 62 Feature 62.4: Section-Aware Citations
 *
 * Tests for the SourceCard component with section badges and document type display
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SourceCard } from './SourceCard';
import type { Source } from '../../types/chat';

describe('SourceCard', () => {
  const baseSource: Source = {
    text: 'Sample source content for testing purposes',
    title: 'Test Document',
    source: '/path/to/test-document.pdf',
    score: 0.95,
    document_id: 'doc-123',
    context: 'This is the full context of the source document',
  };

  describe('Basic Rendering', () => {
    it('renders source card with index', () => {
      render(<SourceCard source={baseSource} index={1} />);

      expect(screen.getByText('1')).toBeInTheDocument();
      expect(screen.getByText('Test Document')).toBeInTheDocument();
    });

    it('displays score badge', () => {
      render(<SourceCard source={baseSource} index={1} />);

      expect(screen.getByText('95%')).toBeInTheDocument();
    });

    it('expands on click to show content', () => {
      render(<SourceCard source={baseSource} index={1} />);

      const header = screen.getByTestId('source-card-header');
      fireEvent.click(header);

      expect(screen.getByText('Chunk-Inhalt')).toBeInTheDocument();
      expect(screen.getByText('This is the full context of the source document')).toBeInTheDocument();
    });

    it('collapses on second click', () => {
      render(<SourceCard source={baseSource} index={1} />);

      const header = screen.getByTestId('source-card-header');
      fireEvent.click(header);
      fireEvent.click(header);

      expect(screen.queryByText('Chunk-Inhalt')).not.toBeInTheDocument();
    });
  });

  describe('Document Type Badge (Sprint 62.4)', () => {
    it('displays PDF badge for PDF documents', () => {
      const pdfSource: Source = {
        ...baseSource,
        source: '/path/to/document.pdf',
      };

      render(<SourceCard source={pdfSource} index={1} />);

      const badge = screen.getByTestId('document-type-badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-red-100');
    });

    it('displays Word badge for DOCX documents', () => {
      const docxSource: Source = {
        ...baseSource,
        source: '/path/to/document.docx',
      };

      render(<SourceCard source={docxSource} index={1} />);

      const badge = screen.getByTestId('document-type-badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-blue-100');
    });

    it('displays Markdown badge for MD documents', () => {
      const mdSource: Source = {
        ...baseSource,
        source: '/path/to/document.md',
      };

      render(<SourceCard source={mdSource} index={1} />);

      const badge = screen.getByTestId('document-type-badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-purple-100');
    });

    it('displays HTML badge for HTML documents', () => {
      const htmlSource: Source = {
        ...baseSource,
        source: '/path/to/document.html',
      };

      render(<SourceCard source={htmlSource} index={1} />);

      const badge = screen.getByTestId('document-type-badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-orange-100');
    });

    it('uses document_type field over file extension', () => {
      const sourceWithType: Source = {
        ...baseSource,
        document_type: 'pdf',
        source: '/path/to/document.txt',
      };

      render(<SourceCard source={sourceWithType} index={1} />);

      const badge = screen.getByTestId('document-type-badge');
      expect(badge).toHaveClass('bg-red-100'); // PDF color
    });

    it('does not display badge for unknown document type', () => {
      const unknownSource: Source = {
        ...baseSource,
        source: '/path/to/document.xyz',
      };

      render(<SourceCard source={unknownSource} index={1} />);

      expect(screen.queryByTestId('document-type-badge')).not.toBeInTheDocument();
    });

    it('displays document type in expanded content', () => {
      const pdfSource: Source = {
        ...baseSource,
        source: '/path/to/document.pdf',
      };

      render(<SourceCard source={pdfSource} index={1} />);

      fireEvent.click(screen.getByTestId('source-card-header'));

      const docTypeInfo = screen.getByTestId('document-type-info');
      expect(docTypeInfo).toBeInTheDocument();
      expect(docTypeInfo).toHaveTextContent('PDF');
    });
  });

  describe('Section Badge (Sprint 62.4)', () => {
    it('displays section badge when section metadata is present', () => {
      const sourceWithSection: Source = {
        ...baseSource,
        section: {
          section_id: 'sec-1',
          section_title: 'Load Balancing',
          section_number: '1.2',
          section_level: 2,
        },
      };

      render(<SourceCard source={sourceWithSection} index={1} />);

      const sectionBadge = screen.getByTestId('section-badge');
      expect(sectionBadge).toBeInTheDocument();
      expect(sectionBadge).toHaveTextContent('Section 1.2: Load Balancing');
    });

    it('displays section level indicator', () => {
      const sourceWithSection: Source = {
        ...baseSource,
        section: {
          section_title: 'Introduction',
          section_level: 1,
        },
      };

      render(<SourceCard source={sourceWithSection} index={1} />);

      const sectionBadge = screen.getByTestId('section-badge');
      expect(sectionBadge).toHaveTextContent('(L1)');
    });

    it('displays section path tooltip', () => {
      const sourceWithPath: Source = {
        ...baseSource,
        section: {
          section_title: 'Details',
          section_number: '1.2.1',
          section_path: ['1. Architecture', '1.2. Components', '1.2.1. Details'],
        },
      };

      render(<SourceCard source={sourceWithPath} index={1} />);

      const sectionBadge = screen.getByTestId('section-badge');
      expect(sectionBadge).toHaveAttribute(
        'title',
        '1. Architecture > 1.2. Components > 1.2.1. Details'
      );
    });

    it('does not display section badge when no section metadata', () => {
      render(<SourceCard source={baseSource} index={1} />);

      expect(screen.queryByTestId('section-badge')).not.toBeInTheDocument();
    });

    it('displays section path in expanded content', () => {
      const sourceWithSection: Source = {
        ...baseSource,
        section: {
          section_title: 'Configuration',
          section_number: '2.3',
          section_path: ['2. Setup', '2.3. Configuration'],
        },
      };

      render(<SourceCard source={sourceWithSection} index={1} />);

      fireEvent.click(screen.getByTestId('source-card-header'));

      const sectionPath = screen.getByTestId('section-path');
      expect(sectionPath).toBeInTheDocument();
      expect(sectionPath).toHaveTextContent('2. Setup > 2.3. Configuration');
    });

    it('extracts section from metadata field (backward compatibility)', () => {
      const legacySource: Source = {
        ...baseSource,
        metadata: {
          section_title: 'Legacy Section',
          section_number: '3.1',
        },
      };

      render(<SourceCard source={legacySource} index={1} />);

      const sectionBadge = screen.getByTestId('section-badge');
      expect(sectionBadge).toBeInTheDocument();
      expect(sectionBadge).toHaveTextContent('Section 3.1: Legacy Section');
    });

    it('handles section with only section_number', () => {
      const sourceWithNumber: Source = {
        ...baseSource,
        section: {
          section_number: '4.2',
        },
      };

      render(<SourceCard source={sourceWithNumber} index={1} />);

      const sectionBadge = screen.getByTestId('section-badge');
      expect(sectionBadge).toHaveTextContent('Section 4.2');
    });

    it('handles section with only section_title', () => {
      const sourceWithTitle: Source = {
        ...baseSource,
        section: {
          section_title: 'Appendix',
        },
      };

      render(<SourceCard source={sourceWithTitle} index={1} />);

      const sectionBadge = screen.getByTestId('section-badge');
      expect(sectionBadge).toHaveTextContent('Appendix');
    });

    it('displays page number for PDFs', () => {
      const sourceWithPage: Source = {
        ...baseSource,
        section: {
          section_title: 'Chapter 1',
          page_number: 42,
        },
      };

      render(<SourceCard source={sourceWithPage} index={1} />);

      fireEvent.click(screen.getByTestId('source-card-header'));

      expect(screen.getByText('Seite:')).toBeInTheDocument();
      expect(screen.getByText('42')).toBeInTheDocument();
    });
  });

  describe('Search Type Badge', () => {
    it('displays vector search type badge', () => {
      const vectorSource: Source = {
        ...baseSource,
        metadata: {
          search_type: 'vector',
        },
      };

      render(<SourceCard source={vectorSource} index={1} />);

      expect(screen.getByText('Vector/Embedding')).toBeInTheDocument();
    });

    it('displays BM25 search type badge', () => {
      const bm25Source: Source = {
        ...baseSource,
        metadata: {
          search_type: 'bm25',
        },
      };

      render(<SourceCard source={bm25Source} index={1} />);

      expect(screen.getByText('BM25/Keyword')).toBeInTheDocument();
    });

    it('displays graph search type badge', () => {
      const graphSource: Source = {
        ...baseSource,
        metadata: {
          search_type: 'graph',
        },
      };

      render(<SourceCard source={graphSource} index={1} />);

      expect(screen.getByText('Graph')).toBeInTheDocument();
    });
  });

  describe('Backward Compatibility', () => {
    it('renders correctly without section metadata', () => {
      const simpleSource: Source = {
        text: 'Simple content',
        title: 'Simple Doc',
        score: 0.8,
      };

      render(<SourceCard source={simpleSource} index={1} />);

      expect(screen.getByText('Simple Doc')).toBeInTheDocument();
      expect(screen.getByText('80%')).toBeInTheDocument();
    });

    it('handles empty metadata object', () => {
      const sourceWithEmptyMeta: Source = {
        ...baseSource,
        metadata: {},
      };

      render(<SourceCard source={sourceWithEmptyMeta} index={1} />);

      expect(screen.queryByTestId('section-badge')).not.toBeInTheDocument();
      expect(screen.getByText('Test Document')).toBeInTheDocument();
    });

    it('handles missing score', () => {
      const sourceNoScore: Source = {
        ...baseSource,
        score: undefined,
      };

      render(<SourceCard source={sourceNoScore} index={1} />);

      expect(screen.queryByText('%')).not.toBeInTheDocument();
    });

    it('handles zero score', () => {
      const zeroScoreSource: Source = {
        ...baseSource,
        score: 0,
      };

      render(<SourceCard source={zeroScoreSource} index={1} />);

      expect(screen.queryByText('0%')).not.toBeInTheDocument();
    });
  });

  describe('Entity Display', () => {
    it('displays entity tags in expanded view', () => {
      const sourceWithEntities: Source = {
        ...baseSource,
        entities: [
          { name: 'John Doe', type: 'person' },
          { name: 'Acme Corp', type: 'organization' },
        ],
      };

      render(<SourceCard source={sourceWithEntities} index={1} />);

      fireEvent.click(screen.getByTestId('source-card-header'));

      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
  });

  describe('Document Name Extraction', () => {
    it('extracts filename from path', () => {
      const sourceWithPath: Source = {
        ...baseSource,
        title: '/long/path/to/my-document.pdf',
      };

      render(<SourceCard source={sourceWithPath} index={1} />);

      expect(screen.getByText('my-document')).toBeInTheDocument();
    });

    it('uses source field when title not available', () => {
      const sourceWithSource: Source = {
        text: 'Content',
        source: '/path/to/source-file.pdf',
        score: 0.9,
      };

      render(<SourceCard source={sourceWithSource} index={1} />);

      expect(screen.getByText('source-file')).toBeInTheDocument();
    });

    it('uses document_id as fallback', () => {
      const sourceWithId: Source = {
        text: 'Content',
        document_id: 'unique-doc-id',
        score: 0.9,
      };

      render(<SourceCard source={sourceWithId} index={1} />);

      expect(screen.getByText('unique-doc-id')).toBeInTheDocument();
    });

    it('displays unknown document message when no identifiers', () => {
      const minimalSource: Source = {
        text: 'Content only',
      };

      render(<SourceCard source={minimalSource} index={1} />);

      expect(screen.getByText('Unbekanntes Dokument')).toBeInTheDocument();
    });
  });

  describe('Expanded Content', () => {
    it('displays chunk content', () => {
      render(<SourceCard source={baseSource} index={1} />);

      fireEvent.click(screen.getByTestId('source-card-header'));

      expect(screen.getByText('Chunk-Inhalt')).toBeInTheDocument();
      expect(
        screen.getByText('This is the full context of the source document')
      ).toBeInTheDocument();
    });

    it('displays source path', () => {
      render(<SourceCard source={baseSource} index={1} />);

      fireEvent.click(screen.getByTestId('source-card-header'));

      expect(screen.getByText('Quelle:')).toBeInTheDocument();
      expect(screen.getByText('/path/to/test-document.pdf')).toBeInTheDocument();
    });

    it('displays document ID', () => {
      render(<SourceCard source={baseSource} index={1} />);

      fireEvent.click(screen.getByTestId('source-card-header'));

      expect(screen.getByText('Doc-ID:')).toBeInTheDocument();
      expect(screen.getByText('doc-123')).toBeInTheDocument();
    });

    it('displays chunk index when available', () => {
      const sourceWithChunk: Source = {
        ...baseSource,
        chunk_index: 3,
        total_chunks: 10,
      };

      render(<SourceCard source={sourceWithChunk} index={1} />);

      fireEvent.click(screen.getByTestId('source-card-header'));

      expect(screen.getByText('Chunk:')).toBeInTheDocument();
      expect(screen.getByText('3 / 10')).toBeInTheDocument();
    });

    it('displays namespace when available', () => {
      const sourceWithNamespace: Source = {
        ...baseSource,
        metadata: {
          namespace: 'project-alpha',
        },
      };

      render(<SourceCard source={sourceWithNamespace} index={1} />);

      fireEvent.click(screen.getByTestId('source-card-header'));

      expect(screen.getByText('Namespace:')).toBeInTheDocument();
      expect(screen.getByText('project-alpha')).toBeInTheDocument();
    });
  });
});

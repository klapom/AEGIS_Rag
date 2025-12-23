/**
 * Citation Parsing Tests
 * Sprint 28 Feature 28.2
 * Sprint 62 Feature 62.4: Section-aware citations
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  parseCitationsInText,
  getSourceSectionMetadata,
  getSourceDocumentType,
  hasSourceSectionMetadata,
  enrichSourcesWithSectionMetadata,
} from './citations';
import type { Source } from '../types/chat';

describe('parseCitationsInText', () => {
  const mockSources: Source[] = [
    {
      text: 'First source content',
      title: 'Document 1',
      document_id: 'doc-1',
      score: 0.95,
      context: 'This is the first source context'
    },
    {
      text: 'Second source content',
      title: 'Document 2',
      document_id: 'doc-2',
      score: 0.87,
      context: 'This is the second source context'
    }
  ];

  const mockCallback = vi.fn();

  it('should parse single citation', () => {
    const text = 'This is a test [1] with citation';
    const result = parseCitationsInText(text, mockSources, mockCallback);

    expect(result.length).toBeGreaterThan(1);
  });

  it('should parse multiple citations', () => {
    const text = 'Test [1] and [2] citations';
    const result = parseCitationsInText(text, mockSources, mockCallback);

    expect(result.length).toBeGreaterThan(2);
  });

  it('should not parse invalid citation numbers', () => {
    const text = 'Invalid [999] citation';
    const result = parseCitationsInText(text, mockSources, mockCallback);

    // Should include the [999] as plain text
    const wrapper = render(<>{result}</>);
    expect(wrapper.container.textContent).toContain('[999]');
  });

  it('should handle text with no citations', () => {
    const text = 'This text has no citations';
    const result = parseCitationsInText(text, mockSources, mockCallback);

    expect(result.length).toBe(1);
    // When there are no citations, the text is returned as-is
    const wrapper = render(<>{result}</>);
    expect(wrapper.container.textContent).toBe(text);
  });

  it('should not parse markdown link syntax as citations', () => {
    const text = 'Link [text](url) should not be parsed';
    const result = parseCitationsInText(text, mockSources, mockCallback);

    // Should not create citation components for [text]
    expect(result.length).toBe(1);
  });

  it('should handle empty sources array', () => {
    const text = 'Test [1] with citation';
    const result = parseCitationsInText(text, [], mockCallback);

    expect(result.length).toBeGreaterThan(0);
  });

  it('should render citation components correctly', () => {
    const text = 'Test [1] citation';
    const result = parseCitationsInText(text, mockSources, mockCallback);

    const wrapper = render(<>{result}</>);
    expect(wrapper.container.textContent).toContain('Test');
    expect(wrapper.container.textContent).toContain('citation');
  });
});

/**
 * Sprint 62.4: Section Metadata Extraction Tests
 */
describe('getSourceSectionMetadata', () => {
  it('extracts section from direct section field', () => {
    const source: Source = {
      text: 'Content',
      section: {
        section_id: 'sec-1',
        section_title: 'Introduction',
        section_number: '1.0',
        section_level: 1,
      },
    };

    const section = getSourceSectionMetadata(source);
    expect(section).not.toBeNull();
    expect(section?.section_title).toBe('Introduction');
    expect(section?.section_number).toBe('1.0');
    expect(section?.section_level).toBe(1);
  });

  it('extracts section from metadata field (backward compatibility)', () => {
    const source: Source = {
      text: 'Content',
      metadata: {
        section_title: 'Legacy Section',
        section_number: '2.1',
        section_level: 2,
      },
    };

    const section = getSourceSectionMetadata(source);
    expect(section).not.toBeNull();
    expect(section?.section_title).toBe('Legacy Section');
    expect(section?.section_number).toBe('2.1');
  });

  it('returns null when no section data', () => {
    const source: Source = {
      text: 'Content',
      title: 'Document',
    };

    const section = getSourceSectionMetadata(source);
    expect(section).toBeNull();
  });

  it('returns null for empty metadata', () => {
    const source: Source = {
      text: 'Content',
      metadata: {},
    };

    const section = getSourceSectionMetadata(source);
    expect(section).toBeNull();
  });

  it('extracts section_path when available', () => {
    const source: Source = {
      text: 'Content',
      section: {
        section_title: 'Details',
        section_path: ['1. Architecture', '1.2. Components', '1.2.1. Details'],
      },
    };

    const section = getSourceSectionMetadata(source);
    expect(section?.section_path).toEqual([
      '1. Architecture',
      '1.2. Components',
      '1.2.1. Details',
    ]);
  });
});

describe('getSourceDocumentType', () => {
  it('returns document_type from direct field', () => {
    const source: Source = {
      text: 'Content',
      document_type: 'pdf',
    };

    expect(getSourceDocumentType(source)).toBe('pdf');
  });

  it('extracts document type from file extension', () => {
    const pdfSource: Source = { text: 'Content', source: '/path/to/file.pdf' };
    const docxSource: Source = { text: 'Content', source: '/path/to/file.docx' };
    const mdSource: Source = { text: 'Content', source: '/path/to/file.md' };
    const txtSource: Source = { text: 'Content', source: '/path/to/file.txt' };
    const htmlSource: Source = { text: 'Content', source: '/path/to/file.html' };

    expect(getSourceDocumentType(pdfSource)).toBe('pdf');
    expect(getSourceDocumentType(docxSource)).toBe('docx');
    expect(getSourceDocumentType(mdSource)).toBe('md');
    expect(getSourceDocumentType(txtSource)).toBe('txt');
    expect(getSourceDocumentType(htmlSource)).toBe('html');
  });

  it('returns unknown for unrecognized extensions', () => {
    const source: Source = { text: 'Content', source: '/path/to/file.xyz' };

    expect(getSourceDocumentType(source)).toBe('unknown');
  });

  it('uses title field as fallback for extension detection', () => {
    const source: Source = { text: 'Content', title: '/path/to/file.pdf' };

    expect(getSourceDocumentType(source)).toBe('pdf');
  });

  it('prefers direct document_type over file extension', () => {
    const source: Source = {
      text: 'Content',
      document_type: 'pdf',
      source: '/path/to/file.txt',
    };

    expect(getSourceDocumentType(source)).toBe('pdf');
  });
});

describe('hasSourceSectionMetadata', () => {
  it('returns true when section_title is present', () => {
    const source: Source = {
      text: 'Content',
      section: { section_title: 'Chapter 1' },
    };

    expect(hasSourceSectionMetadata(source)).toBe(true);
  });

  it('returns true when section_number is present', () => {
    const source: Source = {
      text: 'Content',
      section: { section_number: '1.2.3' },
    };

    expect(hasSourceSectionMetadata(source)).toBe(true);
  });

  it('returns true when section_id is present', () => {
    const source: Source = {
      text: 'Content',
      section: { section_id: 'sec-123' },
    };

    expect(hasSourceSectionMetadata(source)).toBe(true);
  });

  it('returns true when section_level is present and > 0', () => {
    const source: Source = {
      text: 'Content',
      section: { section_level: 2 },
    };

    expect(hasSourceSectionMetadata(source)).toBe(true);
  });

  it('returns false when no section data', () => {
    const source: Source = {
      text: 'Content',
      title: 'Document',
    };

    expect(hasSourceSectionMetadata(source)).toBe(false);
  });

  it('returns false for empty section object', () => {
    const source: Source = {
      text: 'Content',
      section: {},
    };

    expect(hasSourceSectionMetadata(source)).toBe(false);
  });
});

describe('enrichSourcesWithSectionMetadata', () => {
  it('enriches sources with normalized section data', () => {
    const sources: Source[] = [
      {
        text: 'Content 1',
        metadata: {
          section_title: 'Introduction',
          section_number: '1.0',
        },
        source: '/path/to/file.pdf',
      },
      {
        text: 'Content 2',
        section: {
          section_title: 'Chapter 2',
        },
        source: '/path/to/file.docx',
      },
    ];

    const enriched = enrichSourcesWithSectionMetadata(sources);

    expect(enriched[0].section?.section_title).toBe('Introduction');
    expect(enriched[0].document_type).toBe('pdf');
    expect(enriched[1].section?.section_title).toBe('Chapter 2');
    expect(enriched[1].document_type).toBe('docx');
  });

  it('preserves existing section data', () => {
    const sources: Source[] = [
      {
        text: 'Content',
        section: {
          section_title: 'Existing',
          section_level: 1,
        },
      },
    ];

    const enriched = enrichSourcesWithSectionMetadata(sources);

    expect(enriched[0].section?.section_title).toBe('Existing');
    expect(enriched[0].section?.section_level).toBe(1);
  });

  it('handles sources without section data', () => {
    const sources: Source[] = [
      {
        text: 'Content',
        title: 'Document',
      },
    ];

    const enriched = enrichSourcesWithSectionMetadata(sources);

    expect(enriched[0].section).toBeUndefined();
    expect(enriched[0].document_type).toBe('unknown');
  });
});

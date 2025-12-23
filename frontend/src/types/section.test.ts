/**
 * Section Types Tests
 * Sprint 62 Feature 62.4: Section-Aware Citations
 *
 * Tests for section metadata helper functions
 */

import { describe, it, expect } from 'vitest';
import {
  extractSectionMetadata,
  getDocumentType,
  formatSectionDisplay,
  formatSectionPath,
  getSectionLevelName,
  type SectionMetadata,
} from './section';

describe('extractSectionMetadata', () => {
  it('extracts section from direct section field', () => {
    const source = {
      section: {
        section_id: 'sec-1',
        section_title: 'Introduction',
        section_number: '1.0',
        section_level: 1,
      },
    };

    const section = extractSectionMetadata(source);
    expect(section).not.toBeNull();
    expect(section?.section_id).toBe('sec-1');
    expect(section?.section_title).toBe('Introduction');
    expect(section?.section_number).toBe('1.0');
    expect(section?.section_level).toBe(1);
  });

  it('extracts section from metadata field', () => {
    const source = {
      metadata: {
        section_title: 'Chapter 2',
        section_number: '2.0',
        section_level: 1,
      },
    };

    const section = extractSectionMetadata(source);
    expect(section).not.toBeNull();
    expect(section?.section_title).toBe('Chapter 2');
    expect(section?.section_number).toBe('2.0');
  });

  it('returns null when no section data', () => {
    const source = {
      metadata: {
        other_field: 'value',
      },
    };

    const section = extractSectionMetadata(source);
    expect(section).toBeNull();
  });

  it('returns null for empty source', () => {
    const source = {};

    const section = extractSectionMetadata(source);
    expect(section).toBeNull();
  });

  it('prefers direct section field over metadata', () => {
    const source = {
      section: {
        section_title: 'Direct Section',
      },
      metadata: {
        section_title: 'Metadata Section',
      },
    };

    const section = extractSectionMetadata(source);
    expect(section?.section_title).toBe('Direct Section');
  });

  it('extracts section_path from metadata', () => {
    const source = {
      metadata: {
        section_title: 'Details',
        section_path: ['1. Arch', '1.2. Components'],
      },
    };

    const section = extractSectionMetadata(source);
    expect(section?.section_path).toEqual(['1. Arch', '1.2. Components']);
  });

  it('extracts document_type from metadata', () => {
    const source = {
      metadata: {
        section_title: 'Chapter',
        document_type: 'pdf',
      },
    };

    const section = extractSectionMetadata(source);
    expect(section?.document_type).toBe('pdf');
  });

  it('extracts page_number from metadata', () => {
    const source = {
      metadata: {
        section_title: 'Chapter',
        page_number: 42,
      },
    };

    const section = extractSectionMetadata(source);
    expect(section?.page_number).toBe(42);
  });
});

describe('getDocumentType', () => {
  it('returns pdf for .pdf files', () => {
    expect(getDocumentType({ source: '/path/to/file.pdf' })).toBe('pdf');
  });

  it('returns docx for .docx files', () => {
    expect(getDocumentType({ source: '/path/to/file.docx' })).toBe('docx');
  });

  it('returns docx for .doc files', () => {
    expect(getDocumentType({ source: '/path/to/file.doc' })).toBe('docx');
  });

  it('returns md for .md files', () => {
    expect(getDocumentType({ source: '/path/to/file.md' })).toBe('md');
  });

  it('returns md for .markdown files', () => {
    expect(getDocumentType({ source: '/path/to/file.markdown' })).toBe('md');
  });

  it('returns txt for .txt files', () => {
    expect(getDocumentType({ source: '/path/to/file.txt' })).toBe('txt');
  });

  it('returns html for .html files', () => {
    expect(getDocumentType({ source: '/path/to/file.html' })).toBe('html');
  });

  it('returns html for .htm files', () => {
    expect(getDocumentType({ source: '/path/to/file.htm' })).toBe('html');
  });

  it('returns unknown for unrecognized extensions', () => {
    expect(getDocumentType({ source: '/path/to/file.xyz' })).toBe('unknown');
  });

  it('uses title field as fallback', () => {
    expect(getDocumentType({ title: '/path/to/file.pdf' })).toBe('pdf');
  });

  it('uses metadata.document_type when available', () => {
    expect(getDocumentType({ metadata: { document_type: 'pdf' } })).toBe('pdf');
  });

  it('prefers metadata.document_type over file extension', () => {
    expect(
      getDocumentType({
        source: '/path/to/file.txt',
        metadata: { document_type: 'pdf' },
      })
    ).toBe('pdf');
  });

  it('handles empty source', () => {
    expect(getDocumentType({})).toBe('unknown');
  });
});

describe('formatSectionDisplay', () => {
  it('formats section with number and title', () => {
    const section: SectionMetadata = {
      section_number: '1.2',
      section_title: 'Load Balancing',
    };

    expect(formatSectionDisplay(section)).toBe('Section 1.2: Load Balancing');
  });

  it('formats section with only number', () => {
    const section: SectionMetadata = {
      section_number: '3.1.2',
    };

    expect(formatSectionDisplay(section)).toBe('Section 3.1.2');
  });

  it('formats section with only title', () => {
    const section: SectionMetadata = {
      section_title: 'Introduction',
    };

    expect(formatSectionDisplay(section)).toBe('Introduction');
  });

  it('returns empty string for empty section', () => {
    const section: SectionMetadata = {};

    expect(formatSectionDisplay(section)).toBe('');
  });
});

describe('formatSectionPath', () => {
  it('formats section path with arrow separators', () => {
    const section: SectionMetadata = {
      section_title: 'Details',
      section_path: ['1. Architecture', '1.2. Components', '1.2.1. Details'],
    };

    expect(formatSectionPath(section)).toBe(
      '1. Architecture > 1.2. Components > 1.2.1. Details'
    );
  });

  it('falls back to section display when no path', () => {
    const section: SectionMetadata = {
      section_number: '2.1',
      section_title: 'Configuration',
    };

    expect(formatSectionPath(section)).toBe('Section 2.1: Configuration');
  });

  it('returns empty string for empty section', () => {
    const section: SectionMetadata = {};

    expect(formatSectionPath(section)).toBe('');
  });

  it('handles single item path', () => {
    const section: SectionMetadata = {
      section_path: ['1. Introduction'],
    };

    expect(formatSectionPath(section)).toBe('1. Introduction');
  });
});

describe('getSectionLevelName', () => {
  it('returns Chapter for level 1', () => {
    expect(getSectionLevelName(1)).toBe('Chapter');
  });

  it('returns Section for level 2', () => {
    expect(getSectionLevelName(2)).toBe('Section');
  });

  it('returns Subsection for level 3', () => {
    expect(getSectionLevelName(3)).toBe('Subsection');
  });

  it('returns Subsubsection for level 4', () => {
    expect(getSectionLevelName(4)).toBe('Subsubsection');
  });

  it('returns Section for levels > 4', () => {
    expect(getSectionLevelName(5)).toBe('Section');
    expect(getSectionLevelName(10)).toBe('Section');
  });
});

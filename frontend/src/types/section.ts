/**
 * Section Metadata Types
 * Sprint 62 Feature 62.4: Section-Aware Citations
 *
 * Types for section information from document chunking.
 * These types represent section hierarchy from the backend's
 * section-aware chunking (ADR-039).
 */

/**
 * Document type enumeration
 * Represents the source document format
 */
export type DocumentType = 'pdf' | 'docx' | 'txt' | 'md' | 'html' | 'unknown';

/**
 * Section metadata from the backend search results
 * Contains information about the document section where a chunk originates
 */
export interface SectionMetadata {
  /** Unique identifier for the section */
  section_id?: string;

  /** Human-readable section title (e.g., "Load Balancing", "Introduction") */
  section_title?: string;

  /** Section level in hierarchy (1 = top-level, 2 = subsection, etc.) */
  section_level?: number;

  /** Full section hierarchy path (e.g., ["1. Architecture", "1.2. Components", "1.2.1. Load Balancing"]) */
  section_path?: string[];

  /** Section number (e.g., "1.2.1") */
  section_number?: string;

  /** Document type of the source file */
  document_type?: DocumentType;

  /** Page number in original document (for PDFs) */
  page_number?: number;
}

/**
 * Extended source with section metadata
 * Extends the base Source type with section information
 */
export interface SourceWithSection {
  /** Base source text */
  text: string;
  title?: string;
  source?: string;
  score?: number;
  metadata?: Record<string, unknown>;

  // AegisRAG-specific fields
  chunk_id?: string;
  confidence?: number;
  document_id?: string;
  chunk_index?: number;
  total_chunks?: number;
  retrieval_modes?: string[];
  context?: string;
  entities?: Array<{ name: string; type?: string }>;

  // Section metadata (Sprint 62.4)
  section?: SectionMetadata;
}

/**
 * Helper function to extract section metadata from source
 * Handles both direct section field and legacy metadata.section_* fields
 */
export function extractSectionMetadata(source: {
  section?: SectionMetadata;
  metadata?: Record<string, unknown>;
}): SectionMetadata | null {
  // Check for direct section field first
  if (source.section) {
    return source.section;
  }

  // Check for section data in metadata (backward compatibility)
  if (source.metadata) {
    const {
      section_id,
      section_title,
      section_level,
      section_path,
      section_number,
      document_type,
      page_number,
    } = source.metadata;

    // Return null if no section data present
    if (!section_id && !section_title && !section_level && !section_number) {
      return null;
    }

    return {
      section_id: section_id as string | undefined,
      section_title: section_title as string | undefined,
      section_level: section_level as number | undefined,
      section_path: section_path as string[] | undefined,
      section_number: section_number as string | undefined,
      document_type: document_type as DocumentType | undefined,
      page_number: page_number as number | undefined,
    };
  }

  return null;
}

/**
 * Helper function to get document type from file extension or metadata
 */
export function getDocumentType(source: {
  source?: string;
  title?: string;
  metadata?: Record<string, unknown>;
}): DocumentType {
  // Check metadata first
  if (source.metadata?.document_type) {
    return source.metadata.document_type as DocumentType;
  }

  // Extract from file path/name
  const filePath = source.source || source.title || '';
  const extension = filePath.split('.').pop()?.toLowerCase();

  switch (extension) {
    case 'pdf':
      return 'pdf';
    case 'docx':
    case 'doc':
      return 'docx';
    case 'txt':
      return 'txt';
    case 'md':
    case 'markdown':
      return 'md';
    case 'html':
    case 'htm':
      return 'html';
    default:
      return 'unknown';
  }
}

/**
 * Format section display string
 * Creates human-readable section reference (e.g., "Section 1.2: Load Balancing")
 */
export function formatSectionDisplay(section: SectionMetadata): string {
  if (section.section_number && section.section_title) {
    return `Section ${section.section_number}: ${section.section_title}`;
  }

  if (section.section_number) {
    return `Section ${section.section_number}`;
  }

  if (section.section_title) {
    return section.section_title;
  }

  return '';
}

/**
 * Format section path for tooltip
 * Creates hierarchical path string (e.g., "1. Architecture > 1.2. Components > 1.2.1. Load Balancing")
 */
export function formatSectionPath(section: SectionMetadata): string {
  if (section.section_path && section.section_path.length > 0) {
    return section.section_path.join(' > ');
  }

  return formatSectionDisplay(section);
}

/**
 * Get section level display name
 */
export function getSectionLevelName(level: number): string {
  switch (level) {
    case 1:
      return 'Chapter';
    case 2:
      return 'Section';
    case 3:
      return 'Subsection';
    case 4:
      return 'Subsubsection';
    default:
      return 'Section';
  }
}

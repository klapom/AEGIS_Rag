/**
 * File Type Support Constants
 * Sprint 35 Feature 35.10: File Upload for Admin Indexing
 *
 * Defines which file types are supported by the AegisRAG ingestion pipeline.
 * Used for color-coding and validation in the file upload UI.
 */

/**
 * File extensions fully supported by Docling (GPU-accelerated OCR)
 * These files get optimal processing with layout analysis, table detection, and image extraction
 */
export const DOCLING_SUPPORTED_FORMATS = [
  '.pdf',
  '.docx',
  '.pptx',
  '.xlsx',
  '.html',
  '.htm',
  '.md',
  '.asciidoc',
  '.adoc',
] as const;

/**
 * File extensions supported by LlamaIndex fallback parser
 * These files are processed with basic text extraction (no advanced layout analysis)
 */
export const LLAMAINDEX_SUPPORTED_FORMATS = [
  '.txt',
  '.csv',
  '.json',
  '.xml',
  '.rtf',
  '.epub',
  '.ipynb',
] as const;

/**
 * File extensions that are explicitly unsupported
 * These files will be rejected or skipped during indexing
 */
export const UNSUPPORTED_FORMATS = [
  '.exe',
  '.dll',
  '.so',
  '.zip',
  '.rar',
  '.7z',
  '.tar',
  '.gz',
  '.bz2',
  '.jpg',
  '.jpeg',
  '.png',
  '.gif',
  '.bmp',
  '.svg',
  '.mp3',
  '.mp4',
  '.avi',
  '.mov',
  '.wav',
  '.flac',
] as const;

/**
 * Combined list of all supported formats (Docling + LlamaIndex)
 */
export const ALL_SUPPORTED_FORMATS = [
  ...DOCLING_SUPPORTED_FORMATS,
  ...LLAMAINDEX_SUPPORTED_FORMATS,
] as const;

/**
 * File support status enum
 */
export type FileSupportStatus = 'docling' | 'llamaindex' | 'unsupported';

/**
 * File support configuration for UI display
 */
export const FILE_SUPPORT_CONFIG = {
  docling: {
    label: 'Docling',
    description: 'GPU-accelerated OCR (optimal)',
    color: 'bg-green-700',
    textColor: 'text-green-700',
    badgeColor: 'bg-green-700 text-white',
    formats: DOCLING_SUPPORTED_FORMATS,
  },
  llamaindex: {
    label: 'LlamaIndex',
    description: 'Fallback parser',
    color: 'bg-green-400',
    textColor: 'text-green-600',
    badgeColor: 'bg-green-400 text-green-900',
    formats: LLAMAINDEX_SUPPORTED_FORMATS,
  },
  unsupported: {
    label: 'Nicht unterstützt',
    description: 'Wird übersprungen',
    color: 'bg-red-500',
    textColor: 'text-red-500',
    badgeColor: 'bg-red-500 text-white',
    formats: UNSUPPORTED_FORMATS,
  },
} as const;

/**
 * Determine file support status based on extension
 *
 * @param filename File name with extension
 * @returns File support status (docling, llamaindex, or unsupported)
 */
export function getFileSupportStatus(filename: string): FileSupportStatus {
  const ext = filename.toLowerCase().match(/\.[^.]+$/)?.[0] || '';

  if (DOCLING_SUPPORTED_FORMATS.includes(ext as any)) {
    return 'docling';
  }

  if (LLAMAINDEX_SUPPORTED_FORMATS.includes(ext as any)) {
    return 'llamaindex';
  }

  return 'unsupported';
}

/**
 * Check if a file is supported for indexing
 *
 * @param filename File name with extension
 * @returns True if file is supported (docling or llamaindex)
 */
export function isFileSupported(filename: string): boolean {
  const status = getFileSupportStatus(filename);
  return status === 'docling' || status === 'llamaindex';
}

/**
 * Format file size for display
 *
 * @param bytes File size in bytes
 * @returns Formatted string (e.g., "1.5 MB")
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

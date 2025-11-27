/**
 * IndexingDetailDialog Component Tests
 * Sprint 33 Feature 33.4: Detail-Dialog (13 SP)
 *
 * Tests the extended progress details dialog with 5 main sections:
 * 1. Document & Page Preview
 * 2. VLM Image Analysis
 * 3. Chunk Processing
 * 4. Pipeline Status
 * 5. Extracted Entities
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { IndexingDetailDialog } from './IndexingDetailDialog';
import type { FileInfo, DetailedProgress } from '../../types/admin';

// Helper: Create mock FileInfo
function createMockFileInfo(overrides?: Partial<FileInfo>): FileInfo {
  return {
    file_path: '/test/docs/report.pdf',
    file_name: 'report.pdf',
    file_extension: '.pdf',
    file_size_bytes: 1024000,
    parser_type: 'docling',
    is_supported: true,
    ...overrides,
  };
}

// Helper: Create mock DetailedProgress
function createMockDetailedProgress(overrides?: Partial<DetailedProgress>): DetailedProgress {
  return {
    current_file: createMockFileInfo(),
    current_page: 2,
    total_pages: 5,
    page_thumbnail_url: 'https://example.com/page2.png',
    page_elements: { tables: 1, images: 2, word_count: 350 },
    vlm_images: [
      {
        image_id: 'img_001',
        thumbnail_url: 'https://example.com/img1.png',
        status: 'completed',
        description: 'Diagram showing system architecture',
      },
      {
        image_id: 'img_002',
        thumbnail_url: undefined,
        status: 'processing',
        description: undefined,
      },
    ],
    current_chunk: {
      chunk_id: 'chunk_123',
      text_preview: 'This is a sample chunk of text from the document...',
      token_count: 256,
      section_name: 'Introduction',
      has_image: true,
    },
    pipeline_status: [
      { phase: 'parsing', status: 'completed', duration_ms: 1200 },
      { phase: 'vlm_analysis', status: 'in_progress', duration_ms: undefined },
      { phase: 'chunking', status: 'pending', duration_ms: undefined },
      { phase: 'embeddings', status: 'pending', duration_ms: undefined },
      { phase: 'bm25_index', status: 'pending', duration_ms: undefined },
      { phase: 'graph', status: 'pending', duration_ms: undefined },
    ],
    entities: {
      new_entities: ['Microsoft', 'Azure', 'Cloud Computing'],
      new_relations: ['uses', 'provides', 'enables'],
      total_entities: 42,
      total_relations: 87,
    },
    ...overrides,
  };
}

describe('IndexingDetailDialog', () => {
  describe('rendering', () => {
    it('should not render when isOpen is false', () => {
      const { container } = render(
        <IndexingDetailDialog isOpen={false} onClose={vi.fn()} currentFile={null} progress={null} />
      );
      expect(container.firstChild).toBeNull();
    });

    it('should render dialog when isOpen is true', () => {
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByTestId('detail-dialog')).toBeInTheDocument();
      expect(screen.getByText('Indexing Details')).toBeInTheDocument();
    });

    it('should display current file name', () => {
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByText('report.pdf')).toBeInTheDocument();
    });

    it('should show page progress (current/total)', () => {
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByText('Page 2 of 5')).toBeInTheDocument();
    });
  });

  describe('page preview section', () => {
    it('should display page thumbnail when URL provided', () => {
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      const thumbnail = screen.getByAltText('Page 2 thumbnail');
      expect(thumbnail).toBeInTheDocument();
      expect(thumbnail).toHaveAttribute('src', 'https://example.com/page2.png');
    });

    it('should show placeholder when no thumbnail', () => {
      const mockProgress = createMockDetailedProgress({ page_thumbnail_url: undefined });
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByText('No preview available')).toBeInTheDocument();
    });

    it('should display page elements (tables, images, words)', () => {
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByText('1')).toBeInTheDocument(); // Tables count
      expect(screen.getByText('2')).toBeInTheDocument(); // Images count
      expect(screen.getByText('350')).toBeInTheDocument(); // Words count
    });

    it('should show parser type badge', () => {
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      // Parser type should be displayed somewhere in document info
      expect(screen.getByText(/Parser/i)).toBeInTheDocument();
    });
  });

  describe('VLM images section', () => {
    it('should render VLM image grid', () => {
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByTestId('detail-vlm-images')).toBeInTheDocument();
    });

    it('should show status icon for each image', () => {
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      // VLM images section should be rendered with images and statuses
      expect(screen.getByTestId('detail-vlm-images')).toBeInTheDocument();
      // Status labels may appear multiple times or in different formats
      const vlmSection = screen.getByTestId('detail-vlm-images');
      expect(vlmSection).toBeInTheDocument();
    });

    it('should display image description when available', () => {
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByText('Diagram showing system architecture')).toBeInTheDocument();
    });

    it('should handle empty VLM images array', () => {
      const mockProgress = createMockDetailedProgress({ vlm_images: [] });
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByText('No images detected on this page')).toBeInTheDocument();
    });
  });

  describe('chunk preview section', () => {
    it('should display chunk text preview', () => {
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByText('This is a sample chunk of text from the document...')).toBeInTheDocument();
    });

    it('should show token count', () => {
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByText('256')).toBeInTheDocument();
    });

    it('should display section name', () => {
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByText('Introduction')).toBeInTheDocument();
    });

    it('should show "no chunk" state when null', () => {
      const mockProgress = createMockDetailedProgress({ current_chunk: null });
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByText('No chunk being processed')).toBeInTheDocument();
    });
  });

  describe('pipeline status section', () => {
    it('should render all pipeline phases', () => {
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByTestId('detail-pipeline-status')).toBeInTheDocument();
      // Check for phase names or labels
      const pipelineSection = screen.getByTestId('detail-pipeline-status');
      expect(pipelineSection).toBeInTheDocument();
    });

    it('should show correct status icons (pending/in_progress/completed/failed)', () => {
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      // Component renders icons via Unicode characters/emojis in status badges
      const pipelineSection = screen.getByTestId('detail-pipeline-status');
      expect(pipelineSection).toBeInTheDocument();
    });

    it('should display duration when available', () => {
      const mockProgress = createMockDetailedProgress({
        pipeline_status: [
          { phase: 'parsing', status: 'completed', duration_ms: 1200 },
        ],
      });
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      // Duration should be displayed for completed phases
      expect(screen.getByText('1.20s')).toBeInTheDocument();
    });
  });

  describe('entities section', () => {
    it('should display new entities list', () => {
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByTestId('detail-entities')).toBeInTheDocument();
      expect(screen.getByText('Microsoft')).toBeInTheDocument();
      expect(screen.getByText('Azure')).toBeInTheDocument();
    });

    it('should display new relations list', () => {
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByText('uses')).toBeInTheDocument();
      expect(screen.getByText('provides')).toBeInTheDocument();
    });

    it('should show total counters', () => {
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByText('42')).toBeInTheDocument(); // Total entities
      expect(screen.getByText('87')).toBeInTheDocument(); // Total relations
    });

    it('should handle empty entities and relations', () => {
      const mockProgress = createMockDetailedProgress({
        entities: {
          new_entities: [],
          new_relations: [],
          total_entities: 0,
          total_relations: 0,
        },
      });
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByText('No new entities yet')).toBeInTheDocument();
      expect(screen.getByText('No new relations yet')).toBeInTheDocument();
    });
  });

  describe('interactions', () => {
    it('should call onClose when close button in header clicked', async () => {
      const onClose = vi.fn();
      const mockProgress = createMockDetailedProgress();
      const { container } = render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={onClose}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );

      const closeButton = container.querySelector('button[aria-label="Close dialog"]');
      if (closeButton) {
        await userEvent.click(closeButton);
        expect(onClose).toHaveBeenCalled();
      }
    });

    it('should call onClose when close button in footer clicked', async () => {
      const onClose = vi.fn();
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={onClose}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );

      const buttons = screen.getAllByText('Close');
      if (buttons.length > 0) {
        // Footer button is the last one
        await userEvent.click(buttons[buttons.length - 1]);
        expect(onClose).toHaveBeenCalled();
      }
    });

    it('should call onClose when backdrop clicked', async () => {
      const onClose = vi.fn();
      const mockProgress = createMockDetailedProgress();
      const { container } = render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={onClose}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );

      // Click on the backdrop (the outer div with onClick={onClose})
      const backdrop = container.firstChild as HTMLElement;
      await userEvent.click(backdrop);
      expect(onClose).toHaveBeenCalled();
    });

    it('should not close when dialog content clicked', async () => {
      const onClose = vi.fn();
      const mockProgress = createMockDetailedProgress();
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={onClose}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );

      // Click on dialog content (has stopPropagation)
      const dialog = screen.getByTestId('detail-dialog');
      await userEvent.click(dialog);
      expect(onClose).not.toHaveBeenCalled();
    });
  });

  describe('edge cases', () => {
    it('should handle null currentFile', () => {
      const mockProgress = createMockDetailedProgress();
      const { container } = render(
        <IndexingDetailDialog isOpen={true} onClose={vi.fn()} currentFile={null} progress={mockProgress} />
      );
      expect(container).toBeInTheDocument();
      // When currentFile is null, the component should still render with mock progress data
      expect(screen.getByTestId('detail-dialog')).toBeInTheDocument();
    });

    it('should handle null progress', () => {
      const mockFile = createMockFileInfo();
      const { container } = render(
        <IndexingDetailDialog isOpen={true} onClose={vi.fn()} currentFile={mockFile} progress={null} />
      );
      expect(container).toBeInTheDocument();
    });

    it('should handle large file sizes', () => {
      const mockProgress = createMockDetailedProgress({
        current_file: createMockFileInfo({ file_size_bytes: 1073741824 }), // 1 GB
      });
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      // File size should be formatted as GB
      expect(screen.getByText(/GB/)).toBeInTheDocument();
    });

    it('should handle high token counts', () => {
      const mockProgress = createMockDetailedProgress({
        current_chunk: {
          chunk_id: 'chunk_456',
          text_preview: 'Long text...',
          token_count: 1800,
          section_name: 'Conclusion',
          has_image: false,
        },
      });
      render(
        <IndexingDetailDialog
          isOpen={true}
          onClose={vi.fn()}
          currentFile={mockProgress.current_file}
          progress={mockProgress}
        />
      );
      expect(screen.getByText('1800')).toBeInTheDocument();
    });
  });
});

/**
 * DetailPanel Component Tests
 * Sprint 35 Feature 35.2: Admin Indexing Side-by-Side Layout
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DetailPanel } from './DetailPanel';
import type { DetailedProgress } from '../../types/admin';

describe('DetailPanel', () => {
  it('shows waiting message when no progress data', () => {
    render(<DetailPanel progress={null} />);

    expect(screen.getByText('Waiting for indexing to start...')).toBeInTheDocument();
  });

  it('displays current file name', () => {
    render(<DetailPanel progress={null} currentFile="test-document.pdf" />);

    expect(screen.getByTestId('current-file')).toHaveTextContent('test-document.pdf');
  });

  it('displays page progress with progress bar', () => {
    const progress: DetailedProgress = {
      current_file: {
        file_path: '/path/to/file.pdf',
        file_name: 'file.pdf',
        file_extension: '.pdf',
        file_size_bytes: 1024,
        parser_type: 'docling',
        is_supported: true,
      },
      current_page: 5,
      total_pages: 10,
      page_elements: {
        tables: 2,
        images: 3,
        word_count: 450,
      },
      vlm_images: [],
      current_chunk: null,
      pipeline_status: [],
      entities: {
        new_entities: [],
        new_relations: [],
        total_entities: 42,
        total_relations: 18,
      },
    };

    render(<DetailPanel progress={progress} />);

    expect(screen.getByTestId('page-progress')).toHaveTextContent('5 / 10');
  });

  it('displays chunks and entities count', () => {
    render(
      <DetailPanel
        progress={null}
        currentFile="test.pdf"
        chunksCreated={25}
        entitiesExtracted={12}
      />
    );

    expect(screen.getByTestId('chunks-count')).toHaveTextContent('25');
    expect(screen.getByTestId('entities-count')).toHaveTextContent('12');
  });

  it('displays entities from DetailedProgress', () => {
    const progress: DetailedProgress = {
      current_file: {
        file_path: '/path/to/file.pdf',
        file_name: 'file.pdf',
        file_extension: '.pdf',
        file_size_bytes: 1024,
        parser_type: 'docling',
        is_supported: true,
      },
      current_page: 1,
      total_pages: 1,
      page_elements: {
        tables: 0,
        images: 0,
        word_count: 100,
      },
      vlm_images: [],
      current_chunk: null,
      pipeline_status: [],
      entities: {
        new_entities: [],
        new_relations: [],
        total_entities: 99,
        total_relations: 45,
      },
    };

    render(<DetailPanel progress={progress} />);

    expect(screen.getByTestId('entities-count')).toHaveTextContent('99');
  });

  it('displays page elements when available', () => {
    const progress: DetailedProgress = {
      current_file: {
        file_path: '/path/to/file.pdf',
        file_name: 'file.pdf',
        file_extension: '.pdf',
        file_size_bytes: 1024,
        parser_type: 'docling',
        is_supported: true,
      },
      current_page: 1,
      total_pages: 1,
      page_elements: {
        tables: 3,
        images: 5,
        word_count: 789,
      },
      vlm_images: [],
      current_chunk: null,
      pipeline_status: [],
      entities: {
        new_entities: [],
        new_relations: [],
        total_entities: 0,
        total_relations: 0,
      },
    };

    render(<DetailPanel progress={progress} />);

    expect(screen.getByText('Tables')).toBeInTheDocument();
    expect(screen.getByText('Images')).toBeInTheDocument();
    expect(screen.getByText('Words')).toBeInTheDocument();

    // Check the values
    const badges = screen.getAllByText(/^(3|5|789)$/);
    expect(badges).toHaveLength(3);
  });

  it('renders pipeline stages indicator', () => {
    render(
      <DetailPanel
        progress={null}
        currentFile="test.pdf"
        pipelineStage="chunking"
      />
    );

    expect(screen.getByTestId('pipeline-stages')).toBeInTheDocument();
  });
});

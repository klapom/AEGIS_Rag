/**
 * PipelineStages Component Tests
 * Sprint 35 Feature 35.2: Admin Indexing Side-by-Side Layout
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PipelineStages } from './PipelineStages';

describe('PipelineStages', () => {
  it('renders all pipeline stages', () => {
    render(<PipelineStages />);

    expect(screen.getByText('Parsing')).toBeInTheDocument();
    expect(screen.getByText('VLM')).toBeInTheDocument();
    expect(screen.getByText('Chunking')).toBeInTheDocument();
    expect(screen.getByText('Embedding')).toBeInTheDocument();
    expect(screen.getByText('Graph')).toBeInTheDocument();
    expect(screen.getByText('Validation')).toBeInTheDocument();
  });

  it('highlights current stage in blue', () => {
    render(<PipelineStages current="chunking" />);

    const stages = screen.getByTestId('pipeline-stages');
    expect(stages).toBeInTheDocument();

    // Current stage should have blue background
    const chunkingStage = screen.getByText('Chunking');
    expect(chunkingStage).toHaveClass('bg-blue-100');
    expect(chunkingStage).toHaveClass('text-blue-800');
  });

  it('shows completed stages in green', () => {
    render(<PipelineStages current="embedding" />);

    // Parsing, VLM, Chunking should be green (completed)
    const parsingStage = screen.getByText('Parsing');
    const vlmStage = screen.getByText('VLM');
    const chunkingStage = screen.getByText('Chunking');

    expect(parsingStage).toHaveClass('bg-green-100');
    expect(vlmStage).toHaveClass('bg-green-100');
    expect(chunkingStage).toHaveClass('bg-green-100');
  });

  it('shows pending stages in gray', () => {
    render(<PipelineStages current="vlm" />);

    // Chunking, Embedding, Graph, Validation should be gray (pending)
    const graphStage = screen.getByText('Graph');
    const validationStage = screen.getByText('Validation');

    expect(graphStage).toHaveClass('bg-gray-100');
    expect(validationStage).toHaveClass('bg-gray-100');
  });

  it('handles case-insensitive current stage', () => {
    render(<PipelineStages current="PARSING" />);

    const parsingStage = screen.getByText('Parsing');
    expect(parsingStage).toHaveClass('bg-blue-100');
  });

  it('renders arrows between stages', () => {
    const { container } = render(<PipelineStages />);

    // Should have 5 arrows (6 stages - 1)
    const arrows = container.querySelectorAll('div:has(> div.text-gray-300)');
    expect(arrows.length).toBeGreaterThan(0);
  });
});

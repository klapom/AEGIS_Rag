/**
 * Unit Tests for FinalSynthesis Component
 * Sprint 116.10: Deep Research Multi-Step (13 SP)
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { FinalSynthesis } from '../FinalSynthesis';
import type { Source } from '../../../types/research';

describe('FinalSynthesis', () => {
  const mockSources: Source[] = [
    {
      text: 'Machine learning is a subset of AI that enables systems to learn from data.',
      score: 0.95,
      source_type: 'vector',
      metadata: { document_id: 'doc1' },
      entities: ['machine learning', 'AI', 'data'],
      relationships: ['is_subset_of'],
    },
    {
      text: 'Neural networks are the foundation of deep learning.',
      score: 0.88,
      source_type: 'graph',
      metadata: { document_id: 'doc2' },
      entities: ['neural networks', 'deep learning'],
      relationships: ['foundation_of'],
    },
  ];

  const defaultProps = {
    query: 'What is machine learning?',
    finalAnswer: 'Machine learning is a subset of AI that enables systems to learn and improve from experience without being explicitly programmed.',
    sources: mockSources,
    totalTimeMs: 15000,
  };

  beforeEach(() => {
    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders component with query and answer', () => {
    render(<FinalSynthesis {...defaultProps} />);

    expect(screen.getByTestId('final-synthesis')).toBeInTheDocument();
    expect(screen.getByText('Final Synthesis')).toBeInTheDocument();
    expect(screen.getByText(defaultProps.query)).toBeInTheDocument();
    expect(screen.getByText(defaultProps.finalAnswer)).toBeInTheDocument();
  });

  it('displays formatted execution time', () => {
    render(<FinalSynthesis {...defaultProps} />);

    // 15000ms = 15.0s
    expect(screen.getByText('15.0s')).toBeInTheDocument();
  });

  it('formats time correctly for different durations', () => {
    // Test milliseconds
    const { rerender } = render(<FinalSynthesis {...defaultProps} totalTimeMs={500} />);
    expect(screen.getByText('500ms')).toBeInTheDocument();

    // Test minutes and seconds
    rerender(<FinalSynthesis {...defaultProps} totalTimeMs={125000} />);
    expect(screen.getByText('2m 5s')).toBeInTheDocument();
  });

  it('copies answer to clipboard on button click', async () => {
    render(<FinalSynthesis {...defaultProps} />);

    const copyButton = screen.getByTestId('copy-answer-button');
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(defaultProps.finalAnswer);
    });

    // Should show "Copied!" feedback
    expect(screen.getByText('Copied!')).toBeInTheDocument();
  });

  it('resets copy feedback after 2 seconds', async () => {
    vi.useFakeTimers();

    render(<FinalSynthesis {...defaultProps} />);

    const copyButton = screen.getByTestId('copy-answer-button');
    fireEvent.click(copyButton);

    // Initially shows "Copied!"
    await waitFor(() => {
      expect(screen.getByText('Copied!')).toBeInTheDocument();
    });

    // After 2 seconds, should show "Copy Answer" again
    vi.advanceTimersByTime(2000);

    await waitFor(() => {
      expect(screen.getByText('Copy Answer')).toBeInTheDocument();
    });

    vi.useRealTimers();
  });

  it('toggles sources visibility on button click', () => {
    render(<FinalSynthesis {...defaultProps} />);

    const toggleButton = screen.getByTestId('toggle-sources-button');

    // Initially hidden
    expect(screen.getByText(/Show Sources \(2\)/i)).toBeInTheDocument();
    expect(screen.queryByText('Sources (2)')).not.toBeInTheDocument();

    // Click to show
    fireEvent.click(toggleButton);

    expect(screen.getByText(/Hide Sources \(2\)/i)).toBeInTheDocument();
    expect(screen.getByText('Sources (2)')).toBeInTheDocument();

    // Click to hide
    fireEvent.click(toggleButton);

    expect(screen.getByText(/Show Sources \(2\)/i)).toBeInTheDocument();
  });

  it('displays sources when expanded', () => {
    render(<FinalSynthesis {...defaultProps} />);

    const toggleButton = screen.getByTestId('toggle-sources-button');
    fireEvent.click(toggleButton);

    // Check first source
    expect(screen.getByText(/Machine learning is a subset/i)).toBeInTheDocument();
    expect(screen.getByText('vector')).toBeInTheDocument();
    expect(screen.getByText(/Score: 0.950/i)).toBeInTheDocument();

    // Check second source
    expect(screen.getByText(/Neural networks are the foundation/i)).toBeInTheDocument();
    expect(screen.getByText('graph')).toBeInTheDocument();
  });

  it('displays entities when source has them', () => {
    render(<FinalSynthesis {...defaultProps} />);

    const toggleButton = screen.getByTestId('toggle-sources-button');
    fireEvent.click(toggleButton);

    expect(screen.getByText('machine learning')).toBeInTheDocument();
    expect(screen.getByText('AI')).toBeInTheDocument();
    expect(screen.getByText('data')).toBeInTheDocument();
  });

  it('limits entities display to 5 items', () => {
    const sourceWithManyEntities: Source = {
      ...mockSources[0],
      entities: Array(8).fill('entity'),
    };

    render(
      <FinalSynthesis
        {...defaultProps}
        sources={[sourceWithManyEntities]}
      />
    );

    const toggleButton = screen.getByTestId('toggle-sources-button');
    fireEvent.click(toggleButton);

    expect(screen.getByText('+3 more')).toBeInTheDocument();
  });

  it('displays relationships when source has them', () => {
    render(<FinalSynthesis {...defaultProps} />);

    const toggleButton = screen.getByTestId('toggle-sources-button');
    fireEvent.click(toggleButton);

    expect(screen.getByText('is_subset_of')).toBeInTheDocument();
    expect(screen.getByText('foundation_of')).toBeInTheDocument();
  });

  it('calls onExport callback with correct format', () => {
    const onExport = vi.fn();

    render(<FinalSynthesis {...defaultProps} onExport={onExport} />);

    // Export markdown
    const markdownButton = screen.getByTestId('export-markdown-button');
    fireEvent.click(markdownButton);

    expect(onExport).toHaveBeenCalledWith('markdown');

    // Export PDF
    const pdfButton = screen.getByTestId('export-pdf-button');
    fireEvent.click(pdfButton);

    expect(onExport).toHaveBeenCalledWith('pdf');
  });

  it('does not show export buttons when onExport not provided', () => {
    const { onExport, ...propsWithoutExport } = defaultProps;

    render(<FinalSynthesis {...propsWithoutExport} />);

    expect(screen.queryByTestId('export-markdown-button')).not.toBeInTheDocument();
    expect(screen.queryByTestId('export-pdf-button')).not.toBeInTheDocument();
  });

  it('handles empty sources array', () => {
    render(<FinalSynthesis {...defaultProps} sources={[]} />);

    const toggleButton = screen.getByTestId('toggle-sources-button');
    expect(toggleButton).toHaveTextContent('Show Sources (0)');

    fireEvent.click(toggleButton);

    // Should not crash, but no sources to display
    expect(screen.queryByTestId('source-0')).not.toBeInTheDocument();
  });

  it('numbers sources correctly', () => {
    render(<FinalSynthesis {...defaultProps} />);

    const toggleButton = screen.getByTestId('toggle-sources-button');
    fireEvent.click(toggleButton);

    expect(screen.getByText('[1]')).toBeInTheDocument();
    expect(screen.getByText('[2]')).toBeInTheDocument();
  });
});

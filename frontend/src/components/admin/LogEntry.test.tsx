/**
 * LogEntry Component Tests
 * Sprint 35 Feature 35.2: Admin Indexing Side-by-Side Layout
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LogEntry, type LogEntryData } from './LogEntry';

describe('LogEntry', () => {
  it('renders info level log entry', () => {
    const entry: LogEntryData = {
      timestamp: '14:30:45',
      level: 'info',
      message: 'Processing file.pdf',
    };

    render(<LogEntry entry={entry} />);

    expect(screen.getByTestId('log-entry')).toBeInTheDocument();
    expect(screen.getByText('[14:30:45]')).toBeInTheDocument();
    expect(screen.getByText('Processing file.pdf')).toBeInTheDocument();
  });

  it('renders error level log entry with red color', () => {
    const entry: LogEntryData = {
      timestamp: '14:30:46',
      level: 'error',
      message: 'Failed to process file',
    };

    render(<LogEntry entry={entry} />);

    const logElement = screen.getByTestId('log-entry');
    expect(logElement).toHaveClass('text-red-600');
  });

  it('renders warning level log entry with yellow color', () => {
    const entry: LogEntryData = {
      timestamp: '14:30:47',
      level: 'warning',
      message: 'Low memory warning',
    };

    render(<LogEntry entry={entry} />);

    const logElement = screen.getByTestId('log-entry');
    expect(logElement).toHaveClass('text-yellow-600');
  });

  it('renders success level log entry with green color', () => {
    const entry: LogEntryData = {
      timestamp: '14:30:48',
      level: 'success',
      message: 'Indexing completed',
    };

    render(<LogEntry entry={entry} />);

    const logElement = screen.getByTestId('log-entry');
    expect(logElement).toHaveClass('text-green-600');
  });

  it('renders log entry with details', () => {
    const entry: LogEntryData = {
      timestamp: '14:30:49',
      level: 'info',
      message: 'Chunking started',
      details: '[chunking]',
    };

    render(<LogEntry entry={entry} />);

    expect(screen.getByText('- [chunking]')).toBeInTheDocument();
  });
});

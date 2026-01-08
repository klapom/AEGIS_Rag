/**
 * SearchInput Component Tests
 * Sprint 15 Feature 15.3
 * Sprint 79 Feature 79.6: Updated to expect graph expansion config parameter
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SearchInput } from './SearchInput';
import { DEFAULT_GRAPH_EXPANSION_CONFIG, GRAPH_EXPANSION_STORAGE_KEY } from '../../types/settings';

// Mock localStorage to provide consistent graph expansion config
const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
});

describe('SearchInput', () => {
  beforeEach(() => {
    mockLocalStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should render input field with placeholder', () => {
    const mockOnSubmit = vi.fn();
    render(<SearchInput onSubmit={mockOnSubmit} placeholder="Test placeholder" />);

    const input = screen.getByPlaceholderText('Test placeholder');
    expect(input).toBeInTheDocument();
  });

  it('should call onSubmit when Enter key is pressed', () => {
    const mockOnSubmit = vi.fn();
    render(<SearchInput onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText(/Fragen Sie/);
    fireEvent.change(input, { target: { value: 'test query' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    // Sprint 79: onSubmit now includes graph expansion config
    expect(mockOnSubmit).toHaveBeenCalledWith('test query', 'hybrid', [], DEFAULT_GRAPH_EXPANSION_CONFIG);
  });

  it('should call onSubmit when submit button is clicked', () => {
    const mockOnSubmit = vi.fn();
    render(<SearchInput onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText(/Fragen Sie/);
    fireEvent.change(input, { target: { value: 'test query' } });

    const submitButton = screen.getByTitle(/Suche starten/);
    fireEvent.click(submitButton);

    // Sprint 79: onSubmit now includes graph expansion config
    expect(mockOnSubmit).toHaveBeenCalledWith('test query', 'hybrid', [], DEFAULT_GRAPH_EXPANSION_CONFIG);
  });

  it('should not submit empty query', () => {
    const mockOnSubmit = vi.fn();
    render(<SearchInput onSubmit={mockOnSubmit} />);

    const submitButton = screen.getByTitle(/Suche starten/);
    fireEvent.click(submitButton);

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  // Sprint 52: Mode selector removed - always uses hybrid mode
  it('should always use hybrid mode', () => {
    const mockOnSubmit = vi.fn();
    render(<SearchInput onSubmit={mockOnSubmit} />);

    // Submit query
    const input = screen.getByPlaceholderText(/Fragen Sie/);
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    // Should always submit with hybrid mode (Sprint 79: includes graph expansion config)
    expect(mockOnSubmit).toHaveBeenCalledWith('test', 'hybrid', [], DEFAULT_GRAPH_EXPANSION_CONFIG);
  });

  it('should disable submit button when query is empty', () => {
    const mockOnSubmit = vi.fn();
    render(<SearchInput onSubmit={mockOnSubmit} />);

    const submitButton = screen.getByTitle(/Suche starten/) as HTMLButtonElement;
    expect(submitButton.disabled).toBe(true);
  });

  it('should enable submit button when query is not empty', () => {
    const mockOnSubmit = vi.fn();
    render(<SearchInput onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText(/Fragen Sie/);
    fireEvent.change(input, { target: { value: 'test' } });

    const submitButton = screen.getByTitle(/Suche starten/) as HTMLButtonElement;
    expect(submitButton.disabled).toBe(false);
  });

  it('should clear input field after successful submission', () => {
    const mockOnSubmit = vi.fn();
    render(<SearchInput onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText(/Fragen Sie/) as HTMLTextAreaElement;
    fireEvent.change(input, { target: { value: 'What is AI?' } });

    // Verify input has the value before submission
    expect(input.value).toBe('What is AI?');

    // Submit via button click
    const submitButton = screen.getByTitle(/Suche starten/);
    fireEvent.click(submitButton);

    // Input should be cleared immediately
    expect(input.value).toBe('');
    // Sprint 79: onSubmit now includes graph expansion config
    expect(mockOnSubmit).toHaveBeenCalledWith('What is AI?', 'hybrid', [], DEFAULT_GRAPH_EXPANSION_CONFIG);
  });

  it('should clear input field after Enter key submission', () => {
    const mockOnSubmit = vi.fn();
    render(<SearchInput onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText(/Fragen Sie/) as HTMLTextAreaElement;
    fireEvent.change(input, { target: { value: 'test query' } });

    // Verify input has the value before submission
    expect(input.value).toBe('test query');

    // Submit via Enter key
    fireEvent.keyDown(input, { key: 'Enter' });

    // Input should be cleared immediately
    expect(input.value).toBe('');
    // Sprint 79: onSubmit now includes graph expansion config
    expect(mockOnSubmit).toHaveBeenCalledWith('test query', 'hybrid', [], DEFAULT_GRAPH_EXPANSION_CONFIG);
  });
});

/**
 * SearchInput Component Tests
 * Sprint 15 Feature 15.3
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SearchInput } from './SearchInput';

describe('SearchInput', () => {
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

    expect(mockOnSubmit).toHaveBeenCalledWith('test query', 'hybrid', []);
  });

  it('should call onSubmit when submit button is clicked', () => {
    const mockOnSubmit = vi.fn();
    render(<SearchInput onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText(/Fragen Sie/);
    fireEvent.change(input, { target: { value: 'test query' } });

    const submitButton = screen.getByTitle(/Suche starten/);
    fireEvent.click(submitButton);

    expect(mockOnSubmit).toHaveBeenCalledWith('test query', 'hybrid', []);
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

    // Should always submit with hybrid mode
    expect(mockOnSubmit).toHaveBeenCalledWith('test', 'hybrid', []);
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
    expect(mockOnSubmit).toHaveBeenCalledWith('What is AI?', 'hybrid', []);
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
    expect(mockOnSubmit).toHaveBeenCalledWith('test query', 'hybrid', []);
  });
});

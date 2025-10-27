/**
 * SearchInput Component Tests
 * Sprint 15 Feature 15.3
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SearchInput, SearchMode } from './SearchInput';

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

    expect(mockOnSubmit).toHaveBeenCalledWith('test query', 'hybrid');
  });

  it('should call onSubmit when submit button is clicked', () => {
    const mockOnSubmit = vi.fn();
    render(<SearchInput onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText(/Fragen Sie/);
    fireEvent.change(input, { target: { value: 'test query' } });

    const submitButton = screen.getByTitle(/Suche starten/);
    fireEvent.click(submitButton);

    expect(mockOnSubmit).toHaveBeenCalledWith('test query', 'hybrid');
  });

  it('should not submit empty query', () => {
    const mockOnSubmit = vi.fn();
    render(<SearchInput onSubmit={mockOnSubmit} />);

    const submitButton = screen.getByTitle(/Suche starten/);
    fireEvent.click(submitButton);

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('should change mode when chip is clicked', () => {
    const mockOnSubmit = vi.fn();
    render(<SearchInput onSubmit={mockOnSubmit} />);

    // Click Vector chip
    const vectorChip = screen.getByText('Vector');
    fireEvent.click(vectorChip);

    // Submit query
    const input = screen.getByPlaceholderText(/Fragen Sie/);
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(mockOnSubmit).toHaveBeenCalledWith('test', 'vector');
  });

  it('should render all mode chips', () => {
    const mockOnSubmit = vi.fn();
    render(<SearchInput onSubmit={mockOnSubmit} />);

    expect(screen.getByText('Hybrid')).toBeInTheDocument();
    expect(screen.getByText('Vector')).toBeInTheDocument();
    expect(screen.getByText('Graph')).toBeInTheDocument();
    expect(screen.getByText('Memory')).toBeInTheDocument();
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
});

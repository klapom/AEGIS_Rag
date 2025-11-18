/**
 * Citation Parsing Tests
 * Sprint 28 Feature 28.2
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { parseCitationsInText } from './citations';
import type { Source } from '../types/chat';

describe('parseCitationsInText', () => {
  const mockSources: Source[] = [
    {
      text: 'First source content',
      title: 'Document 1',
      document_id: 'doc-1',
      score: 0.95,
      context: 'This is the first source context'
    },
    {
      text: 'Second source content',
      title: 'Document 2',
      document_id: 'doc-2',
      score: 0.87,
      context: 'This is the second source context'
    }
  ];

  const mockCallback = vi.fn();

  it('should parse single citation', () => {
    const text = 'This is a test [1] with citation';
    const result = parseCitationsInText(text, mockSources, mockCallback);

    expect(result.length).toBeGreaterThan(1);
  });

  it('should parse multiple citations', () => {
    const text = 'Test [1] and [2] citations';
    const result = parseCitationsInText(text, mockSources, mockCallback);

    expect(result.length).toBeGreaterThan(2);
  });

  it('should not parse invalid citation numbers', () => {
    const text = 'Invalid [999] citation';
    const result = parseCitationsInText(text, mockSources, mockCallback);

    // Should include the [999] as plain text
    const wrapper = render(<>{result}</>);
    expect(wrapper.container.textContent).toContain('[999]');
  });

  it('should handle text with no citations', () => {
    const text = 'This text has no citations';
    const result = parseCitationsInText(text, mockSources, mockCallback);

    expect(result.length).toBe(1);
    // When there are no citations, the text is returned as-is
    const wrapper = render(<>{result}</>);
    expect(wrapper.container.textContent).toBe(text);
  });

  it('should not parse markdown link syntax as citations', () => {
    const text = 'Link [text](url) should not be parsed';
    const result = parseCitationsInText(text, mockSources, mockCallback);

    // Should not create citation components for [text]
    expect(result.length).toBe(1);
  });

  it('should handle empty sources array', () => {
    const text = 'Test [1] with citation';
    const result = parseCitationsInText(text, [], mockCallback);

    expect(result.length).toBeGreaterThan(0);
  });

  it('should render citation components correctly', () => {
    const text = 'Test [1] citation';
    const result = parseCitationsInText(text, mockSources, mockCallback);

    const wrapper = render(<>{result}</>);
    expect(wrapper.container.textContent).toContain('Test');
    expect(wrapper.container.textContent).toContain('citation');
  });
});

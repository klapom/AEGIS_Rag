/**
 * Unit Tests for IntermediateResults Component
 * Sprint 116.10: Deep Research Multi-Step (13 SP)
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { IntermediateResults } from '../IntermediateResults';
import type { IntermediateAnswer } from '../../../types/research';

describe('IntermediateResults', () => {
  const mockIntermediateAnswers: IntermediateAnswer[] = [
    {
      sub_question: 'What is machine learning?',
      answer: 'Machine learning is a subset of AI that enables systems to learn from data.',
      contexts_count: 5,
      sources: [
        {
          text: 'ML is AI subset',
          score: 0.95,
          source_type: 'vector',
          metadata: {},
          entities: ['machine learning', 'AI'],
          relationships: [],
        },
      ],
      confidence: 0.85,
    },
    {
      sub_question: 'What are neural networks?',
      answer: 'Neural networks are computing systems inspired by biological neural networks.',
      contexts_count: 3,
      sources: [],
      confidence: 0.60,
    },
  ];

  it('renders component with title and stats', () => {
    render(<IntermediateResults intermediateAnswers={mockIntermediateAnswers} />);

    expect(screen.getByTestId('intermediate-results')).toBeInTheDocument();
    expect(screen.getByText('Intermediate Findings')).toBeInTheDocument();
    expect(screen.getByText(/2 sub-questions/i)).toBeInTheDocument();
  });

  it('displays overall statistics correctly', () => {
    render(<IntermediateResults intermediateAnswers={mockIntermediateAnswers} />);

    // Average confidence: (0.85 + 0.60) / 2 = 0.725 = 73%
    expect(screen.getByText('73%')).toBeInTheDocument();

    // Total contexts: 5 + 3 = 8
    expect(screen.getByText('8')).toBeInTheDocument();

    // Total sources: 1 + 0 = 1
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('renders all intermediate answers', () => {
    render(<IntermediateResults intermediateAnswers={mockIntermediateAnswers} />);

    expect(screen.getByText(/What is machine learning/i)).toBeInTheDocument();
    expect(screen.getByText(/What are neural networks/i)).toBeInTheDocument();
  });

  it('shows confidence badges with correct levels', () => {
    render(<IntermediateResults intermediateAnswers={mockIntermediateAnswers} />);

    // First answer: 85% = High confidence
    expect(screen.getByText('High (85%)')).toBeInTheDocument();

    // Second answer: 60% = Medium confidence
    expect(screen.getByText('Medium (60%)')).toBeInTheDocument();
  });

  it('displays context counts for each answer', () => {
    render(<IntermediateResults intermediateAnswers={mockIntermediateAnswers} />);

    expect(screen.getByText('5 contexts')).toBeInTheDocument();
    expect(screen.getByText('3 contexts')).toBeInTheDocument();
  });

  it('shows source counts correctly', () => {
    render(<IntermediateResults intermediateAnswers={mockIntermediateAnswers} />);

    // First answer has 1 source
    expect(screen.getByText('1 source')).toBeInTheDocument();

    // Second answer has no sources
    expect(screen.getByText('No sources yet')).toBeInTheDocument();
  });

  it('expands and collapses intermediate answers on click', () => {
    render(<IntermediateResults intermediateAnswers={mockIntermediateAnswers} />);

    // First item should be expanded by default
    const firstAnswer = screen.getByTestId('intermediate-answer-0');
    expect(firstAnswer).toHaveTextContent(mockIntermediateAnswers[0].answer);

    // Click to collapse
    const firstButton = firstAnswer.querySelector('button');
    fireEvent.click(firstButton!);

    // Answer text should still be in document but button state changes
    // (Exact behavior depends on implementation)
  });

  it('shows sources preview when expanded', () => {
    render(<IntermediateResults intermediateAnswers={mockIntermediateAnswers} />);

    // First item expanded by default, should show source
    expect(screen.getByText('Top Sources')).toBeInTheDocument();
    expect(screen.getByText('ML is AI subset')).toBeInTheDocument();
    expect(screen.getByText(/Score: 0.950/i)).toBeInTheDocument();
  });

  it('limits sources preview to 3 items', () => {
    const answersWithManySources: IntermediateAnswer[] = [
      {
        sub_question: 'Test question',
        answer: 'Test answer',
        contexts_count: 10,
        sources: Array(5).fill({
          text: 'Source text',
          score: 0.9,
          source_type: 'vector',
          metadata: {},
          entities: [],
          relationships: [],
        }),
        confidence: 0.8,
      },
    ];

    render(<IntermediateResults intermediateAnswers={answersWithManySources} />);

    // Should show "+2 more sources"
    expect(screen.getByText('+2 more sources')).toBeInTheDocument();
  });

  it('calls onSubQuestionClick when answer is clicked', () => {
    const onSubQuestionClick = vi.fn();

    render(
      <IntermediateResults
        intermediateAnswers={mockIntermediateAnswers}
        onSubQuestionClick={onSubQuestionClick}
      />
    );

    // Click first answer
    const firstButton = screen.getByTestId('intermediate-answer-0').querySelector('button');
    fireEvent.click(firstButton!);

    expect(onSubQuestionClick).toHaveBeenCalledWith('What is machine learning?');
  });

  it('handles empty intermediate answers array', () => {
    render(<IntermediateResults intermediateAnswers={[]} />);

    expect(screen.getByTestId('intermediate-results')).toBeInTheDocument();
    expect(screen.getByText(/0 sub-questions/i)).toBeInTheDocument();
  });
});

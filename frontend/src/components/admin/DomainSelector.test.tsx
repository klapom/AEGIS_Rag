/**
 * DomainSelector Component Tests
 * Sprint 45 Feature 45.7: Upload Page Domain Suggestion
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { DomainSelector } from './DomainSelector';
import type { ClassificationResult } from '../../hooks/useDomainTraining';

describe('DomainSelector', () => {
  const mockAlternatives: ClassificationResult[] = [
    { domain: 'finance', score: 0.85 },
    { domain: 'legal', score: 0.65 },
    { domain: 'medical', score: 0.40 },
  ];

  describe('loading state', () => {
    it('should show loading message when no alternatives', () => {
      render(<DomainSelector onChange={vi.fn()} />);

      expect(screen.getByTestId('domain-selector-loading')).toBeInTheDocument();
      expect(screen.getByText('Analyzing...')).toBeInTheDocument();
    });

    it('should show loading message when alternatives is empty array', () => {
      render(<DomainSelector alternatives={[]} onChange={vi.fn()} />);

      expect(screen.getByTestId('domain-selector-loading')).toBeInTheDocument();
    });
  });

  describe('rendering options', () => {
    it('should render select with alternatives', () => {
      render(<DomainSelector alternatives={mockAlternatives} onChange={vi.fn()} />);

      const select = screen.getByTestId('domain-selector');
      expect(select).toBeInTheDocument();
      expect(select).toContainHTML('<option value="">Select domain...</option>');
      expect(select).toContainHTML('<option value="finance">finance (85%)</option>');
      expect(select).toContainHTML('<option value="legal">legal (65%)</option>');
      expect(select).toContainHTML('<option value="medical">medical (40%)</option>');
    });

    it('should format percentages correctly', () => {
      const alternatives: ClassificationResult[] = [
        { domain: 'test', score: 0.923 },
      ];
      render(<DomainSelector alternatives={alternatives} onChange={vi.fn()} />);

      const select = screen.getByTestId('domain-selector');
      expect(select).toContainHTML('<option value="test">test (92%)</option>');
    });
  });

  describe('suggested value', () => {
    it('should auto-select suggested domain', () => {
      render(
        <DomainSelector
          suggested="finance"
          alternatives={mockAlternatives}
          onChange={vi.fn()}
        />
      );

      const select = screen.getByTestId('domain-selector') as HTMLSelectElement;
      expect(select.value).toBe('finance');
    });

    it('should call onChange with suggested domain on mount', () => {
      const onChange = vi.fn();
      render(
        <DomainSelector
          suggested="legal"
          alternatives={mockAlternatives}
          onChange={onChange}
        />
      );

      expect(onChange).toHaveBeenCalledWith('legal');
    });

    it('should update when suggested changes', () => {
      const { rerender } = render(
        <DomainSelector
          suggested="finance"
          alternatives={mockAlternatives}
          onChange={vi.fn()}
        />
      );

      let select = screen.getByTestId('domain-selector') as HTMLSelectElement;
      expect(select.value).toBe('finance');

      rerender(
        <DomainSelector
          suggested="legal"
          alternatives={mockAlternatives}
          onChange={vi.fn()}
        />
      );

      select = screen.getByTestId('domain-selector') as HTMLSelectElement;
      expect(select.value).toBe('legal');
    });
  });

  describe('user interactions', () => {
    it('should call onChange when user selects a domain', async () => {
      const onChange = vi.fn();
      const user = userEvent.setup();
      render(<DomainSelector alternatives={mockAlternatives} onChange={onChange} />);

      const select = screen.getByTestId('domain-selector');
      await user.selectOptions(select, 'legal');

      expect(onChange).toHaveBeenCalledWith('legal');
    });

    it('should allow selecting empty option', async () => {
      const onChange = vi.fn();
      const user = userEvent.setup();
      render(
        <DomainSelector
          suggested="finance"
          alternatives={mockAlternatives}
          onChange={onChange}
        />
      );

      const select = screen.getByTestId('domain-selector');
      await user.selectOptions(select, '');

      expect(onChange).toHaveBeenCalledWith('');
    });

    it('should update internal state on change', async () => {
      const user = userEvent.setup();
      render(<DomainSelector alternatives={mockAlternatives} onChange={vi.fn()} />);

      const select = screen.getByTestId('domain-selector') as HTMLSelectElement;
      await user.selectOptions(select, 'medical');

      expect(select.value).toBe('medical');
    });
  });
});

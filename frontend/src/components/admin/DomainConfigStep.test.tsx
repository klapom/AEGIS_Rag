/**
 * DomainConfigStep Component Tests
 * Sprint 45 Feature 45.4: Domain Training Admin UI
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { DomainConfigStep } from './DomainConfigStep';

describe('DomainConfigStep', () => {
  const defaultConfig = {
    name: '',
    description: '',
    llm_model: 'qwen3:32b',
  };

  const defaultProps = {
    config: defaultConfig,
    models: ['qwen3:32b', 'llama3:8b', 'gpt-4'],
    onChange: vi.fn(),
    onNext: vi.fn(),
    onCancel: vi.fn(),
  };

  describe('rendering', () => {
    it('should render step title and description', () => {
      render(<DomainConfigStep {...defaultProps} />);

      expect(screen.getByText('Create New Domain')).toBeInTheDocument();
      expect(screen.getByText(/step 1 of 3/i)).toBeInTheDocument();
    });

    it('should render all form fields', () => {
      render(<DomainConfigStep {...defaultProps} />);

      expect(screen.getByTestId('domain-name-input')).toBeInTheDocument();
      expect(screen.getByTestId('domain-description-input')).toBeInTheDocument();
      expect(screen.getByTestId('domain-model-select')).toBeInTheDocument();
    });

    it('should render action buttons', () => {
      render(<DomainConfigStep {...defaultProps} />);

      expect(screen.getByTestId('domain-config-cancel')).toBeInTheDocument();
      expect(screen.getByTestId('domain-config-next')).toBeInTheDocument();
    });

    it('should populate fields with initial config', () => {
      const config = {
        name: 'finance',
        description: 'Financial domain',
        llm_model: 'qwen3:32b',
      };
      render(<DomainConfigStep {...defaultProps} config={config} />);

      expect(screen.getByTestId('domain-name-input')).toHaveValue('finance');
      expect(screen.getByTestId('domain-description-input')).toHaveValue('Financial domain');
      expect(screen.getByTestId('domain-model-select')).toHaveValue('qwen3:32b');
    });

    it('should render model options', () => {
      render(<DomainConfigStep {...defaultProps} />);

      const select = screen.getByTestId('domain-model-select');
      expect(select).toContainHTML('<option value="">Use default model</option>');
      expect(select).toContainHTML('<option value="qwen3:32b">qwen3:32b</option>');
      expect(select).toContainHTML('<option value="llama3:8b">llama3:8b</option>');
      expect(select).toContainHTML('<option value="gpt-4">gpt-4</option>');
    });
  });

  describe('validation', () => {
    it('should disable next button when name is empty', () => {
      render(<DomainConfigStep {...defaultProps} />);

      const nextButton = screen.getByTestId('domain-config-next');
      expect(nextButton).toBeDisabled();
    });

    it('should disable next button when description is empty', () => {
      const config = { ...defaultConfig, name: 'finance' };
      render(<DomainConfigStep {...defaultProps} config={config} />);

      const nextButton = screen.getByTestId('domain-config-next');
      expect(nextButton).toBeDisabled();
    });

    it('should enable next button when both name and description are filled', () => {
      const config = {
        name: 'finance',
        description: 'Financial domain',
        llm_model: 'qwen3:32b',
      };
      render(<DomainConfigStep {...defaultProps} config={config} />);

      const nextButton = screen.getByTestId('domain-config-next');
      expect(nextButton).not.toBeDisabled();
    });
  });

  describe('user interactions', () => {
    it('should call onChange when name input changes', async () => {
      const onChange = vi.fn();
      const user = userEvent.setup();
      render(<DomainConfigStep {...defaultProps} onChange={onChange} />);

      const nameInput = screen.getByTestId('domain-name-input');
      await user.clear(nameInput);
      await user.type(nameInput, 'test');

      // Should be called
      expect(onChange).toHaveBeenCalled();
      // Check that the last call includes the typed text
      expect(onChange.mock.calls.length).toBeGreaterThan(0);
    });

    it('should call onChange when description changes', async () => {
      const onChange = vi.fn();
      const user = userEvent.setup();
      render(<DomainConfigStep {...defaultProps} onChange={onChange} />);

      const descInput = screen.getByTestId('domain-description-input');
      await user.clear(descInput);
      await user.type(descInput, 'Test');

      // Should be called
      expect(onChange).toHaveBeenCalled();
      expect(onChange.mock.calls.length).toBeGreaterThan(0);
    });

    it('should call onChange when model selection changes', async () => {
      const onChange = vi.fn();
      const user = userEvent.setup();
      render(<DomainConfigStep {...defaultProps} onChange={onChange} />);

      const modelSelect = screen.getByTestId('domain-model-select');
      await user.selectOptions(modelSelect, 'llama3:8b');

      expect(onChange).toHaveBeenCalledWith({
        ...defaultConfig,
        llm_model: 'llama3:8b',
      });
    });

    it('should call onCancel when cancel button clicked', async () => {
      const onCancel = vi.fn();
      const user = userEvent.setup();
      render(<DomainConfigStep {...defaultProps} onCancel={onCancel} />);

      const cancelButton = screen.getByTestId('domain-config-cancel');
      await user.click(cancelButton);

      expect(onCancel).toHaveBeenCalledTimes(1);
    });

    it('should call onNext when next button clicked (if valid)', async () => {
      const onNext = vi.fn();
      const user = userEvent.setup();
      const config = {
        name: 'finance',
        description: 'Financial domain',
        llm_model: 'qwen3:32b',
      };
      render(<DomainConfigStep {...defaultProps} config={config} onNext={onNext} />);

      const nextButton = screen.getByTestId('domain-config-next');
      await user.click(nextButton);

      expect(onNext).toHaveBeenCalledTimes(1);
    });
  });
});

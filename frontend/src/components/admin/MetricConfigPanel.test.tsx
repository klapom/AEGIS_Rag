/**
 * MetricConfigPanel Component Tests
 * Sprint 45 Feature 45.12: Metric Configuration UI
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MetricConfigPanel } from './MetricConfigPanel';

describe('MetricConfigPanel', () => {
  const defaultConfig = {
    preset: 'balanced' as const,
    entity_weight: 0.5,
    relation_weight: 0.5,
    entity_metric: 'f1' as const,
    relation_metric: 'f1' as const,
  };

  describe('rendering', () => {
    it('should render panel with title', () => {
      render(<MetricConfigPanel value={defaultConfig} onChange={() => {}} />);
      expect(screen.getByTestId('metric-config-panel')).toBeInTheDocument();
      expect(screen.getByText('Training Metric Configuration')).toBeInTheDocument();
    });

    it('should render all preset buttons', () => {
      render(<MetricConfigPanel value={defaultConfig} onChange={() => {}} />);
      expect(screen.getByTestId('preset-balanced')).toBeInTheDocument();
      expect(screen.getByTestId('preset-precision_focused')).toBeInTheDocument();
      expect(screen.getByTestId('preset-recall_focused')).toBeInTheDocument();
      expect(screen.getByTestId('preset-custom')).toBeInTheDocument();
    });

    it('should highlight active preset', () => {
      render(<MetricConfigPanel value={defaultConfig} onChange={() => {}} />);
      const balancedButton = screen.getByTestId('preset-balanced');
      expect(balancedButton).toHaveClass('bg-blue-600', 'text-white');
    });

    it('should render strategy description', () => {
      render(<MetricConfigPanel value={defaultConfig} onChange={() => {}} />);
      expect(
        screen.getByText(/balanced optimization for both entities and relations/i)
      ).toBeInTheDocument();
    });
  });

  describe('preset selection', () => {
    it('should show custom controls when custom preset selected', () => {
      const onChange = vi.fn();
      render(
        <MetricConfigPanel value={{ ...defaultConfig, preset: 'custom' }} onChange={onChange} />
      );
      expect(screen.getByTestId('weight-slider')).toBeInTheDocument();
      expect(screen.getByTestId('entity-metric-select')).toBeInTheDocument();
      expect(screen.getByTestId('relation-metric-select')).toBeInTheDocument();
    });

    it('should hide custom controls for preset selections', () => {
      render(<MetricConfigPanel value={defaultConfig} onChange={() => {}} />);
      expect(screen.queryByTestId('weight-slider')).not.toBeInTheDocument();
      expect(screen.queryByTestId('entity-metric-select')).not.toBeInTheDocument();
    });

    it('should call onChange with balanced preset values', async () => {
      const onChange = vi.fn();
      const user = userEvent.setup();
      render(<MetricConfigPanel value={defaultConfig} onChange={onChange} />);

      await user.click(screen.getByTestId('preset-balanced'));

      expect(onChange).toHaveBeenCalledWith({
        preset: 'balanced',
        entity_weight: 0.5,
        relation_weight: 0.5,
        entity_metric: 'f1',
        relation_metric: 'f1',
      });
    });

    it('should call onChange with precision_focused preset values', async () => {
      const onChange = vi.fn();
      const user = userEvent.setup();
      render(<MetricConfigPanel value={defaultConfig} onChange={onChange} />);

      await user.click(screen.getByTestId('preset-precision_focused'));

      expect(onChange).toHaveBeenCalledWith({
        preset: 'precision_focused',
        entity_weight: 0.6,
        relation_weight: 0.4,
        entity_metric: 'precision',
        relation_metric: 'precision',
      });
    });

    it('should call onChange with recall_focused preset values', async () => {
      const onChange = vi.fn();
      const user = userEvent.setup();
      render(<MetricConfigPanel value={defaultConfig} onChange={onChange} />);

      await user.click(screen.getByTestId('preset-recall_focused'));

      expect(onChange).toHaveBeenCalledWith({
        preset: 'recall_focused',
        entity_weight: 0.4,
        relation_weight: 0.6,
        entity_metric: 'recall',
        relation_metric: 'recall',
      });
    });

    it('should switch to custom mode without changing values', async () => {
      const onChange = vi.fn();
      const user = userEvent.setup();
      render(<MetricConfigPanel value={defaultConfig} onChange={onChange} />);

      await user.click(screen.getByTestId('preset-custom'));

      expect(onChange).toHaveBeenCalledWith({
        ...defaultConfig,
        preset: 'custom',
      });
    });
  });

  describe('custom configuration', () => {
    const customConfig = {
      preset: 'custom' as const,
      entity_weight: 0.7,
      relation_weight: 0.3,
      entity_metric: 'precision' as const,
      relation_metric: 'recall' as const,
    };

    it('should display correct weight percentages', () => {
      render(<MetricConfigPanel value={customConfig} onChange={() => {}} />);
      expect(screen.getByText('Entity Weight: 70%')).toBeInTheDocument();
      expect(screen.getByText('Relation Weight: 30%')).toBeInTheDocument();
    });

    it('should update weights when slider changes', async () => {
      const onChange = vi.fn();
      render(<MetricConfigPanel value={customConfig} onChange={onChange} />);

      const slider = screen.getByTestId('weight-slider') as HTMLInputElement;

      // Simulate slider change event
      fireEvent.change(slider, { target: { value: '40' } });

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          entity_weight: 0.4,
          relation_weight: 0.6,
        })
      );
    });

    it('should update entity metric when selection changes', async () => {
      const onChange = vi.fn();
      const user = userEvent.setup();
      render(<MetricConfigPanel value={customConfig} onChange={onChange} />);

      const select = screen.getByTestId('entity-metric-select');
      await user.selectOptions(select, 'recall');

      expect(onChange).toHaveBeenCalledWith({
        ...customConfig,
        entity_metric: 'recall',
      });
    });

    it('should update relation metric when selection changes', async () => {
      const onChange = vi.fn();
      const user = userEvent.setup();
      render(<MetricConfigPanel value={customConfig} onChange={onChange} />);

      const select = screen.getByTestId('relation-metric-select');
      await user.selectOptions(select, 'precision');

      expect(onChange).toHaveBeenCalledWith({
        ...customConfig,
        relation_metric: 'precision',
      });
    });
  });

  describe('strategy descriptions', () => {
    it('should show balanced description for balanced preset', () => {
      render(<MetricConfigPanel value={defaultConfig} onChange={() => {}} />);
      expect(
        screen.getByText(/balanced optimization for both entities and relations using F1 score/i)
      ).toBeInTheDocument();
    });

    it('should show precision description for precision_focused preset', () => {
      const config = { ...defaultConfig, preset: 'precision_focused' as const };
      render(<MetricConfigPanel value={config} onChange={() => {}} />);
      expect(
        screen.getByText(/prioritizes accuracy - extracted items are more likely to be correct/i)
      ).toBeInTheDocument();
    });

    it('should show recall description for recall_focused preset', () => {
      const config = { ...defaultConfig, preset: 'recall_focused' as const };
      render(<MetricConfigPanel value={config} onChange={() => {}} />);
      expect(
        screen.getByText(/prioritizes completeness - less likely to miss entities/i)
      ).toBeInTheDocument();
    });

    it('should show custom description with percentages', () => {
      const config = {
        preset: 'custom' as const,
        entity_weight: 0.7,
        relation_weight: 0.3,
        entity_metric: 'precision' as const,
        relation_metric: 'recall' as const,
      };
      render(<MetricConfigPanel value={config} onChange={() => {}} />);
      expect(screen.getByText(/custom: 70% entity \(precision\), 30% relation \(recall\)/i)).toBeInTheDocument();
    });
  });
});

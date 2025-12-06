/**
 * WorkerConfigSlider Component Tests
 * Sprint 37 Feature 37.7: Admin UI for Worker Pool Configuration
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { WorkerConfigSlider } from './WorkerConfigSlider';

describe('WorkerConfigSlider', () => {
  const defaultProps = {
    label: 'Test Workers',
    value: 4,
    min: 1,
    max: 8,
    description: 'Number of test workers',
    onChange: vi.fn(),
    testId: 'test-slider',
  };

  it('renders with correct label and value', () => {
    render(<WorkerConfigSlider {...defaultProps} />);

    expect(screen.getByText('Test Workers')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('renders description text', () => {
    render(<WorkerConfigSlider {...defaultProps} />);

    expect(screen.getByText('Number of test workers')).toBeInTheDocument();
  });

  it('renders min and max indicators', () => {
    render(<WorkerConfigSlider {...defaultProps} />);

    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
  });

  it('renders with unit suffix when provided', () => {
    render(<WorkerConfigSlider {...defaultProps} unit="s" />);

    expect(screen.getByText('4s')).toBeInTheDocument();
  });

  it('calls onChange when slider value changes', () => {
    const onChange = vi.fn();
    render(<WorkerConfigSlider {...defaultProps} onChange={onChange} />);

    const slider = screen.getByTestId('test-slider-slider');
    fireEvent.change(slider, { target: { value: '6' } });

    expect(onChange).toHaveBeenCalledWith(6);
  });

  it('can be disabled', () => {
    render(<WorkerConfigSlider {...defaultProps} disabled={true} />);

    const slider = screen.getByTestId('test-slider-slider');
    expect(slider).toBeDisabled();
  });

  it('uses correct testId for container and slider', () => {
    render(<WorkerConfigSlider {...defaultProps} />);

    expect(screen.getByTestId('test-slider')).toBeInTheDocument();
    expect(screen.getByTestId('test-slider-slider')).toBeInTheDocument();
  });
});

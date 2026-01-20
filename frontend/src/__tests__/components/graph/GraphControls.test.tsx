/**
 * GraphControls Component Tests
 * Sprint 116 Feature 116.9: Graph controls for navigation and export
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GraphControls } from '../../../components/graph/GraphControls';

describe('GraphControls', () => {
  const mockHandlers = {
    onZoomIn: vi.fn(),
    onZoomOut: vi.fn(),
    onFit: vi.fn(),
    onReset: vi.fn(),
    onExportPNG: vi.fn(),
    onFullscreen: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all control buttons', () => {
    render(<GraphControls {...mockHandlers} isFullscreen={false} />);

    expect(screen.getByTestId('graph-controls')).toBeInTheDocument();
    expect(screen.getByTestId('zoom-in-button')).toBeInTheDocument();
    expect(screen.getByTestId('zoom-out-button')).toBeInTheDocument();
    expect(screen.getByTestId('fit-button')).toBeInTheDocument();
    expect(screen.getByTestId('reset-button')).toBeInTheDocument();
    expect(screen.getByTestId('export-png-button')).toBeInTheDocument();
    expect(screen.getByTestId('fullscreen-button')).toBeInTheDocument();
  });

  it('calls onZoomIn when zoom in button is clicked', () => {
    render(<GraphControls {...mockHandlers} isFullscreen={false} />);

    const zoomInButton = screen.getByTestId('zoom-in-button');
    fireEvent.click(zoomInButton);

    expect(mockHandlers.onZoomIn).toHaveBeenCalledTimes(1);
  });

  it('calls onZoomOut when zoom out button is clicked', () => {
    render(<GraphControls {...mockHandlers} isFullscreen={false} />);

    const zoomOutButton = screen.getByTestId('zoom-out-button');
    fireEvent.click(zoomOutButton);

    expect(mockHandlers.onZoomOut).toHaveBeenCalledTimes(1);
  });

  it('calls onFit when fit button is clicked', () => {
    render(<GraphControls {...mockHandlers} isFullscreen={false} />);

    const fitButton = screen.getByTestId('fit-button');
    fireEvent.click(fitButton);

    expect(mockHandlers.onFit).toHaveBeenCalledTimes(1);
  });

  it('calls onReset when reset button is clicked', () => {
    render(<GraphControls {...mockHandlers} isFullscreen={false} />);

    const resetButton = screen.getByTestId('reset-button');
    fireEvent.click(resetButton);

    expect(mockHandlers.onReset).toHaveBeenCalledTimes(1);
  });

  it('calls onExportPNG when export button is clicked', () => {
    render(<GraphControls {...mockHandlers} isFullscreen={false} />);

    const exportButton = screen.getByTestId('export-png-button');
    fireEvent.click(exportButton);

    expect(mockHandlers.onExportPNG).toHaveBeenCalledTimes(1);
  });

  it('calls onFullscreen when fullscreen button is clicked', () => {
    render(<GraphControls {...mockHandlers} isFullscreen={false} />);

    const fullscreenButton = screen.getByTestId('fullscreen-button');
    fireEvent.click(fullscreenButton);

    expect(mockHandlers.onFullscreen).toHaveBeenCalledTimes(1);
  });

  it('shows enter fullscreen icon when not in fullscreen', () => {
    render(<GraphControls {...mockHandlers} isFullscreen={false} />);

    const fullscreenButton = screen.getByTestId('fullscreen-button');
    expect(fullscreenButton).toHaveAttribute('title', 'Enter Fullscreen');
  });

  it('shows exit fullscreen icon when in fullscreen', () => {
    render(<GraphControls {...mockHandlers} isFullscreen={true} />);

    const fullscreenButton = screen.getByTestId('fullscreen-button');
    expect(fullscreenButton).toHaveAttribute('title', 'Exit Fullscreen');
  });

  it('has proper ARIA labels for accessibility', () => {
    render(<GraphControls {...mockHandlers} isFullscreen={false} />);

    expect(screen.getByLabelText('Zoom in')).toBeInTheDocument();
    expect(screen.getByLabelText('Zoom out')).toBeInTheDocument();
    expect(screen.getByLabelText('Fit to view')).toBeInTheDocument();
    expect(screen.getByLabelText('Reset view')).toBeInTheDocument();
    expect(screen.getByLabelText('Export as PNG')).toBeInTheDocument();
    expect(screen.getByLabelText('Enter fullscreen')).toBeInTheDocument();
  });

  it('has proper ARIA label for exit fullscreen', () => {
    render(<GraphControls {...mockHandlers} isFullscreen={true} />);

    expect(screen.getByLabelText('Exit fullscreen')).toBeInTheDocument();
  });

  it('renders buttons in correct order', () => {
    const { container } = render(<GraphControls {...mockHandlers} isFullscreen={false} />);

    const buttons = container.querySelectorAll('button');
    expect(buttons).toHaveLength(6);

    // Verify order by data-testid
    expect(buttons[0]).toHaveAttribute('data-testid', 'zoom-in-button');
    expect(buttons[1]).toHaveAttribute('data-testid', 'zoom-out-button');
    expect(buttons[2]).toHaveAttribute('data-testid', 'fit-button');
    expect(buttons[3]).toHaveAttribute('data-testid', 'reset-button');
    expect(buttons[4]).toHaveAttribute('data-testid', 'export-png-button');
    expect(buttons[5]).toHaveAttribute('data-testid', 'fullscreen-button');
  });

  it('applies hover styles to buttons', () => {
    render(<GraphControls {...mockHandlers} isFullscreen={false} />);

    const zoomInButton = screen.getByTestId('zoom-in-button');
    expect(zoomInButton).toHaveClass('hover:bg-gray-100');
  });
});

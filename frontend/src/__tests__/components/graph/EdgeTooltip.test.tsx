/**
 * EdgeTooltip Component Tests
 * Sprint 116 Feature 116.9: Edge hover tooltip
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { EdgeTooltip } from '../../../components/graph/EdgeTooltip';

describe('EdgeTooltip', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders edge label', async () => {
    render(<EdgeTooltip edgeLabel="RELATES_TO" x={100} y={100} />);

    await waitFor(() => {
      expect(screen.getByText('RELATES_TO')).toBeInTheDocument();
    });
  });

  it('renders weight when provided', async () => {
    render(<EdgeTooltip edgeLabel="RELATES_TO" weight={0.85} x={100} y={100} />);

    await waitFor(() => {
      expect(screen.getByText(/weight: 85%/i)).toBeInTheDocument();
    });
  });

  it('renders properties when provided', async () => {
    const properties = {
      source: 'Node 1',
      target: 'Node 2',
      description: 'Test relationship',
    };

    render(<EdgeTooltip edgeLabel="RELATES_TO" properties={properties} x={100} y={100} />);

    await waitFor(() => {
      expect(screen.getByText(/source:/i)).toBeInTheDocument();
      expect(screen.getByText(/Node 1/i)).toBeInTheDocument();
      expect(screen.getByText(/target:/i)).toBeInTheDocument();
      expect(screen.getByText(/Node 2/i)).toBeInTheDocument();
      expect(screen.getByText(/description:/i)).toBeInTheDocument();
      expect(screen.getByText(/Test relationship/i)).toBeInTheDocument();
    });
  });

  it('positions tooltip near cursor', async () => {
    const { container } = render(<EdgeTooltip edgeLabel="RELATES_TO" x={150} y={200} />);

    await waitFor(() => {
      const tooltip = container.querySelector('[data-testid="edge-tooltip"]');
      expect(tooltip).toHaveStyle({ left: '160px', top: '210px' });
    });
  });

  it('does not render immediately (200ms delay)', () => {
    render(<EdgeTooltip edgeLabel="RELATES_TO" x={100} y={100} />);

    // Should not be visible immediately
    expect(screen.queryByTestId('edge-tooltip')).not.toBeInTheDocument();
  });

  it('renders after delay', async () => {
    render(<EdgeTooltip edgeLabel="RELATES_TO" x={100} y={100} />);

    await waitFor(
      () => {
        expect(screen.getByTestId('edge-tooltip')).toBeInTheDocument();
      },
      { timeout: 300 }
    );
  });

  it('renders with all props', async () => {
    const properties = { type: 'semantic', confidence: 0.9 };
    render(
      <EdgeTooltip
        edgeLabel="MENTIONED_IN"
        weight={0.75}
        properties={properties}
        x={50}
        y={75}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('MENTIONED_IN')).toBeInTheDocument();
      expect(screen.getByText(/weight: 75%/i)).toBeInTheDocument();
      expect(screen.getByText(/type:/i)).toBeInTheDocument();
    });
  });

  it('handles object properties correctly', async () => {
    const properties = {
      metadata: { nested: 'value' },
    };

    render(<EdgeTooltip edgeLabel="CO_OCCURS" properties={properties} x={100} y={100} />);

    await waitFor(() => {
      expect(screen.getByText(/metadata:/i)).toBeInTheDocument();
      // Should render stringified JSON for objects
      expect(screen.getByText(/"nested":"value"/i)).toBeInTheDocument();
    });
  });
});

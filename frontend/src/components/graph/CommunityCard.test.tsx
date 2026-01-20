/**
 * CommunityCard Component Tests
 * Sprint 116 Feature 116.7: Graph Communities UI
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CommunityCard, CommunitySummary } from './CommunityCard';
import type { Community } from '../../types/graph';

describe('CommunityCard', () => {
  const mockCommunity: Community = {
    id: 'comm-1',
    topic: 'Machine Learning',
    size: 25,
    density: 0.75,
    description: 'AI and ML research community',
  };

  describe('Full Card Rendering', () => {
    it('should render community topic', () => {
      render(<CommunityCard community={mockCommunity} />);

      expect(screen.getByText('Machine Learning')).toBeInTheDocument();
    });

    it('should render member count', () => {
      render(<CommunityCard community={mockCommunity} />);

      expect(screen.getByText('25 members')).toBeInTheDocument();
    });

    it('should render description when provided', () => {
      render(<CommunityCard community={mockCommunity} />);

      expect(screen.getByText('AI and ML research community')).toBeInTheDocument();
    });

    it('should not render description when not provided', () => {
      const communityNoDesc = { ...mockCommunity, description: undefined };
      render(<CommunityCard community={communityNoDesc} />);

      expect(screen.queryByText('AI and ML research community')).not.toBeInTheDocument();
    });

    it('should render density bar when density provided', () => {
      render(<CommunityCard community={mockCommunity} />);

      expect(screen.getByText('Density')).toBeInTheDocument();
      expect(screen.getByText('75.0%')).toBeInTheDocument();
    });

    it('should not render density bar when density not provided', () => {
      const communityNoDensity = { ...mockCommunity, density: undefined };
      render(<CommunityCard community={communityNoDensity} />);

      expect(screen.queryByText('Density')).not.toBeInTheDocument();
    });

    it('should render community ID badge', () => {
      render(<CommunityCard community={mockCommunity} />);

      expect(screen.getByText('comm-1')).toBeInTheDocument();
    });

    it('should render "View Details" button when onClick provided', () => {
      const onClick = vi.fn();
      render(<CommunityCard community={mockCommunity} onClick={onClick} />);

      expect(screen.getByText(/View Details/)).toBeInTheDocument();
    });

    it('should not render "View Details" when onClick not provided', () => {
      render(<CommunityCard community={mockCommunity} />);

      expect(screen.queryByText(/View Details/)).not.toBeInTheDocument();
    });
  });

  describe('Health Indicator', () => {
    it('should show green indicator for high health (>= 0.7)', () => {
      const healthyCommunity = { ...mockCommunity, size: 80, density: 0.8 };
      const { container } = render(<CommunityCard community={healthyCommunity} />);

      const indicator = container.querySelector('.bg-green-500');
      expect(indicator).toBeInTheDocument();
    });

    it('should show yellow indicator for medium health (0.4 - 0.7)', () => {
      const mediumCommunity = { ...mockCommunity, size: 30, density: 0.5 };
      const { container } = render(<CommunityCard community={mediumCommunity} />);

      const indicator = container.querySelector('.bg-yellow-500');
      expect(indicator).toBeInTheDocument();
    });

    it('should show red indicator for low health (< 0.4)', () => {
      const unhealthyCommunity = { ...mockCommunity, size: 5, density: 0.2 };
      const { container } = render(<CommunityCard community={unhealthyCommunity} />);

      const indicator = container.querySelector('.bg-red-500');
      expect(indicator).toBeInTheDocument();
    });
  });

  describe('Selected State', () => {
    it('should apply selected styles when selected=true', () => {
      const { container } = render(<CommunityCard community={mockCommunity} selected={true} />);

      const card = screen.getByTestId('community-card');
      expect(card).toHaveClass('border-purple-500');
      expect(card).toHaveClass('ring-2');
    });

    it('should apply default styles when selected=false', () => {
      const { container } = render(<CommunityCard community={mockCommunity} selected={false} />);

      const card = screen.getByTestId('community-card');
      expect(card).toHaveClass('border-gray-200');
      expect(card).not.toHaveClass('ring-2');
    });
  });

  describe('Click Handling', () => {
    it('should call onClick when card is clicked', () => {
      const onClick = vi.fn();
      render(<CommunityCard community={mockCommunity} onClick={onClick} />);

      const card = screen.getByTestId('community-card');
      fireEvent.click(card);

      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('should support keyboard interaction (Enter)', () => {
      const onClick = vi.fn();
      render(<CommunityCard community={mockCommunity} onClick={onClick} />);

      const card = screen.getByTestId('community-card');
      fireEvent.keyDown(card, { key: 'Enter' });

      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('should support keyboard interaction (Space)', () => {
      const onClick = vi.fn();
      render(<CommunityCard community={mockCommunity} onClick={onClick} />);

      const card = screen.getByTestId('community-card');
      fireEvent.keyDown(card, { key: ' ' });

      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('should not have role/tabIndex when onClick not provided', () => {
      render(<CommunityCard community={mockCommunity} />);

      const card = screen.getByTestId('community-card');
      expect(card).not.toHaveAttribute('role');
      expect(card).not.toHaveAttribute('tabIndex');
    });

    it('should have role=button and tabIndex=0 when onClick provided', () => {
      const onClick = vi.fn();
      render(<CommunityCard community={mockCommunity} onClick={onClick} />);

      const card = screen.getByTestId('community-card');
      expect(card).toHaveAttribute('role', 'button');
      expect(card).toHaveAttribute('tabIndex', '0');
    });
  });

  describe('Compact Variant', () => {
    it('should render compact card when compact=true', () => {
      render(<CommunityCard community={mockCommunity} compact={true} />);

      expect(screen.getByTestId('community-card-compact')).toBeInTheDocument();
    });

    it('should render topic in compact mode', () => {
      render(<CommunityCard community={mockCommunity} compact={true} />);

      expect(screen.getByText('Machine Learning')).toBeInTheDocument();
    });

    it('should render size metric in compact mode', () => {
      render(<CommunityCard community={mockCommunity} compact={true} />);

      expect(screen.getByText('25')).toBeInTheDocument();
      expect(screen.getByText('members')).toBeInTheDocument();
    });

    it('should render density metric in compact mode', () => {
      render(<CommunityCard community={mockCommunity} compact={true} />);

      expect(screen.getByText('75.0%')).toBeInTheDocument();
      expect(screen.getByText('density')).toBeInTheDocument();
    });

    it('should apply selected styles in compact mode', () => {
      render(<CommunityCard community={mockCommunity} compact={true} selected={true} />);

      const card = screen.getByTestId('community-card-compact');
      expect(card).toHaveClass('border-purple-500');
    });

    it('should handle click in compact mode', () => {
      const onClick = vi.fn();
      render(<CommunityCard community={mockCommunity} compact={true} onClick={onClick} />);

      const card = screen.getByTestId('community-card-compact');
      fireEvent.click(card);

      expect(onClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('Accessibility', () => {
    it('should have aria-label for health indicator', () => {
      render(<CommunityCard community={mockCommunity} />);

      const healthIndicator = screen.getByLabelText(/Community health:/);
      expect(healthIndicator).toBeInTheDocument();
    });

    it('should have aria-label for density bar', () => {
      render(<CommunityCard community={mockCommunity} />);

      const densityBar = screen.getByLabelText(/Density: 75.0%/);
      expect(densityBar).toBeInTheDocument();
    });

    it('should have aria-label for view details button', () => {
      const onClick = vi.fn();
      render(<CommunityCard community={mockCommunity} onClick={onClick} />);

      const button = screen.getByLabelText(/View details for Machine Learning/);
      expect(button).toBeInTheDocument();
    });
  });
});

describe('CommunitySummary', () => {
  const mockCommunity: Community = {
    id: 'comm-1',
    topic: 'Machine Learning',
    size: 25,
    density: 0.75,
    description: 'AI and ML research',
  };

  it('should render community topic', () => {
    render(<CommunitySummary community={mockCommunity} />);

    expect(screen.getByText('Machine Learning')).toBeInTheDocument();
  });

  it('should render member count and density', () => {
    render(<CommunitySummary community={mockCommunity} />);

    expect(screen.getByText('25 members')).toBeInTheDocument();
    expect(screen.getByText('75.0% density')).toBeInTheDocument();
  });

  it('should show description when showDescription=true', () => {
    render(<CommunitySummary community={mockCommunity} showDescription={true} />);

    expect(screen.getByText('AI and ML research')).toBeInTheDocument();
  });

  it('should hide description when showDescription=false', () => {
    render(<CommunitySummary community={mockCommunity} showDescription={false} />);

    expect(screen.queryByText('AI and ML research')).not.toBeInTheDocument();
  });

  it('should not render density when not provided', () => {
    const communityNoDensity = { ...mockCommunity, density: undefined };
    render(<CommunitySummary community={communityNoDensity} />);

    expect(screen.queryByText(/density/)).not.toBeInTheDocument();
  });
});

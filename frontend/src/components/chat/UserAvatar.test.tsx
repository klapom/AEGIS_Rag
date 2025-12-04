/**
 * UserAvatar Component Tests
 * Sprint 35 Feature 35.1: Seamless Chat Flow
 *
 * Tests for the UserAvatar component which renders a blue circle avatar
 * with a User icon for user messages in the chat interface.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { UserAvatar } from './UserAvatar';

describe('UserAvatar', () => {
  it('renders with correct data-testid attribute', () => {
    render(<UserAvatar />);
    const avatar = screen.getByTestId('user-avatar');
    expect(avatar).toBeInTheDocument();
  });

  it('has correct accessibility label', () => {
    render(<UserAvatar />);
    const avatar = screen.getByTestId('user-avatar');
    expect(avatar).toHaveAttribute('aria-label', 'User avatar');
  });

  it('applies blue background styling', () => {
    render(<UserAvatar />);
    const avatar = screen.getByTestId('user-avatar');
    expect(avatar).toHaveClass('bg-blue-500');
  });

  it('has correct size styling', () => {
    render(<UserAvatar />);
    const avatar = screen.getByTestId('user-avatar');
    expect(avatar).toHaveClass('w-8');
    expect(avatar).toHaveClass('h-8');
  });

  it('applies rounded-full styling for circular shape', () => {
    render(<UserAvatar />);
    const avatar = screen.getByTestId('user-avatar');
    expect(avatar).toHaveClass('rounded-full');
  });

  it('centers content with flex utilities', () => {
    render(<UserAvatar />);
    const avatar = screen.getByTestId('user-avatar');
    expect(avatar).toHaveClass('flex');
    expect(avatar).toHaveClass('items-center');
    expect(avatar).toHaveClass('justify-center');
  });

  it('prevents flex shrinking', () => {
    render(<UserAvatar />);
    const avatar = screen.getByTestId('user-avatar');
    expect(avatar).toHaveClass('flex-shrink-0');
  });

  it('renders User icon from lucide-react', () => {
    const { container } = render(<UserAvatar />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
    // The SVG should be the lucide User icon
    expect(svg).toHaveClass('w-5');
    expect(svg).toHaveClass('h-5');
  });

  it('icon has white color styling', () => {
    const { container } = render(<UserAvatar />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveClass('text-white');
  });

  it('maintains fixed size for layout consistency', () => {
    const { container } = render(<UserAvatar />);
    const avatar = container.querySelector('[data-testid="user-avatar"]') as HTMLElement;
    // CSS classes w-8 and h-8 should be present for Tailwind size utility
    expect(avatar).toHaveClass('w-8');
    expect(avatar).toHaveClass('h-8');
    // These classes ensure fixed sizing
    const className = avatar.className;
    expect(className).toContain('w-8');
    expect(className).toContain('h-8');
  });

  it('renders without optional props', () => {
    // UserAvatar doesn't accept any props, should render with defaults
    const { container } = render(<UserAvatar />);
    expect(container.querySelector('[data-testid="user-avatar"]')).toBeInTheDocument();
  });

  it('renders in a stable manner across multiple renders', () => {
    const { rerender } = render(<UserAvatar />);
    const firstAvatar = screen.getByTestId('user-avatar');
    expect(firstAvatar).toBeInTheDocument();

    rerender(<UserAvatar />);
    const secondAvatar = screen.getByTestId('user-avatar');
    expect(secondAvatar).toBeInTheDocument();
    expect(firstAvatar.className).toBe(secondAvatar.className);
  });

  it('integrates with ChatMessage layout', () => {
    // Test that avatar can be used within flex container
    const { container } = render(
      <div className="flex gap-4">
        <div className="flex-shrink-0">
          <UserAvatar />
        </div>
        <div className="flex-1">Message content</div>
      </div>
    );

    const avatar = screen.getByTestId('user-avatar');
    expect(avatar).toBeInTheDocument();
    // Parent should be flex-shrink-0 which provides no shrinking
    expect(avatar.parentElement).toHaveClass('flex-shrink-0');
  });
});

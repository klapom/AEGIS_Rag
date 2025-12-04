/**
 * BotAvatar Component Tests
 * Sprint 35 Feature 35.1: Seamless Chat Flow
 *
 * Tests for the BotAvatar component which renders a gradient teal-to-blue
 * avatar with a Bot icon for assistant messages in the chat interface.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BotAvatar } from './BotAvatar';

describe('BotAvatar', () => {
  it('renders with correct data-testid attribute', () => {
    render(<BotAvatar />);
    const avatar = screen.getByTestId('bot-avatar');
    expect(avatar).toBeInTheDocument();
  });

  it('has correct accessibility label for assistant', () => {
    render(<BotAvatar />);
    const avatar = screen.getByTestId('bot-avatar');
    expect(avatar).toHaveAttribute('aria-label', 'AegisRAG assistant avatar');
  });

  it('applies gradient background styling from teal to blue', () => {
    render(<BotAvatar />);
    const avatar = screen.getByTestId('bot-avatar');
    expect(avatar).toHaveClass('bg-gradient-to-br');
    expect(avatar).toHaveClass('from-teal-400');
    expect(avatar).toHaveClass('to-blue-500');
  });

  it('has correct size styling', () => {
    render(<BotAvatar />);
    const avatar = screen.getByTestId('bot-avatar');
    expect(avatar).toHaveClass('w-8');
    expect(avatar).toHaveClass('h-8');
  });

  it('applies rounded-full styling for circular shape', () => {
    render(<BotAvatar />);
    const avatar = screen.getByTestId('bot-avatar');
    expect(avatar).toHaveClass('rounded-full');
  });

  it('centers content with flex utilities', () => {
    render(<BotAvatar />);
    const avatar = screen.getByTestId('bot-avatar');
    expect(avatar).toHaveClass('flex');
    expect(avatar).toHaveClass('items-center');
    expect(avatar).toHaveClass('justify-center');
  });

  it('prevents flex shrinking', () => {
    render(<BotAvatar />);
    const avatar = screen.getByTestId('bot-avatar');
    expect(avatar).toHaveClass('flex-shrink-0');
  });

  it('renders Bot icon from lucide-react', () => {
    const { container } = render(<BotAvatar />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
    // The SVG should be the lucide Bot icon
    expect(svg).toHaveClass('w-5');
    expect(svg).toHaveClass('h-5');
  });

  it('icon has white color styling', () => {
    const { container } = render(<BotAvatar />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveClass('text-white');
  });

  it('distinguishes from UserAvatar with gradient background', () => {
    const { container: botContainer } = render(<BotAvatar />);
    const botAvatar = botContainer.querySelector('[data-testid="bot-avatar"]') as HTMLElement;

    // BotAvatar should have gradient, UserAvatar should have solid color
    expect(botAvatar.className).toContain('bg-gradient-to-br');
    expect(botAvatar.className).toContain('from-teal-400');
    expect(botAvatar.className).toContain('to-blue-500');
  });

  it('maintains fixed size for layout consistency', () => {
    const { container } = render(<BotAvatar />);
    const avatar = container.querySelector('[data-testid="bot-avatar"]') as HTMLElement;
    // CSS classes w-8 and h-8 should be present for Tailwind size utility
    expect(avatar).toHaveClass('w-8');
    expect(avatar).toHaveClass('h-8');
    // These classes ensure fixed sizing
    const className = avatar.className;
    expect(className).toContain('w-8');
    expect(className).toContain('h-8');
  });

  it('renders without optional props', () => {
    // BotAvatar doesn't accept any props, should render with defaults
    const { container } = render(<BotAvatar />);
    expect(container.querySelector('[data-testid="bot-avatar"]')).toBeInTheDocument();
  });

  it('renders in a stable manner across multiple renders', () => {
    const { rerender } = render(<BotAvatar />);
    const firstAvatar = screen.getByTestId('bot-avatar');
    expect(firstAvatar).toBeInTheDocument();

    rerender(<BotAvatar />);
    const secondAvatar = screen.getByTestId('bot-avatar');
    expect(secondAvatar).toBeInTheDocument();
    expect(firstAvatar.className).toBe(secondAvatar.className);
  });

  it('integrates with ChatMessage layout', () => {
    // Test that avatar can be used within flex container for assistant messages
    const { container } = render(
      <div className="flex gap-4">
        <div className="flex-shrink-0">
          <BotAvatar />
        </div>
        <div className="flex-1">Assistant message content</div>
      </div>
    );

    const avatar = screen.getByTestId('bot-avatar');
    expect(avatar).toBeInTheDocument();
    // Parent should be flex-shrink-0 which provides no shrinking
    expect(avatar.parentElement).toHaveClass('flex-shrink-0');
  });

  it('gradient background distinguishes assistant from user', () => {
    render(<BotAvatar />);
    const botAvatar = screen.getByTestId('bot-avatar');
    const classes = botAvatar.className;

    // Verify gradient-specific classes
    expect(classes).toMatch(/bg-gradient-to-br/);
    expect(classes).toMatch(/from-teal-400/);
    expect(classes).toMatch(/to-blue-500/);
  });

  it('uses consistent icon styling with UserAvatar', () => {
    const { container } = render(<BotAvatar />);
    const svg = container.querySelector('svg');
    // Same icon dimensions and color as UserAvatar (w-5 h-5 text-white)
    expect(svg).toHaveClass('w-5');
    expect(svg).toHaveClass('h-5');
    expect(svg).toHaveClass('text-white');
  });
});

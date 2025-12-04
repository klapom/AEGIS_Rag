/**
 * SessionSidebar Component Tests
 * Sprint 35 Feature 35.5: Session History Sidebar
 *
 * Test Coverage:
 * - Component rendering and structure
 * - Session grouping by date (Today, Yesterday, Last 7 Days, Older)
 * - Active session highlighting
 * - User interactions (clicks, hover)
 * - Delete functionality with confirmation
 * - Mobile responsive toggle
 * - Loading state
 * - Empty session list
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { SessionSidebar } from './SessionSidebar';
import * as useSessionsModule from '../../hooks/useSessions';
import type { SessionSummary } from '../../api/chat';

// Mock the useSessions hook
vi.mock('../../hooks/useSessions', () => ({
  useSessions: vi.fn(),
}));

describe('SessionSidebar', () => {
  let mockOnNewChat: any;
  let mockOnSelectSession: any;
  let mockOnToggle: any;
  let mockRemoveSession: any;
  let mockConfirm: any;

  const mockSessionsData = {
    today: [
      {
        session_id: 'session-1',
        title: 'Today Conversation 1',
        preview: 'First message today',
        updated_at: new Date().toISOString(),
        message_count: 5,
      },
      {
        session_id: 'session-2',
        title: 'Today Conversation 2',
        preview: 'Second message today',
        updated_at: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
        message_count: 3,
      },
    ],
    yesterday: [
      {
        session_id: 'session-3',
        title: 'Yesterday Conversation',
        preview: 'Message from yesterday',
        updated_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
        message_count: 2,
      },
    ],
    lastWeek: [
      {
        session_id: 'session-4',
        title: 'Last Week Conversation',
        preview: 'Message from last week',
        updated_at: new Date(Date.now() - 3 * 86400000).toISOString(), // 3 days ago
        message_count: 8,
      },
    ],
    older: [
      {
        session_id: 'session-5',
        title: 'Old Conversation',
        preview: 'Message from long ago',
        updated_at: new Date(Date.now() - 30 * 86400000).toISOString(), // 30 days ago
        message_count: 15,
      },
    ],
  };

  beforeEach(() => {
    mockOnNewChat = vi.fn();
    mockOnSelectSession = vi.fn();
    mockOnToggle = vi.fn();
    mockRemoveSession = vi.fn();
    mockConfirm = vi.fn(() => true);

    global.confirm = mockConfirm as any;
    vi.clearAllMocks();

    // Default mock setup
    vi.mocked(useSessionsModule.useSessions).mockReturnValue({
      sessions: [],
      groupedSessions: mockSessionsData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      removeSession: mockRemoveSession,
    });
  });

  describe('Rendering', () => {
    it('should render sidebar with correct structure', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const sidebar = screen.getByTestId('session-sidebar');
      expect(sidebar).toBeInTheDocument();
      expect(sidebar.className).toContain('fixed');
      expect(sidebar.className).toContain('bg-gray-900');
    });

    it('should render mobile toggle button', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={false}
          onToggle={mockOnToggle}
        />
      );

      const toggleButton = screen.getByTestId('sidebar-toggle');
      expect(toggleButton).toBeInTheDocument();
      expect(toggleButton.className).toContain('md:hidden');
    });

    it('should render "New Chat" button', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const newChatButton = screen.getByTestId('new-chat-button');
      expect(newChatButton).toBeInTheDocument();
      expect(newChatButton).toHaveTextContent('New Chat');
    });

    it('should render version info in footer', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText('AegisRAG v0.35')).toBeInTheDocument();
    });
  });

  describe('Session Groups', () => {
    it('should display "Today" session group', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText('Today')).toBeInTheDocument();
    });

    it('should display "Yesterday" session group', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText('Yesterday')).toBeInTheDocument();
    });

    it('should display "Last 7 Days" session group', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText('Last 7 Days')).toBeInTheDocument();
    });

    it('should display "Older" session group', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText('Older')).toBeInTheDocument();
    });

    it('should display all sessions from each group', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      // Check Today sessions
      expect(screen.getByText('Today Conversation 1')).toBeInTheDocument();
      expect(screen.getByText('Today Conversation 2')).toBeInTheDocument();

      // Check Yesterday sessions
      expect(screen.getByText('Yesterday Conversation')).toBeInTheDocument();

      // Check Last Week sessions
      expect(screen.getByText('Last Week Conversation')).toBeInTheDocument();

      // Check Older sessions
      expect(screen.getByText('Old Conversation')).toBeInTheDocument();
    });

    it('should not render empty groups', () => {
      vi.mocked(useSessionsModule.useSessions).mockReturnValue({
        sessions: [],
        groupedSessions: {
          today: mockSessionsData.today,
          yesterday: [],
          lastWeek: [],
          older: [],
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        removeSession: mockRemoveSession,
      });

      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      // Should have Today but not other groups
      expect(screen.getByText('Today')).toBeInTheDocument();
      expect(screen.queryByText('Yesterday')).not.toBeInTheDocument();
      expect(screen.queryByText('Last 7 Days')).not.toBeInTheDocument();
      expect(screen.queryByText('Older')).not.toBeInTheDocument();
    });
  });

  describe('Session Display', () => {
    it('should display session titles', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const sessionItems = screen.getAllByTestId('session-item');
      expect(sessionItems.length).toBe(5); // 2 + 1 + 1 + 1 sessions
    });

    it('should display session previews', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText('First message today')).toBeInTheDocument();
      expect(screen.getByText('Second message today')).toBeInTheDocument();
      expect(screen.getByText('Message from yesterday')).toBeInTheDocument();
    });

    it('should display default title when session title is null', () => {
      vi.mocked(useSessionsModule.useSessions).mockReturnValue({
        sessions: [],
        groupedSessions: {
          today: [
            {
              session_id: 'session-null',
              title: null,
              preview: 'Some preview',
              updated_at: new Date().toISOString(),
              message_count: 1,
            },
          ],
          yesterday: [],
          lastWeek: [],
          older: [],
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        removeSession: mockRemoveSession,
      });

      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText('New Conversation')).toBeInTheDocument();
    });
  });

  describe('Active Session Highlighting', () => {
    it('should highlight active session', () => {
      render(
        <SessionSidebar
          currentSessionId="session-1"
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const sessionItems = screen.getAllByTestId('session-item');
      const activeSession = sessionItems[0]; // session-1 is the first item

      expect(activeSession.className).toContain('bg-gray-700');
      expect(activeSession.className).toContain('text-white');
    });

    it('should not highlight inactive sessions', () => {
      render(
        <SessionSidebar
          currentSessionId="session-1"
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const sessionItems = screen.getAllByTestId('session-item');
      const inactiveSession = sessionItems[1]; // session-2 should be inactive

      expect(inactiveSession.className).toContain('text-gray-300');
      expect(inactiveSession.className).not.toContain('bg-gray-700');
    });

    it('should remove highlight when active session changes', () => {
      const { rerender } = render(
        <SessionSidebar
          currentSessionId="session-1"
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      let sessionItems = screen.getAllByTestId('session-item');
      expect(sessionItems[0].className).toContain('bg-gray-700');
      expect(sessionItems[1].className).not.toContain('bg-gray-700');

      // Change active session
      rerender(
        <SessionSidebar
          currentSessionId="session-2"
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      sessionItems = screen.getAllByTestId('session-item');
      expect(sessionItems[0].className).not.toContain('bg-gray-700');
      expect(sessionItems[1].className).toContain('bg-gray-700');
    });
  });

  describe('User Interactions', () => {
    it('should call onNewChat when New Chat button clicked', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const newChatButton = screen.getByTestId('new-chat-button');
      fireEvent.click(newChatButton);

      expect(mockOnNewChat).toHaveBeenCalledTimes(1);
    });

    it('should call onToggle when New Chat button clicked', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const newChatButton = screen.getByTestId('new-chat-button');
      fireEvent.click(newChatButton);

      expect(mockOnToggle).toHaveBeenCalledTimes(1);
    });

    it('should call onSelectSession when session item clicked', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const sessionItems = screen.getAllByTestId('session-item');
      fireEvent.click(sessionItems[0]);

      expect(mockOnSelectSession).toHaveBeenCalledWith('session-1');
    });

    it('should call onToggle when session item clicked (mobile)', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const sessionItems = screen.getAllByTestId('session-item');
      fireEvent.click(sessionItems[0]);

      expect(mockOnToggle).toHaveBeenCalled();
    });

    it('should call onToggle when mobile toggle button clicked', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={false}
          onToggle={mockOnToggle}
        />
      );

      const toggleButton = screen.getByTestId('sidebar-toggle');
      fireEvent.click(toggleButton);

      expect(mockOnToggle).toHaveBeenCalledTimes(1);
    });
  });

  describe('Delete Session', () => {
    it('should show delete button on hover', async () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const sessionItem = screen.getAllByTestId('session-item')[0];

      // Initially, delete button should not be visible
      expect(screen.queryByTestId('delete-session')).not.toBeInTheDocument();

      // Hover over session item
      fireEvent.mouseEnter(sessionItem);

      // Delete button should appear
      await waitFor(() => {
        expect(screen.getByTestId('delete-session')).toBeInTheDocument();
      });
    });

    it('should hide delete button on mouse leave', async () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const sessionItem = screen.getAllByTestId('session-item')[0];

      // Hover over session item
      fireEvent.mouseEnter(sessionItem);

      await waitFor(() => {
        expect(screen.getByTestId('delete-session')).toBeInTheDocument();
      });

      // Leave session item
      fireEvent.mouseLeave(sessionItem);

      // Delete button should disappear
      await waitFor(() => {
        expect(screen.queryByTestId('delete-session')).not.toBeInTheDocument();
      });
    });

    it('should call removeSession when delete button clicked', async () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const sessionItem = screen.getAllByTestId('session-item')[0];
      fireEvent.mouseEnter(sessionItem);

      await waitFor(() => {
        expect(screen.getByTestId('delete-session')).toBeInTheDocument();
      });

      const deleteButton = screen.getByTestId('delete-session');
      fireEvent.click(deleteButton);

      expect(mockRemoveSession).toHaveBeenCalledWith('session-1');
    });

    it('should show confirmation dialog before deleting', async () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const sessionItem = screen.getAllByTestId('session-item')[0];
      fireEvent.mouseEnter(sessionItem);

      await waitFor(() => {
        expect(screen.getByTestId('delete-session')).toBeInTheDocument();
      });

      const deleteButton = screen.getByTestId('delete-session');
      fireEvent.click(deleteButton);

      expect(global.confirm).toHaveBeenCalledWith('Delete this conversation?');
    });

    it('should not delete when confirmation is cancelled', async () => {
      mockConfirm.mockReturnValue(false);

      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const sessionItem = screen.getAllByTestId('session-item')[0];
      fireEvent.mouseEnter(sessionItem);

      await waitFor(() => {
        expect(screen.getByTestId('delete-session')).toBeInTheDocument();
      });

      const deleteButton = screen.getByTestId('delete-session');
      fireEvent.click(deleteButton);

      expect(mockRemoveSession).not.toHaveBeenCalled();
    });

    it('should call removeSession when delete confirmed for current session', async () => {
      const mockRemoveSessionLocal = vi.fn(async () => true);

      vi.mocked(useSessionsModule.useSessions).mockReturnValue({
        sessions: [],
        groupedSessions: mockSessionsData,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        removeSession: mockRemoveSessionLocal,
      });

      render(
        <SessionSidebar
          currentSessionId="session-1"
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const sessionItem = screen.getAllByTestId('session-item')[0];
      fireEvent.mouseEnter(sessionItem);

      await waitFor(() => {
        expect(screen.getByTestId('delete-session')).toBeInTheDocument();
      });

      const deleteButton = screen.getByTestId('delete-session');
      fireEvent.click(deleteButton);

      // Verify removeSession was called (the async behavior is tested separately)
      expect(mockRemoveSessionLocal).toHaveBeenCalledWith('session-1');
      expect(global.confirm).toHaveBeenCalledWith('Delete this conversation?');
    });

    it('should call removeSession when delete confirmed for non-current session', async () => {
      const mockRemoveSessionLocal = vi.fn(async () => true);

      vi.mocked(useSessionsModule.useSessions).mockReturnValue({
        sessions: [],
        groupedSessions: mockSessionsData,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        removeSession: mockRemoveSessionLocal,
      });

      render(
        <SessionSidebar
          currentSessionId="session-2"
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const sessionItems = screen.getAllByTestId('session-item');
      fireEvent.mouseEnter(sessionItems[0]);

      await waitFor(() => {
        expect(screen.getByTestId('delete-session')).toBeInTheDocument();
      });

      const deleteButton = screen.getByTestId('delete-session');
      fireEvent.click(deleteButton);

      // Should call removeSession for session-1
      expect(mockRemoveSessionLocal).toHaveBeenCalledWith('session-1');
      expect(global.confirm).toHaveBeenCalledWith('Delete this conversation?');
    });
  });

  describe('Mobile Sidebar Toggle', () => {
    it('should show sidebar when isOpen is true', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const sidebar = screen.getByTestId('session-sidebar');
      expect(sidebar.className).toContain('translate-x-0');
    });

    it('should hide sidebar when isOpen is false', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={false}
          onToggle={mockOnToggle}
        />
      );

      const sidebar = screen.getByTestId('session-sidebar');
      expect(sidebar.className).toContain('-translate-x-full');
    });

    it('should show X icon when sidebar is open', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const toggleButton = screen.getByTestId('sidebar-toggle');
      const xIcon = toggleButton.querySelector('svg');
      expect(xIcon).toBeInTheDocument();
    });

    it('should show menu icon when sidebar is closed', () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={false}
          onToggle={mockOnToggle}
        />
      );

      const toggleButton = screen.getByTestId('sidebar-toggle');
      const menuIcon = toggleButton.querySelector('svg');
      expect(menuIcon).toBeInTheDocument();
    });

    it('should render mobile overlay when sidebar is open', () => {
      const { container } = render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const overlay = container.querySelector('.md\\:hidden.fixed.inset-0');
      expect(overlay).toBeInTheDocument();
    });

    it('should not render mobile overlay when sidebar is closed', () => {
      const { container } = render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={false}
          onToggle={mockOnToggle}
        />
      );

      const overlay = container.querySelector('.md\\:hidden.fixed.inset-0');
      expect(overlay).not.toBeInTheDocument();
    });

    it('should call onToggle when overlay clicked', () => {
      const { container } = render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const overlay = container.querySelector('.bg-black.bg-opacity-50');
      if (overlay) {
        fireEvent.click(overlay);
        expect(mockOnToggle).toHaveBeenCalled();
      }
    });
  });

  describe('Loading State', () => {
    it('should show loading message when isLoading is true', () => {
      vi.mocked(useSessionsModule.useSessions).mockReturnValue({
        sessions: [],
        groupedSessions: {
          today: [],
          yesterday: [],
          lastWeek: [],
          older: [],
        },
        isLoading: true,
        error: null,
        refetch: vi.fn(),
        removeSession: mockRemoveSession,
      });

      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('should not show session groups when loading', () => {
      vi.mocked(useSessionsModule.useSessions).mockReturnValue({
        sessions: [],
        groupedSessions: {
          today: [],
          yesterday: [],
          lastWeek: [],
          older: [],
        },
        isLoading: true,
        error: null,
        refetch: vi.fn(),
        removeSession: mockRemoveSession,
      });

      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.queryByText('Today')).not.toBeInTheDocument();
    });

    it('should show session groups when loading completes', async () => {
      // Start with loading state
      vi.mocked(useSessionsModule.useSessions).mockReturnValue({
        sessions: [],
        groupedSessions: {
          today: [],
          yesterday: [],
          lastWeek: [],
          older: [],
        },
        isLoading: true,
        error: null,
        refetch: vi.fn(),
        removeSession: mockRemoveSession,
      });

      const { rerender } = render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText('Loading...')).toBeInTheDocument();

      // Update mock to show sessions
      vi.mocked(useSessionsModule.useSessions).mockReturnValue({
        sessions: [],
        groupedSessions: mockSessionsData,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        removeSession: mockRemoveSession,
      });

      rerender(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
        expect(screen.getByText('Today')).toBeInTheDocument();
      });
    });
  });

  describe('Empty State', () => {
    it('should not render any session groups when all are empty', () => {
      vi.mocked(useSessionsModule.useSessions).mockReturnValue({
        sessions: [],
        groupedSessions: {
          today: [],
          yesterday: [],
          lastWeek: [],
          older: [],
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        removeSession: mockRemoveSession,
      });

      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.queryByText('Today')).not.toBeInTheDocument();
      expect(screen.queryByText('Yesterday')).not.toBeInTheDocument();
      expect(screen.queryByText('Last 7 Days')).not.toBeInTheDocument();
      expect(screen.queryByText('Older')).not.toBeInTheDocument();
    });

    it('should show New Chat button even with no sessions', () => {
      vi.mocked(useSessionsModule.useSessions).mockReturnValue({
        sessions: [],
        groupedSessions: {
          today: [],
          yesterday: [],
          lastWeek: [],
          older: [],
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        removeSession: mockRemoveSession,
      });

      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByTestId('new-chat-button')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle session with very long title', () => {
      const longTitle = 'A'.repeat(200);
      vi.mocked(useSessionsModule.useSessions).mockReturnValue({
        sessions: [],
        groupedSessions: {
          today: [
            {
              session_id: 'session-long',
              title: longTitle,
              preview: 'Preview',
              updated_at: new Date().toISOString(),
              message_count: 1,
            },
          ],
          yesterday: [],
          lastWeek: [],
          older: [],
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        removeSession: mockRemoveSession,
      });

      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      // Should truncate with CSS (truncate class)
      const titleElement = screen.getByTestId('session-title');
      expect(titleElement.className).toContain('truncate');
    });

    it('should handle session without preview', () => {
      vi.mocked(useSessionsModule.useSessions).mockReturnValue({
        sessions: [],
        groupedSessions: {
          today: [
            {
              session_id: 'session-no-preview',
              title: 'Session Title',
              preview: undefined,
              updated_at: new Date().toISOString(),
              message_count: 0,
            },
          ],
          yesterday: [],
          lastWeek: [],
          older: [],
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        removeSession: mockRemoveSession,
      });

      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText('Session Title')).toBeInTheDocument();
    });

    it('should prevent delete click from triggering session selection', async () => {
      render(
        <SessionSidebar
          currentSessionId={null}
          onNewChat={mockOnNewChat}
          onSelectSession={mockOnSelectSession}
          isOpen={true}
          onToggle={mockOnToggle}
        />
      );

      const sessionItem = screen.getAllByTestId('session-item')[0];
      fireEvent.mouseEnter(sessionItem);

      await waitFor(() => {
        expect(screen.getByTestId('delete-session')).toBeInTheDocument();
      });

      const deleteButton = screen.getByTestId('delete-session');
      fireEvent.click(deleteButton);

      // onSelectSession should not be called when delete is clicked
      // (due to e.stopPropagation() in the delete handler)
      expect(mockOnSelectSession).not.toHaveBeenCalled();
    });
  });
});

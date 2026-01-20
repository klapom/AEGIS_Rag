/**
 * BashToolExecutor Component Tests
 * Sprint 116 Feature 116.6: Bash Tool Execution UI (8 SP)
 *
 * Test Coverage:
 * - Component rendering
 * - Command input and execution
 * - Result display (success/error)
 * - Command history management
 * - Keyboard shortcuts
 * - Error handling
 * - localStorage persistence
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BashToolExecutor, BashExecutionResult } from '../BashToolExecutor';

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock localStorage
const localStorageMock: Record<string, string> = {};
global.localStorage = {
  getItem: vi.fn((key: string) => localStorageMock[key] ?? null),
  setItem: vi.fn((key: string, value: string) => {
    localStorageMock[key] = value;
  }),
  removeItem: vi.fn((key: string) => {
    delete localStorageMock[key];
  }),
  clear: vi.fn(() => {
    Object.keys(localStorageMock).forEach((key) => delete localStorageMock[key]);
  }),
  key: vi.fn(),
  length: 0,
};

// Mock navigator.clipboard
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn(() => Promise.resolve()),
  },
});

describe('BashToolExecutor', () => {
  const mockSuccessResult: BashExecutionResult = {
    result: {
      success: true,
      stdout: 'Hello World\n',
      stderr: '',
      exit_code: 0,
    },
    execution_time_ms: 42,
    status: 'success',
  };

  const mockErrorResult: BashExecutionResult = {
    result: {
      success: false,
      stdout: '',
      stderr: 'command not found: invalid_command\n',
      exit_code: 127,
    },
    execution_time_ms: 15,
    status: 'error',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    Object.keys(localStorageMock).forEach((key) => delete localStorageMock[key]);
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('Rendering', () => {
    it('should render component with all sections', () => {
      render(<BashToolExecutor />);

      expect(screen.getByTestId('bash-tool-executor')).toBeInTheDocument();
      expect(screen.getByText('Bash Command Execution')).toBeInTheDocument();
      expect(screen.getByTestId('bash-command-input')).toBeInTheDocument();
      expect(screen.getByTestId('execute-bash-button')).toBeInTheDocument();
      expect(screen.getByText(/Command History/)).toBeInTheDocument();
    });

    it('should render with custom API base URL', () => {
      render(<BashToolExecutor apiBaseUrl="http://custom.api.com" />);

      expect(screen.getByTestId('bash-tool-executor')).toBeInTheDocument();
    });

    it('should show empty history message initially', () => {
      render(<BashToolExecutor />);

      expect(screen.getByText('No command history yet')).toBeInTheDocument();
    });
  });

  describe('Command Input', () => {
    it('should allow typing in command input', async () => {
      const user = userEvent.setup();
      render(<BashToolExecutor />);

      const input = screen.getByTestId('bash-command-input') as HTMLTextAreaElement;
      await user.type(input, 'ls -la');

      expect(input.value).toBe('ls -la');
    });

    it('should disable execute button when command is empty', () => {
      render(<BashToolExecutor />);

      const executeButton = screen.getByTestId('execute-bash-button');
      expect(executeButton).toBeDisabled();
    });

    it('should enable execute button when command is entered', async () => {
      const user = userEvent.setup();
      render(<BashToolExecutor />);

      const input = screen.getByTestId('bash-command-input');
      await user.type(input, 'pwd');

      const executeButton = screen.getByTestId('execute-bash-button');
      expect(executeButton).not.toBeDisabled();
    });

    it('should copy command to clipboard', async () => {
      const user = userEvent.setup();
      render(<BashToolExecutor />);

      const input = screen.getByTestId('bash-command-input');
      await user.type(input, 'echo "test"');

      const copyButton = screen.getByTestId('copy-command-button');
      await user.click(copyButton);

      await waitFor(() => {
        expect(navigator.clipboard.writeText).toHaveBeenCalledWith('echo "test"');
        expect(screen.getByText('Copied')).toBeInTheDocument();
      });
    });
  });

  describe('Command Execution', () => {
    it('should execute command successfully', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuccessResult,
      });

      render(<BashToolExecutor />);

      const input = screen.getByTestId('bash-command-input');
      await user.type(input, 'echo "Hello World"');

      const executeButton = screen.getByTestId('execute-bash-button');
      await user.click(executeButton);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/mcp/tools/bash/execute',
          expect.objectContaining({
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              parameters: { command: 'echo "Hello World"' },
              timeout: 30,
            }),
          })
        );
      });

      await waitFor(() => {
        expect(screen.getByTestId('bash-execution-result')).toBeInTheDocument();
        expect(screen.getByText('Exit Code: 0')).toBeInTheDocument();
        expect(screen.getByText('42ms')).toBeInTheDocument();
      });
    });

    it('should display stdout output', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuccessResult,
      });

      render(<BashToolExecutor />);

      const input = screen.getByTestId('bash-command-input');
      await user.type(input, 'echo test');

      const executeButton = screen.getByTestId('execute-bash-button');
      await user.click(executeButton);

      await waitFor(() => {
        expect(screen.getByText('Hello World')).toBeInTheDocument();
      });
    });

    it('should display stderr output for failed commands', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockErrorResult,
      });

      render(<BashToolExecutor />);

      const input = screen.getByTestId('bash-command-input');
      await user.type(input, 'invalid_command');

      const executeButton = screen.getByTestId('execute-bash-button');
      await user.click(executeButton);

      await waitFor(() => {
        expect(screen.getByText('Exit Code: 127')).toBeInTheDocument();
        expect(screen.getByText(/command not found/)).toBeInTheDocument();
      });
    });

    it('should handle API errors', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: 'Internal server error' }),
      });

      render(<BashToolExecutor />);

      const input = screen.getByTestId('bash-command-input');
      await user.type(input, 'test');

      const executeButton = screen.getByTestId('execute-bash-button');
      await user.click(executeButton);

      await waitFor(() => {
        expect(screen.getByTestId('bash-execution-error')).toBeInTheDocument();
        expect(screen.getByText(/Internal server error/)).toBeInTheDocument();
      });
    });

    it('should show loading state during execution', async () => {
      const user = userEvent.setup();
      mockFetch.mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () => resolve({ ok: true, json: async () => mockSuccessResult }),
              100
            )
          )
      );

      render(<BashToolExecutor />);

      const input = screen.getByTestId('bash-command-input');
      await user.type(input, 'sleep 1');

      const executeButton = screen.getByTestId('execute-bash-button');
      await user.click(executeButton);

      expect(screen.getByText('Executing...')).toBeInTheDocument();
      expect(executeButton).toBeDisabled();

      await waitFor(
        () => {
          expect(screen.getByText('Execute Command')).toBeInTheDocument();
        },
        { timeout: 200 }
      );
    });

    it('should call onExecute callback', async () => {
      const user = userEvent.setup();
      const onExecute = vi.fn();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuccessResult,
      });

      render(<BashToolExecutor onExecute={onExecute} />);

      const input = screen.getByTestId('bash-command-input');
      await user.type(input, 'pwd');

      const executeButton = screen.getByTestId('execute-bash-button');
      await user.click(executeButton);

      await waitFor(() => {
        expect(onExecute).toHaveBeenCalledWith('pwd', mockSuccessResult);
      });
    });

    it('should prevent execution when command is empty', async () => {
      const user = userEvent.setup();
      render(<BashToolExecutor />);

      const input = screen.getByTestId('bash-command-input');
      await user.type(input, '   '); // Only whitespace

      const executeButton = screen.getByTestId('execute-bash-button');
      expect(executeButton).toBeDisabled();
    });
  });

  describe('Keyboard Shortcuts', () => {
    it('should execute command on Ctrl+Enter', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuccessResult,
      });

      render(<BashToolExecutor />);

      const input = screen.getByTestId('bash-command-input');
      await user.type(input, 'echo test');
      await user.keyboard('{Control>}{Enter}{/Control}');

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });
    });

    it('should execute command on Meta+Enter (Mac)', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuccessResult,
      });

      render(<BashToolExecutor />);

      const input = screen.getByTestId('bash-command-input');
      await user.type(input, 'echo test');
      await user.keyboard('{Meta>}{Enter}{/Meta}');

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });
    });
  });

  describe('Command History', () => {
    it('should add executed command to history', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuccessResult,
      });

      render(<BashToolExecutor />);

      const input = screen.getByTestId('bash-command-input');
      await user.type(input, 'ls -la');

      const executeButton = screen.getByTestId('execute-bash-button');
      await user.click(executeButton);

      await waitFor(() => {
        const historyEntry = screen.getByText('ls -la');
        expect(historyEntry).toBeInTheDocument();
      });
    });

    it('should save history to localStorage', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuccessResult,
      });

      render(<BashToolExecutor />);

      const input = screen.getByTestId('bash-command-input');
      await user.type(input, 'pwd');

      const executeButton = screen.getByTestId('execute-bash-button');
      await user.click(executeButton);

      await waitFor(() => {
        expect(localStorage.setItem).toHaveBeenCalledWith(
          'aegis_bash_command_history',
          expect.stringContaining('pwd')
        );
      });
    });

    it('should load command from history', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuccessResult,
      });

      render(<BashToolExecutor />);

      // Execute first command
      const input = screen.getByTestId('bash-command-input') as HTMLTextAreaElement;
      await user.type(input, 'echo "first"');
      await user.click(screen.getByTestId('execute-bash-button'));

      await waitFor(() => {
        expect(screen.getByText('echo "first"')).toBeInTheDocument();
      });

      // Clear input
      await user.clear(input);
      await user.type(input, 'different command');

      // Click history entry
      const historyEntry = screen.getByText('echo "first"');
      await user.click(historyEntry.closest('button')!);

      expect(input.value).toBe('echo "first"');
    });

    it('should clear all history', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockSuccessResult,
      });

      render(<BashToolExecutor />);

      // Add some commands to history
      const input = screen.getByTestId('bash-command-input');
      await user.type(input, 'ls');
      await user.click(screen.getByTestId('execute-bash-button'));

      await waitFor(() => {
        expect(screen.getByText('ls')).toBeInTheDocument();
      });

      // Clear history
      const clearButton = screen.getByTestId('clear-history');
      await user.click(clearButton);

      expect(screen.getByText('No command history yet')).toBeInTheDocument();
    });

    it('should toggle history visibility', async () => {
      const user = userEvent.setup();
      render(<BashToolExecutor />);

      const toggleButton = screen.getByTestId('toggle-history');

      // History should be visible by default
      expect(screen.getByText('No command history yet')).toBeInTheDocument();

      // Hide history
      await user.click(toggleButton);
      expect(screen.queryByText('No command history yet')).not.toBeInTheDocument();

      // Show history again
      await user.click(toggleButton);
      expect(screen.getByText('No command history yet')).toBeInTheDocument();
    });

    it('should limit history to 10 entries', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockSuccessResult,
      });

      render(<BashToolExecutor />);

      const input = screen.getByTestId('bash-command-input') as HTMLTextAreaElement;
      const executeButton = screen.getByTestId('execute-bash-button');

      // Add 12 commands
      for (let i = 0; i < 12; i++) {
        await user.clear(input);
        await user.type(input, `command${i}`);
        await user.click(executeButton);
        await waitFor(() => {
          expect(screen.getByText(`command${i}`)).toBeInTheDocument();
        });
      }

      // First two commands should not be in history
      expect(screen.queryByText('command0')).not.toBeInTheDocument();
      expect(screen.queryByText('command1')).not.toBeInTheDocument();

      // Last 10 commands should be present
      expect(screen.getByText('command11')).toBeInTheDocument();
      expect(screen.getByText('command2')).toBeInTheDocument();
    });
  });

  describe('Output Display', () => {
    it('should toggle stdout visibility', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuccessResult,
      });

      render(<BashToolExecutor />);

      const input = screen.getByTestId('bash-command-input');
      await user.type(input, 'echo test');
      await user.click(screen.getByTestId('execute-bash-button'));

      await waitFor(() => {
        expect(screen.getByText('Hello World')).toBeInTheDocument();
      });

      const toggleStdout = screen.getByTestId('toggle-stdout');
      await user.click(toggleStdout);

      expect(screen.queryByText('Hello World')).not.toBeInTheDocument();
    });

    it('should toggle stderr visibility', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockErrorResult,
      });

      render(<BashToolExecutor />);

      const input = screen.getByTestId('bash-command-input');
      await user.type(input, 'invalid');
      await user.click(screen.getByTestId('execute-bash-button'));

      await waitFor(() => {
        expect(screen.getByText(/command not found/)).toBeInTheDocument();
      });

      const toggleStderr = screen.getByTestId('toggle-stderr');
      await user.click(toggleStderr);

      expect(screen.queryByText(/command not found/)).not.toBeInTheDocument();
    });

    it('should show "No output" when both stdout and stderr are empty', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          result: {
            success: true,
            stdout: '',
            stderr: '',
            exit_code: 0,
          },
          execution_time_ms: 10,
          status: 'success',
        }),
      });

      render(<BashToolExecutor />);

      const input = screen.getByTestId('bash-command-input');
      await user.type(input, 'true');
      await user.click(screen.getByTestId('execute-bash-button'));

      await waitFor(() => {
        expect(screen.getByText('No output')).toBeInTheDocument();
      });
    });
  });

  describe('Authentication', () => {
    it('should include auth token in API request', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuccessResult,
      });

      render(<BashToolExecutor authToken="test-token-123" />);

      const input = screen.getByTestId('bash-command-input');
      await user.type(input, 'ls');
      await user.click(screen.getByTestId('execute-bash-button'));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            headers: expect.objectContaining({
              Authorization: 'Bearer test-token-123',
            }),
          })
        );
      });
    });
  });
});

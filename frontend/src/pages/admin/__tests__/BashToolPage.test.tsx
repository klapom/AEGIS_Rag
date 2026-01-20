/**
 * BashToolPage Integration Tests
 * Sprint 116 Feature 116.6: Bash Tool Execution UI (8 SP)
 *
 * Integration tests for the BashToolPage component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import { BashToolPage } from '../BashToolPage';

// Mock navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

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

describe('BashToolPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.keys(localStorageMock).forEach((key) => delete localStorageMock[key]);
  });

  it('should render the page with header and bash executor', () => {
    render(
      <BrowserRouter>
        <BashToolPage />
      </BrowserRouter>
    );

    expect(screen.getByText('Bash Tool')).toBeInTheDocument();
    expect(screen.getByText('Execute Bash Commands')).toBeInTheDocument();
    expect(screen.getByTestId('bash-tool-executor')).toBeInTheDocument();
  });

  it('should navigate back to admin dashboard when back button is clicked', async () => {
    const user = userEvent.setup();
    render(
      <BrowserRouter>
        <BashToolPage />
      </BrowserRouter>
    );

    const backButton = screen.getByLabelText('Back to admin dashboard');
    await user.click(backButton);

    expect(mockNavigate).toHaveBeenCalledWith('/admin');
  });

  it('should display usage tips section', () => {
    render(
      <BrowserRouter>
        <BashToolPage />
      </BrowserRouter>
    );

    expect(screen.getByText('Usage Tips')).toBeInTheDocument();
    expect(screen.getAllByText(/Ctrl\+Enter/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Command history is stored locally/)).toBeInTheDocument();
  });

  it('should display security notice', () => {
    render(
      <BrowserRouter>
        <BashToolPage />
      </BrowserRouter>
    );

    expect(screen.getByText('Security Notice')).toBeInTheDocument();
    expect(screen.getByText(/Be cautious when executing commands/)).toBeInTheDocument();
  });

  it('should execute bash command through the executor', async () => {
    const user = userEvent.setup();
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        result: {
          success: true,
          stdout: 'test output\n',
          stderr: '',
          exit_code: 0,
        },
        execution_time_ms: 42,
        status: 'success',
      }),
    });

    render(
      <BrowserRouter>
        <BashToolPage />
      </BrowserRouter>
    );

    const input = screen.getByTestId('bash-command-input');
    await user.type(input, 'echo "test"');

    const executeButton = screen.getByTestId('execute-bash-button');
    await user.click(executeButton);

    await waitFor(
      () => {
        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/mcp/tools/bash/execute',
          expect.any(Object)
        );
      },
      { timeout: 3000 }
    );

    await waitFor(
      () => {
        expect(screen.getByText('test output')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('should pass auth token from localStorage to executor', () => {
    localStorageMock['auth_token'] = 'test-token-123';

    render(
      <BrowserRouter>
        <BashToolPage />
      </BrowserRouter>
    );

    expect(screen.getByTestId('bash-tool-executor')).toBeInTheDocument();
    // Auth token is passed as prop - this is tested in BashToolExecutor.test.tsx
  });

  it('should have proper responsive layout', () => {
    render(
      <BrowserRouter>
        <BashToolPage />
      </BrowserRouter>
    );

    // Check for max-width container
    const mainHeading = screen.getByText('Execute Bash Commands');
    expect(mainHeading).toBeInTheDocument();
    // The parent container should have max-w-7xl class somewhere in hierarchy
    const container = mainHeading.closest('.max-w-7xl');
    expect(container).toBeInTheDocument();
  });

  it('should display all help sections', () => {
    render(
      <BrowserRouter>
        <BashToolPage />
      </BrowserRouter>
    );

    // Usage tips
    expect(screen.getByText('Usage Tips')).toBeInTheDocument();

    // Security notice
    expect(screen.getByText('Security Notice')).toBeInTheDocument();

    // Verify key usage tips are present (using getAllByText for duplicates)
    expect(screen.getByText(/Command history is stored locally/)).toBeInTheDocument();
    expect(screen.getByText(/Click on any command in the history/)).toBeInTheDocument();
    expect(screen.getAllByText(/30-second timeout/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Exit code 0/).length).toBeGreaterThan(0);
  });

  it('should log command execution to console', async () => {
    const user = userEvent.setup();
    const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        result: {
          success: true,
          stdout: 'output\n',
          stderr: '',
          exit_code: 0,
        },
        execution_time_ms: 10,
        status: 'success',
      }),
    });

    render(
      <BrowserRouter>
        <BashToolPage />
      </BrowserRouter>
    );

    const input = screen.getByTestId('bash-command-input');
    await user.type(input, 'pwd');

    const executeButton = screen.getByTestId('execute-bash-button');
    await user.click(executeButton);

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith(
        'Command executed:',
        expect.objectContaining({
          command: 'pwd',
        })
      );
    });

    consoleSpy.mockRestore();
  });

  it('should handle errors gracefully', async () => {
    const user = userEvent.setup();
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Internal server error' }),
    });

    render(
      <BrowserRouter>
        <BashToolPage />
      </BrowserRouter>
    );

    const input = screen.getByTestId('bash-command-input');
    await user.type(input, 'test');

    const executeButton = screen.getByTestId('execute-bash-button');
    await user.click(executeButton);

    await waitFor(() => {
      expect(screen.getByTestId('bash-execution-error')).toBeInTheDocument();
    });
  });
});

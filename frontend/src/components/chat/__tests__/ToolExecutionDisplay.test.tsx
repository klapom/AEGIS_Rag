/**
 * ToolExecutionDisplay Component Tests
 * Sprint 63 Feature 63.10: Tool Output Visualization in Chat UI
 *
 * Tests for the ToolExecutionDisplay component which renders tool execution
 * results with syntax highlighting, stdout/stderr output, and exit codes.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ToolExecutionDisplay } from '../ToolExecutionDisplay';
import type { ToolExecutionStep } from '../../../types/reasoning';

// Mock react-syntax-highlighter to avoid ESM issues in tests
vi.mock('react-syntax-highlighter', () => ({
  Prism: ({ children }: { children: string }) => (
    <pre data-testid="syntax-highlighter">{children}</pre>
  ),
}));

vi.mock('react-syntax-highlighter/dist/esm/styles/prism', () => ({
  oneDark: {},
}));

describe('ToolExecutionDisplay', () => {
  const mockBashStep: ToolExecutionStep = {
    tool_name: 'bash',
    server: 'local',
    input: {
      command: 'ls -la /home/user',
    },
    output: {
      stdout: 'total 24\ndrwxr-xr-x  6 user user 4096 Dec 23 10:00 .\ndrwxr-xr-x  3 root root 4096 Dec 20 09:00 ..',
      stderr: '',
      exit_code: 0,
      success: true,
    },
    duration_ms: 42,
    timestamp: '2025-12-23T10:00:00Z',
  };

  const mockPythonStep: ToolExecutionStep = {
    tool_name: 'python',
    server: 'dgx-spark',
    input: {
      code: 'import sys\nprint(sys.version)\nprint("Hello, World!")',
    },
    output: {
      stdout: '3.12.7 (main, Dec 10 2024, 00:00:00) [GCC 11.4.0]\nHello, World!',
      stderr: '',
      exit_code: 0,
      success: true,
    },
    duration_ms: 156,
    timestamp: '2025-12-23T10:05:00Z',
  };

  const mockFailedStep: ToolExecutionStep = {
    tool_name: 'bash',
    server: 'remote',
    input: {
      command: 'cat /nonexistent/file.txt',
    },
    output: {
      stdout: '',
      stderr: 'cat: /nonexistent/file.txt: No such file or directory',
      exit_code: 1,
      success: false,
      error: 'Command failed with exit code 1',
    },
    duration_ms: 12,
    timestamp: '2025-12-23T10:10:00Z',
  };

  const mockEmptyOutputStep: ToolExecutionStep = {
    tool_name: 'bash',
    server: 'local',
    input: {
      command: 'true',
    },
    output: {
      stdout: '',
      stderr: '',
      exit_code: 0,
      success: true,
    },
    duration_ms: 5,
    timestamp: '2025-12-23T10:15:00Z',
  };

  describe('Basic Rendering', () => {
    it('renders tool execution display container', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      expect(screen.getByTestId('tool-execution-display')).toBeInTheDocument();
    });

    it('sets correct data-tool attribute for bash', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      const display = screen.getByTestId('tool-execution-display');
      expect(display).toHaveAttribute('data-tool', 'bash');
    });

    it('sets correct data-tool attribute for python', () => {
      render(<ToolExecutionDisplay step={mockPythonStep} />);
      const display = screen.getByTestId('tool-execution-display');
      expect(display).toHaveAttribute('data-tool', 'python');
    });
  });

  describe('Header Section', () => {
    it('displays tool name correctly for bash', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      expect(screen.getByText('bash')).toBeInTheDocument();
    });

    it('displays tool name correctly for python', () => {
      render(<ToolExecutionDisplay step={mockPythonStep} />);
      expect(screen.getByText('python')).toBeInTheDocument();
    });

    it('displays server badge', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      const serverBadge = screen.getByTestId('server-badge');
      expect(serverBadge).toBeInTheDocument();
      expect(serverBadge).toHaveTextContent('local');
    });

    it('displays duration for bash step', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      const duration = screen.getByTestId('duration-display');
      expect(duration).toHaveTextContent('42ms');
    });

    it('displays duration in seconds for longer executions', () => {
      const longStep: ToolExecutionStep = {
        ...mockBashStep,
        duration_ms: 1500,
      };
      render(<ToolExecutionDisplay step={longStep} />);
      const duration = screen.getByTestId('duration-display');
      expect(duration).toHaveTextContent('1.50s');
    });

    it('displays exit code badge with success styling for exit_code 0', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      const exitBadge = screen.getByTestId('exit-code-badge');
      expect(exitBadge).toHaveTextContent('Exit: 0');
      expect(exitBadge).toHaveClass('text-green-700');
    });

    it('displays exit code badge with error styling for non-zero exit_code', () => {
      render(<ToolExecutionDisplay step={mockFailedStep} />);
      const exitBadge = screen.getByTestId('exit-code-badge');
      expect(exitBadge).toHaveTextContent('Exit: 1');
      expect(exitBadge).toHaveClass('text-red-700');
    });
  });

  describe('Command/Code Section', () => {
    it('displays bash command with syntax highlighting', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      expect(screen.getByTestId('syntax-highlighter')).toBeInTheDocument();
      expect(screen.getByTestId('syntax-highlighter')).toHaveTextContent('ls -la /home/user');
    });

    it('displays python code with syntax highlighting', () => {
      render(<ToolExecutionDisplay step={mockPythonStep} />);
      expect(screen.getByTestId('syntax-highlighter')).toHaveTextContent('import sys');
      expect(screen.getByTestId('syntax-highlighter')).toHaveTextContent('print(sys.version)');
    });

    it('shows "Command" label for bash tool', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      expect(screen.getByText('Command')).toBeInTheDocument();
    });

    it('shows "Code" label for python tool', () => {
      render(<ToolExecutionDisplay step={mockPythonStep} />);
      expect(screen.getByText('Code')).toBeInTheDocument();
    });

    it('command section is expanded by default', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      expect(screen.getByTestId('command-content')).toBeInTheDocument();
    });

    it('collapses command section when toggle clicked', async () => {
      const user = userEvent.setup();
      render(<ToolExecutionDisplay step={mockBashStep} />);

      const toggle = screen.getByTestId('command-toggle');
      await user.click(toggle);

      expect(screen.queryByTestId('command-content')).not.toBeInTheDocument();
    });

    it('expands command section when toggle clicked again', async () => {
      const user = userEvent.setup();
      render(<ToolExecutionDisplay step={mockBashStep} />);

      const toggle = screen.getByTestId('command-toggle');
      await user.click(toggle); // collapse
      await user.click(toggle); // expand

      expect(screen.getByTestId('command-content')).toBeInTheDocument();
    });
  });

  describe('Output Section - stdout', () => {
    it('displays stdout output', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      const stdoutSection = screen.getByTestId('output-section-stdout');
      expect(stdoutSection).toBeInTheDocument();
      expect(stdoutSection).toHaveTextContent('total 24');
    });

    it('does not display stdout section when stdout is empty', () => {
      render(<ToolExecutionDisplay step={mockEmptyOutputStep} />);
      expect(screen.queryByTestId('output-section-stdout')).not.toBeInTheDocument();
    });

    it('shows "No output" when both stdout and stderr are empty', () => {
      render(<ToolExecutionDisplay step={mockEmptyOutputStep} />);
      expect(screen.getByTestId('no-output')).toHaveTextContent('No output');
    });
  });

  describe('Output Section - stderr', () => {
    it('displays stderr output with error styling', () => {
      render(<ToolExecutionDisplay step={mockFailedStep} />);
      const stderrSection = screen.getByTestId('output-section-stderr');
      expect(stderrSection).toBeInTheDocument();
      expect(stderrSection).toHaveTextContent('No such file or directory');
    });

    it('does not display stderr section when stderr is empty', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      expect(screen.queryByTestId('output-section-stderr')).not.toBeInTheDocument();
    });
  });

  describe('Error Message', () => {
    it('displays error message when present', () => {
      render(<ToolExecutionDisplay step={mockFailedStep} />);
      const errorMsg = screen.getByTestId('error-message');
      expect(errorMsg).toBeInTheDocument();
      expect(errorMsg).toHaveTextContent('Command failed with exit code 1');
    });

    it('does not display error message when not present', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      expect(screen.queryByTestId('error-message')).not.toBeInTheDocument();
    });
  });

  describe('Copy Functionality', () => {
    it('renders copy command button', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      const copyButton = screen.getByTestId('copy-command-button');
      expect(copyButton).toBeInTheDocument();
      expect(copyButton).toHaveAttribute('aria-label', 'Copy command');
    });

    it('renders copy output button for stdout', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      const copyButtons = screen.getAllByTestId('copy-output-button');
      expect(copyButtons.length).toBeGreaterThan(0);
      expect(copyButtons[0]).toHaveAttribute('aria-label', 'Copy output');
    });

    it('copy button is clickable without throwing', async () => {
      const user = userEvent.setup();
      render(<ToolExecutionDisplay step={mockBashStep} />);

      const copyButton = screen.getByTestId('copy-command-button');
      // Should not throw even if clipboard API fails
      await expect(user.click(copyButton)).resolves.not.toThrow();
    });
  });

  describe('Collapsible Behavior', () => {
    it('stdout section is expanded by default', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      const stdoutSection = screen.getByTestId('output-section-stdout');
      expect(stdoutSection.querySelector('pre')).toBeInTheDocument();
    });

    it('stderr section is expanded by default', () => {
      render(<ToolExecutionDisplay step={mockFailedStep} />);
      const stderrSection = screen.getByTestId('output-section-stderr');
      expect(stderrSection.querySelector('pre')).toBeInTheDocument();
    });
  });

  describe('Different Tool Types', () => {
    it('handles unknown tool type gracefully', () => {
      const unknownToolStep: ToolExecutionStep = {
        ...mockBashStep,
        tool_name: 'unknown_tool',
        input: {
          arguments: { foo: 'bar', baz: 123 },
        },
      };
      render(<ToolExecutionDisplay step={unknownToolStep} />);
      expect(screen.getByTestId('tool-execution-display')).toBeInTheDocument();
      expect(screen.getByText('unknown_tool')).toBeInTheDocument();
    });

    it('displays JSON arguments for tools with generic arguments', () => {
      const genericToolStep: ToolExecutionStep = {
        ...mockBashStep,
        tool_name: 'generic',
        input: {
          arguments: { param1: 'value1', param2: 42 },
        },
      };
      render(<ToolExecutionDisplay step={genericToolStep} />);
      const highlighter = screen.getByTestId('syntax-highlighter');
      expect(highlighter).toHaveTextContent('param1');
      expect(highlighter).toHaveTextContent('value1');
    });
  });

  describe('Duration Formatting', () => {
    it('formats sub-millisecond duration correctly', () => {
      const fastStep: ToolExecutionStep = {
        ...mockBashStep,
        duration_ms: 0.5,
      };
      render(<ToolExecutionDisplay step={fastStep} />);
      const duration = screen.getByTestId('duration-display');
      expect(duration).toHaveTextContent('<1ms');
    });

    it('formats millisecond duration correctly', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      const duration = screen.getByTestId('duration-display');
      expect(duration).toHaveTextContent('42ms');
    });

    it('formats seconds duration correctly', () => {
      const slowStep: ToolExecutionStep = {
        ...mockBashStep,
        duration_ms: 2345,
      };
      render(<ToolExecutionDisplay step={slowStep} />);
      const duration = screen.getByTestId('duration-display');
      expect(duration).toHaveTextContent('2.35s');
    });

    it('does not display duration when undefined', () => {
      const noDurationStep: ToolExecutionStep = {
        ...mockBashStep,
        duration_ms: undefined,
      };
      render(<ToolExecutionDisplay step={noDurationStep} />);
      expect(screen.queryByTestId('duration-display')).not.toBeInTheDocument();
    });
  });

  describe('Exit Code Badge', () => {
    it('does not render exit code badge when undefined', () => {
      const noExitCodeStep: ToolExecutionStep = {
        ...mockBashStep,
        output: {
          ...mockBashStep.output,
          exit_code: undefined,
        },
      };
      render(<ToolExecutionDisplay step={noExitCodeStep} />);
      expect(screen.queryByTestId('exit-code-badge')).not.toBeInTheDocument();
    });

    it('renders success icon for exit code 0', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      const badge = screen.getByTestId('exit-code-badge');
      expect(badge.querySelector('svg')).toBeInTheDocument();
    });

    it('renders error icon for non-zero exit code', () => {
      render(<ToolExecutionDisplay step={mockFailedStep} />);
      const badge = screen.getByTestId('exit-code-badge');
      expect(badge.querySelector('svg')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has accessible command toggle button', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      const toggle = screen.getByTestId('command-toggle');
      expect(toggle).toHaveAttribute('aria-expanded', 'true');
    });

    it('updates aria-expanded when command section collapsed', async () => {
      const user = userEvent.setup();
      render(<ToolExecutionDisplay step={mockBashStep} />);

      const toggle = screen.getByTestId('command-toggle');
      await user.click(toggle);

      expect(toggle).toHaveAttribute('aria-expanded', 'false');
    });

    it('has accessible copy buttons with aria-label', () => {
      render(<ToolExecutionDisplay step={mockBashStep} />);
      const copyButton = screen.getByTestId('copy-command-button');
      expect(copyButton).toHaveAttribute('aria-label', 'Copy command');
    });
  });

  describe('Long Output Handling', () => {
    it('renders long stdout with scroll', () => {
      const longOutputStep: ToolExecutionStep = {
        ...mockBashStep,
        output: {
          ...mockBashStep.output,
          stdout: Array(100).fill('Line of output').join('\n'),
        },
      };
      render(<ToolExecutionDisplay step={longOutputStep} />);
      const stdoutSection = screen.getByTestId('output-section-stdout');
      expect(stdoutSection).toBeInTheDocument();
    });

    it('renders multiline command correctly', () => {
      const multilineStep: ToolExecutionStep = {
        ...mockPythonStep,
        input: {
          code: `def hello():
    print("Hello")
    return True

if __name__ == "__main__":
    hello()`,
        },
      };
      render(<ToolExecutionDisplay step={multilineStep} />);
      const highlighter = screen.getByTestId('syntax-highlighter');
      expect(highlighter).toHaveTextContent('def hello():');
      expect(highlighter).toHaveTextContent('return True');
    });
  });

  describe('Edge Cases', () => {
    it('handles empty command gracefully', () => {
      const emptyCommandStep: ToolExecutionStep = {
        ...mockBashStep,
        input: {
          command: '',
        },
      };
      render(<ToolExecutionDisplay step={emptyCommandStep} />);
      expect(screen.getByTestId('tool-execution-display')).toBeInTheDocument();
    });

    it('handles null-like values in output', () => {
      const nullOutputStep: ToolExecutionStep = {
        ...mockBashStep,
        output: {
          stdout: undefined,
          stderr: undefined,
          exit_code: 0,
          success: true,
        },
      };
      render(<ToolExecutionDisplay step={nullOutputStep} />);
      expect(screen.getByTestId('no-output')).toHaveTextContent('No output');
    });

    it('handles special characters in output', () => {
      const specialCharsStep: ToolExecutionStep = {
        ...mockBashStep,
        output: {
          ...mockBashStep.output,
          stdout: '<html>&amp;"quotes"</html>',
        },
      };
      render(<ToolExecutionDisplay step={specialCharsStep} />);
      const stdoutSection = screen.getByTestId('output-section-stdout');
      expect(stdoutSection).toHaveTextContent('<html>');
    });

    it('handles very long single line output', () => {
      const longLineStep: ToolExecutionStep = {
        ...mockBashStep,
        output: {
          ...mockBashStep.output,
          stdout: 'A'.repeat(1000),
        },
      };
      render(<ToolExecutionDisplay step={longLineStep} />);
      expect(screen.getByTestId('output-section-stdout')).toBeInTheDocument();
    });
  });
});

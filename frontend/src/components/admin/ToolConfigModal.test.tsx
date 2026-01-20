/**
 * ToolConfigModal Component Tests
 * Sprint 116 Feature 116.5: MCP Tool Management UI
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ToolConfigModal } from './ToolConfigModal';
import * as adminApi from '../../api/admin';
import type { MCPTool } from '../../types/admin';

// Mock the admin API
vi.mock('../../api/admin');

describe('ToolConfigModal', () => {
  const mockTool: MCPTool = {
    name: 'test-tool',
    description: 'Test tool description',
    server_name: 'test-server',
    parameters: [],
  };

  const mockConfig = {
    timeout: 60,
    max_retries: 3,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should not render when closed', () => {
    render(
      <ToolConfigModal
        tool={mockTool}
        isOpen={false}
        onClose={vi.fn()}
      />
    );

    expect(screen.queryByTestId('tool-config-modal')).not.toBeInTheDocument();
  });

  it('should render when open', () => {
    vi.mocked(adminApi.getToolConfig).mockResolvedValue({ config: mockConfig });

    render(
      <ToolConfigModal
        tool={mockTool}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByTestId('tool-config-modal')).toBeInTheDocument();
    expect(screen.getByText('Tool Configuration')).toBeInTheDocument();
    expect(screen.getByText('test-tool')).toBeInTheDocument();
  });

  it('should load configuration on open', async () => {
    vi.mocked(adminApi.getToolConfig).mockResolvedValue({ config: mockConfig });

    render(
      <ToolConfigModal
        tool={mockTool}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(adminApi.getToolConfig).toHaveBeenCalledWith('test-tool');
    });

    const editor = screen.getByTestId('config-editor') as HTMLTextAreaElement;
    expect(editor.value).toContain('"timeout": 60');
    expect(editor.value).toContain('"max_retries": 3');
  });

  it('should handle config load error', async () => {
    vi.mocked(adminApi.getToolConfig).mockRejectedValue(new Error('Failed to load'));

    render(
      <ToolConfigModal
        tool={mockTool}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('config-error')).toBeInTheDocument();
      expect(screen.getByText('Failed to load')).toBeInTheDocument();
    });
  });

  it('should validate JSON on change', async () => {
    vi.mocked(adminApi.getToolConfig).mockResolvedValue({ config: {} });
    const user = userEvent.setup();

    render(
      <ToolConfigModal
        tool={mockTool}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('config-editor')).toBeInTheDocument();
    });

    const editor = screen.getByTestId('config-editor') as HTMLTextAreaElement;

    // Invalid JSON - use fireEvent to set value directly
    await user.clear(editor);
    const { fireEvent } = await import('@testing-library/react');
    fireEvent.change(editor, { target: { value: '{invalid json' } });

    // Just check that some error text appears (JSON errors vary by browser)
    await waitFor(() => {
      const errorElements = screen.queryAllByText(/expected|unexpected|invalid/i);
      expect(errorElements.length).toBeGreaterThan(0);
    });

    // Valid JSON
    fireEvent.change(editor, { target: { value: '{"key": "value"}' } });

    await waitFor(() => {
      const errorElements = screen.queryAllByText(/expected|unexpected|invalid/i);
      expect(errorElements.length).toBe(0);
    });
  });

  it('should save configuration', async () => {
    vi.mocked(adminApi.getToolConfig).mockResolvedValue({ config: mockConfig });
    vi.mocked(adminApi.updateToolConfig).mockResolvedValue({ config: mockConfig });

    const onSave = vi.fn();
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <ToolConfigModal
        tool={mockTool}
        isOpen={true}
        onClose={onClose}
        onSave={onSave}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('save-config-button')).toBeInTheDocument();
    });

    const saveButton = screen.getByTestId('save-config-button');
    await user.click(saveButton);

    await waitFor(() => {
      expect(adminApi.updateToolConfig).toHaveBeenCalledWith('test-tool', mockConfig);
      expect(onSave).toHaveBeenCalledWith(mockConfig);
    });

    // Should auto-close after success
    await waitFor(
      () => {
        expect(onClose).toHaveBeenCalled();
      },
      { timeout: 2000 }
    );
  });

  it('should handle save error', async () => {
    vi.mocked(adminApi.getToolConfig).mockResolvedValue({ config: mockConfig });
    vi.mocked(adminApi.updateToolConfig).mockRejectedValue(new Error('Save failed'));

    const user = userEvent.setup();

    render(
      <ToolConfigModal
        tool={mockTool}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('save-config-button')).toBeInTheDocument();
    });

    const saveButton = screen.getByTestId('save-config-button');
    await user.click(saveButton);

    await waitFor(() => {
      expect(screen.getByTestId('config-error')).toBeInTheDocument();
      expect(screen.getByText('Save failed')).toBeInTheDocument();
    });
  });

  it('should disable save button for invalid JSON', async () => {
    vi.mocked(adminApi.getToolConfig).mockResolvedValue({ config: {} });
    const user = userEvent.setup();

    render(
      <ToolConfigModal
        tool={mockTool}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('config-editor')).toBeInTheDocument();
    });

    const editor = screen.getByTestId('config-editor');
    await user.clear(editor);
    await user.type(editor, '{{invalid');

    const saveButton = screen.getByTestId('save-config-button');
    expect(saveButton).toBeDisabled();
  });

  it('should close on cancel', async () => {
    vi.mocked(adminApi.getToolConfig).mockResolvedValue({ config: mockConfig });

    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <ToolConfigModal
        tool={mockTool}
        isOpen={true}
        onClose={onClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('cancel-button')).toBeInTheDocument();
    });

    const cancelButton = screen.getByTestId('cancel-button');
    await user.click(cancelButton);

    expect(onClose).toHaveBeenCalled();
  });

  it('should close on X button click', async () => {
    vi.mocked(adminApi.getToolConfig).mockResolvedValue({ config: mockConfig });

    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <ToolConfigModal
        tool={mockTool}
        isOpen={true}
        onClose={onClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('close-modal-button')).toBeInTheDocument();
    });

    const closeButton = screen.getByTestId('close-modal-button');
    await user.click(closeButton);

    expect(onClose).toHaveBeenCalled();
  });

  it('should display tool description and server', async () => {
    vi.mocked(adminApi.getToolConfig).mockResolvedValue({ config: mockConfig });

    render(
      <ToolConfigModal
        tool={mockTool}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Test tool description')).toBeInTheDocument();
      expect(screen.getByText('Server: test-server')).toBeInTheDocument();
    });
  });
});

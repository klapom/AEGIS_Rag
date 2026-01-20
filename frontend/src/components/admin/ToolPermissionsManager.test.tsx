/**
 * ToolPermissionsManager Component Tests
 * Sprint 116 Feature 116.5: MCP Tool Management UI
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ToolPermissionsManager } from './ToolPermissionsManager';
import * as adminApi from '../../api/admin';
import type { MCPTool, MCPToolPermission } from '../../types/admin';

// Mock the admin API
vi.mock('../../api/admin');

describe('ToolPermissionsManager', () => {
  const mockTools: MCPTool[] = [
    {
      name: 'tool1',
      description: 'First tool',
      server_name: 'server1',
      parameters: [],
    },
    {
      name: 'tool2',
      description: 'Second tool',
      server_name: 'server2',
      parameters: [],
    },
  ];

  const mockPermissions: Record<string, MCPToolPermission> = {
    tool1: {
      tool_name: 'tool1',
      server_name: 'server1',
      enabled: true,
      allowed_users: [],
      config: {},
    },
    tool2: {
      tool_name: 'tool2',
      server_name: 'server2',
      enabled: false,
      allowed_users: [],
      config: {},
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render with loading state', () => {
    vi.mocked(adminApi.getMCPTools).mockImplementation(() => new Promise(() => {}));

    render(<ToolPermissionsManager />);

    expect(screen.getByText('Loading tools...')).toBeInTheDocument();
  });

  it('should load and display tools', async () => {
    vi.mocked(adminApi.getMCPTools).mockResolvedValue(mockTools);
    vi.mocked(adminApi.getToolPermissions).mockImplementation((toolName) =>
      Promise.resolve(mockPermissions[toolName])
    );

    render(<ToolPermissionsManager />);

    await waitFor(() => {
      expect(screen.getByTestId('tool-card-tool1')).toBeInTheDocument();
      expect(screen.getByTestId('tool-card-tool2')).toBeInTheDocument();
    });

    expect(screen.getByText('First tool')).toBeInTheDocument();
    expect(screen.getByText('Second tool')).toBeInTheDocument();
  });

  it('should display enabled/disabled status badges', async () => {
    vi.mocked(adminApi.getMCPTools).mockResolvedValue(mockTools);
    vi.mocked(adminApi.getToolPermissions).mockImplementation((toolName) =>
      Promise.resolve(mockPermissions[toolName])
    );

    render(<ToolPermissionsManager />);

    await waitFor(() => {
      expect(screen.getAllByText('Enabled')[0]).toBeInTheDocument();
      expect(screen.getAllByText('Disabled')[0]).toBeInTheDocument();
    });
  });

  it('should show enabled/disabled counts', async () => {
    vi.mocked(adminApi.getMCPTools).mockResolvedValue(mockTools);
    vi.mocked(adminApi.getToolPermissions).mockImplementation((toolName) =>
      Promise.resolve(mockPermissions[toolName])
    );

    render(<ToolPermissionsManager />);

    await waitFor(() => {
      expect(screen.getByText(/1 enabled, 1 disabled/i)).toBeInTheDocument();
    });
  });

  it('should toggle tool permission', async () => {
    vi.mocked(adminApi.getMCPTools).mockResolvedValue(mockTools);
    vi.mocked(adminApi.getToolPermissions).mockImplementation((toolName) =>
      Promise.resolve(mockPermissions[toolName])
    );
    vi.mocked(adminApi.updateToolPermissions).mockResolvedValue({
      ...mockPermissions.tool1,
      enabled: false,
    });

    const user = userEvent.setup();

    render(<ToolPermissionsManager />);

    await waitFor(() => {
      expect(screen.getByTestId('toggle-tool1')).toBeInTheDocument();
    });

    const toggle = screen.getByTestId('toggle-tool1');
    await user.click(toggle);

    await waitFor(() => {
      expect(adminApi.updateToolPermissions).toHaveBeenCalledWith('tool1', false);
    });
  });

  it('should filter tools by search query', async () => {
    vi.mocked(adminApi.getMCPTools).mockResolvedValue(mockTools);
    vi.mocked(adminApi.getToolPermissions).mockImplementation((toolName) =>
      Promise.resolve(mockPermissions[toolName])
    );

    const user = userEvent.setup();

    render(<ToolPermissionsManager />);

    await waitFor(() => {
      expect(screen.getByTestId('tool-card-tool1')).toBeInTheDocument();
      expect(screen.getByTestId('tool-card-tool2')).toBeInTheDocument();
    });

    const searchInput = screen.getByTestId('tool-search-input');
    await user.type(searchInput, 'First');

    await waitFor(() => {
      expect(screen.getByTestId('tool-card-tool1')).toBeInTheDocument();
      expect(screen.queryByTestId('tool-card-tool2')).not.toBeInTheDocument();
    });
  });

  it('should open config modal on config button click', async () => {
    vi.mocked(adminApi.getMCPTools).mockResolvedValue(mockTools);
    vi.mocked(adminApi.getToolPermissions).mockImplementation((toolName) =>
      Promise.resolve(mockPermissions[toolName])
    );
    vi.mocked(adminApi.getToolConfig).mockResolvedValue({ config: {} });

    const user = userEvent.setup();

    render(<ToolPermissionsManager />);

    await waitFor(() => {
      expect(screen.getByTestId('config-button-tool1')).toBeInTheDocument();
    });

    const configButton = screen.getByTestId('config-button-tool1');
    await user.click(configButton);

    await waitFor(() => {
      expect(screen.getByTestId('tool-config-modal')).toBeInTheDocument();
    });
  });

  it('should refresh tools on refresh button click', async () => {
    vi.mocked(adminApi.getMCPTools).mockResolvedValue(mockTools);
    vi.mocked(adminApi.getToolPermissions).mockImplementation((toolName) =>
      Promise.resolve(mockPermissions[toolName])
    );

    const user = userEvent.setup();

    render(<ToolPermissionsManager />);

    await waitFor(() => {
      expect(screen.getByTestId('refresh-permissions')).toBeInTheDocument();
    });

    vi.mocked(adminApi.getMCPTools).mockClear();

    const refreshButton = screen.getByTestId('refresh-permissions');
    await user.click(refreshButton);

    await waitFor(() => {
      expect(adminApi.getMCPTools).toHaveBeenCalled();
    });
  });

  it('should handle error loading tools', async () => {
    vi.mocked(adminApi.getMCPTools).mockRejectedValue(new Error('Failed to load'));

    render(<ToolPermissionsManager />);

    await waitFor(() => {
      expect(screen.getByTestId('permissions-error')).toBeInTheDocument();
      expect(screen.getByText('Failed to load')).toBeInTheDocument();
    });
  });

  it('should show empty state when no tools', async () => {
    vi.mocked(adminApi.getMCPTools).mockResolvedValue([]);

    render(<ToolPermissionsManager />);

    await waitFor(() => {
      expect(screen.getByText('No Tools Available')).toBeInTheDocument();
      expect(screen.getByText(/Connect to MCP servers/i)).toBeInTheDocument();
    });
  });

  it('should show no matching tools when search has no results', async () => {
    vi.mocked(adminApi.getMCPTools).mockResolvedValue(mockTools);
    vi.mocked(adminApi.getToolPermissions).mockImplementation((toolName) =>
      Promise.resolve(mockPermissions[toolName])
    );

    const user = userEvent.setup();

    render(<ToolPermissionsManager />);

    await waitFor(() => {
      expect(screen.getByTestId('tool-search-input')).toBeInTheDocument();
    });

    const searchInput = screen.getByTestId('tool-search-input');
    await user.type(searchInput, 'nonexistent');

    await waitFor(() => {
      expect(screen.getByText('No Matching Tools')).toBeInTheDocument();
    });
  });

  it('should handle permission update error', async () => {
    vi.mocked(adminApi.getMCPTools).mockResolvedValue(mockTools);
    vi.mocked(adminApi.getToolPermissions).mockImplementation((toolName) =>
      Promise.resolve(mockPermissions[toolName])
    );
    vi.mocked(adminApi.updateToolPermissions).mockRejectedValue(
      new Error('Permission update failed')
    );

    // Mock alert
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

    const user = userEvent.setup();

    render(<ToolPermissionsManager />);

    await waitFor(() => {
      expect(screen.getByTestId('toggle-tool1')).toBeInTheDocument();
    });

    const toggle = screen.getByTestId('toggle-tool1');
    await user.click(toggle);

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith('Permission update failed');
    });

    alertSpy.mockRestore();
  });

  it('should display server name for each tool', async () => {
    vi.mocked(adminApi.getMCPTools).mockResolvedValue(mockTools);
    vi.mocked(adminApi.getToolPermissions).mockImplementation((toolName) =>
      Promise.resolve(mockPermissions[toolName])
    );

    render(<ToolPermissionsManager />);

    await waitFor(() => {
      expect(screen.getByText('Server: server1')).toBeInTheDocument();
      expect(screen.getByText('Server: server2')).toBeInTheDocument();
    });
  });
});

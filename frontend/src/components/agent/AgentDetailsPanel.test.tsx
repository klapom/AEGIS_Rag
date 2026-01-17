/**
 * AgentDetailsPanel Unit Tests
 * Sprint 100 - Tests field transformations and rendering
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AgentDetailsPanel } from './AgentDetailsPanel';
import * as agentHierarchyAPI from '../../api/agentHierarchy';

// Mock the API module
vi.mock('../../api/agentHierarchy', () => ({
  fetchAgentDetails: vi.fn(),
  fetchAgentCurrentTasks: vi.fn(),
}));

describe('AgentDetailsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should display "Select an agent" message when no agent is selected', () => {
    render(<AgentDetailsPanel agentId={null} />);
    expect(screen.getByText(/select an agent from the hierarchy tree/i)).toBeInTheDocument();
  });

  it('should display loading state while fetching data', () => {
    // Mock slow API response
    vi.mocked(agentHierarchyAPI.fetchAgentDetails).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );
    vi.mocked(agentHierarchyAPI.fetchAgentCurrentTasks).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<AgentDetailsPanel agentId="test-agent" />);
    expect(screen.getByText(/loading agent details/i)).toBeInTheDocument();
  });

  it('should transform and display agent fields correctly (Sprint 100 Fix #7)', async () => {
    // Mock API responses with backend format
    const mockDetails = {
      agent_id: 'manager-1',
      agent_name: 'Research Manager', // Already transformed by API client
      agent_level: 'MANAGER' as const, // Already transformed to UPPERCASE by API client
      skills: ['retrieval', 'search', 'analysis'],
      active_tasks: 2,
      completed_tasks: 150,
      failed_tasks: 5,
      success_rate_pct: 95.24, // Already transformed to percentage by API client
      avg_latency_ms: 180.5,
      p95_latency_ms: 320.0,
      current_load: 2,
      max_concurrent_tasks: 10,
      status: 'active' as const,
      last_active: '2024-01-17T12:00:00Z',
      parent_agent_id: 'executive-1',
      child_agent_ids: ['worker-1', 'worker-2'],
    };

    const mockTasks = {
      tasks: [
        {
          task_id: 'task-1',
          task_name: 'Search scientific papers',
          status: 'running' as const,
          started_at: '2024-01-17T11:55:00Z',
          assigned_skill: 'search',
        },
      ],
      total_count: 1,
    };

    vi.mocked(agentHierarchyAPI.fetchAgentDetails).mockResolvedValue(mockDetails);
    vi.mocked(agentHierarchyAPI.fetchAgentCurrentTasks).mockResolvedValue(mockTasks);

    render(<AgentDetailsPanel agentId="manager-1" />);

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByTestId('agent-name')).toBeInTheDocument();
    });

    // Verify agent name
    expect(screen.getByTestId('agent-name')).toHaveTextContent('Research Manager');

    // Verify level is UPPERCASE
    const levelBadge = screen.getByTestId('agent-level');
    expect(levelBadge).toHaveTextContent('MANAGER');

    // Verify status is lowercase
    const statusBadge = screen.getByTestId('agent-status');
    expect(statusBadge).toHaveTextContent('active');

    // Verify success rate is displayed as percentage with % symbol
    const successRate = screen.getByTestId('success-rate');
    expect(successRate.textContent).toMatch(/95\.\d%/); // Should be "95.2%" or similar

    // Verify skills are displayed
    expect(screen.getByTestId('agent-skill-retrieval')).toBeInTheDocument();
    expect(screen.getByTestId('agent-skill-search')).toBeInTheDocument();
    expect(screen.getByTestId('agent-skill-analysis')).toBeInTheDocument();
  });

  it('should display performance metrics correctly', async () => {
    const mockDetails = {
      agent_id: 'exec-1',
      agent_name: 'Executive',
      agent_level: 'EXECUTIVE' as const,
      skills: ['planning'],
      active_tasks: 0,
      completed_tasks: 500,
      failed_tasks: 25,
      success_rate_pct: 95.0,
      avg_latency_ms: 250.0,
      p95_latency_ms: 450.0,
      current_load: 0,
      max_concurrent_tasks: 5,
      status: 'idle' as const,
      last_active: '2024-01-17T12:00:00Z',
      parent_agent_id: null,
      child_agent_ids: ['manager-1', 'manager-2'],
    };

    vi.mocked(agentHierarchyAPI.fetchAgentDetails).mockResolvedValue(mockDetails);
    vi.mocked(agentHierarchyAPI.fetchAgentCurrentTasks).mockResolvedValue({
      tasks: [],
      total_count: 0,
    });

    render(<AgentDetailsPanel agentId="exec-1" />);

    await waitFor(() => {
      expect(screen.getByTestId('performance-metrics')).toBeInTheDocument();
    });

    const metricsSection = screen.getByTestId('performance-metrics');

    // Success rate should be 95%
    expect(screen.getByTestId('success-rate')).toHaveTextContent('95.0%');

    // Completed tasks
    expect(metricsSection).toHaveTextContent('500');

    // Failed tasks
    expect(metricsSection).toHaveTextContent('25');

    // Latency metrics
    expect(metricsSection).toHaveTextContent('250ms'); // Avg latency
    expect(metricsSection).toHaveTextContent('450ms'); // P95 latency
  });

  it('should handle API errors gracefully', async () => {
    vi.mocked(agentHierarchyAPI.fetchAgentDetails).mockRejectedValue(
      new Error('Failed to fetch agent details')
    );
    vi.mocked(agentHierarchyAPI.fetchAgentCurrentTasks).mockRejectedValue(
      new Error('Failed to fetch tasks')
    );

    render(<AgentDetailsPanel agentId="error-agent" />);

    await waitFor(() => {
      expect(screen.getByText(/failed to fetch agent details/i)).toBeInTheDocument();
    });
  });

  it('should display UPPERCASE levels for all agent types', async () => {
    const levels: Array<'EXECUTIVE' | 'MANAGER' | 'WORKER'> = ['EXECUTIVE', 'MANAGER', 'WORKER'];

    for (const level of levels) {
      vi.clearAllMocks();

      const mockDetails = {
        agent_id: `${level.toLowerCase()}-1`,
        agent_name: `${level} Agent`,
        agent_level: level,
        skills: ['test'],
        active_tasks: 0,
        completed_tasks: 100,
        failed_tasks: 5,
        success_rate_pct: 95.0,
        avg_latency_ms: 200,
        p95_latency_ms: 300,
        current_load: 0,
        max_concurrent_tasks: 10,
        status: 'active' as const,
        last_active: '2024-01-17T12:00:00Z',
        parent_agent_id: null,
        child_agent_ids: [],
      };

      vi.mocked(agentHierarchyAPI.fetchAgentDetails).mockResolvedValue(mockDetails);
      vi.mocked(agentHierarchyAPI.fetchAgentCurrentTasks).mockResolvedValue({
        tasks: [],
        total_count: 0,
      });

      const { unmount } = render(<AgentDetailsPanel agentId={`${level.toLowerCase()}-1`} />);

      await waitFor(() => {
        expect(screen.getByTestId('agent-level')).toBeInTheDocument();
      });

      const levelBadge = screen.getByTestId('agent-level');
      expect(levelBadge).toHaveTextContent(level); // UPPERCASE

      unmount();
    }
  });

  it('should display lowercase status for all status types', async () => {
    const statuses: Array<'active' | 'idle' | 'busy' | 'offline'> = [
      'active',
      'idle',
      'busy',
      'offline',
    ];

    for (const status of statuses) {
      vi.clearAllMocks();

      const mockDetails = {
        agent_id: 'test-agent',
        agent_name: 'Test Agent',
        agent_level: 'WORKER' as const,
        skills: ['test'],
        active_tasks: 0,
        completed_tasks: 100,
        failed_tasks: 5,
        success_rate_pct: 95.0,
        avg_latency_ms: 200,
        p95_latency_ms: 300,
        current_load: 0,
        max_concurrent_tasks: 10,
        status: status,
        last_active: '2024-01-17T12:00:00Z',
        parent_agent_id: null,
        child_agent_ids: [],
      };

      vi.mocked(agentHierarchyAPI.fetchAgentDetails).mockResolvedValue(mockDetails);
      vi.mocked(agentHierarchyAPI.fetchAgentCurrentTasks).mockResolvedValue({
        tasks: [],
        total_count: 0,
      });

      const { unmount } = render(<AgentDetailsPanel agentId="test-agent" />);

      await waitFor(() => {
        expect(screen.getByTestId('agent-status')).toBeInTheDocument();
      });

      const statusBadge = screen.getByTestId('agent-status');
      expect(statusBadge).toHaveTextContent(status); // lowercase

      unmount();
    }
  });
});

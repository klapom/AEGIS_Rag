/**
 * SkillRegistry Component Tests
 * Sprint 97 Feature 97.1: Skill Registry Browser UI
 *
 * Tests:
 * - Renders loading state
 * - Renders skill cards
 * - Handles search filtering
 * - Handles status filtering
 * - Handles pagination
 * - Handles activation toggle
 * - Handles error state
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { SkillRegistry } from './SkillRegistry';
import * as skillsApi from '../../api/skills';
import type { SkillSummary } from '../../types/skills';

// Mock the skills API
vi.mock('../../api/skills');

const mockSkills: SkillSummary[] = [
  {
    name: 'retrieval',
    version: '1.2.0',
    description: 'Vector and graph retrieval skill',
    author: 'AegisRAG Team',
    is_active: true,
    tools_count: 3,
    triggers_count: 4,
    icon: '🔍',
  },
  {
    name: 'web_search',
    version: '1.1.0',
    description: 'Web browsing with browser-use',
    author: 'AegisRAG Team',
    is_active: false,
    tools_count: 2,
    triggers_count: 5,
    icon: '🌐',
  },
];

function renderComponent() {
  return render(
    <BrowserRouter>
      <SkillRegistry />
    </BrowserRouter>
  );
}

describe('SkillRegistry', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', async () => {
    vi.mocked(skillsApi.listSkills).mockImplementation(
      () =>
        new Promise(() => {
          // Never resolves to keep loading state
        })
    );

    renderComponent();

    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders skill cards after loading', async () => {
    vi.mocked(skillsApi.listSkills).mockResolvedValue({
      skills: mockSkills,
      total_count: 2,
      page: 1,
      limit: 12,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('retrieval')).toBeInTheDocument();
      expect(screen.getByText('web_search')).toBeInTheDocument();
    });

    // Check descriptions
    expect(screen.getByText('Vector and graph retrieval skill')).toBeInTheDocument();
    expect(screen.getByText('Web browsing with browser-use')).toBeInTheDocument();

    // Check tool/trigger counts
    expect(screen.getByText('🔧 3 tools')).toBeInTheDocument();
    expect(screen.getByText('🎯 4 triggers')).toBeInTheDocument();
  });

  it('handles search filtering', async () => {
    vi.mocked(skillsApi.listSkills).mockResolvedValue({
      skills: mockSkills,
      total_count: 2,
      page: 1,
      limit: 12,
    });

    const user = userEvent.setup();
    renderComponent();

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('retrieval')).toBeInTheDocument();
    });

    // Type in search box
    const searchInput = screen.getByPlaceholderText(/search skills/i);
    await user.type(searchInput, 'retrieval');

    // Verify API was called with search parameter
    await waitFor(() => {
      expect(skillsApi.listSkills).toHaveBeenCalledWith(
        expect.objectContaining({
          search: 'retrieval',
        })
      );
    });
  });

  it('handles status filtering', async () => {
    vi.mocked(skillsApi.listSkills).mockResolvedValue({
      skills: mockSkills,
      total_count: 2,
      page: 1,
      limit: 12,
    });

    const user = userEvent.setup();
    renderComponent();

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('retrieval')).toBeInTheDocument();
    });

    // Change status filter
    const statusSelect = screen.getByRole('combobox');
    await user.selectOptions(statusSelect, 'active');

    // Verify API was called with status filter
    await waitFor(() => {
      expect(skillsApi.listSkills).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 'active',
        })
      );
    });
  });

  it('handles activation toggle', async () => {
    vi.mocked(skillsApi.listSkills).mockResolvedValue({
      skills: mockSkills,
      total_count: 2,
      page: 1,
      limit: 12,
    });

    vi.mocked(skillsApi.deactivateSkill).mockResolvedValue({
      status: 'deactivated',
      skill_name: 'retrieval',
    });

    const user = userEvent.setup();
    renderComponent();

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('retrieval')).toBeInTheDocument();
    });

    // Click active toggle button for retrieval skill
    const activeButton = screen.getAllByText('🟢 Active')[0];
    await user.click(activeButton);

    // Verify deactivate API was called
    await waitFor(() => {
      expect(skillsApi.deactivateSkill).toHaveBeenCalledWith('retrieval');
    });
  });

  it('handles error state', async () => {
    vi.mocked(skillsApi.listSkills).mockRejectedValue(new Error('Failed to load skills'));

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/failed to load skills/i)).toBeInTheDocument();
    });
  });

  it('handles empty state', async () => {
    vi.mocked(skillsApi.listSkills).mockResolvedValue({
      skills: [],
      total_count: 0,
      page: 1,
      limit: 12,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('No skills found')).toBeInTheDocument();
    });
  });

  it('handles pagination', async () => {
    vi.mocked(skillsApi.listSkills).mockResolvedValue({
      skills: mockSkills,
      total_count: 24,
      page: 1,
      limit: 12,
    });

    const user = userEvent.setup();
    renderComponent();

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('retrieval')).toBeInTheDocument();
    });

    // Click next page button
    const nextButton = screen.getByText('Next');
    await user.click(nextButton);

    // Verify API was called with page 2
    await waitFor(() => {
      expect(skillsApi.listSkills).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 2,
        })
      );
    });
  });
});

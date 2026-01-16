/**
 * ExplainabilityPage Unit Tests
 * Sprint 98 Feature 98.5: Explainability Dashboard
 *
 * Tests:
 * - Component renders successfully
 * - Loads recent traces on mount
 * - Displays trace list items
 * - Handles trace selection
 * - Switches between explanation levels (user/expert/audit)
 * - Displays decision flow stages
 * - Shows confidence and hallucination metrics
 * - Displays source attribution
 * - Handles loading states
 * - Handles error states
 * - Handles empty trace list
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import { ExplainabilityPage } from './ExplainabilityPage';
import * as adminApi from '../../api/admin';
import type {
  TraceListItem,
  DecisionTrace,
  UserExplanation,
  ExpertExplanation,
  AuditExplanation,
  SourceDocument,
} from '../../types/admin';

// Mock admin API
vi.mock('../../api/admin', () => ({
  getRecentTraces: vi.fn(),
  getDecisionTrace: vi.fn(),
  getExplanation: vi.fn(),
  getSourceAttribution: vi.fn(),
}));

// Mock useNavigate and useSearchParams
const mockNavigate = vi.fn();
const mockSetSearchParams = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useSearchParams: () => [new URLSearchParams(), mockSetSearchParams],
  };
});

// Helper function to render with router
const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

// Mock data
const mockTraceListItem: TraceListItem = {
  trace_id: 'trace-123',
  query: 'What is RAG?',
  timestamp: '2024-01-15T10:00:00Z',
  confidence: 0.92,
  user_id: 'user-456',
};

const mockDecisionTrace: DecisionTrace = {
  trace_id: 'trace-123',
  query: 'What is RAG?',
  timestamp: '2024-01-15T10:00:00Z',
  user_id: 'user-456',
  intent: {
    classification: 'knowledge_retrieval',
    confidence: 0.95,
  },
  decision_flow: [
    {
      stage: 'intent',
      status: 'completed',
      details: 'Query classified as knowledge retrieval',
      timestamp: '2024-01-15T10:00:01Z',
    },
    {
      stage: 'retrieval',
      status: 'completed',
      details: 'Retrieved 5 relevant chunks using hybrid search',
      timestamp: '2024-01-15T10:00:02Z',
    },
    {
      stage: 'response',
      status: 'completed',
      details: 'Generated response using top 3 chunks',
      timestamp: '2024-01-15T10:00:03Z',
    },
  ],
  confidence_overall: 0.92,
  hallucination_risk: 0.15,
};

const mockUserExplanation: UserExplanation = {
  summary:
    'I found information about RAG from 3 documents in our knowledge base. RAG stands for Retrieval-Augmented Generation, a technique that combines information retrieval with text generation.',
  sources: [
    { name: 'rag-overview.pdf', relevance: 0.95, page: 1, confidence: 'high' },
    { name: 'llm-techniques.pdf', relevance: 0.88, page: 5, confidence: 'medium' },
  ],
  capabilities_used: 3,
  capabilities_list: ['Vector Search', 'Document Retrieval', 'Answer Generation'],
};

const mockExpertExplanation: ExpertExplanation = {
  ...mockUserExplanation,
  technical_details: {
    skills_considered: [
      {
        name: 'Vector Search',
        confidence: 0.95,
        trigger: 'semantic_similarity',
        selected: true,
      },
      {
        name: 'Graph Search',
        confidence: 0.65,
        selected: false,
      },
    ],
    retrieval_mode: 'hybrid',
    chunks_retrieved: 15,
    chunks_used: 3,
    tools_invoked: [
      { tool: 'QdrantSearch', outcome: 'success', duration_ms: 120 },
      { tool: 'BM25Rerank', outcome: 'success', duration_ms: 50 },
    ],
    performance_metrics: {
      duration: 370,
      skill_times: {
        'Vector Search': 120,
        'Document Retrieval': 50,
        'Answer Generation': 200,
      },
    },
  },
};

const mockAuditExplanation: AuditExplanation = {
  ...mockExpertExplanation,
  full_trace: {
    langchain_run_id: 'run-123',
    agent_states: [
      { agent: 'coordinator', state: 'completed', timestamp: '2024-01-15T10:00:00Z' },
      { agent: 'vector_agent', state: 'completed', timestamp: '2024-01-15T10:00:01Z' },
    ],
    llm_calls: [
      { model: 'Nemotron3', tokens: 1500, cost_usd: 0.003, duration_ms: 200 },
    ],
  },
};

const mockSources: SourceDocument[] = [
  {
    name: 'rag-overview.pdf',
    relevance: 0.95,
    page: 1,
    snippet: 'RAG combines retrieval and generation...',
    confidence: 'high',
  },
  {
    name: 'llm-techniques.pdf',
    relevance: 0.88,
    page: 5,
    snippet: 'Modern LLMs use various techniques...',
    confidence: 'medium',
  },
];

describe('ExplainabilityPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should render the page with header', async () => {
    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([]);

    renderWithRouter(<ExplainabilityPage />);

    expect(screen.getByTestId('explainability-page')).toBeInTheDocument();
    expect(screen.getByText('Explainability Dashboard')).toBeInTheDocument();
    expect(
      screen.getByText('EU AI Act Art. 13 - Decision Transparency & Source Attribution')
    ).toBeInTheDocument();
  });

  it('should load recent traces on mount', async () => {
    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([mockTraceListItem]);

    renderWithRouter(<ExplainabilityPage />);

    await waitFor(() => {
      expect(adminApi.getRecentTraces).toHaveBeenCalledWith(undefined, 20);
    });

    expect(screen.getByText('What is RAG?')).toBeInTheDocument();
    expect(screen.getByText('92%')).toBeInTheDocument(); // Confidence
  });

  it('should display empty state when no traces available', async () => {
    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([]);

    renderWithRouter(<ExplainabilityPage />);

    await waitFor(() => {
      expect(
        screen.getByText('No recent traces available. Submit queries to see traces here.')
      ).toBeInTheDocument();
    });
  });

  it('should display placeholder when no trace selected', async () => {
    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([]);

    renderWithRouter(<ExplainabilityPage />);

    await waitFor(() => {
      expect(screen.getByText('Select a query trace to view details')).toBeInTheDocument();
    });
  });

  it('should load trace details when trace is selected', async () => {
    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([mockTraceListItem]);
    vi.mocked(adminApi.getDecisionTrace).mockResolvedValue(mockDecisionTrace);
    vi.mocked(adminApi.getExplanation).mockResolvedValue(mockUserExplanation);
    vi.mocked(adminApi.getSourceAttribution).mockResolvedValue(mockSources);

    const user = userEvent.setup();
    renderWithRouter(<ExplainabilityPage />);

    // Wait for traces to load
    await waitFor(() => {
      expect(screen.getByText('What is RAG?')).toBeInTheDocument();
    });

    // Click on trace item
    const traceButton = screen.getByTestId('trace-item-trace-123');
    await user.click(traceButton);

    // Verify API calls
    await waitFor(() => {
      expect(adminApi.getDecisionTrace).toHaveBeenCalledWith('trace-123');
      expect(adminApi.getExplanation).toHaveBeenCalledWith('trace-123', 'user');
      expect(adminApi.getSourceAttribution).toHaveBeenCalledWith('trace-123');
    });

    // Verify trace details displayed
    expect(screen.getByText('trace-123')).toBeInTheDocument();
  });

  it('should display decision flow stages', async () => {
    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([mockTraceListItem]);
    vi.mocked(adminApi.getDecisionTrace).mockResolvedValue(mockDecisionTrace);
    vi.mocked(adminApi.getExplanation).mockResolvedValue(mockUserExplanation);
    vi.mocked(adminApi.getSourceAttribution).mockResolvedValue(mockSources);

    const user = userEvent.setup();
    renderWithRouter(<ExplainabilityPage />);

    await waitFor(() => {
      expect(screen.getByText('What is RAG?')).toBeInTheDocument();
    });

    const traceButton = screen.getByTestId('trace-item-trace-123');
    await user.click(traceButton);

    // Wait for decision flow to load
    await waitFor(() => {
      expect(screen.getByText('Decision Flow')).toBeInTheDocument();
    });

    // Verify stages
    expect(screen.getByText('1. Intent')).toBeInTheDocument();
    expect(screen.getByText('Query classified as knowledge retrieval')).toBeInTheDocument();
    expect(screen.getByText('2. Retrieval')).toBeInTheDocument();
    expect(
      screen.getByText('Retrieved 5 relevant chunks using hybrid search')
    ).toBeInTheDocument();
    expect(screen.getByText('3. Response')).toBeInTheDocument();
  });

  it('should switch between explanation levels', async () => {
    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([mockTraceListItem]);
    vi.mocked(adminApi.getDecisionTrace).mockResolvedValue(mockDecisionTrace);
    vi.mocked(adminApi.getExplanation)
      .mockResolvedValueOnce(mockUserExplanation)
      .mockResolvedValueOnce(mockExpertExplanation);
    vi.mocked(adminApi.getSourceAttribution).mockResolvedValue(mockSources);

    const user = userEvent.setup();
    renderWithRouter(<ExplainabilityPage />);

    await waitFor(() => {
      expect(screen.getByText('What is RAG?')).toBeInTheDocument();
    });

    const traceButton = screen.getByTestId('trace-item-trace-123');
    await user.click(traceButton);

    await waitFor(() => {
      expect(screen.getByTestId('level-user')).toBeInTheDocument();
    });

    // Switch to Expert level
    const expertButton = screen.getByTestId('level-expert');
    await user.click(expertButton);

    await waitFor(() => {
      expect(adminApi.getExplanation).toHaveBeenCalledWith('trace-123', 'expert');
    });

    // Verify expert description text
    expect(screen.getByText('Technical details for developers')).toBeInTheDocument();
  });

  it('should display technical details in expert mode', async () => {
    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([mockTraceListItem]);
    vi.mocked(adminApi.getDecisionTrace).mockResolvedValue(mockDecisionTrace);
    vi.mocked(adminApi.getExplanation).mockResolvedValue(mockExpertExplanation);
    vi.mocked(adminApi.getSourceAttribution).mockResolvedValue(mockSources);

    const user = userEvent.setup();
    renderWithRouter(<ExplainabilityPage />);

    await waitFor(() => {
      expect(screen.getByText('What is RAG?')).toBeInTheDocument();
    });

    const traceButton = screen.getByTestId('trace-item-trace-123');
    await user.click(traceButton);

    await waitFor(() => {
      expect(screen.getByTestId('level-expert')).toBeInTheDocument();
    });

    const expertButton = screen.getByTestId('level-expert');
    await user.click(expertButton);

    await waitFor(() => {
      expect(screen.getByText('Technical Details')).toBeInTheDocument();
    });

    // Verify technical details
    expect(screen.getByText('hybrid')).toBeInTheDocument(); // Retrieval mode
    expect(screen.getByText('15')).toBeInTheDocument(); // Chunks retrieved
    expect(screen.getByText('3')).toBeInTheDocument(); // Chunks used
    expect(screen.getByText('370ms')).toBeInTheDocument(); // Duration
  });

  it('should display full trace in audit mode', async () => {
    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([mockTraceListItem]);
    vi.mocked(adminApi.getDecisionTrace).mockResolvedValue(mockDecisionTrace);
    vi.mocked(adminApi.getExplanation).mockResolvedValue(mockAuditExplanation);
    vi.mocked(adminApi.getSourceAttribution).mockResolvedValue(mockSources);

    const user = userEvent.setup();
    renderWithRouter(<ExplainabilityPage />);

    await waitFor(() => {
      expect(screen.getByText('What is RAG?')).toBeInTheDocument();
    });

    const traceButton = screen.getByTestId('trace-item-trace-123');
    await user.click(traceButton);

    await waitFor(() => {
      expect(screen.getByTestId('level-audit')).toBeInTheDocument();
    });

    const auditButton = screen.getByTestId('level-audit');
    await user.click(auditButton);

    await waitFor(() => {
      expect(screen.getByText('Complete Trace (for compliance)')).toBeInTheDocument();
    });

    // Verify JSON trace is displayed
    const preElement = screen.getByText(/langchain_run_id/);
    expect(preElement).toBeInTheDocument();
  });

  it('should display confidence metrics', async () => {
    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([mockTraceListItem]);
    vi.mocked(adminApi.getDecisionTrace).mockResolvedValue(mockDecisionTrace);
    vi.mocked(adminApi.getExplanation).mockResolvedValue(mockUserExplanation);
    vi.mocked(adminApi.getSourceAttribution).mockResolvedValue(mockSources);

    const user = userEvent.setup();
    renderWithRouter(<ExplainabilityPage />);

    await waitFor(() => {
      expect(screen.getByText('What is RAG?')).toBeInTheDocument();
    });

    const traceButton = screen.getByTestId('trace-item-trace-123');
    await user.click(traceButton);

    await waitFor(() => {
      expect(screen.getByText('Confidence Metrics')).toBeInTheDocument();
    });

    // Verify confidence score (92%)
    const confidenceElements = screen.getAllByText('92%');
    expect(confidenceElements.length).toBeGreaterThan(0);

    // Verify hallucination risk (15%)
    expect(screen.getByText('15%')).toBeInTheDocument();
  });

  it('should display source attribution', async () => {
    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([mockTraceListItem]);
    vi.mocked(adminApi.getDecisionTrace).mockResolvedValue(mockDecisionTrace);
    vi.mocked(adminApi.getExplanation).mockResolvedValue(mockUserExplanation);
    vi.mocked(adminApi.getSourceAttribution).mockResolvedValue(mockSources);

    const user = userEvent.setup();
    renderWithRouter(<ExplainabilityPage />);

    await waitFor(() => {
      expect(screen.getByText('What is RAG?')).toBeInTheDocument();
    });

    const traceButton = screen.getByTestId('trace-item-trace-123');
    await user.click(traceButton);

    await waitFor(() => {
      expect(screen.getByText('Source Attribution')).toBeInTheDocument();
    });

    // Verify sources
    expect(screen.getByText('rag-overview.pdf')).toBeInTheDocument();
    expect(screen.getByText('llm-techniques.pdf')).toBeInTheDocument();
    expect(screen.getByText('Page 1')).toBeInTheDocument();
    expect(screen.getByText('Page 5')).toBeInTheDocument();
    // Snippet text is wrapped in quotes in UI
    expect(screen.getByText(/"RAG combines retrieval and generation\.\.\."/)).toBeInTheDocument();
  });

  it('should display loading state', async () => {
    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([mockTraceListItem]);
    vi.mocked(adminApi.getDecisionTrace).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(mockDecisionTrace), 1000))
    );
    vi.mocked(adminApi.getExplanation).mockResolvedValue(mockUserExplanation);
    vi.mocked(adminApi.getSourceAttribution).mockResolvedValue(mockSources);

    const user = userEvent.setup();
    renderWithRouter(<ExplainabilityPage />);

    await waitFor(() => {
      expect(screen.getByText('What is RAG?')).toBeInTheDocument();
    });

    const traceButton = screen.getByTestId('trace-item-trace-123');
    await user.click(traceButton);

    // Verify loading state
    expect(screen.getByText('Loading trace details...')).toBeInTheDocument();

    // Wait for loading to complete
    await waitFor(
      () => {
        expect(screen.queryByText('Loading trace details...')).not.toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });

  it('should display error message on API failure', async () => {
    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([mockTraceListItem]);
    vi.mocked(adminApi.getDecisionTrace).mockRejectedValue(
      new Error('Failed to load trace')
    );

    const user = userEvent.setup();
    renderWithRouter(<ExplainabilityPage />);

    await waitFor(() => {
      expect(screen.getByText('What is RAG?')).toBeInTheDocument();
    });

    const traceButton = screen.getByTestId('trace-item-trace-123');
    await user.click(traceButton);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load trace details/)).toBeInTheDocument();
    });
  });

  it('should navigate back to admin page', async () => {
    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([]);

    const user = userEvent.setup();
    renderWithRouter(<ExplainabilityPage />);

    const backButton = screen.getByTestId('back-to-admin-button');
    expect(backButton).toBeInTheDocument();

    await user.click(backButton);

    expect(mockNavigate).toHaveBeenCalledWith('/admin');
  });

  it('should display skills considered in expert mode', async () => {
    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([mockTraceListItem]);
    vi.mocked(adminApi.getDecisionTrace).mockResolvedValue(mockDecisionTrace);
    vi.mocked(adminApi.getExplanation).mockResolvedValue(mockExpertExplanation);
    vi.mocked(adminApi.getSourceAttribution).mockResolvedValue(mockSources);

    const user = userEvent.setup();
    renderWithRouter(<ExplainabilityPage />);

    await waitFor(() => {
      expect(screen.getByText('What is RAG?')).toBeInTheDocument();
    });

    const traceButton = screen.getByTestId('trace-item-trace-123');
    await user.click(traceButton);

    await waitFor(() => {
      expect(screen.getByTestId('level-expert')).toBeInTheDocument();
    });

    const expertButton = screen.getByTestId('level-expert');
    await user.click(expertButton);

    await waitFor(() => {
      expect(screen.getByText('Skills Considered:')).toBeInTheDocument();
    });

    // Verify skills section exists and contains skill names
    const skillsSection = screen.getByText('Skills Considered:').closest('div');
    expect(skillsSection).toBeInTheDocument();

    // Verify skills within the technical details section
    expect(within(skillsSection!).getAllByText(/Vector Search/).length).toBeGreaterThan(0);
    expect(within(skillsSection!).getAllByText(/Graph Search/).length).toBeGreaterThan(0);
    expect(within(skillsSection!).getByText(/semantic_similarity/)).toBeInTheDocument();
  });

  it('should color confidence scores correctly', async () => {
    const highConfidenceTrace: TraceListItem = {
      ...mockTraceListItem,
      confidence: 0.85, // High (>= 0.8)
    };
    const mediumConfidenceTrace: TraceListItem = {
      ...mockTraceListItem,
      trace_id: 'trace-456',
      confidence: 0.65, // Medium (>= 0.5, < 0.8)
    };
    const lowConfidenceTrace: TraceListItem = {
      ...mockTraceListItem,
      trace_id: 'trace-789',
      confidence: 0.35, // Low (< 0.5)
    };

    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([
      highConfidenceTrace,
      mediumConfidenceTrace,
      lowConfidenceTrace,
    ]);

    renderWithRouter(<ExplainabilityPage />);

    await waitFor(() => {
      expect(screen.getByText('85%')).toBeInTheDocument();
      expect(screen.getByText('65%')).toBeInTheDocument();
      expect(screen.getByText('35%')).toBeInTheDocument();
    });

    // Verify colors (via class names)
    const highElement = screen.getByText('85%');
    expect(highElement.className).toMatch(/green/);

    const mediumElement = screen.getByText('65%');
    expect(mediumElement.className).toMatch(/yellow/);

    const lowElement = screen.getByText('35%');
    expect(lowElement.className).toMatch(/red/);
  });

  it('should handle explanation loading failure gracefully', async () => {
    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([mockTraceListItem]);
    vi.mocked(adminApi.getDecisionTrace).mockResolvedValue(mockDecisionTrace);
    vi.mocked(adminApi.getExplanation).mockRejectedValue(
      new Error('Failed to load explanation')
    );
    vi.mocked(adminApi.getSourceAttribution).mockResolvedValue(mockSources);

    const user = userEvent.setup();
    renderWithRouter(<ExplainabilityPage />);

    await waitFor(() => {
      expect(screen.getByText('What is RAG?')).toBeInTheDocument();
    });

    const traceButton = screen.getByTestId('trace-item-trace-123');
    await user.click(traceButton);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load explanation/)).toBeInTheDocument();
    });
  });

  it('should highlight selected trace', async () => {
    vi.mocked(adminApi.getRecentTraces).mockResolvedValue([
      mockTraceListItem,
      { ...mockTraceListItem, trace_id: 'trace-456', query: 'Another query' },
    ]);
    vi.mocked(adminApi.getDecisionTrace).mockResolvedValue(mockDecisionTrace);
    vi.mocked(adminApi.getExplanation).mockResolvedValue(mockUserExplanation);
    vi.mocked(adminApi.getSourceAttribution).mockResolvedValue(mockSources);

    const user = userEvent.setup();
    renderWithRouter(<ExplainabilityPage />);

    await waitFor(() => {
      expect(screen.getByText('What is RAG?')).toBeInTheDocument();
    });

    const traceButton = screen.getByTestId('trace-item-trace-123');
    await user.click(traceButton);

    await waitFor(() => {
      const selectedButton = screen.getByTestId('trace-item-trace-123');
      expect(selectedButton.className).toMatch(/purple/); // Highlighted with purple
    });
  });
});

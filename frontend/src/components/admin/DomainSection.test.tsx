/**
 * DomainSection Component Tests
 * Sprint 46 Feature 46.8: Admin Area Consolidation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { DomainSection } from './DomainSection';
import type { Domain } from '../../hooks/useDomainTraining';

// Mock the useDomains hook
const mockUseDomains = vi.fn();
vi.mock('../../hooks/useDomainTraining', () => ({
  useDomains: () => mockUseDomains(),
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Counter for generating unique IDs
let idCounter = 0;

// Helper: Create mock Domain
function createMockDomain(overrides?: Partial<Domain>): Domain {
  idCounter += 1;
  return {
    id: `domain-${idCounter}`,
    name: 'test-domain',
    description: 'Test domain description',
    llm_model: 'qwen3:32b',
    status: 'ready',
    ...overrides,
  };
}

describe('DomainSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    idCounter = 0; // Reset ID counter for each test
    mockUseDomains.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });
  });

  const renderComponent = () => {
    return render(
      <BrowserRouter>
        <DomainSection />
      </BrowserRouter>
    );
  };

  describe('loading state', () => {
    it('should show loading state when loading', () => {
      mockUseDomains.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
      });

      renderComponent();

      expect(screen.getByTestId('admin-section-loading')).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('should show error message when error occurs', () => {
      mockUseDomains.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('Failed to fetch domains'),
      });

      renderComponent();

      expect(screen.getByTestId('admin-section-error')).toBeInTheDocument();
      expect(screen.getByText('Failed to fetch domains')).toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('should show empty state when no domains exist', () => {
      mockUseDomains.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
      });

      renderComponent();

      expect(screen.getByTestId('domains-empty-state')).toBeInTheDocument();
      expect(screen.getByText(/no domains configured yet/i)).toBeInTheDocument();
    });
  });

  describe('domain list rendering', () => {
    it('should render domain list with items', () => {
      const domains = [
        createMockDomain({ name: 'omnitracker', status: 'ready' }),
        createMockDomain({ name: 'legal', status: 'training' }),
        createMockDomain({ name: 'general', status: 'pending' }),
      ];
      mockUseDomains.mockReturnValue({
        data: domains,
        isLoading: false,
        error: null,
      });

      renderComponent();

      expect(screen.getByTestId('domain-list')).toBeInTheDocument();
      expect(screen.getByTestId('domain-item-omnitracker')).toBeInTheDocument();
      expect(screen.getByTestId('domain-item-legal')).toBeInTheDocument();
      expect(screen.getByTestId('domain-item-general')).toBeInTheDocument();
    });

    it('should render status badges with correct labels', () => {
      const domains = [
        createMockDomain({ name: 'd1', status: 'ready' }),
        createMockDomain({ name: 'd2', status: 'training' }),
        createMockDomain({ name: 'd3', status: 'pending' }),
        createMockDomain({ name: 'd4', status: 'failed' }),
      ];
      mockUseDomains.mockReturnValue({
        data: domains,
        isLoading: false,
        error: null,
      });

      renderComponent();

      expect(screen.getByTestId('domain-status-badge-ready')).toHaveTextContent('ready');
      expect(screen.getByTestId('domain-status-badge-training')).toHaveTextContent('training...');
      expect(screen.getByTestId('domain-status-badge-pending')).toHaveTextContent('pending');
      expect(screen.getByTestId('domain-status-badge-failed')).toHaveTextContent('failed');
    });
  });

  describe('navigation', () => {
    it('should navigate to domain training page on New Domain click', () => {
      mockUseDomains.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
      });

      renderComponent();

      fireEvent.click(screen.getByTestId('new-domain-button'));

      expect(mockNavigate).toHaveBeenCalledWith('/admin/domain-training');
    });

    it('should navigate to domain training page with selected domain on click', () => {
      const domains = [createMockDomain({ name: 'omnitracker' })];
      mockUseDomains.mockReturnValue({
        data: domains,
        isLoading: false,
        error: null,
      });

      renderComponent();

      fireEvent.click(screen.getByTestId('domain-item-omnitracker'));

      expect(mockNavigate).toHaveBeenCalledWith('/admin/domain-training', {
        state: { selectedDomain: 'omnitracker' },
      });
    });

    it('should navigate on Enter key press', () => {
      const domains = [createMockDomain({ name: 'omnitracker' })];
      mockUseDomains.mockReturnValue({
        data: domains,
        isLoading: false,
        error: null,
      });

      renderComponent();

      const item = screen.getByTestId('domain-item-omnitracker');
      fireEvent.keyDown(item, { key: 'Enter' });

      expect(mockNavigate).toHaveBeenCalled();
    });
  });

  describe('section header', () => {
    it('should display Domains title', () => {
      renderComponent();

      expect(screen.getByText('Domains')).toBeInTheDocument();
    });

    it('should render New Domain button', () => {
      renderComponent();

      expect(screen.getByTestId('new-domain-button')).toBeInTheDocument();
      expect(screen.getByText('New Domain')).toBeInTheDocument();
    });
  });
});

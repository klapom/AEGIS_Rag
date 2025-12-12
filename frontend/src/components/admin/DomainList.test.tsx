/**
 * DomainList Component Tests
 * Sprint 45 Feature 45.4: Domain Training Admin UI
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DomainList } from './DomainList';
import type { Domain } from '../../hooks/useDomainTraining';

// Helper: Create mock Domain
function createMockDomain(overrides?: Partial<Domain>): Domain {
  return {
    id: '1',
    name: 'finance',
    description: 'Financial domain for banking queries',
    llm_model: 'qwen3:32b',
    status: 'ready',
    ...overrides,
  };
}

describe('DomainList', () => {
  describe('loading state', () => {
    it('should show loading spinner when loading', () => {
      render(<DomainList domains={null} isLoading={true} />);
      expect(screen.getByTestId('domain-list-loading')).toBeInTheDocument();
      expect(screen.getByText(/loading domains/i)).toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('should show empty message when no domains', () => {
      render(<DomainList domains={[]} isLoading={false} />);
      expect(screen.getByTestId('domain-list-empty')).toBeInTheDocument();
      expect(screen.getByText(/no domains found/i)).toBeInTheDocument();
    });
  });

  describe('domain list rendering', () => {
    it('should render domain table with headers', () => {
      const domains = [createMockDomain()];
      render(<DomainList domains={domains} isLoading={false} />);

      expect(screen.getByTestId('domain-list')).toBeInTheDocument();
      expect(screen.getByText('Name')).toBeInTheDocument();
      expect(screen.getByText('Description')).toBeInTheDocument();
      expect(screen.getByText('Model')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
      expect(screen.getByText('Actions')).toBeInTheDocument();
    });

    it('should render domain rows', () => {
      const domains = [
        createMockDomain({ name: 'finance', description: 'Finance domain' }),
        createMockDomain({ name: 'legal', description: 'Legal domain', status: 'training' }),
      ];
      render(<DomainList domains={domains} isLoading={false} />);

      expect(screen.getByTestId('domain-row-finance')).toBeInTheDocument();
      expect(screen.getByTestId('domain-row-legal')).toBeInTheDocument();
      expect(screen.getByText('Finance domain')).toBeInTheDocument();
      expect(screen.getByText('Legal domain')).toBeInTheDocument();
    });

    it('should render domain status badges with correct colors', () => {
      const domains = [
        createMockDomain({ name: 'd1', status: 'ready' }),
        createMockDomain({ name: 'd2', status: 'training' }),
        createMockDomain({ name: 'd3', status: 'pending' }),
        createMockDomain({ name: 'd4', status: 'failed' }),
      ];
      render(<DomainList domains={domains} isLoading={false} />);

      const readyBadge = screen.getByTestId('domain-status-d1');
      expect(readyBadge).toHaveTextContent('ready');
      expect(readyBadge).toHaveClass('bg-green-100', 'text-green-800');

      const trainingBadge = screen.getByTestId('domain-status-d2');
      expect(trainingBadge).toHaveTextContent('training');
      expect(trainingBadge).toHaveClass('bg-yellow-100', 'text-yellow-800');

      const pendingBadge = screen.getByTestId('domain-status-d3');
      expect(pendingBadge).toHaveTextContent('pending');
      expect(pendingBadge).toHaveClass('bg-gray-100', 'text-gray-800');

      const failedBadge = screen.getByTestId('domain-status-d4');
      expect(failedBadge).toHaveTextContent('failed');
      expect(failedBadge).toHaveClass('bg-red-100', 'text-red-800');
    });

    it('should show "-" for null model', () => {
      const domains = [createMockDomain({ llm_model: null })];
      render(<DomainList domains={domains} isLoading={false} />);

      expect(screen.getByText('-')).toBeInTheDocument();
    });

    it('should render view button for each domain', () => {
      const domains = [createMockDomain({ name: 'finance' })];
      render(<DomainList domains={domains} isLoading={false} />);

      expect(screen.getByTestId('domain-view-finance')).toBeInTheDocument();
      expect(screen.getByTestId('domain-view-finance')).toHaveTextContent('View');
    });
  });
});

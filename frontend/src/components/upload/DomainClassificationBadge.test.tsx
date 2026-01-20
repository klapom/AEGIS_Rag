/**
 * Unit tests for DomainClassificationBadge component
 * Sprint 117 Feature 117.10: Upload Dialog Classification Display
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DomainClassificationBadge } from './DomainClassificationBadge';

describe('DomainClassificationBadge', () => {
  it('renders domain name and confidence percentage', () => {
    render(
      <DomainClassificationBadge
        domainName="Medical Documents"
        confidence={0.94}
        classificationPath="fast"
      />
    );

    expect(screen.getByText('Medical Documents')).toBeInTheDocument();
    expect(screen.getByText('94.0%')).toBeInTheDocument();
  });

  it('applies green styling for high confidence (>= 0.85)', () => {
    const { container } = render(
      <DomainClassificationBadge
        domainName="Legal Documents"
        confidence={0.92}
        classificationPath="verified"
      />
    );

    const badge = container.querySelector('[data-testid="domain-classification-badge"]');
    expect(badge).toHaveClass('bg-green-50', 'border-green-200');
  });

  it('applies yellow styling for medium confidence (0.60-0.85)', () => {
    const { container } = render(
      <DomainClassificationBadge
        domainName="Business Documents"
        confidence={0.72}
        classificationPath="fast"
      />
    );

    const badge = container.querySelector('[data-testid="domain-classification-badge"]');
    expect(badge).toHaveClass('bg-yellow-50', 'border-yellow-200');
  });

  it('applies red styling for low confidence (< 0.60)', () => {
    const { container } = render(
      <DomainClassificationBadge
        domainName="General Documents"
        confidence={0.45}
        classificationPath="fallback"
      />
    );

    const badge = container.querySelector('[data-testid="domain-classification-badge"]');
    expect(badge).toHaveClass('bg-red-50', 'border-red-200');
  });

  it('renders classification path icon', () => {
    render(
      <DomainClassificationBadge
        domainName="Research Papers"
        confidence={0.88}
        classificationPath="fast"
      />
    );

    // Check that ClassificationPathIcon is rendered
    expect(screen.getByLabelText('Fast Classification')).toBeInTheDocument();
  });

  it('formats confidence percentage to one decimal place', () => {
    render(
      <DomainClassificationBadge
        domainName="Technical Docs"
        confidence={0.876543}
        classificationPath="verified"
      />
    );

    expect(screen.getByText('87.7%')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <DomainClassificationBadge
        domainName="Custom Domain"
        confidence={0.8}
        classificationPath="fast"
        className="custom-class"
      />
    );

    const badge = container.querySelector('[data-testid="domain-classification-badge"]');
    expect(badge).toHaveClass('custom-class');
  });
});

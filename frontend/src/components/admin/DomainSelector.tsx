/**
 * DomainSelector Component
 * Sprint 45 Feature 45.7: Upload Page Domain Suggestion
 *
 * Dropdown selector for domain with AI-suggested recommendations
 */

import { useEffect, useState } from 'react';
import type { ClassificationResult } from '../../hooks/useDomainTraining';

interface DomainSelectorProps {
  suggested?: string;
  alternatives?: ClassificationResult[];
  onChange: (domain: string) => void;
}

export function DomainSelector({ suggested, alternatives, onChange }: DomainSelectorProps) {
  const [selected, setSelected] = useState(suggested || '');

  useEffect(() => {
    if (suggested) {
      setSelected(suggested);
      onChange(suggested);
    }
  }, [suggested, onChange]);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    setSelected(value);
    onChange(value);
  };

  if (!alternatives || alternatives.length === 0) {
    return (
      <div className="text-sm text-gray-500" data-testid="domain-selector-loading">
        Analyzing...
      </div>
    );
  }

  return (
    <select
      value={selected}
      onChange={handleChange}
      className="border border-gray-300 rounded px-3 py-1 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      data-testid="domain-selector"
    >
      <option value="">Select domain...</option>
      {alternatives.map((alt) => (
        <option key={alt.domain} value={alt.domain}>
          {alt.domain} ({(alt.score * 100).toFixed(0)}%)
        </option>
      ))}
    </select>
  );
}

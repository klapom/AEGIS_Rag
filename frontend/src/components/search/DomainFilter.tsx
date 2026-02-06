/**
 * DomainFilter Component
 * Sprint 125 Feature 125.9d: Domain Filter in Search
 *
 * Multi-select domain filter for search/chat settings
 */

import { useState, useEffect, useRef } from 'react';
import { ChevronDown, Filter, X } from 'lucide-react';

interface Domain {
  domain_id: string;
  domain_name: string;
  ddc_code: string;
}

interface DomainFilterProps {
  selectedDomains: string[];
  onSelectionChange: (domains: string[]) => void;
  compact?: boolean;
}

export function DomainFilter({
  selectedDomains,
  onSelectionChange,
  compact = false,
}: DomainFilterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Load domains from active deployment profile
  useEffect(() => {
    const loadDomains = async () => {
      setLoading(true);
      try {
        const response = await fetch('/api/v1/admin/domains');
        if (response.ok) {
          const data = await response.json();
          setDomains(data.domains || []);
        }
      } catch (err) {
        console.error('Failed to load domains:', err);
      } finally {
        setLoading(false);
      }
    };

    loadDomains();
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleDomain = (domainId: string) => {
    const newSelection = selectedDomains.includes(domainId)
      ? selectedDomains.filter((id) => id !== domainId)
      : [...selectedDomains, domainId];
    onSelectionChange(newSelection);
  };

  const clearSelection = () => {
    onSelectionChange([]);
  };

  const selectAll = () => {
    onSelectionChange(domains.map((d) => d.domain_id));
  };

  const getDisplayText = () => {
    if (selectedDomains.length === 0) {
      return 'All Domains';
    }
    if (selectedDomains.length === 1) {
      const domain = domains.find((d) => d.domain_id === selectedDomains[0]);
      return domain?.domain_name || 'Domain';
    }
    return `${selectedDomains.length} Domains`;
  };

  if (compact) {
    return (
      <div className="relative" ref={dropdownRef} data-testid="domain-filter-compact">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          data-testid="domain-filter-button"
        >
          <Filter className="w-3.5 h-3.5 text-gray-600" />
          <span className="text-gray-700">{getDisplayText()}</span>
          <ChevronDown
            className={`w-3.5 h-3.5 text-gray-600 transition-transform ${
              isOpen ? 'rotate-180' : ''
            }`}
          />
        </button>

        {isOpen && (
          <div className="absolute top-full left-0 mt-2 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
            <div className="p-3 border-b border-gray-200 flex items-center justify-between">
              <span className="text-sm font-semibold text-gray-900">
                Filter by Domain
              </span>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {loading ? (
              <div className="p-4 text-sm text-gray-500 text-center">
                Loading domains...
              </div>
            ) : domains.length === 0 ? (
              <div className="p-4 text-sm text-gray-500 text-center">
                No domains available
              </div>
            ) : (
              <>
                <div className="max-h-64 overflow-y-auto p-2">
                  {domains.map((domain) => (
                    <label
                      key={domain.domain_id}
                      className="flex items-start gap-3 px-3 py-2 hover:bg-gray-50 rounded cursor-pointer"
                      data-testid={`domain-option-${domain.domain_id}`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedDomains.includes(domain.domain_id)}
                        onChange={() => toggleDomain(domain.domain_id)}
                        className="mt-0.5 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900 truncate">
                          {domain.domain_name}
                        </div>
                        <div className="text-xs text-gray-500">
                          DDC: {domain.ddc_code}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>

                <div className="p-2 border-t border-gray-200 flex items-center justify-between">
                  <button
                    onClick={selectAll}
                    className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                  >
                    Select All
                  </button>
                  <button
                    onClick={clearSelection}
                    className="text-xs text-gray-600 hover:text-gray-700 font-medium"
                  >
                    Clear
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    );
  }

  // Full size version (for settings page)
  return (
    <div className="w-full" data-testid="domain-filter">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Domain Filter
      </label>
      <div className="border border-gray-300 rounded-lg p-3">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-gray-600">
            {selectedDomains.length} of {domains.length} domains selected
          </span>
          <div className="flex gap-2">
            <button
              onClick={selectAll}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium"
            >
              Select All
            </button>
            <button
              onClick={clearSelection}
              className="text-xs text-gray-600 hover:text-gray-700 font-medium"
            >
              Clear
            </button>
          </div>
        </div>

        <div className="max-h-64 overflow-y-auto space-y-2">
          {loading ? (
            <div className="text-sm text-gray-500 text-center py-4">
              Loading domains...
            </div>
          ) : domains.length === 0 ? (
            <div className="text-sm text-gray-500 text-center py-4">
              No domains available
            </div>
          ) : (
            domains.map((domain) => (
              <label
                key={domain.domain_id}
                className="flex items-start gap-3 p-2 hover:bg-gray-50 rounded cursor-pointer"
                data-testid={`domain-option-${domain.domain_id}`}
              >
                <input
                  type="checkbox"
                  checked={selectedDomains.includes(domain.domain_id)}
                  onChange={() => toggleDomain(domain.domain_id)}
                  className="mt-0.5 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">
                    {domain.domain_name}
                  </div>
                  <div className="text-xs text-gray-500">
                    DDC: {domain.ddc_code}
                  </div>
                </div>
              </label>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * CommunityHighlight Component
 * Sprint 29 Feature 29.5: Graph Explorer with Search
 * Sprint 29 Feature 29.7: Community Document Browser Integration
 *
 * Features:
 * - Dropdown to select community for highlighting
 * - Option "None (Show All)"
 * - Each option shows topic name + member count
 * - onCommunitySelect callback
 * - "View Documents" button when community selected (Feature 29.7)
 */

import { useState } from 'react';
import { FileText } from 'lucide-react';
import { CommunityDocuments } from './CommunityDocuments';

export interface Community {
  id: string;
  topic: string;
  size: number; // Number of members
  description?: string;
}

interface CommunityHighlightProps {
  communities: Community[];
  selectedCommunity: string | null;
  onCommunitySelect: (communityId: string | null) => void;
  onDocumentPreview?: (documentId: string) => void; // Optional callback for document preview
}

/**
 * Component for selecting and highlighting a community in the graph
 *
 * @param communities Available communities
 * @param selectedCommunity Currently selected community ID
 * @param onCommunitySelect Callback when community selection changes
 * @param onDocumentPreview Optional callback for document preview
 */
export function CommunityHighlight({
  communities,
  selectedCommunity,
  onCommunitySelect,
  onDocumentPreview,
}: CommunityHighlightProps) {
  const [showDocuments, setShowDocuments] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onCommunitySelect(value === '' ? null : value);
  };

  // Sort communities by size (largest first)
  const sortedCommunities = [...communities].sort((a, b) => b.size - a.size);

  return (
    <div className="space-y-2">
      <label htmlFor="community-select" className="block text-sm font-semibold text-gray-900">
        Highlight Community
      </label>
      <select
        id="community-select"
        value={selectedCommunity || ''}
        onChange={handleChange}
        className="w-full px-3 py-2.5 text-sm bg-white border-2 border-gray-300 rounded-lg
                   focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20
                   hover:border-gray-400 transition-all duration-200 cursor-pointer"
        aria-label="Select community to highlight"
      >
        <option value="">None (Show All)</option>
        {sortedCommunities.map((community) => (
          <option key={community.id} value={community.id}>
            {community.topic} ({community.size} members)
          </option>
        ))}
      </select>

      {/* Selected Community Info */}
      {selectedCommunity && (
        <div className="mt-3 p-3 bg-purple-50 border-2 border-purple-200 rounded-lg">
          <div className="flex items-start justify-between">
            <div className="flex-grow">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-3 h-3 bg-purple-500 rounded-full" aria-hidden="true" />
                <span className="text-sm font-semibold text-purple-900">
                  {sortedCommunities.find((c) => c.id === selectedCommunity)?.topic}
                </span>
              </div>
              <div className="text-xs text-purple-700">
                {sortedCommunities.find((c) => c.id === selectedCommunity)?.size} members
              </div>
              {sortedCommunities.find((c) => c.id === selectedCommunity)?.description && (
                <div className="text-xs text-purple-600 mt-2">
                  {sortedCommunities.find((c) => c.id === selectedCommunity)?.description}
                </div>
              )}

              {/* View Documents Button (Feature 29.7) */}
              <button
                onClick={() => setShowDocuments(true)}
                className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium text-purple-700 bg-white border-2 border-purple-300 rounded-lg hover:bg-purple-50 hover:border-purple-400 transition-all"
              >
                <FileText className="w-4 h-4" />
                View Documents
              </button>
            </div>
            <button
              onClick={() => onCommunitySelect(null)}
              className="ml-2 text-purple-600 hover:text-purple-800 p-1"
              aria-label="Clear community selection"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Community Documents Modal (Feature 29.7) */}
      {showDocuments && selectedCommunity && (
        <CommunityDocuments
          communityId={selectedCommunity}
          onClose={() => setShowDocuments(false)}
          onDocumentPreview={onDocumentPreview}
        />
      )}

      {/* No Communities Message */}
      {communities.length === 0 && (
        <div className="mt-2 p-3 bg-gray-50 border-2 border-gray-200 rounded-lg text-center">
          <div className="text-xs text-gray-500">
            No communities detected in the graph
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Compact variant for use in toolbars/headers
 */
interface CommunityHighlightCompactProps {
  communities: Community[];
  selectedCommunity: string | null;
  onCommunitySelect: (communityId: string | null) => void;
}

export function CommunityHighlightCompact({
  communities,
  selectedCommunity,
  onCommunitySelect,
}: CommunityHighlightCompactProps) {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onCommunitySelect(value === '' ? null : value);
  };

  const sortedCommunities = [...communities].sort((a, b) => b.size - a.size);
  const selectedCommunityData = sortedCommunities.find((c) => c.id === selectedCommunity);

  return (
    <div className="flex items-center gap-2">
      {selectedCommunity && (
        <div className="w-3 h-3 bg-purple-500 rounded-full flex-shrink-0" aria-hidden="true" />
      )}
      <select
        value={selectedCommunity || ''}
        onChange={handleChange}
        className="px-3 py-1.5 text-xs bg-white border border-gray-300 rounded-md
                   focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/20
                   hover:border-gray-400 transition-all duration-200 cursor-pointer"
        aria-label="Select community to highlight"
      >
        <option value="">All Communities</option>
        {sortedCommunities.map((community) => (
          <option key={community.id} value={community.id}>
            {community.topic} ({community.size})
          </option>
        ))}
      </select>
      {selectedCommunity && selectedCommunityData && (
        <span className="text-xs text-gray-600">
          {selectedCommunityData.size} members
        </span>
      )}
    </div>
  );
}

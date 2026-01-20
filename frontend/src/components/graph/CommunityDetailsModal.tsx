/**
 * CommunityDetailsModal Component
 * Sprint 116 Feature 116.7: Graph Communities UI
 *
 * Features:
 * - Full community details in modal dialog
 * - Member entities list with types
 * - Related documents via existing CommunityDocuments component
 * - Export community data
 * - Visual metrics and statistics
 */

import { useEffect, useState } from 'react';
import { X, Users, TrendingUp, FileText, Download, Loader2 } from 'lucide-react';
import { useCommunityDocuments } from '../../hooks/useCommunityDocuments';
import type { Community } from '../../types/graph';

interface CommunityDetailsModalProps {
  communityId: string;
  onClose: () => void;
}

/**
 * Modal component for viewing detailed community information
 *
 * @param communityId Community ID to display details for
 * @param onClose Callback when modal is closed
 */
export function CommunityDetailsModal({ communityId, onClose }: CommunityDetailsModalProps) {
  const [community, setCommunity] = useState<Community | null>(null);
  const [members, setMembers] = useState<CommunityMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [activeTab, setActiveTab] = useState<'members' | 'documents'>('members');

  // Fetch community documents using existing hook
  const { documents, community: communityData, loading: docsLoading } = useCommunityDocuments(communityId);

  // Fetch community details (mock for now - would use API)
  useEffect(() => {
    const fetchCommunityDetails = async () => {
      setLoading(true);
      setError(null);
      try {
        // TODO: Replace with actual API call
        // For now, use the community data from useCommunityDocuments hook
        if (communityData) {
          setCommunity(communityData);
        }

        // Mock members data (would come from API)
        const mockMembers: CommunityMember[] = [
          { id: '1', name: 'Entity A', type: 'PERSON', connections: 5 },
          { id: '2', name: 'Entity B', type: 'ORGANIZATION', connections: 8 },
          { id: '3', name: 'Entity C', type: 'LOCATION', connections: 3 },
        ];
        setMembers(mockMembers);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to fetch community details'));
      } finally {
        setLoading(false);
      }
    };

    void fetchCommunityDetails();
  }, [communityId, communityData]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  // Prevent body scroll
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  // Handle export
  const handleExport = () => {
    const data = {
      community,
      members,
      documents: documents.map(d => ({ id: d.id, title: d.title, entities: d.entities })),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `community_${communityId}_${new Date().toISOString()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Dialog */}
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <div
          className="bg-white rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-start justify-between px-6 py-5 border-b border-gray-200">
            <div className="flex-1">
              <h2
                id="modal-title"
                className="text-2xl font-bold text-gray-900 mb-2 flex items-center gap-2"
              >
                <Users className="w-6 h-6 text-purple-600" />
                {loading ? 'Loading...' : community?.topic || 'Community Details'}
              </h2>
              {community && (
                <div className="flex items-center gap-4 text-sm text-gray-600">
                  <span>{community.size} members</span>
                  {community.density !== undefined && (
                    <>
                      <span>•</span>
                      <span>{(community.density * 100).toFixed(1)}% density</span>
                    </>
                  )}
                  <span>•</span>
                  <span className="font-mono text-xs">{communityId}</span>
                </div>
              )}
            </div>
            <div className="flex items-center gap-2 ml-4">
              <button
                onClick={handleExport}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="Export community data"
              >
                <Download className="w-5 h-5" />
              </button>
              <button
                onClick={onClose}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="Close modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-gray-200 px-6">
            <button
              onClick={() => setActiveTab('members')}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'members'
                  ? 'border-purple-600 text-purple-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
              data-testid="tab-members"
            >
              Members ({members.length})
            </button>
            <button
              onClick={() => setActiveTab('documents')}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'documents'
                  ? 'border-purple-600 text-purple-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
              data-testid="tab-documents"
            >
              Documents ({documents.length})
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-6 py-5">
            {loading ? (
              <LoadingState />
            ) : error ? (
              <ErrorState error={error} />
            ) : activeTab === 'members' ? (
              <MembersTab members={members} />
            ) : (
              <DocumentsTab documents={documents} loading={docsLoading} />
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
            <button
              onClick={onClose}
              className="px-5 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

/**
 * Community Member Type
 */
interface CommunityMember {
  id: string;
  name: string;
  type: string;
  connections: number;
}

/**
 * Members Tab Component
 */
function MembersTab({ members }: { members: CommunityMember[] }) {
  if (members.length === 0) {
    return (
      <div className="text-center py-12">
        <Users className="w-12 h-12 text-gray-400 mx-auto mb-3" />
        <h3 className="text-lg font-semibold text-gray-900 mb-1">No members found</h3>
        <p className="text-sm text-gray-600">This community has no member entities</p>
      </div>
    );
  }

  // Group members by type
  const membersByType = members.reduce((acc, member) => {
    if (!acc[member.type]) {
      acc[member.type] = [];
    }
    acc[member.type].push(member);
    return acc;
  }, {} as Record<string, CommunityMember[]>);

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <div className="text-sm font-medium text-purple-600 mb-1">Total Members</div>
          <div className="text-2xl font-bold text-purple-900">{members.length}</div>
        </div>
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="text-sm font-medium text-blue-600 mb-1">Entity Types</div>
          <div className="text-2xl font-bold text-blue-900">{Object.keys(membersByType).length}</div>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="text-sm font-medium text-green-600 mb-1">Avg Connections</div>
          <div className="text-2xl font-bold text-green-900">
            {(members.reduce((sum, m) => sum + m.connections, 0) / members.length).toFixed(1)}
          </div>
        </div>
      </div>

      {/* Members by Type */}
      <div className="space-y-4">
        {Object.entries(membersByType).map(([type, typeMembers]) => (
          <div key={type} className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
              <h3 className="font-semibold text-gray-900">
                {type} <span className="text-sm font-normal text-gray-600">({typeMembers.length})</span>
              </h3>
            </div>
            <div className="divide-y divide-gray-100">
              {typeMembers.map((member) => (
                <div key={member.id} className="px-4 py-3 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-gray-900">{member.name}</div>
                      <div className="text-xs text-gray-500">ID: {member.id}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-gray-900">{member.connections}</div>
                      <div className="text-xs text-gray-500">connections</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Documents Tab Component
 */
function DocumentsTab({ documents, loading }: { documents: any[]; loading: boolean }) {
  if (loading) {
    return <LoadingState />;
  }

  if (documents.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className="w-12 h-12 text-gray-400 mx-auto mb-3" />
        <h3 className="text-lg font-semibold text-gray-900 mb-1">No documents found</h3>
        <p className="text-sm text-gray-600">No documents mention entities from this community</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {documents.map((doc) => (
        <div
          key={doc.id}
          className="border border-gray-200 rounded-lg p-4 hover:border-purple-300 hover:shadow-sm transition-all"
        >
          <h3 className="font-semibold text-gray-900 mb-2 flex items-start gap-2">
            <FileText className="w-4 h-4 text-purple-600 flex-shrink-0 mt-0.5" />
            <span className="flex-1">{doc.title}</span>
          </h3>
          <p className="text-sm text-gray-600 mb-3 line-clamp-2">{doc.excerpt}</p>
          <div className="flex flex-wrap gap-1.5">
            {doc.entities.slice(0, 5).map((entity: string, idx: number) => (
              <span
                key={idx}
                className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-800 rounded-md"
              >
                {entity}
              </span>
            ))}
            {doc.entities.length > 5 && (
              <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 rounded-md">
                +{doc.entities.length - 5} more
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Loading State
 */
function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <Loader2 className="w-12 h-12 text-purple-600 animate-spin mb-4" />
      <p className="text-sm text-gray-600">Loading community details...</p>
    </div>
  );
}

/**
 * Error State
 */
function ErrorState({ error }: { error: Error }) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
        <X className="w-8 h-8 text-red-600" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">Failed to load details</h3>
      <p className="text-sm text-gray-600 max-w-md text-center">{error.message}</p>
    </div>
  );
}

/**
 * DataSubjectRights Component
 * Sprint 98 Feature 98.3: GDPR Consent Manager UI
 *
 * Handles data subject rights requests (GDPR Articles 15-22):
 * - Right to Access (Art. 15)
 * - Right to Erasure (Art. 17)
 * - Right to Portability (Art. 20)
 * - Right to Rectification (Art. 16)
 */

import { useState } from 'react';
import {
  Download,
  Trash2,
  Eye,
  Edit,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
} from 'lucide-react';
import type {
  DataSubjectRightsRequest,
  DataSubjectRightType,
  RequestStatus,
} from '../../types/gdpr';
import {
  getRightArticleReference,
  getRequestStatusColor,
} from '../../types/gdpr';

interface DataSubjectRightsProps {
  requests: DataSubjectRightsRequest[];
  onApproveRequest: (requestId: string) => void;
  onRejectRequest: (requestId: string, reason: string) => void;
  onViewRequest: (request: DataSubjectRightsRequest) => void;
  onCreateRequest: (userId: string, requestType: DataSubjectRightType) => void;
}

export function DataSubjectRights({
  requests,
  onApproveRequest,
  onRejectRequest,
  onViewRequest,
  onCreateRequest,
}: DataSubjectRightsProps) {
  const [filterStatus, setFilterStatus] = useState<RequestStatus | 'all'>('all');
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Filter requests
  const filteredRequests = requests.filter((request) => {
    return filterStatus === 'all' || request.status === filterStatus;
  });

  const pendingRequests = requests.filter((r) => r.status === 'pending');

  return (
    <div className="space-y-4" data-testid="data-subject-rights-list">
      {/* Header with Summary - Sprint 111: Added rights description for E2E test compatibility */}
      <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4 border border-yellow-200 dark:border-yellow-800">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h3 className="text-lg font-semibold text-yellow-900 dark:text-yellow-100">
              Data Subject Rights Requests
            </h3>
            <p className="text-sm text-yellow-700 dark:text-yellow-300">
              {pendingRequests.length} pending request{pendingRequests.length !== 1 ? 's' : ''}
            </p>
            <p className="text-xs text-yellow-600 dark:text-yellow-400" data-testid="rights-description">
              Manage requests for: Right to Access (Art. 15), Right to Rectification (Art. 16),
              Right to Erasure (Art. 17), Right to Portability (Art. 20)
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg transition-colors"
          >
            New Request
          </button>
        </div>
      </div>

      {/* Filter */}
      <div>
        <label htmlFor="request-status-filter" className="sr-only">
          Filter by status
        </label>
        <select
          id="request-status-filter"
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value as RequestStatus | 'all')}
          className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Status</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="completed">Completed</option>
          <option value="rejected">Rejected</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {/* Request List */}
      <div className="space-y-3">
        {filteredRequests.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No requests found matching your filters.
          </div>
        ) : (
          filteredRequests.map((request) => (
            <RequestCard
              key={request.id}
              request={request}
              onApprove={onApproveRequest}
              onReject={onRejectRequest}
              onView={onViewRequest}
            />
          ))
        )}
      </div>

      {/* Create Request Modal */}
      {showCreateModal && (
        <CreateRequestModal
          onSubmit={(userId, requestType) => {
            onCreateRequest(userId, requestType);
            setShowCreateModal(false);
          }}
          onCancel={() => setShowCreateModal(false)}
        />
      )}
    </div>
  );
}

/**
 * Single Request Card
 */
interface RequestCardProps {
  request: DataSubjectRightsRequest;
  onApprove: (requestId: string) => void;
  onReject: (requestId: string, reason: string) => void;
  onView: (request: DataSubjectRightsRequest) => void;
}

function RequestCard({ request, onApprove, onReject, onView }: RequestCardProps) {
  const [showRejectModal, setShowRejectModal] = useState(false);

  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 space-y-3"
      data-testid={`right-request-${request.id}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <RequestTypeIcon type={request.requestType} />
          <div>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100">
              Request #{request.id.slice(0, 8)}: <span data-testid={`right-type-${request.id}`}>{formatRequestType(request.requestType)}</span> (
              {request.userId})
            </h4>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Article: {request.articleReference}
            </p>
          </div>
        </div>
        <span data-testid={`right-status-${request.id}`}>
          <RequestStatusBadge status={request.status} />
        </span>
      </div>

      {/* Dates */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-600 dark:text-gray-400">Submitted: </span>
          <span className="text-gray-900 dark:text-gray-100">
            {new Date(request.submittedAt).toLocaleString()}
          </span>
        </div>
        {request.status !== 'pending' && request.reviewedAt && (
          <div>
            <span className="text-gray-600 dark:text-gray-400">Reviewed: </span>
            <span className="text-gray-900 dark:text-gray-100">
              {new Date(request.reviewedAt).toLocaleString()}
            </span>
          </div>
        )}
      </div>

      {/* Scope */}
      <div className="text-sm">
        <span className="text-gray-600 dark:text-gray-400">Scope:</span>
        <ul className="mt-1 ml-4 list-disc list-inside text-gray-900 dark:text-gray-100">
          {request.scope.map((item, idx) => (
            <li key={idx}>{item}</li>
          ))}
        </ul>
      </div>

      {/* Rejection Reason (if rejected) */}
      {request.status === 'rejected' && request.rejectionReason && (
        <div className="text-sm bg-red-50 dark:bg-red-900/20 p-3 rounded border border-red-200 dark:border-red-800">
          <span className="font-medium text-red-700 dark:text-red-300">Rejection Reason: </span>
          <span className="text-red-600 dark:text-red-400">{request.rejectionReason}</span>
        </div>
      )}

      {/* Actions */}
      {request.status === 'pending' && (
        <div className="flex gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={() => onApprove(request.id)}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
          >
            Approve & Execute
          </button>
          <button
            onClick={() => setShowRejectModal(true)}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
          >
            Reject
          </button>
          <button
            onClick={() => onView(request)}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
          >
            Request Info
          </button>
        </div>
      )}
      {request.status !== 'pending' && (
        <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={() => onView(request)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            View Details
          </button>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && (
        <RejectModal
          onSubmit={(reason) => {
            onReject(request.id, reason);
            setShowRejectModal(false);
          }}
          onCancel={() => setShowRejectModal(false)}
        />
      )}
    </div>
  );
}

/**
 * Request Type Icon
 */
function RequestTypeIcon({ type }: { type: DataSubjectRightType }) {
  switch (type) {
    case 'access':
      return <Eye className="w-5 h-5 text-blue-600 dark:text-blue-400" />;
    case 'erasure':
      return <Trash2 className="w-5 h-5 text-red-600 dark:text-red-400" />;
    case 'portability':
      return <Download className="w-5 h-5 text-green-600 dark:text-green-400" />;
    case 'rectification':
      return <Edit className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />;
    default:
      return <AlertCircle className="w-5 h-5 text-gray-600 dark:text-gray-400" />;
  }
}

/**
 * Request Status Badge
 */
function RequestStatusBadge({ status }: { status: RequestStatus }) {
  const statusColor = getRequestStatusColor(status);

  const colorClasses = {
    green: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300',
    red: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300',
    yellow: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300',
    blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300',
  };

  return (
    <span
      className={`px-3 py-1 text-xs font-semibold rounded-full ${
        colorClasses[statusColor as keyof typeof colorClasses]
      }`}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

/**
 * Format Request Type for Display
 */
function formatRequestType(type: DataSubjectRightType): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

/**
 * Create Request Modal
 */
interface CreateRequestModalProps {
  onSubmit: (userId: string, requestType: DataSubjectRightType) => void;
  onCancel: () => void;
}

function CreateRequestModal({ onSubmit, onCancel }: CreateRequestModalProps) {
  const [userId, setUserId] = useState('');
  const [requestType, setRequestType] = useState<DataSubjectRightType>('access');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (userId.trim()) {
      onSubmit(userId.trim(), requestType);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          Create Data Subject Rights Request
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="userId" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              User ID
            </label>
            <input
              id="userId"
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label htmlFor="requestType" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Request Type
            </label>
            <select
              id="requestType"
              value={requestType}
              onChange={(e) => setRequestType(e.target.value as DataSubjectRightType)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
            >
              <option value="access">Access (Art. 15)</option>
              <option value="erasure">Erasure (Art. 17)</option>
              <option value="portability">Portability (Art. 20)</option>
              <option value="rectification">Rectification (Art. 16)</option>
            </select>
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              Create Request
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/**
 * Reject Modal
 */
interface RejectModalProps {
  onSubmit: (reason: string) => void;
  onCancel: () => void;
}

function RejectModal({ onSubmit, onCancel }: RejectModalProps) {
  const [reason, setReason] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (reason.trim()) {
      onSubmit(reason.trim());
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          Reject Request
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="reason" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Rejection Reason
            </label>
            <textarea
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
            >
              Reject Request
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

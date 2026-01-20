/**
 * Audit Trail Types
 * Sprint 98 Feature 98.4: Audit Trail Viewer
 *
 * TypeScript types for audit trail events, compliance reports,
 * and cryptographic integrity verification. Implements EU AI Act Art. 12.
 */

/**
 * Audit Event Types
 */
export type AuditEventType =
  // Authentication Events
  | 'AUTH_SUCCESS'
  | 'AUTH_FAILURE'
  | 'AUTH_LOGOUT'
  // Data Access Events
  | 'DATA_READ'
  | 'DATA_WRITE'
  | 'DATA_DELETE'
  // Skill Execution Events
  | 'SKILL_EXECUTED'
  | 'SKILL_FAILED'
  | 'SKILL_BLOCKED'
  // Policy Events
  | 'POLICY_VIOLATION'
  | 'POLICY_UPDATED'
  // GDPR Events
  | 'CONSENT_GRANTED'
  | 'CONSENT_WITHDRAWN'
  | 'DATA_EXPORTED'
  | 'DATA_ERASED'
  // System Events
  | 'CONFIG_CHANGED'
  | 'SYSTEM_ERROR';

/**
 * Audit Event Outcome
 */
export type AuditEventOutcome = 'success' | 'failure' | 'blocked' | 'error';

/**
 * Audit Event
 */
export interface AuditEvent {
  id: string;
  timestamp: string; // ISO 8601 timestamp
  eventType: AuditEventType;
  actorId: string; // User ID or system identifier
  actorName: string | null; // Human-readable actor name
  resourceId: string; // Resource being accessed (document_id, query_id, etc.)
  resourceType: string; // "document", "query", "skill", etc.
  outcome: AuditEventOutcome;
  duration: number | null; // Duration in ms (for operations)
  message: string; // Human-readable event description
  metadata: AuditEventMetadata;
  hash: string; // SHA-256 hash for integrity verification
  previousHash: string | null; // Previous event hash (chain)
}

/**
 * Audit Event Metadata
 */
export interface AuditEventMetadata {
  // Data categories (for GDPR compliance)
  dataCategories?: string[];

  // Skill-specific data
  skillName?: string;
  skillVersion?: string;

  // Error information
  errorMessage?: string;
  errorCode?: string;

  // IP and location
  ipAddress?: string;
  userAgent?: string;

  // Additional context
  [key: string]: unknown;
}

/**
 * Audit Event Filters
 */
export interface AuditEventFilters {
  eventType?: AuditEventType;
  actorId?: string;
  startTime?: string; // ISO 8601 timestamp
  endTime?: string; // ISO 8601 timestamp
  outcome?: AuditEventOutcome;
  searchQuery?: string; // Free-text search
  page?: number;
  pageSize?: number;
}

/**
 * Audit Event List Response
 */
export interface AuditEventListResponse {
  events: AuditEvent[];
  total: number;
  page: number;
  pageSize: number;
  filters: AuditEventFilters;
}

/**
 * Compliance Report Type
 */
export type ComplianceReportType =
  | 'gdpr' // GDPR Art. 30 processing activities
  | 'security' // Security events and policy violations
  | 'skill_usage'; // Skill usage and performance

/**
 * Compliance Report
 */
export interface ComplianceReport {
  id: string;
  reportType: ComplianceReportType;
  generatedAt: string; // ISO 8601 timestamp
  startTime: string; // Report time range start
  endTime: string; // Report time range end
  summary: ComplianceReportSummary;
  sections: ComplianceReportSection[];
  format: 'json' | 'csv' | 'pdf';
}

/**
 * Compliance Report Summary
 */
export interface ComplianceReportSummary {
  totalEvents: number;
  successRate: number; // 0-1
  failureRate: number; // 0-1
  policyViolations: number;
  topActors: Array<{ actorId: string; actorName: string; count: number }>;
  topEventTypes: Array<{ eventType: AuditEventType; count: number }>;
}

/**
 * Compliance Report Section
 */
export interface ComplianceReportSection {
  title: string;
  description: string;
  data: Array<Record<string, unknown>>;
  charts?: Array<{
    type: 'bar' | 'line' | 'pie';
    data: unknown;
  }>;
}

/**
 * GDPR Compliance Report (Article 30)
 */
export interface GDPRComplianceReport extends ComplianceReport {
  reportType: 'gdpr';
  gdprMetrics: {
    totalProcessingActivities: number;
    dataSubjectRequests: {
      access: number;
      erasure: number;
      rectification: number;
      portability: number;
    };
    consentsGranted: number;
    consentsWithdrawn: number;
    dataExports: number;
    dataErasures: number;
  };
}

/**
 * Security Compliance Report
 */
export interface SecurityComplianceReport extends ComplianceReport {
  reportType: 'security';
  securityMetrics: {
    authenticationFailures: number;
    policyViolations: number;
    blockedOperations: number;
    systemErrors: number;
    suspiciousActivities: Array<{
      actorId: string;
      eventCount: number;
      riskScore: number;
    }>;
  };
}

/**
 * Integrity Verification Result
 */
export interface IntegrityVerificationResult {
  verified: boolean;
  totalEvents: number;
  verifiedEvents: number;
  failedEvents: number;
  brokenChains: Array<{
    eventId: string;
    timestamp: string;
    reason: string;
  }>;
  verifiedAt: string; // ISO 8601 timestamp
  timeRange: {
    startTime: string;
    endTime: string;
  };
}

/**
 * Audit Export Options
 */
export interface AuditExportOptions {
  format: 'json' | 'csv';
  filters: AuditEventFilters;
  includeMetadata: boolean;
}

/**
 * Helper: Get event type badge color
 */
export function getEventTypeColor(eventType: AuditEventType): string {
  // Handle null/undefined eventType
  if (!eventType) {
    return 'gray';
  }
  // Authentication events - blue
  if (eventType.startsWith('AUTH_')) {
    return 'blue';
  }
  // Data events - purple
  if (eventType.startsWith('DATA_')) {
    return 'purple';
  }
  // Skill events - green
  if (eventType.startsWith('SKILL_')) {
    return 'green';
  }
  // Policy events - red
  if (eventType.startsWith('POLICY_')) {
    return 'red';
  }
  // GDPR events - yellow
  if (eventType.startsWith('CONSENT_') || eventType.includes('EXPORTED') || eventType.includes('ERASED')) {
    return 'yellow';
  }
  // System events - gray
  return 'gray';
}

/**
 * Helper: Get outcome badge color
 */
export function getOutcomeColor(outcome: AuditEventOutcome): string {
  const colorMap: Record<AuditEventOutcome, string> = {
    success: 'green',
    failure: 'red',
    blocked: 'red',
    error: 'red',
  };
  return colorMap[outcome];
}

/**
 * Helper: Get outcome icon
 */
export function getOutcomeIcon(outcome: AuditEventOutcome): string {
  const iconMap: Record<AuditEventOutcome, string> = {
    success: '✅',
    failure: '❌',
    blocked: '🚫',
    error: '⚠️',
  };
  return iconMap[outcome];
}

/**
 * Helper: Format event type for display
 */
export function formatEventType(eventType: AuditEventType): string {
  return eventType
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

/**
 * Helper: Format duration
 */
export function formatDuration(durationMs: number | null): string {
  if (durationMs === null) {
    return 'N/A';
  }
  if (durationMs < 1000) {
    return `${durationMs}ms`;
  }
  const seconds = (durationMs / 1000).toFixed(2);
  return `${seconds}s`;
}

/**
 * Helper: Verify event hash (client-side verification)
 */
export function verifyEventHash(event: AuditEvent, previousEvent: AuditEvent | null): boolean {
  // Note: This is a simplified client-side verification
  // The backend should perform the actual SHA-256 verification
  if (previousEvent === null) {
    return event.previousHash === null;
  }
  return event.previousHash === previousEvent.hash;
}

/**
 * GDPR Types
 * Sprint 98 Feature 98.3: GDPR Consent Manager UI
 *
 * TypeScript types for GDPR consent management, data subject rights,
 * and GDPR compliance. Implements EU GDPR Articles 6, 7, 13-22, 30.
 */

/**
 * GDPR Legal Basis (Article 6)
 */
export type LegalBasis =
  | 'consent' // Art. 6(1)(a) - Explicit consent
  | 'contract' // Art. 6(1)(b) - Contract performance
  | 'legal_obligation' // Art. 6(1)(c) - Legal obligation
  | 'vital_interests' // Art. 6(1)(d) - Vital interests
  | 'public_task' // Art. 6(1)(e) - Public interest
  | 'legitimate_interests'; // Art. 6(1)(f) - Legitimate interests

/**
 * GDPR Data Categories
 */
export type DataCategory =
  | 'identifier' // Name, ID, email
  | 'contact' // Address, phone
  | 'financial' // Payment info
  | 'health' // Medical data
  | 'behavioral' // Browsing, preferences
  | 'biometric' // Fingerprints, facial recognition
  | 'location' // GPS, IP address
  | 'demographic' // Age, gender
  | 'professional' // Job title, company
  | 'other'; // Other data

/**
 * Consent Status
 */
export type ConsentStatus =
  | 'active' // Currently valid
  | 'expired' // Expired consent
  | 'withdrawn' // User revoked consent
  | 'pending'; // Awaiting approval

/**
 * GDPR Consent Record
 */
export interface GDPRConsent {
  id: string;
  userId: string;
  purpose: string; // e.g., "Customer Support", "Marketing Communications"
  legalBasis: LegalBasis;
  legalBasisText: string; // e.g., "Art. 6(1)(a) Consent"
  dataCategories: DataCategory[];
  skillRestrictions: string[]; // List of skills this consent applies to (empty = all)
  grantedAt: string; // ISO 8601 timestamp
  expiresAt: string | null; // ISO 8601 timestamp or null for no expiration
  withdrawnAt: string | null; // ISO 8601 timestamp or null if active
  status: ConsentStatus;
  version: string; // Consent version (e.g., "1.0")
  metadata: Record<string, unknown>;
}

/**
 * Consent Form Data (for creating/editing)
 */
export interface ConsentFormData {
  userId: string;
  purpose: string;
  legalBasis: LegalBasis;
  dataCategories: DataCategory[];
  skillRestrictions: string[];
  expiresAt: string | null;
}

/**
 * Data Subject Rights Request Types (Articles 15-22)
 */
export type DataSubjectRightType =
  | 'access' // Art. 15 - Right to access
  | 'rectification' // Art. 16 - Right to rectification
  | 'erasure' // Art. 17 - Right to erasure (RTBF)
  | 'restriction' // Art. 18 - Right to restriction
  | 'portability' // Art. 20 - Right to data portability
  | 'objection'; // Art. 21 - Right to object

/**
 * Request Status
 */
export type RequestStatus =
  | 'pending' // Awaiting review
  | 'approved' // Approved, executing
  | 'completed' // Completed successfully
  | 'rejected' // Rejected
  | 'failed'; // Failed execution

/**
 * Data Subject Rights Request
 */
export interface DataSubjectRightsRequest {
  id: string;
  userId: string;
  requestType: DataSubjectRightType;
  articleReference: string; // e.g., "GDPR Art. 17"
  submittedAt: string; // ISO 8601 timestamp
  status: RequestStatus;
  scope: string[]; // e.g., ["Revoke all consents", "Delete processing records"]
  reviewedBy: string | null; // Admin user ID
  reviewedAt: string | null;
  completedAt: string | null;
  rejectionReason: string | null;
  metadata: Record<string, unknown>;
}

/**
 * Processing Activity Record (Article 30)
 */
export interface ProcessingActivity {
  id: string;
  userId: string | null; // null for system-level activities
  timestamp: string; // ISO 8601 timestamp
  activity: string; // e.g., "data_read", "data_write", "skill_executed"
  purpose: string; // Processing purpose
  legalBasis: LegalBasis;
  dataCategories: DataCategory[];
  skillName: string | null; // Skill that performed the activity
  resourceId: string; // Document ID, query ID, etc.
  duration: number | null; // Duration in ms
  metadata: Record<string, unknown>;
}

/**
 * PII Detection Result
 */
export interface PIIDetectionResult {
  text: string;
  piiEntities: PIIEntity[];
  confidence: number;
}

/**
 * PII Entity
 */
export interface PIIEntity {
  type: DataCategory;
  value: string;
  start: number;
  end: number;
  confidence: number;
}

/**
 * PII Redaction Settings
 */
export interface PIIRedactionSettings {
  enabled: boolean;
  autoRedact: boolean; // Automatically redact PII in responses
  redactionChar: string; // Character to use for redaction (e.g., "*")
  detectionThreshold: number; // Confidence threshold (0-1)
  enabledCategories: DataCategory[]; // Which categories to detect
}

/**
 * GDPR Data Export (Article 20 - Data Portability)
 */
export interface GDPRDataExport {
  userId: string;
  exportedAt: string; // ISO 8601 timestamp
  dataCategories: DataCategory[];
  data: {
    consents: GDPRConsent[];
    processingActivities: ProcessingActivity[];
    userData: Record<string, unknown>;
  };
  format: 'json' | 'csv';
}

/**
 * API Response Types
 */
export interface ConsentListResponse {
  consents: GDPRConsent[];
  total: number;
  page: number;
  pageSize: number;
}

export interface RequestListResponse {
  requests: DataSubjectRightsRequest[];
  total: number;
  page: number;
  pageSize: number;
}

export interface ProcessingActivityListResponse {
  activities: ProcessingActivity[];
  total: number;
  page: number;
  pageSize: number;
}

/**
 * Helper: Get legal basis display text
 */
export function getLegalBasisText(basis: LegalBasis): string {
  const textMap: Record<LegalBasis, string> = {
    consent: 'Art. 6(1)(a) Consent',
    contract: 'Art. 6(1)(b) Contract',
    legal_obligation: 'Art. 6(1)(c) Legal Obligation',
    vital_interests: 'Art. 6(1)(d) Vital Interests',
    public_task: 'Art. 6(1)(e) Public Task',
    legitimate_interests: 'Art. 6(1)(f) Legitimate Interests',
  };
  return textMap[basis];
}

/**
 * Helper: Get data subject right article reference
 */
export function getRightArticleReference(rightType: DataSubjectRightType): string {
  const articleMap: Record<DataSubjectRightType, string> = {
    access: 'GDPR Art. 15',
    rectification: 'GDPR Art. 16',
    erasure: 'GDPR Art. 17',
    restriction: 'GDPR Art. 18',
    portability: 'GDPR Art. 20',
    objection: 'GDPR Art. 21',
  };
  return articleMap[rightType];
}

/**
 * Helper: Get consent status badge color
 */
export function getConsentStatusColor(status: ConsentStatus): string {
  const colorMap: Record<ConsentStatus, string> = {
    active: 'green',
    expired: 'red',
    withdrawn: 'gray',
    pending: 'yellow',
  };
  return colorMap[status];
}

/**
 * Helper: Get request status badge color
 */
export function getRequestStatusColor(status: RequestStatus): string {
  const colorMap: Record<RequestStatus, string> = {
    pending: 'yellow',
    approved: 'blue',
    completed: 'green',
    rejected: 'red',
    failed: 'red',
  };
  return colorMap[status];
}

/**
 * Helper: Check if consent is expiring soon (within 30 days)
 */
export function isConsentExpiringSoon(consent: GDPRConsent): boolean {
  if (!consent.expiresAt || consent.status !== 'active') {
    return false;
  }
  const expiresAt = new Date(consent.expiresAt);
  const now = new Date();
  const daysUntilExpiry = (expiresAt.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
  return daysUntilExpiry > 0 && daysUntilExpiry <= 30;
}

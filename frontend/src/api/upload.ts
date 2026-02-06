/**
 * Upload API Client
 * Sprint 125 Feature 125.9a: Domain Detection at Upload
 *
 * Handles document uploads and domain detection
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface DomainDetectionResult {
  domain_id: string;
  domain_name: string;
  confidence: number;
  ddc_code?: string;
}

export interface DomainDetectionResponse {
  domains: DomainDetectionResult[];
  top_domain: DomainDetectionResult | null;
}

export interface UploadResponse {
  document_id: string;
  status: string;
  message: string;
}

/**
 * Detect domain for a document file
 * Sprint 125 Feature 125.9a: Domain Detection
 *
 * @param file Document file to analyze
 * @returns Domain detection results with confidence scores
 */
export async function detectDomain(file: File): Promise<DomainDetectionResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/v1/retrieval/detect-domain`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Upload document with optional domain classification
 * Sprint 125 Feature 125.9a: Upload with domain_id
 *
 * @param file Document file to upload
 * @param namespace Namespace for the document (default: 'default')
 * @param domainId Optional domain ID for classification
 * @returns Upload response with document ID
 */
export async function uploadDocument(
  file: File,
  namespace: string = 'default',
  domainId?: string
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('namespace', namespace);

  if (domainId) {
    formData.append('domain_id', domainId);
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/retrieval/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Get upload status by document ID
 *
 * @param documentId Document ID to check
 * @returns Upload status information
 */
export async function getUploadStatus(documentId: string): Promise<{
  document_id: string;
  status: string;
  progress: number;
  message?: string;
}> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/upload-status/${documentId}`,
    {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

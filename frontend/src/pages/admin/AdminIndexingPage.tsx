/**
 * Admin Indexing Page Component
 * Sprint 31 Feature 31.7: Admin Indexing E2E Tests - UI Implementation
 * Sprint 33 Feature 33.1: Directory Selector Dialog
 * Sprint 33 Feature 33.2: File List with Color Coding
 * Sprint 33 Feature 33.3: Compact Live Progress Display
 *
 * Features:
 * - Directory path input with validation
 * - Recursive directory scanning option
 * - File list with color coding (Docling=dark green, LlamaIndex=light green, unsupported=red)
 * - File selection (all, none, supported only)
 * - Start/Cancel indexing controls
 * - Real-time SSE progress tracking
 * - Progress bar with percentage display
 * - Status message updates (Processing -> Chunking -> Embedding -> Complete)
 * - Indexed document count display
 * - Error handling for invalid paths
 *
 * All data-testid attributes match E2E test expectations from AdminIndexingPage POM
 */

import { useState, useCallback, useRef, useMemo, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { scanDirectory, streamAddDocuments, uploadFiles } from '../../api/admin';
import type {
  ReindexProgressChunk,
  ScanDirectoryResponse,
  FileInfo,
  DetailedProgress,
  IngestionError,
  PipelineProgressData,
  StageProgress,
} from '../../types/admin';
import { IndexingDetailDialog } from '../../components/admin/IndexingDetailDialog';
import { ErrorTrackingButton } from '../../components/admin/ErrorTrackingButton';
import { PipelineProgressVisualization } from '../../components/admin/PipelineProgressVisualization';
import { NamespaceSelector } from '../../components/search/NamespaceSelector';
import { useDomains } from '../../hooks/useDomainTraining';
import {
  getFileSupportStatus,
  isFileSupported,
  formatFileSize,
  FILE_SUPPORT_CONFIG,
} from '../../constants/fileSupport';

// Alias for backward compatibility with existing code
const FILE_TYPE_CONFIG = FILE_SUPPORT_CONFIG;

/**
 * Convert SSE progress data to PipelineProgressData format
 * Sprint 37 Feature 37.4: Pipeline Progress Visualization
 */
function createPipelineProgressData(
  progress: ReindexProgressChunk,
  detailed: DetailedProgress | null,
  startTime: number
): PipelineProgressData {
  const now = Date.now();
  const elapsed = now - startTime;
  const progressPercent = progress.progress_percent || 0;

  // Estimate remaining time based on progress
  const estimatedRemaining = progressPercent > 0 && progressPercent < 100
    ? Math.round((elapsed / progressPercent) * (100 - progressPercent))
    : 0;

  // Create default stage
  const createStage = (
    name: string,
    isActive: boolean,
    isComplete: boolean,
    processed: number = 0,
    total: number = 0
  ): StageProgress => ({
    name,
    status: isComplete ? 'completed' : isActive ? 'in_progress' : 'pending',
    processed,
    total,
    in_flight: isActive ? 1 : 0,
    progress_percent: total > 0 ? (processed / total) * 100 : (isComplete ? 100 : 0),
    duration_ms: 0,
    is_complete: isComplete,
  });

  // Determine current phase
  const phase = progress.phase || 'initialization';
  const phases = ['initialization', 'deletion', 'chunking', 'embedding', 'indexing', 'validation', 'completed'];
  const currentPhaseIndex = phases.indexOf(phase);

  // Map phases to stages
  const parsingDone = currentPhaseIndex >= 2; // After initialization/deletion
  const vlmDone = currentPhaseIndex >= 2;
  const chunkingActive = phase === 'chunking';
  const chunkingDone = currentPhaseIndex > 2;
  const embeddingActive = phase === 'embedding';
  const embeddingDone = currentPhaseIndex > 3;
  const extractionActive = phase === 'indexing';
  const extractionDone = currentPhaseIndex >= 5;

  const docsProcessed = progress.documents_processed || 0;
  const docsTotal = progress.documents_total || 1;
  const chunksTotal = detailed?.chunks_total || docsTotal * 10;
  const chunksProcessed = detailed?.chunks_processed || (progressPercent / 100) * chunksTotal;

  return {
    document_id: `doc_${startTime}`,
    document_name: progress.current_document || 'Processing documents...',
    total_chunks: Math.round(chunksTotal),
    total_images: detailed?.page_elements?.images || 0,
    stages: {
      parsing: createStage('Parsing', !parsingDone, parsingDone, parsingDone ? docsTotal : docsProcessed, docsTotal),
      vlm: createStage('VLM', vlmDone && !chunkingDone, vlmDone, detailed?.vlm_images?.length || 0, detailed?.page_elements?.images || 0),
      chunking: createStage('Chunking', chunkingActive, chunkingDone, Math.round(chunkingDone ? chunksTotal : chunksProcessed), Math.round(chunksTotal)),
      embedding: createStage('Embedding', embeddingActive, embeddingDone, Math.round(embeddingDone ? chunksTotal : chunksProcessed * 0.8), Math.round(chunksTotal)),
      extraction: createStage('Extraction', extractionActive, extractionDone, detailed?.entities?.total_entities || 0, Math.round(chunksTotal)),
    },
    worker_pool: {
      active: extractionActive ? 4 : embeddingActive ? 3 : 1,
      max: 4,
      queue_depth: Math.max(0, Math.round(chunksTotal) - Math.round(chunksProcessed)),
      workers: [
        { id: 0, status: extractionActive ? 'processing' : 'idle', current_chunk: extractionActive ? 'chunk_001' : null, progress_percent: progressPercent },
        { id: 1, status: extractionActive ? 'processing' : 'idle', current_chunk: extractionActive ? 'chunk_002' : null, progress_percent: progressPercent },
        { id: 2, status: embeddingActive ? 'processing' : 'idle', current_chunk: embeddingActive ? 'chunk_003' : null, progress_percent: progressPercent },
        { id: 3, status: chunkingActive ? 'processing' : 'idle', current_chunk: chunkingActive ? 'chunk_004' : null, progress_percent: progressPercent },
      ],
    },
    metrics: {
      entities_total: detailed?.entities?.total_entities || 0,
      relations_total: detailed?.entities?.total_relations || 0,
      neo4j_writes: detailed?.entities?.total_entities || 0,
      qdrant_writes: Math.round(chunksProcessed),
    },
    timing: {
      started_at: startTime,
      elapsed_ms: elapsed,
      estimated_remaining_ms: estimatedRemaining,
    },
    overall_progress_percent: progressPercent,
  };
}

export function AdminIndexingPage() {
  // Form state
  const [directory, setDirectory] = useState('data/sample_documents');
  const [recursive, setRecursive] = useState(false);

  // Sprint 76 Feature 76.1 (TD-084): Namespace selection for multi-tenant isolation
  const [selectedNamespace, setSelectedNamespace] = useState<string>('default');

  // Sprint 76 Feature 76.2 (TD-085): Domain selection for DSPy optimized prompts
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
  const { data: domainsData } = useDomains();

  // Sprint 35 Feature 35.10: File upload state
  const [selectedLocalFiles, setSelectedLocalFiles] = useState<File[]>([]);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sprint 51: Ref for auto-scroll in progress log
  const progressLogRef = useRef<HTMLDivElement>(null);

  // Scan state
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState<ScanDirectoryResponse | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);

  // File selection state
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());

  // Indexing state
  const [isIndexing, setIsIndexing] = useState(false);
  const [progress, setProgress] = useState<ReindexProgressChunk | null>(null);
  const [progressHistory, setProgressHistory] = useState<ReindexProgressChunk[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [indexingStartTime, setIndexingStartTime] = useState<number>(0);

  // Sprint 33 Feature 33.4: Detail Dialog state
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false);
  const [detailedProgress, setDetailedProgress] = useState<DetailedProgress | null>(null);

  // Sprint 33 Feature 33.5: Error Tracking state
  const [errors, setErrors] = useState<IngestionError[]>([]);

  // Sprint 51: Auto-scroll progress log to show latest entry
  useEffect(() => {
    if (progressLogRef.current && progressHistory.length > 0) {
      progressLogRef.current.scrollTop = progressLogRef.current.scrollHeight;
    }
  }, [progressHistory]);

  // Handle directory scan
  const handleScanDirectory = useCallback(async () => {
    if (!directory.trim()) {
      setScanError('Bitte geben Sie einen Verzeichnispfad ein');
      return;
    }

    setIsScanning(true);
    setScanResult(null);
    setScanError(null);
    setSelectedFiles(new Set());

    try {
      const result = await scanDirectory({
        path: directory,
        recursive,
      });
      setScanResult(result);

      // Auto-select all supported files
      const supportedFiles = new Set(
        result.files.filter((f) => f.is_supported).map((f) => f.file_path)
      );
      setSelectedFiles(supportedFiles);
    } catch (err) {
      console.error('Scan error:', err);
      setScanError(err instanceof Error ? err.message : 'Verzeichnis-Scan fehlgeschlagen');
    } finally {
      setIsScanning(false);
    }
  }, [directory, recursive]);

  // Sprint 35 Feature 35.10: File upload handlers
  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setSelectedLocalFiles(files);
    setUploadError(null);
    // Clear previous upload state when selecting new files (Sprint 38 UX fix)
    setUploadedFiles([]);
  }, []);

  const handleRemoveFile = useCallback((index: number) => {
    setSelectedLocalFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleUploadFiles = useCallback(async () => {
    if (selectedLocalFiles.length === 0) {
      setUploadError('Bitte wählen Sie mindestens eine Datei aus');
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    try {
      const response = await uploadFiles(selectedLocalFiles);

      // Extract uploaded file paths
      const filePaths = response.files.map((f) => f.file_path);
      setUploadedFiles(filePaths);

      // Auto-select uploaded files for indexing
      setSelectedFiles(new Set(filePaths));

      // Clear local file selection
      setSelectedLocalFiles([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      // Show success message
      console.log(`Uploaded ${response.files.length} files to ${response.upload_dir}`);
    } catch (err) {
      console.error('Upload error:', err);
      setUploadError(err instanceof Error ? err.message : 'Datei-Upload fehlgeschlagen');
    } finally {
      setIsUploading(false);
    }
  }, [selectedLocalFiles]);

  const handleClearUploads = useCallback(() => {
    setUploadedFiles([]);
    setSelectedFiles(new Set());
  }, []);

  // File selection handlers
  const handleSelectAll = useCallback(() => {
    if (scanResult) {
      setSelectedFiles(new Set(scanResult.files.map((f) => f.file_path)));
    }
  }, [scanResult]);

  const handleSelectNone = useCallback(() => {
    setSelectedFiles(new Set());
  }, []);

  const handleSelectSupported = useCallback(() => {
    if (scanResult) {
      const supportedFiles = new Set(
        scanResult.files.filter((f) => f.is_supported).map((f) => f.file_path)
      );
      setSelectedFiles(supportedFiles);
    }
  }, [scanResult]);

  const handleToggleFile = useCallback((filePath: string) => {
    setSelectedFiles((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(filePath)) {
        newSet.delete(filePath);
      } else {
        newSet.add(filePath);
      }
      return newSet;
    });
  }, []);

  const handleStartIndexing = useCallback(async () => {
    // Sprint 35: Support both directory scanning and file upload workflows
    // Priority: uploaded files > scanned files > auto-scan directory

    // If uploaded files exist, use them
    if (uploadedFiles.length > 0) {
      if (selectedFiles.size === 0) {
        setError('Bitte wählen Sie mindestens eine Datei aus');
        return;
      }
      // Continue with uploaded files
    }
    // If scanned files exist, use them
    else if (scanResult) {
      if (selectedFiles.size === 0) {
        setError('Bitte wählen Sie mindestens eine Datei aus');
        return;
      }
      // Continue with scanned files
    }
    // Otherwise, validate directory and auto-scan (backward compatibility)
    else if (directory.trim()) {
      await handleScanDirectory();
      return; // handleScanDirectory will auto-select supported files
    }
    // No files selected and no directory provided
    else {
      setError('Bitte wählen Sie Dateien hoch oder geben Sie einen Verzeichnispfad ein');
      return;
    }

    // Sprint 51: Removed confirmation dialog - direct start for better UX

    // Reset state
    setIsIndexing(true);
    setProgress(null);
    setProgressHistory([]);
    setError(null);
    setErrors([]); // Reset errors for new indexing run
    setDetailedProgress(null); // Reset detailed progress
    setIndexingStartTime(Date.now()); // Sprint 37: Track start time for pipeline progress

    const controller = new AbortController();
    setAbortController(controller);

    // Get selected file paths as array
    const filePaths = Array.from(selectedFiles);

    try {
      // Sprint 76 Features 76.1 & 76.2: Pass namespace and domain for isolation
      for await (const chunk of streamAddDocuments(
        filePaths,
        false, // dry_run = false
        selectedNamespace, // namespace_id for multi-tenant isolation
        selectedDomain, // domain_id for DSPy optimized prompts
        controller.signal
      )) {
        setProgress(chunk);
        setProgressHistory((prev) => [...prev, chunk]);

        // Sprint 33 Feature 33.6: Update detailed progress from SSE
        // Sprint 51 Fix: Only update entity/relation counts if new values are higher (prevent reset to 0)
        const detailedProgressFromChunk = chunk.detailed_progress;
        if (detailedProgressFromChunk) {
          setDetailedProgress((prev) => {
            if (!prev) return detailedProgressFromChunk;

            const newEntities = detailedProgressFromChunk.entities;
            const prevEntities = prev.entities || {
              new_entities: [],
              new_relations: [],
              total_entities: 0,
              total_relations: 0
            };

            return {
              ...detailedProgressFromChunk,
              entities: {
                // Preserve arrays from chunk or previous state
                new_entities: newEntities?.new_entities || prevEntities.new_entities || [],
                new_relations: newEntities?.new_relations || prevEntities.new_relations || [],
                // Keep highest counts
                total_entities: Math.max(
                  newEntities?.total_entities || 0,
                  prevEntities.total_entities || 0
                ),
                total_relations: Math.max(
                  newEntities?.total_relations || 0,
                  prevEntities.total_relations || 0
                ),
              },
            };
          });
        }

        // Sprint 33 Feature 33.6: Accumulate errors from SSE
        if (chunk.errors && chunk.errors.length > 0) {
          const newErrors = chunk.errors;
          setErrors((prev) => [...prev, ...newErrors]);
        }

        // Handle completion
        if (chunk.status === 'completed') {
          setIsIndexing(false);
          setAbortController(null);
        }

        // Handle errors
        if (chunk.status === 'error') {
          setError(chunk.error || chunk.message);
          setIsIndexing(false);
          setAbortController(null);
        }
      }
    } catch (err) {
      console.error('Indexing error:', err);
      if (err instanceof Error && err.name !== 'AbortError') {
        setError(err.message);
      }
      setIsIndexing(false);
      setAbortController(null);
    }
  }, [directory, selectedFiles, scanResult, uploadedFiles, handleScanDirectory]);

  const handleCancelIndexing = useCallback(() => {
    if (abortController) {
      abortController.abort();
      setIsIndexing(false);
      setAbortController(null);
      setError('Indizierung vom Benutzer abgebrochen');
    }
  }, [abortController]);

  // Sprint 33 Feature 33.5: CSV Export Handler
  const handleExportCSV = useCallback(() => {
    if (errors.length === 0) return;

    // Build CSV content
    const headers = ['Type', 'Timestamp', 'File Name', 'Page', 'Message', 'Details'];
    const rows = errors.map((err) => [
      err.type,
      err.timestamp,
      err.file_name,
      err.page_number?.toString() || '',
      err.message,
      err.details || '',
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map((row) =>
        row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(',')
      ),
    ].join('\n');

    // Download CSV
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `indexing-errors-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [errors]);

  const percentage = progress?.progress_percent || 0;
  const isComplete = progress?.status === 'completed';
  const documentsProcessed = progress?.documents_processed || 0;
  const documentsTotal = progress?.documents_total || 0;

  // Sprint 37: Compute pipeline progress data for visualization
  const pipelineProgressData = useMemo<PipelineProgressData | null>(() => {
    if (!progress || !isIndexing) return null;
    return createPipelineProgressData(progress, detailedProgress, indexingStartTime);
  }, [progress, detailedProgress, isIndexing, indexingStartTime]);

  // Calculate selected files statistics
  const selectedSupportedCount = scanResult
    ? scanResult.files.filter((f) => selectedFiles.has(f.file_path) && f.is_supported).length
    : 0;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-6 px-4 space-y-4">
        {/* Back Link */}
        <Link
          to="/admin"
          className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Admin
        </Link>

        {/* Header */}
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-gray-900">Document Indexing</h1>
          <p className="text-sm text-gray-600">
            Indizieren Sie Dokumente durch Datei-Upload oder aus einem Serververzeichnis
          </p>
        </div>

        {/* Sprint 76 Features 76.1 & 76.2: Namespace & Domain Selection */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Namespace & Domain Auswahl
          </h2>
          <p className="text-xs text-gray-600">
            Wählen Sie den Namespace für Multi-Tenant-Isolation und optional eine Domain für DSPy-optimierte Extraktion.
          </p>

          {/* Namespace Selector */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Namespace (Multi-Tenant Isolation)
            </label>
            <NamespaceSelector
              selectedNamespaces={[selectedNamespace]}
              onSelectionChange={(namespaces) => setSelectedNamespace(namespaces[0] || 'default')}
              compact={false}
            />
            <p className="text-xs text-gray-500 mt-1">
              Standard: &quot;default&quot;. Wählen Sie einen eigenen Namespace für isolierte Projekte oder RAGAS-Evaluationen.
            </p>
          </div>

          {/* Domain Selector */}
          <div>
            <label
              htmlFor="domain-selector"
              className="block text-xs font-medium text-gray-700 mb-2"
            >
              Domain (Optional - DSPy Optimized Prompts)
            </label>
            <select
              id="domain-selector"
              data-testid="domain-selector"
              value={selectedDomain || ''}
              onChange={(e) => setSelectedDomain(e.target.value || null)}
              className="w-full px-3 py-2 text-sm rounded-md border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Keine Domain (Generic Prompts)</option>
              {domainsData?.map((domain) => (
                <option key={domain.name} value={domain.name}>
                  {domain.name} - {domain.description || 'No description'}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Wählen Sie eine trainierte Domain für domain-spezifische Entity/Relation-Extraktion.
            </p>
          </div>
        </div>

        {/* Sprint 35 Feature 35.10: File Upload Section */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Option 1: Dateien hochladen
          </h2>
          <p className="text-xs text-gray-600">
            Laden Sie Dateien von Ihrem Computer hoch. Unterstützte Formate: PDF, DOCX, PPTX,
            TXT, MD, HTML und mehr.
          </p>

          {/* File Input */}
          <div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              onChange={handleFileSelect}
              disabled={isIndexing || isUploading}
              className="hidden"
              id="file-upload-input"
              data-testid="file-upload-input"
            />
            <label
              htmlFor="file-upload-input"
              className={`
                inline-flex items-center px-4 py-2 rounded-md font-medium text-sm
                bg-indigo-600 text-white cursor-pointer
                hover:bg-indigo-700 transition-all
                ${isIndexing || isUploading ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              <svg
                className="w-4 h-4 mr-1.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              Dateien auswählen
            </label>
            <span className="ml-3 text-xs text-gray-600">
              {selectedLocalFiles.length > 0
                ? `${selectedLocalFiles.length} Datei(en) ausgewählt`
                : 'Keine Dateien ausgewählt'}
            </span>
          </div>

          {/* Selected Files List */}
          {selectedLocalFiles.length > 0 && (
            <div className="space-y-3">
              <div className="max-h-48 overflow-y-auto border border-gray-200 rounded-md divide-y divide-gray-200">
                {selectedLocalFiles.map((file, index) => {
                  const supportStatus = getFileSupportStatus(file.name);
                  const config = FILE_TYPE_CONFIG[supportStatus];
                  const supported = isFileSupported(file.name);

                  return (
                    <div
                      key={index}
                      data-testid={`upload-file-${file.name}`}
                      className={`flex items-center space-x-2 px-3 py-2 ${
                        !supported ? 'opacity-60' : ''
                      }`}
                    >
                      {/* Support Status Indicator */}
                      <div
                        className={`w-1.5 h-1.5 rounded-full ${config.color}`}
                        title={config.description}
                      />

                      {/* File Name */}
                      <span className="flex-1 text-xs font-medium text-gray-900 truncate">
                        {file.name}
                      </span>

                      {/* Support Badge */}
                      <span
                        className={`px-1.5 py-0.5 text-xs font-medium rounded ${config.badgeColor}`}
                      >
                        {config.label}
                      </span>

                      {/* File Size */}
                      <span className="text-xs text-gray-500 w-14 text-right">
                        {formatFileSize(file.size)}
                      </span>

                      {/* Remove Button */}
                      <button
                        onClick={() => handleRemoveFile(index)}
                        disabled={isUploading}
                        className="text-red-600 hover:text-red-700 disabled:opacity-50"
                        aria-label="Datei entfernen"
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
                  );
                })}
              </div>

              {/* Upload Button */}
              <button
                data-testid="upload-files-button"
                onClick={handleUploadFiles}
                disabled={isUploading || selectedLocalFiles.length === 0}
                className="
                  px-4 py-2 rounded-md font-medium text-sm
                  bg-indigo-600 text-white
                  hover:bg-indigo-700
                  disabled:bg-gray-300 disabled:cursor-not-allowed
                  transition-all
                  flex items-center space-x-1.5
                "
              >
                {isUploading ? (
                  <>
                    <LoadingSpinner />
                    <span>Wird hochgeladen...</span>
                  </>
                ) : (
                  <>
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
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10"
                      />
                    </svg>
                    <span>Hochladen ({selectedLocalFiles.length} Datei{selectedLocalFiles.length !== 1 ? 'en' : ''})</span>
                  </>
                )}
              </button>
            </div>
          )}

          {/* Uploaded Files Summary */}
          {uploadedFiles.length > 0 && (
            <div
              data-testid="uploaded-files-summary"
              className="flex items-center space-x-2 p-3 bg-green-50 border border-green-200 rounded-md"
            >
              <SuccessIcon />
              <span className="text-xs font-medium text-green-800 flex-1">
                {uploadedFiles.length} Datei(en) erfolgreich hochgeladen und bereit zur
                Indizierung
              </span>
              <button
                onClick={handleClearUploads}
                className="text-xs text-green-700 hover:text-green-900 font-medium"
              >
                Zurücksetzen
              </button>
            </div>
          )}

          {/* Upload Error */}
          {uploadError && (
            <div
              data-testid="upload-error"
              className="flex items-center space-x-2 p-3 bg-red-50 border border-red-200 rounded-md"
            >
              <ErrorIcon />
              <span className="text-xs font-medium text-red-800">{uploadError}</span>
            </div>
          )}
        </div>

        {/* Directory Selection Section */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Option 2: Serververzeichnis scannen
          </h2>
          <p className="text-xs text-gray-600">
            Scannen Sie ein Verzeichnis auf dem Server nach Dokumenten. Ideal für große Mengen
            bereits vorhandener Dateien.
          </p>

          {/* Directory Input */}
          <div>
            <label
              htmlFor="directory-input"
              className="block text-xs font-medium text-gray-700 mb-1"
            >
              Verzeichnispfad
            </label>
            <div className="flex space-x-3">
              <input
                id="directory-input"
                data-testid="directory-input"
                type="text"
                value={directory}
                onChange={(e) => setDirectory(e.target.value)}
                placeholder="z.B. C:\Dokumente oder data/sample_documents"
                disabled={isIndexing || isScanning}
                className="
                  flex-1 px-3 py-2 text-sm rounded-md border border-gray-300
                  focus:ring-2 focus:ring-blue-500 focus:border-transparent
                  disabled:bg-gray-100 disabled:cursor-not-allowed
                  transition-all
                "
              />
              <button
                data-testid="scan-directory"
                onClick={handleScanDirectory}
                disabled={!directory.trim() || isIndexing || isScanning}
                className="
                  px-4 py-2 rounded-md font-medium text-sm
                  bg-blue-600 text-white
                  hover:bg-blue-700
                  disabled:bg-gray-300 disabled:cursor-not-allowed
                  transition-all
                  flex items-center space-x-1.5
                "
              >
                {isScanning ? (
                  <>
                    <LoadingSpinner />
                    <span>Scanne...</span>
                  </>
                ) : (
                  <span>Verzeichnis scannen</span>
                )}
              </button>
            </div>
          </div>

          {/* Recursive Checkbox */}
          <div className="flex items-center space-x-2">
            <input
              id="recursive-checkbox"
              data-testid="recursive-checkbox"
              type="checkbox"
              checked={recursive}
              onChange={(e) => setRecursive(e.target.checked)}
              disabled={isIndexing || isScanning}
              className="
                w-4 h-4 rounded border-gray-300 text-blue-600
                focus:ring-2 focus:ring-blue-500
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            />
            <label htmlFor="recursive-checkbox" className="text-sm text-gray-700">
              Unterverzeichnisse einbeziehen (rekursiv)
            </label>
          </div>

          {/* Scan Error */}
          {scanError && (
            <div
              data-testid="scan-error"
              className="flex items-center space-x-2 p-3 bg-red-50 border border-red-200 rounded-md"
            >
              <ErrorIcon />
              <span className="text-xs font-medium text-red-800">{scanError}</span>
            </div>
          )}
        </div>

        {/* File List Section (Sprint 33 Feature 33.2) */}
        {scanResult && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Schritt 2: Dateien auswählen
            </h2>

            {/* Statistics */}
            <div
              data-testid="scan-statistics"
              className="grid grid-cols-2 md:grid-cols-4 gap-2"
            >
              <StatCard
                label="Gesamt"
                value={scanResult.statistics.total}
                color="bg-gray-100"
              />
              <StatCard
                label="Docling"
                value={scanResult.statistics.docling_supported}
                color="bg-green-700"
                textColor="text-white"
              />
              <StatCard
                label="LlamaIndex"
                value={scanResult.statistics.llamaindex_supported}
                color="bg-green-400"
              />
              <StatCard
                label="Nicht unterstützt"
                value={scanResult.statistics.unsupported}
                color="bg-red-500"
                textColor="text-white"
              />
            </div>

            {/* Selection Buttons */}
            <div className="flex flex-wrap gap-2">
              <button
                data-testid="select-all"
                onClick={handleSelectAll}
                disabled={isIndexing}
                className="px-3 py-1.5 text-xs rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
              >
                Alle auswählen
              </button>
              <button
                data-testid="select-none"
                onClick={handleSelectNone}
                disabled={isIndexing}
                className="px-3 py-1.5 text-xs rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
              >
                Keine auswählen
              </button>
              <button
                data-testid="select-supported"
                onClick={handleSelectSupported}
                disabled={isIndexing}
                className="px-3 py-1.5 text-xs rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
              >
                Nur unterstützte
              </button>
              <span className="ml-auto text-xs text-gray-600 self-center">
                {selectedFiles.size} von {scanResult.files.length} ausgewählt
                ({selectedSupportedCount} unterstützt)
              </span>
            </div>

            {/* File List */}
            <div
              data-testid="file-list"
              className="max-h-64 overflow-y-auto border border-gray-200 rounded-md divide-y divide-gray-200"
            >
              {scanResult.files.map((file) => (
                <FileListItem
                  key={file.file_path}
                  file={file}
                  isSelected={selectedFiles.has(file.file_path)}
                  onToggle={() => handleToggleFile(file.file_path)}
                  disabled={isIndexing}
                />
              ))}
            </div>
          </div>
        )}

        {/* Indexing Section */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">
            {uploadedFiles.length > 0
              ? 'Schritt 2: Hochgeladene Dateien indizieren'
              : scanResult && selectedFiles.size > 0
              ? 'Schritt 3: Indizierung starten'
              : 'Indizierung starten'
            }
          </h2>

          {!scanResult && uploadedFiles.length === 0 && (
            <p className="text-xs text-gray-600">
              Laden Sie Dateien hoch oder geben Sie einen Verzeichnispfad ein, um zu beginnen.
            </p>
          )}

          {uploadedFiles.length > 0 && (
            <p className="text-xs text-gray-600">
              {uploadedFiles.length} Datei(en) hochgeladen und bereit zur Indizierung.
              Klicken Sie auf "Indizierung starten", um fortzufahren.
            </p>
          )}

          {/* Action Buttons */}
          <div className="flex space-x-3">
            <button
              data-testid="start-indexing"
              onClick={handleStartIndexing}
              disabled={
                isIndexing ||
                (uploadedFiles.length === 0 && !directory.trim()) ||
                (uploadedFiles.length === 0 && scanResult !== null && selectedSupportedCount === 0)
              }
              className="
                flex-1 px-4 py-2 rounded-md font-medium text-sm
                bg-blue-600 text-white
                hover:bg-blue-700
                disabled:bg-gray-300 disabled:cursor-not-allowed
                transition-all
                flex items-center justify-center space-x-1.5
              "
            >
              {isIndexing ? (
                <>
                  <LoadingSpinner />
                  <span>Indizierung läuft...</span>
                </>
              ) : uploadedFiles.length > 0 ? (
                <span>
                  Indizierung starten ({uploadedFiles.length} hochgeladene Datei
                  {uploadedFiles.length !== 1 ? 'en' : ''})
                </span>
              ) : scanResult ? (
                <span>
                  Indizierung starten ({selectedSupportedCount} Datei
                  {selectedSupportedCount !== 1 ? 'en' : ''})
                </span>
              ) : (
                <span>Indizierung starten</span>
              )}
            </button>

              {isIndexing && (
                <button
                  data-testid="cancel-indexing"
                  onClick={handleCancelIndexing}
                  className="
                    px-4 py-2 rounded-md font-medium text-sm
                    bg-red-600 text-white
                    hover:bg-red-700
                    transition-all
                  "
                >
                  Abbrechen
                </button>
              )}
            </div>

            {/* Sprint 37: Pipeline Progress Visualization */}
            {isIndexing && (
              <PipelineProgressVisualization
                progress={pipelineProgressData}
                isProcessing={isIndexing}
              />
            )}

            {/* Progress Display (Sprint 33 Feature 33.3) */}
            {isIndexing && progress && (
              <div className="space-y-3 pt-3 border-t border-gray-200">
                {/* Status Message with Error Button and Details Button */}
                <div className="flex items-center justify-between">
                  <div
                    data-testid="indexing-status"
                    className="text-xs font-medium text-gray-700"
                  >
                    {progress.message || 'Verarbeite...'}
                  </div>

                  <div className="flex items-center space-x-2">
                    {/* Sprint 33 Feature 33.5: Error Tracking Button */}
                    <ErrorTrackingButton errors={errors} onExportCSV={handleExportCSV} />

                    {/* Sprint 33 Feature 33.4: Details Button - Always enabled during indexing */}
                    <button
                      onClick={() => setIsDetailDialogOpen(true)}
                      className="
                        px-3 py-1.5 rounded-md font-medium text-xs
                        bg-indigo-600 text-white
                        hover:bg-indigo-700
                        transition-all
                      "
                    >
                      Details...
                    </button>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-600">Fortschritt</span>
                    <span data-testid="progress-percentage" className="font-semibold">
                      {percentage.toFixed(0)}%
                    </span>
                  </div>
                  <div
                    data-testid="progress-bar"
                    className="w-full h-2 bg-gray-200 rounded-full overflow-hidden"
                  >
                    <div
                      className={`
                        h-full transition-all duration-300 rounded-full
                        ${isComplete ? 'bg-green-500' : 'bg-blue-600'}
                      `}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>

                {/* Document Count */}
                {documentsTotal > 0 && (
                  <div data-testid="indexed-count" className="text-xs text-gray-600">
                    Dokumente: {documentsProcessed} / {documentsTotal}
                  </div>
                )}

                {/* Sprint 36: Chunk Progress during Entity/Relation Extraction */}
                {detailedProgress && detailedProgress.chunks_total !== undefined && detailedProgress.chunks_total > 0 && (
                  <div data-testid="chunk-progress" className="text-xs text-gray-600 flex items-center space-x-3">
                    <span>Chunks: {detailedProgress.chunks_processed || 0} / {detailedProgress.chunks_total}</span>
                    {detailedProgress.entities && (
                      <span className="text-indigo-600">
                        Entities: {detailedProgress.entities.total_entities} | Relations: {detailedProgress.entities.total_relations}
                      </span>
                    )}
                  </div>
                )}

                {/* Phase Badge */}
                {progress.phase && (
                  <div className="flex items-center space-x-2">
                    <PhaseBadge phase={progress.phase} />
                    {progress.current_document && (
                      <span className="text-xs text-gray-600 truncate max-w-xs">
                        {progress.current_document}
                      </span>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Success Message - Sprint 49 Feature 49.4: Status-based styling */}
            {isComplete && progress && !error && (
              <div
                data-testid="success-message"
                className={`flex items-center space-x-2 p-3 rounded-md ${
                  progress.failed_documents === undefined || progress.failed_documents === 0
                    ? 'bg-green-50 border border-green-200'
                    : progress.documents_processed === 0
                    ? 'bg-red-50 border border-red-200'
                    : 'bg-yellow-50 border border-yellow-200'
                }`}
              >
                {progress.failed_documents === undefined || progress.failed_documents === 0 ? (
                  <SuccessIcon />
                ) : progress.documents_processed === 0 ? (
                  <ErrorIcon />
                ) : (
                  <WarningIcon />
                )}
                <span className={`text-xs font-medium ${
                  progress.failed_documents === undefined || progress.failed_documents === 0
                    ? 'text-green-800'
                    : progress.documents_processed === 0
                    ? 'text-red-800'
                    : 'text-yellow-800'
                }`}>
                  {progress.message || 'Indizierung abgeschlossen'}
                </span>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div
                data-testid="error-message"
                className="flex items-center space-x-2 p-3 bg-red-50 border border-red-200 rounded-md"
              >
                <ErrorIcon />
                <span className="text-xs font-medium text-red-800">{error}</span>
              </div>
            )}

          {/* Progress History (Collapsible) */}
          {progressHistory.length > 0 && (
            <details className="mt-3">
              <summary className="cursor-pointer text-xs font-medium text-gray-700 hover:text-gray-900">
                Fortschritts-Log anzeigen ({progressHistory.length} Ereignisse)
              </summary>
              <div
                ref={progressLogRef}
                className="mt-2 max-h-48 overflow-y-auto space-y-0.5 text-xs font-mono bg-gray-50 rounded p-2"
              >
                {progressHistory.map((chunk, i) => (
                  <div key={i} className="text-gray-600">
                    <span className="text-gray-400">[{chunk.phase || 'unknown'}]</span>{' '}
                    {chunk.message}{' '}
                    {chunk.progress_percent
                      ? `(${chunk.progress_percent.toFixed(0)}%)`
                      : ''}
                  </div>
                ))}
              </div>
            </details>
          )}
        </div>

      </div>

      {/* Sprint 33 Feature 33.4: Detail Dialog */}
      <IndexingDetailDialog
        isOpen={isDetailDialogOpen}
        onClose={() => setIsDetailDialogOpen(false)}
        currentFile={detailedProgress?.current_file || null}
        progress={detailedProgress}
      />
    </div>
  );
}

// ============================================================================
// Utility Components
// ============================================================================

interface StatCardProps {
  label: string;
  value: number;
  color: string;
  textColor?: string;
}

function StatCard({ label, value, color, textColor = 'text-gray-900' }: StatCardProps) {
  return (
    <div className={`${color} rounded-md p-2`}>
      <div className={`text-lg font-bold ${textColor}`}>{value}</div>
      <div className={`text-xs ${textColor} opacity-80`}>{label}</div>
    </div>
  );
}

interface FileListItemProps {
  file: FileInfo;
  isSelected: boolean;
  onToggle: () => void;
  disabled: boolean;
}

function FileListItem({ file, isSelected, onToggle, disabled }: FileListItemProps) {
  const config = FILE_TYPE_CONFIG[file.parser_type];

  return (
    <div
      data-testid={`file-item-${file.file_name}`}
      className={`
        flex items-center space-x-2 px-3 py-1.5 hover:bg-gray-50
        ${!file.is_supported ? 'opacity-60' : ''}
        ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'}
      `}
      onClick={disabled ? undefined : onToggle}
    >
      <input
        type="checkbox"
        checked={isSelected}
        onChange={onToggle}
        disabled={disabled}
        className="w-3.5 h-3.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        onClick={(e) => e.stopPropagation()}
      />

      {/* Parser Type Indicator */}
      <div className={`w-1.5 h-1.5 rounded-full ${config.color}`} title={config.description} />

      {/* File Name */}
      <span className="flex-1 text-xs font-medium text-gray-900 truncate">
        {file.file_name}
      </span>

      {/* Parser Badge */}
      <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${config.badgeColor}`}>
        {config.label}
      </span>

      {/* File Size */}
      <span className="text-xs text-gray-500 w-14 text-right">
        {formatFileSize(file.file_size_bytes)}
      </span>
    </div>
  );
}

interface PhaseBadgeProps {
  phase: string;
}

function PhaseBadge({ phase }: PhaseBadgeProps) {
  const colors: Record<string, string> = {
    initialization: 'bg-blue-100 text-blue-700',
    deletion: 'bg-red-100 text-red-700',
    chunking: 'bg-yellow-100 text-yellow-700',
    embedding: 'bg-purple-100 text-purple-700',
    indexing: 'bg-indigo-100 text-indigo-700',
    validation: 'bg-green-100 text-green-700',
    completed: 'bg-green-100 text-green-700',
  };

  const colorClass = colors[phase] || 'bg-gray-100 text-gray-700';

  return (
    <span
      className={`
        px-2 py-0.5 rounded-full text-xs font-medium uppercase
        ${colorClass}
      `}
    >
      {phase}
    </span>
  );
}

function LoadingSpinner() {
  return (
    <svg
      className="w-4 h-4 animate-spin"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

function SuccessIcon() {
  return (
    <svg
      className="w-4 h-4 text-green-600 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 13l4 4L19 7"
      />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg
      className="w-4 h-4 text-red-600 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg
      className="w-4 h-4 text-yellow-600 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      />
    </svg>
  );
}

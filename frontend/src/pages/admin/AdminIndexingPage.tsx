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

import { useState, useCallback } from 'react';
import { scanDirectory, streamAddDocuments } from '../../api/admin';
import type {
  ReindexProgressChunk,
  ScanDirectoryResponse,
  FileInfo,
  DetailedProgress,
  IngestionError,
} from '../../types/admin';
import { IndexingDetailDialog } from '../../components/admin/IndexingDetailDialog';
import { ErrorTrackingButton } from '../../components/admin/ErrorTrackingButton';

// File type configuration for color coding
const FILE_TYPE_CONFIG = {
  docling: {
    color: 'bg-green-700',
    textColor: 'text-green-700',
    badgeColor: 'bg-green-700 text-white',
    label: 'Docling',
    description: 'GPU-accelerated OCR (optimal)',
  },
  llamaindex: {
    color: 'bg-green-400',
    textColor: 'text-green-600',
    badgeColor: 'bg-green-400 text-green-900',
    label: 'LlamaIndex',
    description: 'Fallback parser',
  },
  unsupported: {
    color: 'bg-red-500',
    textColor: 'text-red-500',
    badgeColor: 'bg-red-500 text-white',
    label: 'Nicht unterstützt',
    description: 'Wird übersprungen',
  },
};

// Helper function to format file size
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export function AdminIndexingPage() {
  // Form state
  const [directory, setDirectory] = useState('data/sample_documents');
  const [recursive, setRecursive] = useState(false);

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

  // Sprint 33 Feature 33.4: Detail Dialog state
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false);
  const [detailedProgress, setDetailedProgress] = useState<DetailedProgress | null>(null);

  // Sprint 33 Feature 33.5: Error Tracking state
  const [errors, setErrors] = useState<IngestionError[]>([]);

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
    // Validation
    if (!directory.trim()) {
      setError('Bitte geben Sie einen Verzeichnispfad ein');
      return;
    }

    if (selectedFiles.size === 0) {
      setError('Bitte wählen Sie mindestens eine Datei aus');
      return;
    }

    // Confirmation (ADD-only mode - no deletion warning)
    const confirmed = window.confirm(
      `${selectedFiles.size} Datei(en) werden zum Index hinzugefuegt.\n\n` +
        'Bestehende Dokumente bleiben erhalten.\n\n' +
        'Fortfahren?'
    );
    if (!confirmed) {
      return;
    }

    // Reset state
    setIsIndexing(true);
    setProgress(null);
    setProgressHistory([]);
    setError(null);
    setErrors([]); // Reset errors for new indexing run
    setDetailedProgress(null); // Reset detailed progress

    const controller = new AbortController();
    setAbortController(controller);

    // Get selected file paths as array
    const filePaths = Array.from(selectedFiles);

    try {
      for await (const chunk of streamAddDocuments(
        filePaths,
        false, // dry_run = false
        controller.signal
      )) {
        setProgress(chunk);
        setProgressHistory((prev) => [...prev, chunk]);

        // Sprint 33 Feature 33.6: Update detailed progress from SSE
        if (chunk.detailed_progress) {
          setDetailedProgress(chunk.detailed_progress);
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
  }, [directory, selectedFiles]);

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

  // Calculate selected files statistics
  const selectedSupportedCount = scanResult
    ? scanResult.files.filter((f) => selectedFiles.has(f.file_path) && f.is_supported).length
    : 0;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-8 px-6 space-y-8">
        {/* Header */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold text-gray-900">Document Indexing</h1>
          <p className="text-gray-600">
            Indizieren Sie Dokumente aus einem Verzeichnis in die Wissensdatenbank
          </p>
        </div>

        {/* Directory Selection Section */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-6">
          <h2 className="text-xl font-semibold text-gray-900">
            Schritt 1: Verzeichnis auswählen
          </h2>

          {/* Directory Input */}
          <div>
            <label
              htmlFor="directory-input"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Verzeichnispfad
            </label>
            <div className="flex space-x-4">
              <input
                id="directory-input"
                data-testid="directory-input"
                type="text"
                value={directory}
                onChange={(e) => setDirectory(e.target.value)}
                placeholder="z.B. C:\Dokumente oder data/sample_documents"
                disabled={isIndexing || isScanning}
                className="
                  flex-1 px-4 py-3 rounded-lg border border-gray-300
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
                  px-6 py-3 rounded-lg font-semibold
                  bg-blue-600 text-white
                  hover:bg-blue-700
                  disabled:bg-gray-300 disabled:cursor-not-allowed
                  transition-all
                  flex items-center space-x-2
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
          <div className="flex items-center space-x-3">
            <input
              id="recursive-checkbox"
              data-testid="recursive-checkbox"
              type="checkbox"
              checked={recursive}
              onChange={(e) => setRecursive(e.target.checked)}
              disabled={isIndexing || isScanning}
              className="
                w-5 h-5 rounded border-gray-300 text-blue-600
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
              className="flex items-center space-x-2 p-4 bg-red-50 border border-red-200 rounded-lg"
            >
              <ErrorIcon />
              <span className="text-sm font-medium text-red-800">{scanError}</span>
            </div>
          )}
        </div>

        {/* File List Section (Sprint 33 Feature 33.2) */}
        {scanResult && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-6">
            <h2 className="text-xl font-semibold text-gray-900">
              Schritt 2: Dateien auswählen
            </h2>

            {/* Statistics */}
            <div
              data-testid="scan-statistics"
              className="grid grid-cols-2 md:grid-cols-4 gap-4"
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
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
              >
                Alle auswählen
              </button>
              <button
                data-testid="select-none"
                onClick={handleSelectNone}
                disabled={isIndexing}
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
              >
                Keine auswählen
              </button>
              <button
                data-testid="select-supported"
                onClick={handleSelectSupported}
                disabled={isIndexing}
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
              >
                Nur unterstützte
              </button>
              <span className="ml-auto text-sm text-gray-600 self-center">
                {selectedFiles.size} von {scanResult.files.length} ausgewählt
                ({selectedSupportedCount} unterstützt)
              </span>
            </div>

            {/* File List */}
            <div
              data-testid="file-list"
              className="max-h-96 overflow-y-auto border border-gray-200 rounded-lg divide-y divide-gray-200"
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
        {scanResult && selectedFiles.size > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-6">
            <h2 className="text-xl font-semibold text-gray-900">
              Schritt 3: Indizierung starten
            </h2>

            {/* Action Buttons */}
            <div className="flex space-x-4">
              <button
                data-testid="start-indexing"
                onClick={handleStartIndexing}
                disabled={selectedSupportedCount === 0 || isIndexing}
                className="
                  flex-1 px-6 py-3 rounded-lg font-semibold
                  bg-blue-600 text-white
                  hover:bg-blue-700
                  disabled:bg-gray-300 disabled:cursor-not-allowed
                  transition-all
                  flex items-center justify-center space-x-2
                "
              >
                {isIndexing ? (
                  <>
                    <LoadingSpinner />
                    <span>Indizierung läuft...</span>
                  </>
                ) : (
                  <span>
                    Indizierung starten ({selectedSupportedCount} Datei
                    {selectedSupportedCount !== 1 ? 'en' : ''})
                  </span>
                )}
              </button>

              {isIndexing && (
                <button
                  data-testid="cancel-indexing"
                  onClick={handleCancelIndexing}
                  className="
                    px-6 py-3 rounded-lg font-semibold
                    bg-red-600 text-white
                    hover:bg-red-700
                    transition-all
                  "
                >
                  Abbrechen
                </button>
              )}
            </div>

            {/* Progress Display (Sprint 33 Feature 33.3) */}
            {isIndexing && progress && (
              <div className="space-y-4 pt-4 border-t border-gray-200">
                {/* Status Message with Error Button and Details Button */}
                <div className="flex items-center justify-between">
                  <div
                    data-testid="indexing-status"
                    className="text-sm font-medium text-gray-700"
                  >
                    {progress.message || 'Verarbeite...'}
                  </div>

                  <div className="flex items-center space-x-2">
                    {/* Sprint 33 Feature 33.5: Error Tracking Button */}
                    <ErrorTrackingButton errors={errors} onExportCSV={handleExportCSV} />

                    {/* Sprint 33 Feature 33.4: Details Button */}
                    <button
                      onClick={() => setIsDetailDialogOpen(true)}
                      disabled={!detailedProgress}
                      className="
                        px-4 py-2 rounded-lg font-semibold text-sm
                        bg-indigo-600 text-white
                        hover:bg-indigo-700
                        disabled:bg-gray-300 disabled:cursor-not-allowed
                        transition-all
                      "
                    >
                      Details...
                    </button>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Fortschritt</span>
                    <span data-testid="progress-percentage" className="font-semibold">
                      {percentage.toFixed(0)}%
                    </span>
                  </div>
                  <div
                    data-testid="progress-bar"
                    className="w-full h-3 bg-gray-200 rounded-full overflow-hidden"
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
                  <div data-testid="indexed-count" className="text-sm text-gray-600">
                    Dokumente: {documentsProcessed} / {documentsTotal}
                  </div>
                )}

                {/* Phase Badge */}
                {progress.phase && (
                  <div className="flex items-center space-x-2">
                    <PhaseBadge phase={progress.phase} />
                    {progress.current_document && (
                      <span className="text-sm text-gray-600 truncate">
                        {progress.current_document}
                      </span>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Success Message */}
            {isComplete && (
              <div
                data-testid="success-message"
                className="flex items-center space-x-2 p-4 bg-green-50 border border-green-200 rounded-lg"
              >
                <SuccessIcon />
                <span className="text-sm font-medium text-green-800">
                  Indizierung erfolgreich abgeschlossen! {documentsProcessed} Dokumente
                  verarbeitet.
                </span>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div
                data-testid="error-message"
                className="flex items-center space-x-2 p-4 bg-red-50 border border-red-200 rounded-lg"
              >
                <ErrorIcon />
                <span className="text-sm font-medium text-red-800">{error}</span>
              </div>
            )}

            {/* Progress History (Collapsible) */}
            {progressHistory.length > 0 && (
              <details className="mt-4">
                <summary className="cursor-pointer text-sm font-medium text-gray-700 hover:text-gray-900">
                  Fortschritts-Log anzeigen ({progressHistory.length} Ereignisse)
                </summary>
                <div className="mt-3 max-h-64 overflow-y-auto space-y-1 text-xs font-mono bg-gray-50 rounded-lg p-3">
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
        )}

        {/* Advanced Options (Optional - for future enhancements) */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <details>
            <summary
              data-testid="advanced-options"
              className="cursor-pointer text-lg font-semibold text-gray-900 hover:text-blue-600"
            >
              Erweiterte Optionen
            </summary>
            <div className="mt-4 space-y-4 text-sm text-gray-600">
              <p>Erweiterte Indizierungsoptionen werden in einer zukünftigen Version verfügbar sein.</p>
              <p>
                Aktuelle Einstellungen: BGE-M3 Embeddings, 1800-Token Chunks, Gemma-3-4B
                Extraktion
              </p>
            </div>
          </details>
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
    <div className={`${color} rounded-lg p-4`}>
      <div className={`text-2xl font-bold ${textColor}`}>{value}</div>
      <div className={`text-sm ${textColor} opacity-80`}>{label}</div>
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
        flex items-center space-x-3 px-4 py-3 hover:bg-gray-50
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
        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        onClick={(e) => e.stopPropagation()}
      />

      {/* Parser Type Indicator */}
      <div className={`w-2 h-2 rounded-full ${config.color}`} title={config.description} />

      {/* File Name */}
      <span className="flex-1 text-sm font-medium text-gray-900 truncate">
        {file.file_name}
      </span>

      {/* Parser Badge */}
      <span className={`px-2 py-0.5 text-xs font-semibold rounded ${config.badgeColor}`}>
        {config.label}
      </span>

      {/* File Size */}
      <span className="text-xs text-gray-500 w-16 text-right">
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
        px-3 py-1 rounded-full text-xs font-semibold uppercase
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
      className="w-5 h-5 animate-spin"
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
      className="w-5 h-5 text-green-600 flex-shrink-0"
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
      className="w-5 h-5 text-red-600 flex-shrink-0"
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

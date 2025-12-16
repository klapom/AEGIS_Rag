/**
 * DomainAutoDiscovery Component
 * Sprint 46 Feature 46.5: DomainAutoDiscovery Frontend Component
 *
 * Allows users to upload 1-3 sample documents to auto-generate
 * domain title and description using LLM analysis.
 */

import { useState, useRef, useCallback, type DragEvent, type ChangeEvent } from 'react';
import { Upload, FileText, X, Search, Check, AlertCircle, Loader2, Edit2 } from 'lucide-react';
import { formatFileSize } from '../../constants/fileSupport';

// ============================================================================
// Types
// ============================================================================

/**
 * Domain suggestion response from the API
 */
export interface DomainSuggestion {
  title: string;
  description: string;
  confidence: number;
  detected_topics: string[];
}

/**
 * Uploaded file info for display
 */
interface UploadedFile {
  file: File;
  name: string;
  size: number;
  extension: string;
}

/**
 * Props for the DomainAutoDiscovery component
 */
export interface DomainAutoDiscoveryProps {
  /** Callback when a domain suggestion is received */
  onDomainSuggested: (suggestion: DomainSuggestion) => void;
  /** Callback when user accepts the suggestion with optional edits */
  onAccept: (title: string, description: string) => void;
  /** Callback when user cancels the auto-discovery */
  onCancel: () => void;
}

// ============================================================================
// Constants
// ============================================================================

/** Supported file extensions for auto-discovery */
const SUPPORTED_EXTENSIONS = ['.txt', '.md', '.docx', '.html', '.htm'];

/** Maximum number of files allowed */
const MAX_FILES = 3;

/** Maximum file size in bytes (10 MB) */
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;

/** API base URL */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// ============================================================================
// Component
// ============================================================================

export function DomainAutoDiscovery({
  onDomainSuggested,
  onAccept,
  onCancel,
}: DomainAutoDiscoveryProps) {
  // File upload state
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Analysis state
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [suggestion, setSuggestion] = useState<DomainSuggestion | null>(null);

  // Editing state
  const [isEditing, setIsEditing] = useState(false);
  const [editedTitle, setEditedTitle] = useState('');
  const [editedDescription, setEditedDescription] = useState('');

  // ============================================================================
  // File Validation
  // ============================================================================

  /**
   * Validate a file for upload
   */
  const validateFile = useCallback((file: File): string | null => {
    const extension = file.name.toLowerCase().match(/\.[^.]+$/)?.[0] || '';

    if (!SUPPORTED_EXTENSIONS.includes(extension)) {
      return `Nicht unterstütztes Format: ${extension}. Unterstützt: ${SUPPORTED_EXTENSIONS.join(', ')}`;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      return `Datei zu groß: ${formatFileSize(file.size)}. Maximum: ${formatFileSize(MAX_FILE_SIZE_BYTES)}`;
    }

    return null;
  }, []);

  /**
   * Process files for upload
   */
  const processFiles = useCallback(
    (files: FileList | File[]) => {
      setUploadError(null);
      const fileArray = Array.from(files);

      // Check total file count
      const newTotal = uploadedFiles.length + fileArray.length;
      if (newTotal > MAX_FILES) {
        setUploadError(`Maximal ${MAX_FILES} Dateien erlaubt. Aktuell: ${uploadedFiles.length}`);
        return;
      }

      // Validate each file
      const validFiles: UploadedFile[] = [];
      for (const file of fileArray) {
        const error = validateFile(file);
        if (error) {
          setUploadError(error);
          return;
        }

        // Check for duplicates
        if (uploadedFiles.some((f) => f.name === file.name)) {
          setUploadError(`Datei bereits hochgeladen: ${file.name}`);
          return;
        }

        const extension = file.name.toLowerCase().match(/\.[^.]+$/)?.[0] || '';
        validFiles.push({
          file,
          name: file.name,
          size: file.size,
          extension,
        });
      }

      setUploadedFiles((prev) => [...prev, ...validFiles]);
      // Clear suggestion when files change
      setSuggestion(null);
      setIsEditing(false);
    },
    [uploadedFiles, validateFile]
  );

  // ============================================================================
  // Drag & Drop Handlers
  // ============================================================================

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        processFiles(files);
      }
    },
    [processFiles]
  );

  const handleFileInputChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        processFiles(files);
      }
      // Reset input so same file can be selected again
      e.target.value = '';
    },
    [processFiles]
  );

  const handleRemoveFile = useCallback((fileName: string) => {
    setUploadedFiles((prev) => prev.filter((f) => f.name !== fileName));
    setUploadError(null);
    setSuggestion(null);
    setIsEditing(false);
  }, []);

  const handleDropZoneClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  // ============================================================================
  // API Integration
  // ============================================================================

  /**
   * Analyze documents via API
   */
  const handleAnalyzeDocuments = useCallback(async () => {
    if (uploadedFiles.length === 0) {
      setAnalysisError('Bitte mindestens eine Datei hochladen.');
      return;
    }

    setIsAnalyzing(true);
    setAnalysisError(null);

    try {
      const formData = new FormData();
      for (const uploadedFile of uploadedFiles) {
        formData.append('files', uploadedFile.file);
      }

      const response = await fetch(`${API_BASE_URL}/api/v1/admin/domains/discover`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const result: DomainSuggestion = await response.json();
      setSuggestion(result);
      setEditedTitle(result.title);
      setEditedDescription(result.description);
      onDomainSuggested(result);
    } catch (error) {
      console.error('Domain discovery failed:', error);
      setAnalysisError(
        error instanceof Error ? error.message : 'Analyse fehlgeschlagen. Bitte erneut versuchen.'
      );
    } finally {
      setIsAnalyzing(false);
    }
  }, [uploadedFiles, onDomainSuggested]);

  // ============================================================================
  // Edit Handlers
  // ============================================================================

  const handleStartEditing = useCallback(() => {
    setIsEditing(true);
  }, []);

  const handleAcceptSuggestion = useCallback(() => {
    const title = isEditing ? editedTitle : suggestion?.title || '';
    const description = isEditing ? editedDescription : suggestion?.description || '';

    // Sanitize title: lowercase, replace spaces with underscore, remove invalid chars
    const sanitizedTitle = title
      .toLowerCase()
      .replace(/[\s-]+/g, '_')
      .replace(/[^a-z0-9_]/g, '');

    onAccept(sanitizedTitle, description);
  }, [isEditing, editedTitle, editedDescription, suggestion, onAccept]);

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="space-y-6" data-testid="domain-auto-discovery">
      {/* Header */}
      <div className="space-y-2">
        <p className="text-gray-600">
          Laden Sie 1-3 Beispieldokumente hoch, um automatisch einen Domain-Titel und eine
          Beschreibung zu generieren.
        </p>
      </div>

      {/* Drop Zone */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 transition-colors cursor-pointer ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleDropZoneClick}
        data-testid="drop-zone"
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            handleDropZoneClick();
          }
        }}
        aria-label="Dateien hochladen"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={SUPPORTED_EXTENSIONS.join(',')}
          multiple
          onChange={handleFileInputChange}
          className="hidden"
          data-testid="file-input"
          aria-label="Datei auswählen"
        />
        <div className="flex flex-col items-center text-center">
          <Upload
            className={`w-12 h-12 mb-4 ${isDragging ? 'text-blue-500' : 'text-gray-400'}`}
            aria-hidden="true"
          />
          <span className="text-lg font-medium text-gray-700">
            Dateien hier ablegen oder klicken zum Durchsuchen
          </span>
          <span className="text-sm text-gray-500 mt-2">
            Unterstützt: TXT, MD, DOCX, HTML
          </span>
          <span className="text-sm text-gray-500">
            Max. {MAX_FILES} Dateien, je {formatFileSize(MAX_FILE_SIZE_BYTES)}
          </span>
        </div>
      </div>

      {/* Upload Error */}
      {uploadError && (
        <div
          className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-lg"
          data-testid="upload-error"
          role="alert"
        >
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" aria-hidden="true" />
          <p className="text-sm text-red-800">{uploadError}</p>
        </div>
      )}

      {/* Uploaded Files List */}
      {uploadedFiles.length > 0 && (
        <div className="space-y-2" data-testid="uploaded-files">
          <h3 className="text-sm font-medium text-gray-700">Hochgeladen:</h3>
          <div className="space-y-2">
            {uploadedFiles.map((file) => (
              <div
                key={file.name}
                className="flex items-center justify-between p-3 bg-gray-50 border border-gray-200 rounded-lg"
                data-testid={`uploaded-file-${file.name}`}
              >
                <div className="flex items-center gap-3">
                  <Check className="w-5 h-5 text-green-500" aria-hidden="true" />
                  <FileText className="w-5 h-5 text-gray-400" aria-hidden="true" />
                  <span className="text-sm text-gray-900">{file.name}</span>
                  <span className="text-xs text-gray-500">({formatFileSize(file.size)})</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveFile(file.name);
                  }}
                  className="p-1 text-gray-400 hover:text-red-500 rounded"
                  aria-label={`${file.name} entfernen`}
                  data-testid={`remove-file-${file.name}`}
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Analyze Button */}
      {uploadedFiles.length > 0 && !suggestion && (
        <button
          onClick={handleAnalyzeDocuments}
          disabled={isAnalyzing}
          className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          data-testid="analyze-button"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" aria-hidden="true" />
              Analysiere Dokumente... (5-15 Sekunden)
            </>
          ) : (
            <>
              <Search className="w-5 h-5" aria-hidden="true" />
              Dokumente analysieren
            </>
          )}
        </button>
      )}

      {/* Analysis Error */}
      {analysisError && (
        <div
          className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-lg"
          data-testid="analysis-error"
          role="alert"
        >
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" aria-hidden="true" />
          <p className="text-sm text-red-800">{analysisError}</p>
        </div>
      )}

      {/* Suggestion Display */}
      {suggestion && (
        <div
          className="space-y-4 p-4 bg-gray-50 border border-gray-200 rounded-lg"
          data-testid="suggestion-panel"
        >
          <h3 className="text-lg font-semibold text-gray-900">Vorgeschlagene Domain:</h3>

          {/* Title */}
          <div>
            <label
              htmlFor="suggested-title"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Titel:
            </label>
            {isEditing ? (
              <input
                id="suggested-title"
                type="text"
                value={editedTitle}
                onChange={(e) => {
                  // Sanitize as user types
                  const sanitized = e.target.value
                    .toLowerCase()
                    .replace(/[\s-]+/g, '_')
                    .replace(/[^a-z0-9_]/g, '');
                  setEditedTitle(sanitized);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                data-testid="edit-title-input"
              />
            ) : (
              <p
                className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-gray-900"
                data-testid="suggested-title"
              >
                {suggestion.title}
              </p>
            )}
            {isEditing && (
              <p className="mt-1 text-xs text-gray-500">
                Kleinbuchstaben, Zahlen und Unterstriche erlaubt
              </p>
            )}
          </div>

          {/* Description */}
          <div>
            <label
              htmlFor="suggested-description"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Beschreibung:
            </label>
            {isEditing ? (
              <textarea
                id="suggested-description"
                value={editedDescription}
                onChange={(e) => setEditedDescription(e.target.value)}
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                data-testid="edit-description-input"
              />
            ) : (
              <p
                className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-gray-900 whitespace-pre-wrap"
                data-testid="suggested-description"
              >
                {suggestion.description}
              </p>
            )}
          </div>

          {/* Confidence & Topics */}
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">Konfidenz:</span>
              <ConfidenceIndicator confidence={suggestion.confidence} />
            </div>
            {suggestion.detected_topics.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-gray-700">Themen:</span>
                {suggestion.detected_topics.map((topic, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full"
                    data-testid={`topic-${idx}`}
                  >
                    {topic}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
            {!isEditing ? (
              <button
                onClick={handleStartEditing}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
                data-testid="edit-button"
              >
                <Edit2 className="w-4 h-4" aria-hidden="true" />
                Bearbeiten
              </button>
            ) : (
              <button
                onClick={() => {
                  setIsEditing(false);
                  setEditedTitle(suggestion.title);
                  setEditedDescription(suggestion.description);
                }}
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
                data-testid="cancel-edit-button"
              >
                Abbrechen
              </button>
            )}
            <button
              onClick={handleAcceptSuggestion}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              data-testid="accept-button"
            >
              <Check className="w-4 h-4" aria-hidden="true" />
              Akzeptieren & Domain erstellen
            </button>
          </div>
        </div>
      )}

      {/* Cancel Button (always visible at bottom) */}
      {!suggestion && (
        <div className="flex justify-end pt-4 border-t border-gray-200">
          <button
            onClick={onCancel}
            className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            data-testid="cancel-button"
          >
            Abbrechen
          </button>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Helper Components
// ============================================================================

interface ConfidenceIndicatorProps {
  confidence: number;
}

/**
 * Visual indicator for confidence score
 */
function ConfidenceIndicator({ confidence }: ConfidenceIndicatorProps) {
  const percentage = Math.round(confidence * 100);
  let colorClass: string;
  let label: string;

  if (confidence > 0.8) {
    colorClass = 'bg-green-100 text-green-800';
    label = 'Hoch';
  } else if (confidence > 0.5) {
    colorClass = 'bg-yellow-100 text-yellow-800';
    label = 'Mittel';
  } else {
    colorClass = 'bg-red-100 text-red-800';
    label = 'Niedrig';
  }

  return (
    <span
      className={`px-2 py-1 rounded text-xs font-semibold ${colorClass}`}
      data-testid="confidence-indicator"
      title={`Konfidenz: ${percentage}%`}
    >
      {label} ({percentage}%)
    </span>
  );
}

export default DomainAutoDiscovery;

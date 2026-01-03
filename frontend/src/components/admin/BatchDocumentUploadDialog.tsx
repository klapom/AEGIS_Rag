/**
 * BatchDocumentUploadDialog Component
 * Sprint 71 Feature 71.14: Batch Document Upload
 *
 * Dialog for uploading multiple documents to a domain for batch processing.
 * Integrates with IngestionJobList for progress tracking.
 */

import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, Folder, File, X, Loader2, AlertCircle } from 'lucide-react';
import { scanDirectory } from '../../api/admin';
import { useIngestBatch, type Domain } from '../../hooks/useDomainTraining';

interface BatchDocumentUploadDialogProps {
  domain: Domain;
  onClose: () => void;
}

export function BatchDocumentUploadDialog({ domain, onClose }: BatchDocumentUploadDialogProps) {
  const navigate = useNavigate();
  const [directoryPath, setDirectoryPath] = useState('');
  const [recursive, setRecursive] = useState(false);
  const [files, setFiles] = useState<string[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);

  const { mutateAsync: ingestBatch, isLoading: isIngesting, error: ingestError } = useIngestBatch();

  // Scan directory for files
  const handleScan = useCallback(async () => {
    if (!directoryPath.trim()) {
      setScanError('Please enter a directory path');
      return;
    }

    setIsScanning(true);
    setScanError(null);
    try {
      const result = await scanDirectory({ path: directoryPath, recursive });
      const filePaths = result.files.map((f) => f.file_path);
      setFiles(filePaths);
    } catch (err) {
      setScanError(err instanceof Error ? err.message : 'Failed to scan directory');
    } finally {
      setIsScanning(false);
    }
  }, [directoryPath, recursive]);

  // Start batch ingestion
  const handleUpload = useCallback(async () => {
    if (files.length === 0) {
      setScanError('No files to upload');
      return;
    }

    try {
      const result = await ingestBatch({
        domain_name: domain.name,
        file_paths: files,
        recursive,
      });

      // Redirect to ingestion jobs page with job_id
      navigate(`/admin/jobs?job_id=${result.job_id}`);
      onClose();
    } catch (err) {
      // Error is handled by hook
    }
  }, [files, domain.name, recursive, ingestBatch, navigate, onClose]);

  const error = scanError || ingestError?.message;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <Upload className="w-6 h-6 text-blue-600" />
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Upload Documents
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Domain: <span className="font-medium">{domain.name}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Info */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              <strong>Batch Upload</strong> allows you to upload multiple documents to this domain
              for processing. You'll be redirected to the Jobs page to monitor progress.
            </p>
          </div>

          {/* Directory Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Directory Path
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Folder className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  value={directoryPath}
                  onChange={(e) => setDirectoryPath(e.target.value)}
                  placeholder="/path/to/documents"
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={isScanning || isIngesting}
                  data-testid="directory-path-input"
                />
              </div>
              <button
                onClick={handleScan}
                disabled={isScanning || isIngesting}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                data-testid="scan-files-button"
              >
                {isScanning ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  'Scan'
                )}
              </button>
            </div>
          </div>

          {/* Recursive Checkbox */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="recursive"
              checked={recursive}
              onChange={(e) => setRecursive(e.target.checked)}
              disabled={isScanning || isIngesting}
              className="w-4 h-4 text-blue-600 bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500"
              data-testid="recursive-checkbox"
            />
            <label
              htmlFor="recursive"
              className="text-sm text-gray-700 dark:text-gray-300 cursor-pointer"
            >
              Scan subdirectories recursively
            </label>
          </div>

          {/* File List */}
          {files.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Found {files.length} file{files.length !== 1 ? 's' : ''}
              </p>
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 max-h-64 overflow-y-auto space-y-1">
                {files.map((file, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-sm">
                    <File className="w-4 h-4 text-gray-400 flex-shrink-0" />
                    <span className="text-gray-700 dark:text-gray-300 truncate">{file}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-800 dark:text-red-200">Error</p>
                <p className="text-sm text-red-600 dark:text-red-400 mt-1">{error}</p>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              onClick={handleUpload}
              disabled={files.length === 0 || isIngesting}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
              data-testid="upload-documents-button"
            >
              {isIngesting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Starting Ingestion...
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5" />
                  Upload {files.length} Document{files.length !== 1 ? 's' : ''}
                </>
              )}
            </button>
            <button
              onClick={onClose}
              disabled={isIngesting}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default BatchDocumentUploadDialog;

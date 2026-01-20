/**
 * GraphControls Component
 * Sprint 116 Feature 116.9: Graph controls for navigation and export
 *
 * Features:
 * - Zoom in/out buttons
 * - Fit to view button
 * - Reset view button
 * - Export as PNG button
 * - Fullscreen toggle
 */

interface GraphControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFit: () => void;
  onReset: () => void;
  onExportPNG: () => void;
  onFullscreen: () => void;
  isFullscreen: boolean;
}

export function GraphControls({
  onZoomIn,
  onZoomOut,
  onFit,
  onReset,
  onExportPNG,
  onFullscreen,
  isFullscreen,
}: GraphControlsProps) {
  return (
    <div className="bg-white/90 backdrop-blur-sm rounded-lg shadow-lg border border-gray-200 p-2 space-y-1" data-testid="graph-controls">
      {/* Zoom In */}
      <button
        onClick={onZoomIn}
        className="w-full p-2 text-gray-700 hover:bg-gray-100 rounded transition-colors flex items-center justify-center"
        title="Zoom In"
        data-testid="zoom-in-button"
        aria-label="Zoom in"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7" />
        </svg>
      </button>

      {/* Zoom Out */}
      <button
        onClick={onZoomOut}
        className="w-full p-2 text-gray-700 hover:bg-gray-100 rounded transition-colors flex items-center justify-center"
        title="Zoom Out"
        data-testid="zoom-out-button"
        aria-label="Zoom out"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
        </svg>
      </button>

      {/* Fit to View */}
      <button
        onClick={onFit}
        className="w-full p-2 text-gray-700 hover:bg-gray-100 rounded transition-colors flex items-center justify-center"
        title="Fit to View"
        data-testid="fit-button"
        aria-label="Fit to view"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
        </svg>
      </button>

      {/* Reset View */}
      <button
        onClick={onReset}
        className="w-full p-2 text-gray-700 hover:bg-gray-100 rounded transition-colors flex items-center justify-center"
        title="Reset View"
        data-testid="reset-button"
        aria-label="Reset view"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </button>

      <div className="border-t border-gray-200 my-1" />

      {/* Export PNG */}
      <button
        onClick={onExportPNG}
        className="w-full p-2 text-gray-700 hover:bg-gray-100 rounded transition-colors flex items-center justify-center"
        title="Export as PNG"
        data-testid="export-png-button"
        aria-label="Export as PNG"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
      </button>

      {/* Fullscreen Toggle */}
      <button
        onClick={onFullscreen}
        className="w-full p-2 text-gray-700 hover:bg-gray-100 rounded transition-colors flex items-center justify-center"
        title={isFullscreen ? 'Exit Fullscreen' : 'Enter Fullscreen'}
        data-testid="fullscreen-button"
        aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
      >
        {isFullscreen ? (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        )}
      </button>
    </div>
  );
}

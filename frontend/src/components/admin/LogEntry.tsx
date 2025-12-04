/**
 * LogEntry Component
 * Sprint 35 Feature 35.2: Admin Indexing Side-by-Side Layout
 *
 * Displays a single log entry with:
 * - Timestamp
 * - Color-coded log level (info, warning, error, success)
 * - Message
 * - Optional details
 */

export type LogLevel = 'info' | 'warning' | 'error' | 'success';

export interface LogEntryData {
  timestamp: string;
  level: LogLevel;
  message: string;
  details?: string;
}

interface LogEntryProps {
  entry: LogEntryData;
}

const LEVEL_COLORS: Record<LogLevel, string> = {
  info: 'text-gray-600',
  warning: 'text-yellow-600',
  error: 'text-red-600',
  success: 'text-green-600',
};

export function LogEntry({ entry }: LogEntryProps) {
  return (
    <div className={`${LEVEL_COLORS[entry.level]} py-0.5`} data-testid="log-entry">
      <span className="text-gray-400">[{entry.timestamp}]</span>
      <span className="ml-2">{entry.message}</span>
      {entry.details && (
        <span className="ml-2 text-gray-500 text-xs">- {entry.details}</span>
      )}
    </div>
  );
}

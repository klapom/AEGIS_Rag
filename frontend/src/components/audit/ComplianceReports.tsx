/**
 * ComplianceReports Component
 * Sprint 98 Feature 98.4: Audit Trail Viewer
 *
 * Generate and view compliance reports (GDPR Art. 30, Security).
 */

import { FileText, Download, Clock } from 'lucide-react';
import type { ComplianceReportType } from '../../types/audit';

interface ComplianceReportsProps {
  onGenerateReport: (reportType: ComplianceReportType, timeRange: string) => void;
}

export function ComplianceReports({ onGenerateReport }: ComplianceReportsProps) {
  const reportTypes: Array<{ type: ComplianceReportType; label: string; description: string }> = [
    {
      type: 'gdpr',
      label: 'GDPR Compliance Report (Art. 30)',
      description: 'Processing activities, consents, data subject rights requests',
    },
    {
      type: 'security',
      label: 'Security Report',
      description: 'Authentication failures, policy violations, suspicious activities',
    },
    {
      type: 'skill_usage',
      label: 'Skill Usage Report',
      description: 'Skill execution statistics, performance metrics',
    },
  ];

  const timeRanges = [
    { value: '24h', label: 'Last 24 Hours' },
    { value: '7d', label: 'Last 7 Days' },
    { value: '30d', label: 'Last 30 Days' },
    { value: '90d', label: 'Last 90 Days' },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Compliance Reports
        </h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {reportTypes.map((report) => (
          <div
            key={report.type}
            className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 space-y-3"
          >
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-gray-100">{report.label}</h4>
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                {report.description}
              </p>
            </div>
            <div>
              <label htmlFor={`${report.type}-range`} className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Time Range
              </label>
              <select
                id={`${report.type}-range`}
                className="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
              >
                {timeRanges.map((range) => (
                  <option key={range.value} value={range.value}>
                    {range.label}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={() => {
                const select = document.getElementById(`${report.type}-range`) as HTMLSelectElement;
                onGenerateReport(report.type, select?.value || '30d');
              }}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors"
            >
              <Download className="w-4 h-4" />
              Generate Report
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

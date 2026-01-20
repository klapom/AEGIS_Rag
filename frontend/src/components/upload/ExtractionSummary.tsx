/**
 * ExtractionSummary Component
 * Sprint 117 Feature 117.10: Upload Dialog Classification Display
 *
 * Displays extraction statistics after document upload.
 */

interface ExtractionSummaryProps {
  entitiesCount: number;
  relationsCount: number;
  chunksCount: number;
  mentionedInCount: number;
  className?: string;
}

/**
 * Component displaying extraction statistics.
 *
 * Shows bullet list of:
 * - Entities extracted
 * - Relations extracted
 * - Chunks created
 * - MENTIONED_IN relations
 *
 * @param entitiesCount - Number of entities extracted
 * @param relationsCount - Number of relations extracted
 * @param chunksCount - Number of chunks created
 * @param mentionedInCount - Number of MENTIONED_IN relations
 * @param className - Additional CSS classes
 */
export function ExtractionSummary({
  entitiesCount,
  relationsCount,
  chunksCount,
  mentionedInCount,
  className = '',
}: ExtractionSummaryProps) {
  return (
    <div className={`space-y-2 ${className}`} data-testid="extraction-summary">
      <h4 className="text-sm font-semibold text-gray-700">Extraction Summary</h4>
      <ul className="flex flex-wrap gap-4 text-sm text-gray-600">
        <li className="flex items-center gap-1">
          <span className="font-medium text-gray-900">{entitiesCount}</span> Entities
        </li>
        <li className="flex items-center gap-1">
          <span className="font-medium text-gray-900">{relationsCount}</span> Relations
        </li>
        <li className="flex items-center gap-1">
          <span className="font-medium text-gray-900">{chunksCount}</span> Chunks
        </li>
        <li className="flex items-center gap-1">
          <span className="font-medium text-gray-900">{mentionedInCount}</span> MENTIONED_IN
        </li>
      </ul>
    </div>
  );
}

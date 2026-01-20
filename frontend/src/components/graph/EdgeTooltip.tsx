/**
 * EdgeTooltip Component
 * Sprint 116 Feature 116.9: Edge hover tooltip for graph visualization
 *
 * Features:
 * - Show tooltip on edge hover
 * - Display relationship details (type, weight, properties)
 * - Position near mouse cursor
 * - 200ms delay before showing (handled by vis-network)
 */

import { useEffect, useState } from 'react';

interface EdgeTooltipProps {
  edgeLabel: string;
  weight?: number;
  properties?: Record<string, unknown>;
  x: number;
  y: number;
}

export function EdgeTooltip({ edgeLabel, weight, properties, x, y }: EdgeTooltipProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Small delay before showing tooltip for better UX
    const timer = setTimeout(() => setVisible(true), 200);
    return () => {
      clearTimeout(timer);
      setVisible(false);
    };
  }, [edgeLabel, x, y]);

  if (!visible) return null;

  return (
    <div
      className="absolute z-50 bg-gray-900 text-white text-sm rounded-lg shadow-lg px-3 py-2 pointer-events-none max-w-xs"
      style={{
        left: `${x + 10}px`,
        top: `${y + 10}px`,
      }}
      data-testid="edge-tooltip"
    >
      <div className="space-y-1">
        <div className="font-semibold">{edgeLabel}</div>
        {weight !== undefined && (
          <div className="text-xs text-gray-300">
            Weight: {Math.round(weight * 100)}%
          </div>
        )}
        {properties && Object.keys(properties).length > 0 && (
          <div className="text-xs text-gray-300 border-t border-gray-700 pt-1 mt-1">
            {Object.entries(properties).map(([key, value]) => (
              <div key={key}>
                <span className="font-medium">{key}:</span>{' '}
                {typeof value === 'object' ? JSON.stringify(value) : String(value)}
              </div>
            ))}
          </div>
        )}
      </div>
      {/* Arrow pointer */}
      <div
        className="absolute w-2 h-2 bg-gray-900 transform rotate-45"
        style={{
          left: '-4px',
          top: '8px',
        }}
      />
    </div>
  );
}

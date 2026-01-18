/**
 * TimeRangeSlider Component
 * Sprint 111 Feature 111.2: Token Usage Chart
 *
 * Time range selector with:
 * - Preset buttons (1d, 7d, 30d, 90d, 1y, 3y)
 * - Continuous slider for custom ranges
 */

import { useMemo } from 'react';
import { Calendar } from 'lucide-react';

export type TimeRangePreset = '1d' | '7d' | '30d' | '90d' | '1y' | '3y';

interface TimeRangeSliderProps {
  value: number; // Days
  onChange: (days: number) => void;
  minDays?: number;
  maxDays?: number;
  className?: string;
}

const PRESETS: { label: TimeRangePreset; days: number }[] = [
  { label: '1d', days: 1 },
  { label: '7d', days: 7 },
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
  { label: '1y', days: 365 },
  { label: '3y', days: 1095 },
];

export function TimeRangeSlider({
  value,
  onChange,
  minDays = 1,
  maxDays = 1095,
  className = '',
}: TimeRangeSliderProps) {
  // Format the display value
  const displayValue = useMemo(() => {
    if (value === 1) return '1 day';
    if (value < 30) return `${value} days`;
    if (value < 365) return `${Math.round(value / 30)} months`;
    return `${(value / 365).toFixed(1)} years`;
  }, [value]);

  // Calculate slider position (logarithmic scale for better UX)
  const sliderPosition = useMemo(() => {
    const minLog = Math.log(minDays);
    const maxLog = Math.log(maxDays);
    const valueLog = Math.log(value);
    return ((valueLog - minLog) / (maxLog - minLog)) * 100;
  }, [value, minDays, maxDays]);

  // Convert slider position to days
  const handleSliderChange = (position: number) => {
    const minLog = Math.log(minDays);
    const maxLog = Math.log(maxDays);
    const valueLog = minLog + (position / 100) * (maxLog - minLog);
    const newDays = Math.round(Math.exp(valueLog));
    onChange(Math.max(minDays, Math.min(maxDays, newDays)));
  };

  // Get date range for display
  const dateRange = useMemo(() => {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - value);
    return {
      start: startDate.toLocaleDateString(),
      end: endDate.toLocaleDateString(),
    };
  }, [value]);

  return (
    <div className={`space-y-3 ${className}`} data-testid="time-range-slider">
      {/* Preset Buttons */}
      <div className="flex flex-wrap gap-2" data-testid="time-range-presets">
        {PRESETS.map((preset) => (
          <button
            key={preset.label}
            onClick={() => onChange(preset.days)}
            className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
              value === preset.days
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
            data-testid={`preset-${preset.label}`}
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* Slider */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500 dark:text-gray-400">Time Range:</span>
          <span className="font-medium text-gray-900 dark:text-gray-100" data-testid="range-display">
            {displayValue}
          </span>
        </div>

        <input
          type="range"
          min="0"
          max="100"
          step="1"
          value={sliderPosition}
          onChange={(e) => handleSliderChange(Number(e.target.value))}
          className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
          data-testid="range-slider"
        />

        <div className="flex justify-between text-xs text-gray-400">
          <span>1 day</span>
          <span>3 years</span>
        </div>
      </div>

      {/* Date Range Display */}
      <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400" data-testid="date-range">
        <Calendar className="w-4 h-4" />
        <span>{dateRange.start}</span>
        <span>—</span>
        <span>{dateRange.end}</span>
      </div>
    </div>
  );
}

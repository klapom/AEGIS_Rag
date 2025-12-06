/**
 * WorkerConfigSlider Component
 * Sprint 37 Feature 37.7: Admin UI for Worker Pool Configuration
 *
 * Reusable slider component for worker pool configuration parameters
 */

import React from "react";

interface WorkerConfigSliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  description: string;
  onChange: (value: number) => void;
  testId: string;
  unit?: string;
  disabled?: boolean;
}

export const WorkerConfigSlider: React.FC<WorkerConfigSliderProps> = ({
  label,
  value,
  min,
  max,
  description,
  onChange,
  testId,
  unit = "",
  disabled = false,
}) => {
  const percentage = ((value - min) / (max - min)) * 100;

  return (
    <div className="space-y-2" data-testid={testId}>
      {/* Label and Current Value */}
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-gray-700">{label}</label>
        <span className="text-sm font-semibold text-blue-600">
          {value}
          {unit}
        </span>
      </div>

      {/* Slider */}
      <div className="relative">
        <input
          type="range"
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          disabled={disabled}
          className={`
            w-full h-2 rounded-lg appearance-none cursor-pointer
            ${disabled ? "opacity-50 cursor-not-allowed" : ""}
          `}
          style={{
            background: `linear-gradient(to right, #3B82F6 0%, #3B82F6 ${percentage}%, #E5E7EB ${percentage}%, #E5E7EB 100%)`,
          }}
          data-testid={`${testId}-slider`}
        />
      </div>

      {/* Min/Max Indicators */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>
          {min}
          {unit}
        </span>
        <span>
          {max}
          {unit}
        </span>
      </div>

      {/* Description */}
      <p className="text-xs text-gray-600">{description}</p>
    </div>
  );
};

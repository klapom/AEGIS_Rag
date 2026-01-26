/**
 * SkillActivationIndicator Component
 * Sprint 119 Feature 119.1: Skills/Tools Chat Integration
 *
 * Inline indicator showing when a skill is activated in the chat flow.
 * Displays skill name, icon, and reason for activation.
 */

import { CheckCircle, Zap } from 'lucide-react';
import type { SkillActivationEvent } from '../../types/skills-events';

interface SkillActivationIndicatorProps {
  /** Skill activation event data */
  event: SkillActivationEvent;
}

/**
 * Get icon for skill based on name (can be extended with skill metadata later)
 */
function getSkillIcon(skillName: string): string {
  // Default icons based on common skill patterns
  if (skillName.includes('bash') || skillName.includes('shell')) return '⌨️';
  if (skillName.includes('python') || skillName.includes('code')) return '🐍';
  if (skillName.includes('browser') || skillName.includes('web')) return '🌐';
  if (skillName.includes('search')) return '🔍';
  if (skillName.includes('file')) return '📁';
  if (skillName.includes('data')) return '📊';
  return '⚡'; // Default skill icon
}

/**
 * Format skill name for display (convert snake_case to Title Case)
 */
function formatSkillName(skillName: string): string {
  return skillName
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * SkillActivationIndicator displays an inline notification when a skill is activated
 */
export function SkillActivationIndicator({ event }: SkillActivationIndicatorProps) {
  const icon = getSkillIcon(event.skill);
  const displayName = formatSkillName(event.skill);

  return (
    <div
      className="my-3 px-4 py-3 bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg"
      data-testid={`skill-activated-${event.skill}`}
      data-skill={event.skill}
    >
      <div className="flex items-start gap-3">
        {/* Skill Icon */}
        <div className="flex-shrink-0 mt-0.5">
          <div className="w-8 h-8 flex items-center justify-center bg-white rounded-lg shadow-sm text-lg">
            {icon}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Zap className="w-4 h-4 text-blue-600" />
            <span className="text-sm font-semibold text-gray-900">
              Skill aktiviert
            </span>
            <CheckCircle className="w-4 h-4 text-green-600" />
          </div>

          <div className="text-sm text-gray-700">
            <span className="font-medium text-blue-700">{displayName}</span>
            {event.version && (
              <span className="ml-2 text-xs text-gray-500">v{event.version}</span>
            )}
          </div>

          {event.reason && (
            <div className="mt-1.5 text-xs text-gray-600 italic">
              {event.reason}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

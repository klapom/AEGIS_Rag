/**
 * BotAvatar Component
 * Sprint 35 Feature 35.1: Seamless Chat Flow
 *
 * Gradient teal-to-blue avatar with Bot icon for assistant messages
 */

import { Bot } from 'lucide-react';

export function BotAvatar() {
  return (
    <div
      className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-teal-400 to-blue-500 flex-shrink-0"
      data-testid="bot-avatar"
      aria-label="AegisRAG assistant avatar"
    >
      <Bot className="w-5 h-5 text-white" />
    </div>
  );
}

/**
 * UserAvatar Component
 * Sprint 35 Feature 35.1: Seamless Chat Flow
 *
 * Blue circle avatar with User icon for user messages
 */

import { User } from 'lucide-react';

export function UserAvatar() {
  return (
    <div
      className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-500 flex-shrink-0"
      data-testid="user-avatar"
      aria-label="User avatar"
    >
      <User className="w-5 h-5 text-white" />
    </div>
  );
}

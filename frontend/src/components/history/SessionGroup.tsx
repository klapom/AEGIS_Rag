/**
 * SessionGroup Component
 * Sprint 15 Feature 15.5: Group of sessions by date
 */

import type { SessionInfo } from '../../types/chat';
import { SessionItem } from './SessionItem';

interface SessionGroupProps {
  title: string;
  sessions: SessionInfo[];
  onDelete: (sessionId: string) => void;
}

export function SessionGroup({ title, sessions, onDelete }: SessionGroupProps) {
  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide px-2">
        {title}
      </h3>
      <div className="space-y-1">
        {sessions.map((session) => (
          <SessionItem
            key={session.session_id}
            session={session}
            onDelete={onDelete}
          />
        ))}
      </div>
    </div>
  );
}

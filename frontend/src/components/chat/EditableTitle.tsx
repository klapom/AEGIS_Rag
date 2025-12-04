/**
 * EditableTitle Component
 * Sprint 35 Feature 35.4: Auto-Generated Conversation Titles
 *
 * Displays and allows editing of conversation titles.
 * Supports both auto-generated and manually edited titles.
 */

import { useState, useRef, useEffect } from 'react';
import { Pencil, Check, X } from 'lucide-react';
import { updateConversationTitle } from '../../api/chat';

interface EditableTitleProps {
  sessionId: string;
  initialTitle: string | null;
  onTitleChange?: (newTitle: string) => void;
}

export function EditableTitle({
  sessionId,
  initialTitle,
  onTitleChange
}: EditableTitleProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [title, setTitle] = useState(initialTitle || 'New Conversation');
  const [editValue, setEditValue] = useState(title);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (initialTitle) setTitle(initialTitle);
  }, [initialTitle]);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleSave = async () => {
    if (editValue.trim() && editValue !== title) {
      try {
        await updateConversationTitle(sessionId, editValue.trim());
        setTitle(editValue.trim());
        onTitleChange?.(editValue.trim());
      } catch (error) {
        console.error('Failed to update title:', error);
        setEditValue(title); // Revert on error
      }
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditValue(title);
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSave();
    if (e.key === 'Escape') handleCancel();
  };

  if (isEditing) {
    return (
      <div className="flex items-center gap-1" data-testid="editable-title">
        <input
          ref={inputRef}
          type="text"
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onKeyDown={handleKeyDown}
          className="px-2 py-1 text-sm border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          maxLength={100}
          data-testid="title-input"
        />
        <button
          onClick={handleSave}
          className="p-1 text-green-600 hover:bg-green-50 rounded"
          data-testid="title-save"
        >
          <Check className="w-4 h-4" />
        </button>
        <button
          onClick={handleCancel}
          className="p-1 text-red-600 hover:bg-red-50 rounded"
          data-testid="title-cancel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <div
      className="flex items-center gap-2 group"
      data-testid="editable-title"
    >
      <span className="text-sm font-medium text-gray-700" data-testid="title-display">
        {title}
      </span>
      <button
        onClick={() => setIsEditing(true)}
        className="p-1 opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-gray-600 rounded"
        data-testid="title-edit"
      >
        <Pencil className="w-3 h-3" />
      </button>
    </div>
  );
}

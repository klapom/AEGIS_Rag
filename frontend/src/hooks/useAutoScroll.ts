/**
 * useAutoScroll Hook
 * Sprint 35 Feature 35.1: Seamless Chat Flow
 *
 * Automatically scrolls to bottom when new messages arrive.
 * Only scrolls if user is near the bottom (doesn't interrupt reading).
 */

import { useEffect, useRef } from 'react';

interface UseAutoScrollOptions {
  /**
   * Threshold in pixels from bottom to consider "near bottom"
   * Default: 100px
   */
  threshold?: number;
  /**
   * Enable smooth scrolling animation
   * Default: true
   */
  smooth?: boolean;
}

/**
 * Hook to automatically scroll to bottom of a container when content changes.
 * Returns a ref to attach to the scroll anchor element.
 *
 * @example
 * ```tsx
 * const messagesEndRef = useAutoScroll({ smooth: true });
 *
 * return (
 *   <div className="overflow-y-auto">
 *     {messages.map(msg => <Message key={msg.id} {...msg} />)}
 *     <div ref={messagesEndRef} />
 *   </div>
 * );
 * ```
 */
export function useAutoScroll(options: UseAutoScrollOptions = {}) {
  const { threshold = 100, smooth = true } = options;
  const endRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const scrollToBottom = () => {
      if (!endRef.current) return;

      // Find scrollable container (parent with overflow)
      if (!containerRef.current) {
        let parent = endRef.current.parentElement;
        while (parent) {
          const style = window.getComputedStyle(parent);
          if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
            containerRef.current = parent;
            break;
          }
          parent = parent.parentElement;
        }
      }

      const container = containerRef.current;
      if (!container) {
        // Fallback: scroll element into view
        endRef.current.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
        return;
      }

      // Check if user is near bottom
      const scrollTop = container.scrollTop;
      const scrollHeight = container.scrollHeight;
      const clientHeight = container.clientHeight;
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

      // Only auto-scroll if user is near bottom (don't interrupt reading)
      if (distanceFromBottom <= threshold) {
        endRef.current.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
      }
    };

    // Use setTimeout to ensure DOM has updated
    const timer = setTimeout(scrollToBottom, 100);
    return () => clearTimeout(timer);
  });

  return endRef;
}

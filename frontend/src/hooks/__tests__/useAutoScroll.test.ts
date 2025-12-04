/**
 * useAutoScroll Hook Tests
 * Sprint 35 Feature 35.1: Seamless Chat Flow
 *
 * Tests for automatic scroll-to-bottom behavior with smart threshold detection
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useAutoScroll } from '../useAutoScroll';

describe('useAutoScroll', () => {
  let scrollIntoViewMock: ReturnType<typeof vi.fn>;
  let getComputedStyleMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    // Use fake timers for all tests
    vi.useFakeTimers();

    // Mock scrollIntoView on Element prototype
    scrollIntoViewMock = vi.fn();
    Element.prototype.scrollIntoView = scrollIntoViewMock;

    // Mock getComputedStyle
    getComputedStyleMock = vi.fn().mockReturnValue({
      overflowY: 'visible',
    });
    window.getComputedStyle = getComputedStyleMock as any;

    // Clear all timers
    vi.clearAllTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllTimers();
    vi.clearAllMocks();
  });

  describe('Initialization', () => {
    it('should return a ref object', () => {
      const { result } = renderHook(() => useAutoScroll());
      expect(result.current).toBeDefined();
      expect(result.current.current).toBeNull();
    });

    it('should return a ref with correct type annotation', () => {
      const { result } = renderHook(() => useAutoScroll());
      expect(typeof result.current).toBe('object');
      expect(result.current).toHaveProperty('current');
    });

    it('should accept no options and use defaults', () => {
      const { result } = renderHook(() => useAutoScroll());
      expect(result.current).toBeDefined();
    });

    it('should accept options with threshold', () => {
      const { result } = renderHook(() => useAutoScroll({ threshold: 50 }));
      expect(result.current).toBeDefined();
    });

    it('should accept options with smooth scrolling disabled', () => {
      const { result } = renderHook(() => useAutoScroll({ smooth: false }));
      expect(result.current).toBeDefined();
    });

    it('should accept both threshold and smooth options', () => {
      const { result } = renderHook(() => useAutoScroll({ threshold: 200, smooth: false }));
      expect(result.current).toBeDefined();
    });
  });

  describe('Scroll Behavior', () => {
    it('should scroll to bottom when component mounts', () => {
      const { result } = renderHook(() => useAutoScroll());

      // Set up the ref with a mock element
      const mockElement = document.createElement('div');
      act(() => {
        result.current.current = mockElement;
      });

      // Fast-forward the setTimeout
      vi.advanceTimersByTime(100);

      // Should have called scrollIntoView (from the fallback path since no container found)
      expect(scrollIntoViewMock).toHaveBeenCalled();
    });

    it('should use smooth behavior by default', () => {
      const { result } = renderHook(() => useAutoScroll());

      const mockElement = document.createElement('div');
      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      expect(scrollIntoViewMock).toHaveBeenCalledWith({
        behavior: 'smooth',
      });
    });

    it('should use auto behavior when smooth is false', () => {
      const { result } = renderHook(() => useAutoScroll({ smooth: false }));

      const mockElement = document.createElement('div');
      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      expect(scrollIntoViewMock).toHaveBeenCalledWith({
        behavior: 'auto',
      });
    });

    it('should only scroll when user is near the bottom', () => {
      const { result } = renderHook(() => useAutoScroll({ threshold: 100 }));

      const mockElement = document.createElement('div');
      const mockContainer = document.createElement('div');

      // Mock container properties
      Object.defineProperty(mockContainer, 'scrollTop', { value: 0, writable: true });
      Object.defineProperty(mockContainer, 'scrollHeight', { value: 1000, writable: true });
      Object.defineProperty(mockContainer, 'clientHeight', { value: 500, writable: true });

      // Mock that container has overflow-y: auto
      getComputedStyleMock.mockReturnValue({ overflowY: 'auto' });

      // Add container as parent
      mockContainer.appendChild(mockElement);

      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      // User is at top (distance from bottom = 1000 - 0 - 500 = 500, which is > 100 threshold)
      // Should NOT scroll
      expect(scrollIntoViewMock).not.toHaveBeenCalled();
    });

    it('should scroll when user is near the bottom within threshold', () => {
      const { result } = renderHook(() => useAutoScroll({ threshold: 100 }));

      const mockElement = document.createElement('div');
      const mockContainer = document.createElement('div');

      // Mock container properties - user is near bottom
      Object.defineProperty(mockContainer, 'scrollTop', { value: 400, writable: true });
      Object.defineProperty(mockContainer, 'scrollHeight', { value: 1000, writable: true });
      Object.defineProperty(mockContainer, 'clientHeight', { value: 500, writable: true });

      // Mock that container has overflow-y: auto
      getComputedStyleMock.mockReturnValue({ overflowY: 'auto' });

      // Add container as parent
      mockContainer.appendChild(mockElement);

      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      // User is near bottom (distance from bottom = 1000 - 400 - 500 = 100, which is <= 100 threshold)
      // Should scroll
      expect(scrollIntoViewMock).toHaveBeenCalled();
    });

    it('should respect custom threshold values', () => {
      const { result } = renderHook(() => useAutoScroll({ threshold: 50 }));

      const mockElement = document.createElement('div');
      const mockContainer = document.createElement('div');

      // Mock container properties
      Object.defineProperty(mockContainer, 'scrollTop', { value: 450, writable: true });
      Object.defineProperty(mockContainer, 'scrollHeight', { value: 1000, writable: true });
      Object.defineProperty(mockContainer, 'clientHeight', { value: 500, writable: true });

      getComputedStyleMock.mockReturnValue({ overflowY: 'scroll' });
      mockContainer.appendChild(mockElement);

      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      // Distance from bottom = 1000 - 450 - 500 = 50, which is <= 50 threshold
      // Should scroll
      expect(scrollIntoViewMock).toHaveBeenCalled();
    });

    it('should not scroll when distance from bottom exceeds threshold', () => {
      const { result } = renderHook(() => useAutoScroll({ threshold: 50 }));

      const mockElement = document.createElement('div');
      const mockContainer = document.createElement('div');

      // Mock container properties
      Object.defineProperty(mockContainer, 'scrollTop', { value: 200, writable: true });
      Object.defineProperty(mockContainer, 'scrollHeight', { value: 1000, writable: true });
      Object.defineProperty(mockContainer, 'clientHeight', { value: 500, writable: true });

      getComputedStyleMock.mockReturnValue({ overflowY: 'auto' });
      mockContainer.appendChild(mockElement);

      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      // Distance from bottom = 1000 - 200 - 500 = 300, which is > 50 threshold
      // Should NOT scroll
      expect(scrollIntoViewMock).not.toHaveBeenCalled();
    });
  });

  describe('Container Detection', () => {
    it('should find scrollable parent with overflow-y auto', () => {
      const { result } = renderHook(() => useAutoScroll());

      const mockElement = document.createElement('div');
      const mockContainer = document.createElement('div');

      Object.defineProperty(mockContainer, 'scrollTop', { value: 0, writable: true });
      Object.defineProperty(mockContainer, 'scrollHeight', { value: 100, writable: true });
      Object.defineProperty(mockContainer, 'clientHeight', { value: 100, writable: true });

      getComputedStyleMock.mockReturnValue({ overflowY: 'auto' });
      mockContainer.appendChild(mockElement);

      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      // Should have found the container and called scrollIntoView
      expect(scrollIntoViewMock).toHaveBeenCalled();
    });

    it('should find scrollable parent with overflow-y scroll', () => {
      const { result } = renderHook(() => useAutoScroll());

      const mockElement = document.createElement('div');
      const mockContainer = document.createElement('div');

      Object.defineProperty(mockContainer, 'scrollTop', { value: 0, writable: true });
      Object.defineProperty(mockContainer, 'scrollHeight', { value: 100, writable: true });
      Object.defineProperty(mockContainer, 'clientHeight', { value: 100, writable: true });

      getComputedStyleMock.mockReturnValue({ overflowY: 'scroll' });
      mockContainer.appendChild(mockElement);

      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      expect(scrollIntoViewMock).toHaveBeenCalled();
    });

    it('should traverse multiple parent levels to find scrollable container', () => {
      const { result } = renderHook(() => useAutoScroll());

      const mockElement = document.createElement('div');
      const middleDiv = document.createElement('div');
      const scrollableContainer = document.createElement('div');

      Object.defineProperty(scrollableContainer, 'scrollTop', { value: 0, writable: true });
      Object.defineProperty(scrollableContainer, 'scrollHeight', { value: 100, writable: true });
      Object.defineProperty(scrollableContainer, 'clientHeight', { value: 100, writable: true });

      // Mock getComputedStyle to return different values based on element
      getComputedStyleMock.mockImplementation((elem: any) => {
        if (elem === scrollableContainer) {
          return { overflowY: 'auto' };
        }
        return { overflowY: 'visible' };
      });

      scrollableContainer.appendChild(middleDiv);
      middleDiv.appendChild(mockElement);

      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      expect(scrollIntoViewMock).toHaveBeenCalled();
    });

    it('should use fallback scrollIntoView when no scrollable container found', () => {
      const { result } = renderHook(() => useAutoScroll());

      const mockElement = document.createElement('div');

      // Mock that no container has overflow
      getComputedStyleMock.mockReturnValue({ overflowY: 'visible' });

      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      // Should still call scrollIntoView as fallback
      expect(scrollIntoViewMock).toHaveBeenCalled();
    });

    it('should cache the scrollable container after finding it', () => {
      const { result } = renderHook(() => useAutoScroll());

      const mockElement = document.createElement('div');
      const mockContainer = document.createElement('div');

      Object.defineProperty(mockContainer, 'scrollTop', { value: 0, writable: true });
      Object.defineProperty(mockContainer, 'scrollHeight', { value: 100, writable: true });
      Object.defineProperty(mockContainer, 'clientHeight', { value: 100, writable: true });

      getComputedStyleMock.mockReturnValue({ overflowY: 'auto' });
      mockContainer.appendChild(mockElement);

      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      const callCountAfterFirst = getComputedStyleMock.mock.calls.length;

      // Trigger the effect again (simulate dependency change)
      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      // getComputedStyle should have been called same number of times
      // because the container is cached (not traversed again)
      expect(getComputedStyleMock.mock.calls.length).toBe(callCountAfterFirst);
    });
  });

  describe('Null Ref Handling', () => {
    it('should handle null ref gracefully', () => {
      const { result } = renderHook(() => useAutoScroll());

      // Keep ref as null
      act(() => {
        result.current.current = null;
      });

      vi.advanceTimersByTime(100);

      // Should not throw and should not call scrollIntoView
      expect(scrollIntoViewMock).not.toHaveBeenCalled();
    });

    it('should not throw error when calling hook without attaching ref', () => {
      expect(() => {
        renderHook(() => useAutoScroll());
        vi.advanceTimersByTime(100);
      }).not.toThrow();
    });

    it('should handle rapid ref changes', () => {
      const { result } = renderHook(() => useAutoScroll());

      const elem1 = document.createElement('div');
      const elem2 = document.createElement('div');

      act(() => {
        result.current.current = elem1;
      });

      vi.advanceTimersByTime(50);

      act(() => {
        result.current.current = elem2;
      });

      vi.advanceTimersByTime(50);

      // Should handle without throwing
      expect(scrollIntoViewMock).toHaveBeenCalled();
    });
  });

  describe('Dependency and Timing', () => {
    it('should delay scroll by 100ms via setTimeout', () => {
      const { result } = renderHook(() => useAutoScroll());

      const mockElement = document.createElement('div');
      act(() => {
        result.current.current = mockElement;
      });

      // Should not have scrolled yet
      expect(scrollIntoViewMock).not.toHaveBeenCalled();

      // Advance 50ms - still not called
      vi.advanceTimersByTime(50);
      expect(scrollIntoViewMock).not.toHaveBeenCalled();

      // Advance 50ms more (total 100ms)
      vi.advanceTimersByTime(50);
      expect(scrollIntoViewMock).toHaveBeenCalled();
    });

    it('should clear timeout on unmount', () => {
      const { result, unmount } = renderHook(() => useAutoScroll());

      const mockElement = document.createElement('div');
      act(() => {
        result.current.current = mockElement;
      });

      // Unmount before timer completes
      unmount();

      vi.advanceTimersByTime(100);

      // Should not have called scrollIntoView
      expect(scrollIntoViewMock).not.toHaveBeenCalled();
    });

    it('should run effect on every render (no dependency array)', () => {
      const { result, rerender } = renderHook(() => useAutoScroll());

      const mockElement = document.createElement('div');
      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);
      const callCount = scrollIntoViewMock.mock.calls.length;

      // Rerender with same hook
      rerender();
      vi.advanceTimersByTime(100);

      // Should have been called again
      expect(scrollIntoViewMock.mock.calls.length).toBeGreaterThan(callCount);
    });

    it('should work correctly with multiple instances', () => {
      const { result: result1 } = renderHook(() => useAutoScroll());
      const { result: result2 } = renderHook(() => useAutoScroll());

      const elem1 = document.createElement('div');
      const elem2 = document.createElement('div');

      act(() => {
        result1.current.current = elem1;
        result2.current.current = elem2;
      });

      vi.advanceTimersByTime(100);

      // Both should have triggered scrollIntoView
      expect(scrollIntoViewMock).toHaveBeenCalledTimes(2);
    });
  });

  describe('Edge Cases', () => {
    it('should handle element with zero height container', () => {
      const { result } = renderHook(() => useAutoScroll());

      const mockElement = document.createElement('div');
      const mockContainer = document.createElement('div');

      Object.defineProperty(mockContainer, 'scrollTop', { value: 0, writable: true });
      Object.defineProperty(mockContainer, 'scrollHeight', { value: 0, writable: true });
      Object.defineProperty(mockContainer, 'clientHeight', { value: 0, writable: true });

      getComputedStyleMock.mockReturnValue({ overflowY: 'auto' });
      mockContainer.appendChild(mockElement);

      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      // Should not throw
      expect(scrollIntoViewMock).toHaveBeenCalled();
    });

    it('should handle negative scroll position values', () => {
      const { result } = renderHook(() => useAutoScroll({ threshold: 100 }));

      const mockElement = document.createElement('div');
      const mockContainer = document.createElement('div');

      // Negative scroll (shouldn't happen in practice but handle gracefully)
      // Use values where distance from bottom is within threshold despite negative scroll
      // Distance from bottom = 1000 - (-10) - 500 = 510 (> 100 threshold, so NO scroll)
      // Let's make it: scrollHeight=200, clientHeight=50, scrollTop=-10
      // Distance = 200 - (-10) - 50 = 160 (still > 100)
      // So use: scrollHeight=100, clientHeight=100, scrollTop=-10
      // Distance = 100 - (-10) - 100 = 10 (<= 100)
      Object.defineProperty(mockContainer, 'scrollTop', { value: -10, writable: true });
      Object.defineProperty(mockContainer, 'scrollHeight', { value: 100, writable: true });
      Object.defineProperty(mockContainer, 'clientHeight', { value: 80, writable: true });

      getComputedStyleMock.mockReturnValue({ overflowY: 'auto' });
      mockContainer.appendChild(mockElement);

      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      // Distance from bottom = 100 - (-10) - 80 = 30, which is <= 100
      // Should scroll
      expect(scrollIntoViewMock).toHaveBeenCalled();
    });

    it('should handle very large threshold values', () => {
      const { result } = renderHook(() => useAutoScroll({ threshold: 10000 }));

      const mockElement = document.createElement('div');
      const mockContainer = document.createElement('div');

      Object.defineProperty(mockContainer, 'scrollTop', { value: 0, writable: true });
      Object.defineProperty(mockContainer, 'scrollHeight', { value: 100, writable: true });
      Object.defineProperty(mockContainer, 'clientHeight', { value: 100, writable: true });

      getComputedStyleMock.mockReturnValue({ overflowY: 'auto' });
      mockContainer.appendChild(mockElement);

      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      // Even at top, should scroll because threshold is huge
      expect(scrollIntoViewMock).toHaveBeenCalled();
    });

    it('should handle threshold of 0', () => {
      const { result } = renderHook(() => useAutoScroll({ threshold: 0 }));

      const mockElement = document.createElement('div');
      const mockContainer = document.createElement('div');

      // User is exactly at bottom
      Object.defineProperty(mockContainer, 'scrollTop', { value: 400, writable: true });
      Object.defineProperty(mockContainer, 'scrollHeight', { value: 1000, writable: true });
      Object.defineProperty(mockContainer, 'clientHeight', { value: 600, writable: true });

      getComputedStyleMock.mockReturnValue({ overflowY: 'auto' });
      mockContainer.appendChild(mockElement);

      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      // Distance from bottom = 1000 - 400 - 600 = 0, which is <= 0
      expect(scrollIntoViewMock).toHaveBeenCalled();
    });

    it('should work with document.body as scrollable parent', () => {
      const { result } = renderHook(() => useAutoScroll());

      const mockElement = document.createElement('div');
      document.body.appendChild(mockElement);

      // Mock getComputedStyle to return overflowY for body element
      getComputedStyleMock.mockImplementation((elem: any) => {
        if (elem === document.body) {
          return { overflowY: 'auto' };
        }
        return { overflowY: 'visible' };
      });

      // User is near bottom: distance = 5000 - 4900 - 800 = -700 (<= 100)
      Object.defineProperty(document.body, 'scrollTop', { value: 4900, writable: true });
      Object.defineProperty(document.body, 'scrollHeight', { value: 5000, writable: true });
      Object.defineProperty(document.body, 'clientHeight', { value: 800, writable: true });

      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      expect(scrollIntoViewMock).toHaveBeenCalled();

      document.body.removeChild(mockElement);
    });
  });

  describe('Scroll Behavior Options', () => {
    it('should pass correct options to scrollIntoView with smooth true', () => {
      const { result } = renderHook(() => useAutoScroll({ smooth: true }));

      const mockElement = document.createElement('div');
      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      expect(scrollIntoViewMock).toHaveBeenCalledWith({ behavior: 'smooth' });
    });

    it('should pass correct options to scrollIntoView with smooth false', () => {
      const { result } = renderHook(() => useAutoScroll({ smooth: false }));

      const mockElement = document.createElement('div');
      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      expect(scrollIntoViewMock).toHaveBeenCalledWith({ behavior: 'auto' });
    });

    it('should default smooth to true when not specified', () => {
      const { result } = renderHook(() => useAutoScroll({}));

      const mockElement = document.createElement('div');
      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      expect(scrollIntoViewMock).toHaveBeenCalledWith({ behavior: 'smooth' });
    });

    it('should default threshold to 100 when not specified', () => {
      const { result } = renderHook(() => useAutoScroll({ smooth: false }));

      const mockElement = document.createElement('div');
      const mockContainer = document.createElement('div');

      // User at exactly 100px from bottom
      Object.defineProperty(mockContainer, 'scrollTop', { value: 400, writable: true });
      Object.defineProperty(mockContainer, 'scrollHeight', { value: 1000, writable: true });
      Object.defineProperty(mockContainer, 'clientHeight', { value: 500, writable: true });

      getComputedStyleMock.mockReturnValue({ overflowY: 'auto' });
      mockContainer.appendChild(mockElement);

      act(() => {
        result.current.current = mockElement;
      });

      vi.advanceTimersByTime(100);

      // Distance from bottom = 1000 - 400 - 500 = 100, which is <= 100 (default)
      expect(scrollIntoViewMock).toHaveBeenCalled();
    });
  });

  describe('Real-world Scenarios', () => {
    it('should handle chat message stream scenario', () => {
      const { result } = renderHook(() => useAutoScroll({ smooth: true, threshold: 50 }));

      const mockContainer = document.createElement('div');
      const mockMessages = document.createElement('div');
      const mockAnchor = document.createElement('div');

      Object.defineProperty(mockContainer, 'scrollTop', { value: 3900, writable: true });
      Object.defineProperty(mockContainer, 'scrollHeight', { value: 4000, writable: true });
      Object.defineProperty(mockContainer, 'clientHeight', { value: 800, writable: true });

      getComputedStyleMock.mockReturnValue({ overflowY: 'auto' });

      mockContainer.appendChild(mockMessages);
      mockMessages.appendChild(mockAnchor);

      act(() => {
        result.current.current = mockAnchor;
      });

      vi.advanceTimersByTime(100);

      // User is near bottom (distance = 4000 - 3900 - 800 = -700, which is <= 50)
      expect(scrollIntoViewMock).toHaveBeenCalledWith({ behavior: 'smooth' });
    });

    it('should not interrupt reading when user scrolls up', () => {
      const { result } = renderHook(() => useAutoScroll({ threshold: 100 }));

      const mockContainer = document.createElement('div');
      const mockAnchor = document.createElement('div');

      // User scrolled up to read earlier messages
      Object.defineProperty(mockContainer, 'scrollTop', { value: 1000, writable: true });
      Object.defineProperty(mockContainer, 'scrollHeight', { value: 4000, writable: true });
      Object.defineProperty(mockContainer, 'clientHeight', { value: 800, writable: true });

      getComputedStyleMock.mockReturnValue({ overflowY: 'auto' });

      mockContainer.appendChild(mockAnchor);

      act(() => {
        result.current.current = mockAnchor;
      });

      vi.advanceTimersByTime(100);

      // User is far from bottom (distance = 4000 - 1000 - 800 = 2200 > 100)
      expect(scrollIntoViewMock).not.toHaveBeenCalled();
    });

    it('should handle rapid message additions', () => {
      const { result } = renderHook(() => useAutoScroll());

      const mockElement = document.createElement('div');

      act(() => {
        result.current.current = mockElement;
      });

      // Simulate rapid messages by advancing timer multiple times
      for (let i = 0; i < 5; i++) {
        vi.advanceTimersByTime(100);
        // In real scenario, new message would be added and ref reassigned
      }

      // Should handle without throwing
      expect(scrollIntoViewMock).toHaveBeenCalled();
    });
  });
});

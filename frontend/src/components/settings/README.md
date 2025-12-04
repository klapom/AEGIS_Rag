# Dark Mode Settings Components

Sprint 35 Feature 35.7: Dark Mode Preparation

## Overview

This directory contains components for managing dark mode theme settings in the AegisRAG frontend. The implementation provides a foundation for dark mode support with full component integration planned for Sprint 36.

## Components

### ThemeToggle

A flexible theme toggle component that can be rendered as a button or switch.

**Props:**
- `className?: string` - Optional CSS class name
- `showLabel?: boolean` - Show label text next to icon (default: false)
- `variant?: 'button' | 'switch'` - Component style variant (default: 'button')

**Usage:**

```tsx
import { ThemeToggle } from '@/components/settings';

// Simple icon button (header/toolbar)
<ThemeToggle />

// Button with label text
<ThemeToggle showLabel />

// Switch variant (settings page)
<ThemeToggle variant="switch" showLabel />
```

### ThemeToggleIcon

Standalone icon-only theme toggle for use in headers or toolbars.

**Props:**
- `className?: string` - Optional CSS class name

**Usage:**

```tsx
import { ThemeToggleIcon } from '@/components/settings';

<ThemeToggleIcon className="ml-4" />
```

## Related Files

### useDarkMode Hook

Location: `/src/hooks/useDarkMode.ts`

Custom React hook for managing dark mode state with:
- localStorage persistence
- System preference detection (prefers-color-scheme)
- Automatic document class management

**API:**

```tsx
interface UseDarkModeReturn {
  isDark: boolean;      // Current dark mode state
  toggle: () => void;   // Toggle dark/light mode
  setDark: (value: boolean) => void;  // Set explicitly
}
```

**Usage:**

```tsx
import { useDarkMode } from '@/hooks';

function MyComponent() {
  const { isDark, toggle, setDark } = useDarkMode();

  return (
    <div>
      <p>Current mode: {isDark ? 'Dark' : 'Light'}</p>
      <button onClick={toggle}>Toggle Theme</button>
      <button onClick={() => setDark(true)}>Force Dark</button>
      <button onClick={() => setDark(false)}>Force Light</button>
    </div>
  );
}
```

## CSS Custom Properties

Location: `/src/index.css`

The dark mode implementation uses CSS custom properties for theming:

### Background Colors
- `--bg-primary` - Main background color
- `--bg-secondary` - Secondary background (cards, panels)
- `--bg-tertiary` - Tertiary background (hover states)
- `--bg-hover` - Hover state background

### Text Colors
- `--text-primary` - Primary text color
- `--text-secondary` - Secondary text (muted)
- `--text-tertiary` - Tertiary text (very muted)
- `--text-inverse` - Inverse text color

### Border Colors
- `--border-primary` - Primary border color
- `--border-secondary` - Secondary border color
- `--border-focus` - Focus state border color

### Accent Colors
- `--accent-primary` - Primary accent color
- `--accent-hover` - Accent hover state
- `--accent-light` - Light accent variant

### Status Colors
- `--status-success` - Success state color
- `--status-warning` - Warning state color
- `--status-error` - Error state color
- `--status-info` - Info state color

## Tailwind Configuration

Location: `/tailwind.config.js`

Dark mode is configured with class-based strategy:

```js
export default {
  darkMode: 'class',  // Enable class-based dark mode
  theme: {
    extend: {
      colors: {
        // Dark mode specific colors
        dark: {
          bg: {
            primary: '#111827',
            secondary: '#1F2937',
            tertiary: '#374151',
          },
          text: {
            primary: '#F9FAFB',
            secondary: '#9CA3AF',
            tertiary: '#6B7280',
          },
          border: '#374151',
        },
      },
    },
  },
}
```

## Usage in Components

To prepare components for dark mode (Sprint 36), use Tailwind's dark mode utilities:

```tsx
// Example component with dark mode support
export function Card({ children }) {
  return (
    <div className="
      bg-white dark:bg-dark-bg-secondary
      text-gray-900 dark:text-dark-text-primary
      border border-gray-200 dark:border-dark-border
    ">
      {children}
    </div>
  );
}
```

Or use CSS custom properties for more flexibility:

```tsx
export function Card({ children }) {
  return (
    <div style={{
      backgroundColor: 'var(--bg-secondary)',
      color: 'var(--text-primary)',
      borderColor: 'var(--border-primary)',
    }}>
      {children}
    </div>
  );
}
```

## Testing

### Hook Tests
Location: `/src/hooks/__tests__/useDarkMode.test.ts`

- 13 comprehensive tests covering:
  - Initialization (localStorage, system preference)
  - Toggle functionality
  - Explicit setDark() calls
  - System preference tracking
  - Persistence across hook instances

### Component Tests
Location: `/src/components/settings/__tests__/ThemeToggle.test.tsx`

- 22 comprehensive tests covering:
  - Button variant rendering
  - Switch variant rendering
  - Icon-only variant
  - Label display
  - Toggle interactions
  - Accessibility (ARIA labels, keyboard navigation)

### Running Tests

```bash
# Run all dark mode tests
npm test -- useDarkMode

# Run hook tests
npm test -- useDarkMode.test.ts

# Run component tests
npm test -- ThemeToggle.test.tsx
```

## Implementation Status

### Completed (Sprint 35.7)
- ✅ Tailwind dark mode configuration
- ✅ CSS custom properties for theming
- ✅ useDarkMode hook with localStorage + system preference
- ✅ ThemeToggle component (button + switch variants)
- ✅ ThemeToggleIcon component
- ✅ Comprehensive test coverage (35 tests total)
- ✅ TypeScript type definitions
- ✅ Accessibility features (ARIA labels, keyboard nav)

### Planned (Sprint 36)
- ⏳ Update all components with dark mode styles
- ⏳ Add dark mode to chat interface
- ⏳ Add dark mode to graph visualization
- ⏳ Add dark mode to admin pages
- ⏳ Add dark mode to settings pages
- ⏳ Dark mode documentation screenshots

## Accessibility

The theme toggle components follow WCAG 2.1 AA guidelines:

- **Keyboard Navigation:** All toggles are keyboard accessible
- **Focus Indicators:** Visible focus rings on all interactive elements
- **ARIA Labels:** Proper aria-label and aria-checked attributes
- **Screen Reader Support:** Descriptive labels for assistive technology
- **Color Contrast:** All color combinations meet 4.5:1 contrast ratio

## Performance

The dark mode implementation is optimized for performance:

- **CSS Transitions:** Smooth 0.2s transitions for theme changes
- **No Re-renders:** Hook uses useEffect to minimize component re-renders
- **localStorage Caching:** Theme preference is cached to avoid flicker
- **System Preference Sync:** Automatically updates when system preference changes

## Browser Support

Dark mode works in all modern browsers:

- Chrome/Edge: Full support (including system preference)
- Firefox: Full support (including system preference)
- Safari: Full support (including system preference)
- Opera: Full support (including system preference)

## Migration Guide (Sprint 36)

When updating components to support dark mode:

1. **Use Tailwind dark utilities:**
   ```tsx
   className="bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
   ```

2. **Or use CSS custom properties:**
   ```tsx
   style={{ backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)' }}
   ```

3. **Test both modes:**
   - Verify colors in light mode
   - Verify colors in dark mode
   - Check contrast ratios

4. **Add data-testid for E2E tests:**
   ```tsx
   data-testid="theme-toggle-button"
   ```

## Resources

- [Tailwind CSS Dark Mode](https://tailwindcss.com/docs/dark-mode)
- [MDN: prefers-color-scheme](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-color-scheme)
- [WCAG 2.1 Contrast Guidelines](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)

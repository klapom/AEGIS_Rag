/**
 * Dark Mode Integration Examples
 * Sprint 35 Feature 35.7: Dark Mode Preparation
 *
 * This file contains examples showing how to integrate dark mode
 * into your components for Sprint 36 migration.
 *
 * DO NOT IMPORT THIS FILE IN PRODUCTION CODE.
 * This is for documentation purposes only.
 */

import { ThemeToggle, ThemeToggleIcon } from './ThemeToggle';
import { useDarkMode } from '../../hooks/useDarkMode';

/**
 * Example 1: Simple Header with Theme Toggle Icon
 */
export function ExampleHeader() {
  return (
    <header className="flex items-center justify-between p-4 bg-white dark:bg-dark-bg-secondary border-b border-gray-200 dark:border-dark-border">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-dark-text-primary">
        AegisRAG
      </h1>
      <div className="flex items-center gap-4">
        {/* Icon-only toggle for headers */}
        <ThemeToggleIcon />
        <button className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary">
          Settings
        </button>
      </div>
    </header>
  );
}

/**
 * Example 2: Settings Page with Switch Toggle
 */
export function ExampleSettings() {
  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6" style={{ color: 'var(--text-primary)' }}>
        Settings
      </h1>

      <div className="bg-white dark:bg-dark-bg-secondary rounded-lg border border-gray-200 dark:border-dark-border p-6 space-y-6">
        {/* Appearance Section */}
        <div>
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
            Appearance
          </h2>

          {/* Theme Toggle as Switch */}
          <ThemeToggle variant="switch" showLabel />
        </div>

        {/* Other Settings */}
        <div className="pt-6 border-t border-gray-200 dark:border-dark-border">
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
            Notifications
          </h2>
          {/* More settings... */}
        </div>
      </div>
    </div>
  );
}

/**
 * Example 3: Card Component with Dark Mode Support
 */
export function ExampleCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="
      bg-white dark:bg-dark-bg-secondary
      border border-gray-200 dark:border-dark-border
      rounded-lg p-6 shadow-sm
      hover:shadow-md transition-shadow
    ">
      <h3 className="text-xl font-semibold mb-3 text-gray-900 dark:text-dark-text-primary">
        {title}
      </h3>
      <div className="text-gray-600 dark:text-dark-text-secondary">
        {children}
      </div>
    </div>
  );
}

/**
 * Example 4: Using CSS Variables for Dynamic Styling
 */
export function ExampleDynamicCard() {
  return (
    <div
      style={{
        backgroundColor: 'var(--bg-secondary)',
        borderColor: 'var(--border-primary)',
        color: 'var(--text-primary)',
        padding: '1.5rem',
        borderRadius: '0.5rem',
        borderWidth: '1px',
        borderStyle: 'solid',
      }}
    >
      <h3 style={{ color: 'var(--accent-primary)', marginBottom: '1rem' }}>
        Dynamic Theming
      </h3>
      <p style={{ color: 'var(--text-secondary)' }}>
        This card uses CSS custom properties for theming.
        Colors automatically update when dark mode is toggled.
      </p>
    </div>
  );
}

/**
 * Example 5: Conditional Rendering Based on Theme
 */
export function ExampleConditionalContent() {
  const { isDark } = useDarkMode();

  return (
    <div className="p-6">
      {isDark ? (
        <img src="/logo-dark.svg" alt="Logo" className="h-8" />
      ) : (
        <img src="/logo-light.svg" alt="Logo" className="h-8" />
      )}

      <div className="mt-4">
        <p style={{ color: 'var(--text-secondary)' }}>
          Current theme: {isDark ? 'Dark' : 'Light'}
        </p>
      </div>
    </div>
  );
}

/**
 * Example 6: Status Badges with Theme Support
 */
export function ExampleStatusBadge({ status }: { status: 'success' | 'warning' | 'error' | 'info' }) {
  const statusStyles = {
    success: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300',
    warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300',
    error: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300',
    info: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300',
  };

  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusStyles[status]}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

/**
 * Example 7: Button with Dark Mode Variants
 */
export function ExampleButton({ children, variant = 'primary' }: {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary';
}) {
  if (variant === 'primary') {
    return (
      <button className="
        px-4 py-2 rounded-lg font-medium
        bg-primary hover:bg-primary-hover dark:bg-primary-dark
        text-white
        transition-colors
        focus:outline-none focus:ring-2 focus:ring-primary dark:focus:ring-primary-dark
      ">
        {children}
      </button>
    );
  }

  return (
    <button className="
      px-4 py-2 rounded-lg font-medium
      bg-gray-100 hover:bg-gray-200 dark:bg-dark-bg-tertiary dark:hover:bg-gray-700
      text-gray-900 dark:text-dark-text-primary
      transition-colors
      focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-gray-600
    ">
      {children}
    </button>
  );
}

/**
 * Example 8: Form Input with Dark Mode
 */
export function ExampleInput({ label, placeholder }: { label: string; placeholder?: string }) {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700 dark:text-dark-text-secondary">
        {label}
      </label>
      <input
        type="text"
        placeholder={placeholder}
        className="
          w-full px-3 py-2 rounded-lg
          bg-white dark:bg-dark-bg-tertiary
          border border-gray-300 dark:border-dark-border
          text-gray-900 dark:text-dark-text-primary
          placeholder-gray-400 dark:placeholder-gray-500
          focus:outline-none focus:ring-2 focus:ring-primary dark:focus:ring-primary-dark
          transition-colors
        "
      />
    </div>
  );
}

/**
 * Example 9: Sidebar with Dark Mode
 */
export function ExampleSidebar() {
  return (
    <aside className="
      w-64 h-screen
      bg-gray-50 dark:bg-dark-bg-primary
      border-r border-gray-200 dark:border-dark-border
      p-4
    ">
      <nav className="space-y-2">
        {['Dashboard', 'Search', 'Settings'].map((item) => (
          <a
            key={item}
            href="#"
            className="
              block px-4 py-2 rounded-lg
              text-gray-700 dark:text-dark-text-secondary
              hover:bg-gray-100 dark:hover:bg-dark-bg-tertiary
              hover:text-gray-900 dark:hover:text-dark-text-primary
              transition-colors
            "
          >
            {item}
          </a>
        ))}
      </nav>
    </aside>
  );
}

/**
 * Example 10: Custom Hook Usage for Complex Logic
 */
export function ExampleCustomThemeLogic() {
  const { isDark, setDark } = useDarkMode();

  const handlePreferredTheme = () => {
    // Complex logic based on user preferences, time of day, etc.
    const hour = new Date().getHours();

    // Auto dark mode from 8 PM to 6 AM
    if (hour >= 20 || hour < 6) {
      setDark(true);
    } else {
      setDark(false);
    }
  };

  return (
    <div className="p-6">
      <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
        Smart Theme
      </h3>
      <p className="mb-4" style={{ color: 'var(--text-secondary)' }}>
        Current theme: {isDark ? 'Dark' : 'Light'}
      </p>
      <button
        onClick={handlePreferredTheme}
        className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover"
      >
        Use Time-Based Theme
      </button>
    </div>
  );
}

/**
 * MIGRATION CHECKLIST FOR SPRINT 36
 *
 * When migrating a component to dark mode:
 *
 * 1. ✅ Add dark mode Tailwind utilities:
 *    - bg-white → bg-white dark:bg-dark-bg-secondary
 *    - text-gray-900 → text-gray-900 dark:text-dark-text-primary
 *    - border-gray-200 → border-gray-200 dark:border-dark-border
 *
 * 2. ✅ OR use CSS custom properties:
 *    - style={{ color: 'var(--text-primary)' }}
 *    - style={{ backgroundColor: 'var(--bg-secondary)' }}
 *
 * 3. ✅ Test both light and dark modes:
 *    - Visual appearance
 *    - Contrast ratios (WCAG 2.1 AA)
 *    - Transitions
 *
 * 4. ✅ Handle images/icons:
 *    - Provide dark mode variants
 *    - OR use filter: invert(1) for simple icons
 *
 * 5. ✅ Add E2E tests:
 *    - Toggle dark mode
 *    - Verify colors change
 *    - Check localStorage persistence
 *
 * 6. ✅ Document component:
 *    - Add dark mode screenshots
 *    - Note any special dark mode behavior
 */

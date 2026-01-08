/**
 * GraphExpansionSettings Component Tests
 * Sprint 79 Feature 79.6: UI Settings for Graph Expansion
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  GraphExpansionSettings,
  GraphExpansionSettingsCompact,
  loadGraphExpansionConfig,
  saveGraphExpansionConfig,
} from '../GraphExpansionSettings';
import {
  DEFAULT_GRAPH_EXPANSION_CONFIG,
  GRAPH_EXPANSION_STORAGE_KEY,
  type GraphExpansionConfig,
} from '../../../types/settings';

// Mock localStorage
const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
});

describe('GraphExpansionSettings', () => {
  beforeEach(() => {
    mockLocalStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('loadGraphExpansionConfig', () => {
    it('returns default config when localStorage is empty', () => {
      const config = loadGraphExpansionConfig();
      expect(config).toEqual(DEFAULT_GRAPH_EXPANSION_CONFIG);
    });

    it('loads config from localStorage', () => {
      const customConfig: GraphExpansionConfig = {
        enabled: false,
        graphExpansionHops: 3,
        minEntitiesThreshold: 15,
        maxSynonymsPerEntity: 2,
      };
      mockLocalStorage.setItem(
        GRAPH_EXPANSION_STORAGE_KEY,
        JSON.stringify(customConfig)
      );

      const config = loadGraphExpansionConfig();
      expect(config).toEqual(customConfig);
    });

    it('merges with defaults for partial config', () => {
      const partialConfig = { enabled: false };
      mockLocalStorage.setItem(
        GRAPH_EXPANSION_STORAGE_KEY,
        JSON.stringify(partialConfig)
      );

      const config = loadGraphExpansionConfig();
      expect(config.enabled).toBe(false);
      expect(config.graphExpansionHops).toBe(
        DEFAULT_GRAPH_EXPANSION_CONFIG.graphExpansionHops
      );
    });

    it('returns defaults on parse error', () => {
      mockLocalStorage.setItem(GRAPH_EXPANSION_STORAGE_KEY, 'invalid-json');

      const config = loadGraphExpansionConfig();
      expect(config).toEqual(DEFAULT_GRAPH_EXPANSION_CONFIG);
    });
  });

  describe('saveGraphExpansionConfig', () => {
    it('saves config to localStorage', () => {
      const config: GraphExpansionConfig = {
        enabled: true,
        graphExpansionHops: 2,
        minEntitiesThreshold: 12,
        maxSynonymsPerEntity: 4,
      };

      saveGraphExpansionConfig(config);

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        GRAPH_EXPANSION_STORAGE_KEY,
        JSON.stringify(config)
      );
    });
  });

  describe('GraphExpansionSettings Component', () => {
    it('renders with default collapsed state', () => {
      render(<GraphExpansionSettings />);

      // Header should be visible
      expect(screen.getByTestId('graph-expansion-header')).toBeInTheDocument();
      expect(screen.getByText('Graph Expansion')).toBeInTheDocument();

      // Content should be collapsed (not visible)
      expect(
        screen.queryByTestId('graph-expansion-content')
      ).not.toBeInTheDocument();
    });

    it('expands when header is clicked', async () => {
      render(<GraphExpansionSettings />);

      // Click to expand
      fireEvent.click(screen.getByTestId('graph-expansion-header'));

      // Content should now be visible
      await waitFor(() => {
        expect(screen.getByTestId('graph-expansion-content')).toBeInTheDocument();
      });
    });

    it('shows enabled status badge', () => {
      render(<GraphExpansionSettings />);

      // Default is enabled
      expect(screen.getByText('Aktiv')).toBeInTheDocument();
    });

    it('toggles enabled state', async () => {
      render(<GraphExpansionSettings defaultCollapsed={false} />);

      const toggle = screen.getByTestId('graph-expansion-toggle');

      // Toggle off
      fireEvent.click(toggle);

      await waitFor(() => {
        expect(screen.getByText('Inaktiv')).toBeInTheDocument();
      });
    });

    it('updates hop depth slider', async () => {
      render(<GraphExpansionSettings defaultCollapsed={false} />);

      const slider = screen.getByTestId('graph-expansion-hops-slider');

      // Change to 3 hops
      fireEvent.change(slider, { target: { value: '3' } });

      await waitFor(() => {
        expect(screen.getByText('3 Hops')).toBeInTheDocument();
      });
    });

    it('updates threshold slider', async () => {
      render(<GraphExpansionSettings defaultCollapsed={false} />);

      const slider = screen.getByTestId('min-entities-threshold-slider');

      // Change to 15 entities
      fireEvent.change(slider, { target: { value: '15' } });

      await waitFor(() => {
        expect(screen.getByText('15 Entities')).toBeInTheDocument();
      });
    });

    it('updates max synonyms slider', async () => {
      render(<GraphExpansionSettings defaultCollapsed={false} />);

      const slider = screen.getByTestId('max-synonyms-slider');

      // Change to 5 synonyms
      fireEvent.change(slider, { target: { value: '5' } });

      await waitFor(() => {
        expect(screen.getByText('5')).toBeInTheDocument();
      });
    });

    it('resets to defaults', async () => {
      // Start with custom config - enabled so sliders are visible
      const customConfig: GraphExpansionConfig = {
        enabled: true,
        graphExpansionHops: 3,
        minEntitiesThreshold: 20,
        maxSynonymsPerEntity: 5,
      };
      const onChange = vi.fn();

      render(
        <GraphExpansionSettings
          config={customConfig}
          onChange={onChange}
          defaultCollapsed={false}
        />
      );

      // Reset button should be visible when enabled
      expect(screen.getByTestId('graph-expansion-reset')).toBeInTheDocument();

      // Click reset
      fireEvent.click(screen.getByTestId('graph-expansion-reset'));

      await waitFor(() => {
        expect(onChange).toHaveBeenCalledWith(DEFAULT_GRAPH_EXPANSION_CONFIG);
      });
    });

    it('calls onChange in controlled mode', async () => {
      const onChange = vi.fn();
      const config: GraphExpansionConfig = {
        enabled: true,
        graphExpansionHops: 1,
        minEntitiesThreshold: 10,
        maxSynonymsPerEntity: 3,
      };

      render(
        <GraphExpansionSettings
          config={config}
          onChange={onChange}
          defaultCollapsed={false}
        />
      );

      // Change hop depth
      fireEvent.change(screen.getByTestId('graph-expansion-hops-slider'), {
        target: { value: '2' },
      });

      await waitFor(() => {
        expect(onChange).toHaveBeenCalledWith({
          ...config,
          graphExpansionHops: 2,
        });
      });
    });

    it('hides sliders when disabled', async () => {
      render(<GraphExpansionSettings defaultCollapsed={false} />);

      // Toggle off
      fireEvent.click(screen.getByTestId('graph-expansion-toggle'));

      await waitFor(() => {
        // Sliders should not be visible when disabled
        expect(
          screen.queryByTestId('graph-expansion-hops-slider')
        ).not.toBeInTheDocument();
      });
    });

    it('has correct ARIA attributes', () => {
      render(<GraphExpansionSettings />);

      const header = screen.getByTestId('graph-expansion-header');
      expect(header).toHaveAttribute('aria-expanded', 'false');
      expect(header).toHaveAttribute('aria-controls', 'graph-expansion-content');
    });
  });

  describe('GraphExpansionSettingsCompact Component', () => {
    it('renders compact toggle button', () => {
      render(<GraphExpansionSettingsCompact />);

      expect(
        screen.getByTestId('graph-expansion-compact-toggle')
      ).toBeInTheDocument();
    });

    it('shows enabled state with hop count', () => {
      render(<GraphExpansionSettingsCompact />);

      // Default is enabled with 1 hop
      const toggle = screen.getByTestId('graph-expansion-compact-toggle');
      expect(toggle).toHaveTextContent('1H');
    });

    it('toggles enabled state on click', async () => {
      const onChange = vi.fn();
      const config: GraphExpansionConfig = {
        enabled: true,
        graphExpansionHops: 2,
        minEntitiesThreshold: 10,
        maxSynonymsPerEntity: 3,
      };

      render(<GraphExpansionSettingsCompact config={config} onChange={onChange} />);

      fireEvent.click(screen.getByTestId('graph-expansion-compact-toggle'));

      await waitFor(() => {
        expect(onChange).toHaveBeenCalledWith({
          ...config,
          enabled: false,
        });
      });
    });

    it('shows settings dropdown when settings trigger is clicked', async () => {
      render(<GraphExpansionSettingsCompact />);

      // Click settings trigger
      const trigger = screen.getByTestId('graph-expansion-settings-trigger');
      fireEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByTestId('graph-expansion-dropdown')).toBeInTheDocument();
      });
    });

    it('hides settings trigger when disabled', async () => {
      const config: GraphExpansionConfig = {
        enabled: false,
        graphExpansionHops: 1,
        minEntitiesThreshold: 10,
        maxSynonymsPerEntity: 3,
      };

      render(<GraphExpansionSettingsCompact config={config} />);

      expect(
        screen.queryByTestId('graph-expansion-settings-trigger')
      ).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('toggle has accessible name', () => {
      render(<GraphExpansionSettings defaultCollapsed={false} />);

      const toggle = screen.getByTestId('graph-expansion-toggle');
      expect(toggle).toHaveAttribute('role', 'switch');
      expect(toggle).toHaveAttribute('aria-checked', 'true');
    });

    it('sliders have accessible labels', () => {
      render(<GraphExpansionSettings defaultCollapsed={false} />);

      const hopsSlider = screen.getByLabelText('Graph-Traversierungstiefe');
      expect(hopsSlider).toBeInTheDocument();

      const thresholdSlider = screen.getByLabelText('Synonym-Fallback Schwelle');
      expect(thresholdSlider).toBeInTheDocument();

      const synonymsSlider = screen.getByLabelText('Max. Synonyme pro Entity');
      expect(synonymsSlider).toBeInTheDocument();
    });

    it('sliders have correct ARIA attributes', () => {
      render(<GraphExpansionSettings defaultCollapsed={false} />);

      const hopsSlider = screen.getByTestId('graph-expansion-hops-slider');
      expect(hopsSlider).toHaveAttribute('aria-valuemin', '1');
      expect(hopsSlider).toHaveAttribute('aria-valuemax', '3');
      expect(hopsSlider).toHaveAttribute('aria-valuenow', '1');
    });

    it('compact toggle has aria-pressed attribute', () => {
      render(<GraphExpansionSettingsCompact />);

      const toggle = screen.getByTestId('graph-expansion-compact-toggle');
      expect(toggle).toHaveAttribute('aria-pressed', 'true');
    });
  });
});

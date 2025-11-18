# ADR-036: Settings Management via localStorage

**Status:** ✅ ACCEPTED (2025-11-16)
**Supersedes:** None
**Deciders:** Frontend Team, Product Lead (Klaus Pommer)
**Date Created:** 2025-11-16
**Date Accepted:** 2025-11-16
**Sprint:** Sprint 27 (Frontend Polish) - Preparation for Sprint 28

---

## Context and Problem Statement

### Current State

As of Sprint 27, AegisRAG has **no user settings management**:
- No theme selection (always light mode)
- No model selection (always default models)
- No API key configuration
- No user preferences (language, timezone, etc.)

Users cannot customize their experience or configure advanced options.

### Problem Statement

> How should we persist user settings (theme, models, API keys, preferences) in a way that is fast, simple, and privacy-preserving, while planning for future multi-device sync?

### Use Cases

**Sprint 28 Settings Requirements:**

1. **Theme Selection:**
   - Light mode (default)
   - Dark mode
   - System preference (auto-detect)

2. **Model Selection:**
   - Local Ollama models (free)
   - Alibaba Cloud models (paid, requires API key)
   - OpenAI models (paid, requires API key)

3. **API Key Configuration:**
   - Alibaba Cloud API key (for DashScope)
   - OpenAI API key (optional)
   - Encrypted storage preferred

4. **User Preferences:**
   - Language (German, English)
   - Timezone (for conversation timestamps)
   - Default search mode (simple, advanced, hybrid)

5. **Privacy Settings:**
   - Data classification (PII, internal, public)
   - LLM routing preference (local-only, cloud-allowed)

---

## Decision Drivers

### Functional Requirements
- **Fast Access:** Settings needed on every page load (<10ms)
- **Privacy:** No sensitive data sent to backend without user consent
- **Offline Support:** Settings available without internet connection
- **Simplicity:** Minimal infrastructure for Sprint 28 (Settings Page feature)

### Non-Functional Requirements
- **Security:** API keys must be protected (encryption preferred)
- **Portability:** Support future cross-device sync (backend database)
- **User Experience:** No login required for basic settings
- **Development Velocity:** Simple implementation for Sprint 28 (5 SP allocated)

### Technical Constraints
- **Frontend:** React 18 with TypeScript
- **Backend:** FastAPI (optional for settings sync)
- **Timeline:** Sprint 28 (Settings Page in 5 SP)
- **Browser Support:** Modern browsers (localStorage available in 98%)

---

## Considered Options

### Option 1: Backend Database (User Settings Table) ⚠️

**Description:** Store settings in PostgreSQL/MongoDB with user authentication.

**Architecture:**
```
User Settings Table (Backend)
├── user_id (primary key)
├── theme (string)
├── models_config (JSON)
├── api_keys_encrypted (string)
├── preferences (JSON)
└── updated_at (timestamp)

API Endpoints:
- GET /users/me/settings → Fetch settings
- PUT /users/me/settings → Update settings
```

**Pros:**
- ✅ **Cross-device sync:** Settings available on all devices
- ✅ **Backup:** Settings preserved if localStorage cleared
- ✅ **Encryption:** API keys encrypted at rest (AES-256)
- ✅ **Audit trail:** Track settings changes (compliance)

**Cons:**
- ❌ **Authentication required:** Users must log in (no guest mode)
- ❌ **Backend dependency:** Requires backend availability for settings
- ❌ **Latency:** 50-200ms round-trip to fetch settings
- ❌ **Infrastructure:** PostgreSQL/MongoDB setup, migrations
- ❌ **Complexity:** 10-15 SP (vs 5 SP for Sprint 28)
- ❌ **Overkill:** No multi-user requirement in Sprint 28

**Verdict:** Too complex for Sprint 28, defer to future.

---

### Option 2: Browser Cookies ❌

**Description:** Store settings in HTTP cookies.

**Implementation:**
```javascript
// Set cookie
document.cookie = "theme=dark; max-age=31536000; path=/";

// Read cookie
const theme = document.cookie
  .split('; ')
  .find(row => row.startsWith('theme='))
  ?.split('=')[1];
```

**Pros:**
- ✅ **Simple:** Native browser API
- ✅ **Server access:** Backend can read cookies (SSR)
- ✅ **Expiration:** Automatic cleanup after max-age

**Cons:**
- ❌ **Size limit:** 4KB per cookie (too small for API keys)
- ❌ **Security risk:** Cookies sent with every request (CSRF, XSS)
- ❌ **Privacy:** Cookies tracked by advertisers
- ❌ **Complex API:** Manual parsing required
- ❌ **HTTP-only limitation:** Cannot store large JSON objects

**Verdict:** Too limited and insecure for settings.

---

### Option 3: IndexedDB (Client-Side Database) ⚠️

**Description:** Use IndexedDB for structured client-side storage.

**Implementation:**
```javascript
// Store settings
const db = await openDB('aegis-settings', 1);
await db.put('settings', {
  theme: 'dark',
  models: { local: 'llama3.2:8b' },
  apiKeys: { alibaba: 'sk-...' }
});

// Retrieve settings
const settings = await db.get('settings');
```

**Pros:**
- ✅ **Large storage:** 50MB+ per domain (vs 5MB localStorage)
- ✅ **Structured data:** Schema, indexes, transactions
- ✅ **Async API:** Non-blocking reads/writes

**Cons:**
- ❌ **Complexity:** Low-level API (requires wrapper like `idb`)
- ❌ **Overkill:** Settings are small (<5KB), don't need 50MB
- ❌ **Browser support:** 95% (vs 98% localStorage)
- ❌ **Debugging:** Harder to inspect than localStorage

**Verdict:** Too complex for simple settings, better for large datasets.

---

### Option 4: localStorage (Client-Side Key-Value Store) ⭐ (Recommended)

**Description:** Store settings as JSON in `localStorage`.

**Implementation:**
```typescript
// Settings interface
interface UserSettings {
  theme: 'light' | 'dark' | 'system';
  models: {
    local: string;
    alibaba?: string;
    openai?: string;
  };
  apiKeys: {
    alibaba?: string;
    openai?: string;
  };
  preferences: {
    language: 'de' | 'en';
    timezone: string;
    searchMode: 'simple' | 'advanced' | 'hybrid';
  };
  privacy: {
    dataClassification: 'pii' | 'internal' | 'public';
    llmRouting: 'local-only' | 'cloud-allowed';
  };
}

// Save settings
function saveSettings(settings: UserSettings): void {
  localStorage.setItem('aegis-settings', JSON.stringify(settings));
}

// Load settings
function loadSettings(): UserSettings | null {
  const stored = localStorage.getItem('aegis-settings');
  if (!stored) return null;
  return JSON.parse(stored) as UserSettings;
}

// Get setting with default
function getSetting<K extends keyof UserSettings>(
  key: K,
  defaultValue: UserSettings[K]
): UserSettings[K] {
  const settings = loadSettings();
  return settings?.[key] ?? defaultValue;
}
```

**Pros:**
- ✅ **Simplicity:** 20 LOC for full settings management
- ✅ **Fast:** Synchronous API, <1ms access time
- ✅ **Browser support:** 98% (IE 8+, all modern browsers)
- ✅ **Debugging:** Inspect via DevTools → Application → Local Storage
- ✅ **Sufficient size:** 5-10MB per domain (vs <5KB settings needed)
- ✅ **No backend dependency:** Works offline, no server required
- ✅ **Privacy:** Data never leaves user's browser (unless explicitly synced)

**Cons:**
- ⚠️ **No cross-device sync:** Settings local to single browser
- ⚠️ **No encryption:** API keys stored in plaintext
- ⚠️ **Browser-specific:** Clear cache = lost settings
- ⚠️ **No versioning:** Schema changes require migration logic

**Mitigation:**
- **Cross-device sync:** Add backend sync in Sprint 30+ (optional feature)
- **Encryption:** Use Web Crypto API for API key encryption (Sprint 29)
- **Backup:** Export/import settings as JSON file (Sprint 29)
- **Versioning:** Add `version` field to settings object, migration on load

**Verdict:** Optimal for Sprint 28 (simple, fast, privacy-preserving).

---

## Decision Outcome

### ✅ **Chosen Option: Option 4 (localStorage)**

**Rationale:**

1. **Simplicity:** 20 LOC vs 100+ LOC for backend database
2. **Speed:** <1ms access vs 50-200ms backend API
3. **Privacy:** No data sent to backend without user consent
4. **Timeline:** Fits Sprint 28's 5 SP allocation
5. **Offline Support:** Works without internet connection
6. **Future-Proof:** Can add backend sync later (non-breaking)

**Sprint 28 Implementation Plan:**

**Phase 1: Core Settings (3 SP)**
- Settings context provider (`frontend/src/contexts/SettingsContext.tsx`)
- localStorage wrapper (`frontend/src/utils/settings.ts`)
- Default settings (light theme, local models, English)
- TypeScript interfaces for all settings

**Phase 2: Settings Page (2 SP)**
- Settings UI (`frontend/src/pages/SettingsPage.tsx`)
- Theme selector (light, dark, system)
- Model selector (local, Alibaba, OpenAI)
- API key input fields (with show/hide)
- Save/reset buttons

**Phase 3: Integration (0 SP - part of Phase 1)**
- QuickActionsBar → Settings button enabled
- Apply theme to entire app (CSS variables)
- Apply model selection to chat API calls

---

## Consequences

### Positive Consequences

1. **Fast Settings Access**
   - <1ms load time (synchronous localStorage API)
   - No backend round-trip delay
   - Settings available instantly on page load

2. **Privacy-Preserving**
   - API keys never sent to backend (unless user explicitly syncs)
   - No telemetry or tracking (settings stay local)
   - GDPR-compliant by design (no data collection)

3. **Simple Implementation**
   - 20 LOC for settings management
   - No database migrations or schema changes
   - No authentication required (guest mode supported)

4. **Offline Support**
   - Settings work without internet connection
   - No dependency on backend availability
   - Fully functional in air-gapped deployments

5. **Developer Experience**
   - Easy debugging (DevTools → Application → Local Storage)
   - Simple testing (mock localStorage in tests)
   - No backend coordination required

6. **User Experience**
   - No login required for basic settings
   - Settings persist across sessions
   - Fast save/load (no loading spinners)

### Negative Consequences

1. **No Cross-Device Sync**
   - Settings local to single browser/device
   - User must manually reconfigure on new device
   - **Mitigation:** Add backend sync in Sprint 30+ (optional)

2. **API Keys in Plaintext**
   - localStorage not encrypted by default
   - Risk: Malicious scripts can read API keys
   - **Mitigation:** Web Crypto API encryption in Sprint 29

3. **Browser Cache Dependency**
   - Clear cache → lost settings
   - No automatic backup
   - **Mitigation:** Export/import settings (Sprint 29)

4. **No Schema Versioning**
   - Settings schema changes require manual migration
   - Risk: Old settings format breaks new app version
   - **Mitigation:** Add `version` field, migration logic

5. **No Audit Trail**
   - Cannot track settings changes
   - No history or rollback
   - **Mitigation:** Acceptable for single-user app (not enterprise requirement)

### Neutral Consequences

1. **Browser-Specific Storage**
   - Chrome/Firefox/Safari each have separate localStorage
   - Not a problem for single-browser users
   - Could be issue for users switching browsers

2. **5MB Storage Limit**
   - Sufficient for settings (<5KB)
   - Not suitable for large datasets (use IndexedDB)

---

## Implementation Details

### Settings Interface (TypeScript)

```typescript
// frontend/src/types/settings.ts

export interface UserSettings {
  version: number; // Schema version (1 for Sprint 28)

  theme: 'light' | 'dark' | 'system';

  models: {
    local: string; // e.g., "llama3.2:8b"
    alibaba?: string; // e.g., "qwen-turbo"
    openai?: string; // e.g., "gpt-4o"
  };

  apiKeys: {
    alibaba?: string; // DashScope API key
    openai?: string; // OpenAI API key
  };

  preferences: {
    language: 'de' | 'en';
    timezone: string; // e.g., "Europe/Berlin"
    searchMode: 'simple' | 'advanced' | 'hybrid';
  };

  privacy: {
    dataClassification: 'pii' | 'internal' | 'public';
    llmRouting: 'local-only' | 'cloud-allowed';
  };
}

export const DEFAULT_SETTINGS: UserSettings = {
  version: 1,
  theme: 'light',
  models: {
    local: 'llama3.2:8b',
  },
  apiKeys: {},
  preferences: {
    language: 'de',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    searchMode: 'hybrid',
  },
  privacy: {
    dataClassification: 'internal',
    llmRouting: 'cloud-allowed',
  },
};
```

---

### Settings Utility (localStorage Wrapper)

```typescript
// frontend/src/utils/settings.ts

import { UserSettings, DEFAULT_SETTINGS } from '../types/settings';

const SETTINGS_KEY = 'aegis-settings';

export function saveSettings(settings: UserSettings): void {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch (error) {
    console.error('Failed to save settings:', error);
  }
}

export function loadSettings(): UserSettings {
  try {
    const stored = localStorage.getItem(SETTINGS_KEY);
    if (!stored) return DEFAULT_SETTINGS;

    const parsed = JSON.parse(stored) as UserSettings;

    // Schema migration (if version changed)
    if (parsed.version !== DEFAULT_SETTINGS.version) {
      return migrateSettings(parsed);
    }

    return parsed;
  } catch (error) {
    console.error('Failed to load settings:', error);
    return DEFAULT_SETTINGS;
  }
}

export function resetSettings(): void {
  localStorage.removeItem(SETTINGS_KEY);
}

export function exportSettings(): string {
  const settings = loadSettings();
  return JSON.stringify(settings, null, 2);
}

export function importSettings(json: string): boolean {
  try {
    const settings = JSON.parse(json) as UserSettings;
    saveSettings(settings);
    return true;
  } catch (error) {
    console.error('Failed to import settings:', error);
    return false;
  }
}

function migrateSettings(old: UserSettings): UserSettings {
  // Future: Add migration logic when schema changes
  // Example: v1 → v2 adds new field
  console.warn('Migrating settings from version', old.version);
  return { ...DEFAULT_SETTINGS, ...old, version: DEFAULT_SETTINGS.version };
}
```

---

### Settings Context (React)

```typescript
// frontend/src/contexts/SettingsContext.tsx

import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserSettings, DEFAULT_SETTINGS } from '../types/settings';
import { loadSettings, saveSettings } from '../utils/settings';

interface SettingsContextType {
  settings: UserSettings;
  updateSettings: (updates: Partial<UserSettings>) => void;
  resetSettings: () => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS);

  // Load settings on mount
  useEffect(() => {
    const loaded = loadSettings();
    setSettings(loaded);
  }, []);

  const updateSettings = (updates: Partial<UserSettings>) => {
    const newSettings = { ...settings, ...updates };
    setSettings(newSettings);
    saveSettings(newSettings);
  };

  const resetSettings = () => {
    setSettings(DEFAULT_SETTINGS);
    saveSettings(DEFAULT_SETTINGS);
  };

  return (
    <SettingsContext.Provider value={{ settings, updateSettings, resetSettings }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within SettingsProvider');
  }
  return context;
}
```

---

### Settings Page (UI)

```typescript
// frontend/src/pages/SettingsPage.tsx

import React, { useState } from 'react';
import { useSettings } from '../contexts/SettingsContext';

export function SettingsPage() {
  const { settings, updateSettings, resetSettings } = useSettings();
  const [showApiKeys, setShowApiKeys] = useState(false);

  return (
    <div className="settings-page">
      <h1>Einstellungen</h1>

      {/* Theme Selection */}
      <section>
        <h2>Theme</h2>
        <select
          value={settings.theme}
          onChange={(e) => updateSettings({ theme: e.target.value as any })}
        >
          <option value="light">Hell</option>
          <option value="dark">Dunkel</option>
          <option value="system">System</option>
        </select>
      </section>

      {/* Model Selection */}
      <section>
        <h2>Modelle</h2>
        <label>
          Lokales Modell:
          <input
            type="text"
            value={settings.models.local}
            onChange={(e) => updateSettings({
              models: { ...settings.models, local: e.target.value }
            })}
          />
        </label>
      </section>

      {/* API Keys */}
      <section>
        <h2>API-Schlüssel</h2>
        <button onClick={() => setShowApiKeys(!showApiKeys)}>
          {showApiKeys ? 'Verbergen' : 'Anzeigen'}
        </button>
        {showApiKeys && (
          <>
            <label>
              Alibaba Cloud:
              <input
                type="password"
                value={settings.apiKeys.alibaba || ''}
                onChange={(e) => updateSettings({
                  apiKeys: { ...settings.apiKeys, alibaba: e.target.value }
                })}
              />
            </label>
            <label>
              OpenAI:
              <input
                type="password"
                value={settings.apiKeys.openai || ''}
                onChange={(e) => updateSettings({
                  apiKeys: { ...settings.apiKeys, openai: e.target.value }
                })}
              />
            </label>
          </>
        )}
      </section>

      {/* Actions */}
      <section>
        <button onClick={resetSettings}>Zurücksetzen</button>
      </section>
    </div>
  );
}
```

---

## Security Considerations

### API Key Storage

**Current Approach (Sprint 28):**
- API keys stored in **plaintext** in localStorage
- Accessible to JavaScript on same domain
- Risk: XSS attacks can read API keys

**Future Encryption (Sprint 29):**
```typescript
// Use Web Crypto API for encryption
async function encryptApiKey(apiKey: string, password: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(apiKey);
  const salt = crypto.getRandomValues(new Uint8Array(16));

  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    encoder.encode(password),
    'PBKDF2',
    false,
    ['deriveBits', 'deriveKey']
  );

  const key = await crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations: 100000, hash: 'SHA-256' },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt']
  );

  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encrypted = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv },
    key,
    data
  );

  // Return base64-encoded: salt + iv + encrypted
  const combined = new Uint8Array(salt.length + iv.length + encrypted.byteLength);
  combined.set(salt, 0);
  combined.set(iv, salt.length);
  combined.set(new Uint8Array(encrypted), salt.length + iv.length);

  return btoa(String.fromCharCode(...combined));
}
```

**Decision:** Defer encryption to Sprint 29 (out of scope for Sprint 28).

---

## Migration Path

### Phase 1: localStorage (Sprint 28) ✅
- Settings stored locally
- No cross-device sync
- API keys in plaintext

### Phase 2: Encryption (Sprint 29)
- Web Crypto API for API key encryption
- User-provided password or device-generated key
- Backward-compatible (migrate plaintext → encrypted)

### Phase 3: Backend Sync (Sprint 30+)
- Optional backend database (PostgreSQL)
- User authentication required
- Sync settings across devices
- localStorage as local cache (offline-first)

**Architecture (Future):**
```
User Settings Flow
    │
    ├─ Load from localStorage (fast, <1ms)
    │   ├─ If available → Use immediately
    │   └─ If missing → Fetch from backend
    │
    ├─ Update Settings
    │   ├─ Save to localStorage (instant)
    │   └─ Sync to backend (background, optional)
    │
    └─ Cross-Device Sync
        ├─ Backend as source of truth
        ├─ localStorage as cache
        └─ Conflict resolution: backend wins
```

---

## Testing Strategy

### Unit Tests (Sprint 28)

```typescript
// frontend/src/utils/settings.test.ts

describe('Settings Utilities', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('loadSettings returns defaults when empty', () => {
    const settings = loadSettings();
    expect(settings).toEqual(DEFAULT_SETTINGS);
  });

  test('saveSettings persists to localStorage', () => {
    const settings = { ...DEFAULT_SETTINGS, theme: 'dark' };
    saveSettings(settings);
    expect(localStorage.getItem('aegis-settings')).toBeTruthy();
  });

  test('loadSettings retrieves saved settings', () => {
    const settings = { ...DEFAULT_SETTINGS, theme: 'dark' };
    saveSettings(settings);
    const loaded = loadSettings();
    expect(loaded.theme).toBe('dark');
  });

  test('exportSettings returns JSON string', () => {
    const settings = { ...DEFAULT_SETTINGS, theme: 'dark' };
    saveSettings(settings);
    const exported = exportSettings();
    expect(JSON.parse(exported).theme).toBe('dark');
  });

  test('importSettings restores from JSON', () => {
    const json = JSON.stringify({ ...DEFAULT_SETTINGS, theme: 'dark' });
    const success = importSettings(json);
    expect(success).toBe(true);
    expect(loadSettings().theme).toBe('dark');
  });
});
```

### Integration Tests (Sprint 28)

```typescript
// frontend/src/pages/SettingsPage.test.tsx

describe('SettingsPage', () => {
  test('updates theme when selected', async () => {
    render(
      <SettingsProvider>
        <SettingsPage />
      </SettingsProvider>
    );

    const themeSelect = screen.getByLabelText('Theme');
    fireEvent.change(themeSelect, { target: { value: 'dark' } });

    expect(loadSettings().theme).toBe('dark');
  });

  test('resets to default settings', async () => {
    const settings = { ...DEFAULT_SETTINGS, theme: 'dark' };
    saveSettings(settings);

    render(
      <SettingsProvider>
        <SettingsPage />
      </SettingsProvider>
    );

    const resetButton = screen.getByText('Zurücksetzen');
    fireEvent.click(resetButton);

    expect(loadSettings().theme).toBe('light');
  });
});
```

---

## Performance Impact

### Load Time
- **localStorage read:** <1ms (synchronous)
- **JSON parse:** <1ms (for ~5KB settings)
- **Total:** <2ms (vs 50-200ms backend API)

### Save Time
- **JSON stringify:** <1ms
- **localStorage write:** <1ms
- **Total:** <2ms

### Memory
- **Settings object:** ~5KB in memory
- **localStorage:** ~5KB persistent
- **Negligible impact:** <0.01% of 16GB RAM

---

## References

### Web Standards
- [Web Storage API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Web_Storage_API)
- [localStorage (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage)
- [Web Crypto API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Web_Crypto_API)

### Best Practices
- [Don't use localStorage (Critical CSS)](https://www.smashingmagazine.com/2010/10/local-storage-and-how-to-use-it/) - Outdated (2010)
- [localStorage vs IndexedDB](https://developers.google.com/web/fundamentals/instant-and-offline/web-storage/offline-for-pwa)

### Related Documentation
- [Sprint 27 Completion Report](../sprints/SPRINT_27_COMPLETION_REPORT.md)
- [Sprint 28 Planning](../sprints/SPRINT_28_PLAN.md) (future)

### Related ADRs
- [ADR-034: Perplexity UX Features](./ADR-034-perplexity-ux-features.md) - Settings button in Quick Actions
- [ADR-021: Perplexity UI Design](./ADR-021-perplexity-ui-design.md) - UI patterns

---

## Revision History

- **2025-11-16:** Initial version (Status: Proposed)
- **2025-11-16:** Accepted for Sprint 28 implementation
  - localStorage chosen for simplicity, speed, privacy
  - Backend sync deferred to Sprint 30+
  - Encryption deferred to Sprint 29

---

**Status:** ✅ ACCEPTED (2025-11-16)
**Next Steps:**
- Sprint 28: Implement Settings Page (5 SP)
- Sprint 29: Add Web Crypto API encryption for API keys
- Sprint 30+: Optional backend sync for cross-device support
- Monitor user feedback on settings UX

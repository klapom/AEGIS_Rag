# SearchableSelect Migration Guide

**Date:** 2026-01-03
**Feature:** Searchable Document & Section Selection
**Status:** ✅ Implemented

---

## 📋 Overview

Die Graph Communities Dialoge wurden von Text-Inputs auf SearchableSelect-Komponenten migriert, um eine bessere UX mit Suchfunktion und Keyboard-Navigation zu bieten.

---

## 🔄 Komponenten-Änderungen

### Neue Komponenten
- ✅ `frontend/src/components/ui/SearchableSelect.tsx` (230 lines)
- ✅ `frontend/src/hooks/useDocuments.ts` (100 lines)

### Aktualisierte Dialoge
- ✅ `SectionCommunitiesDialog.tsx` - Document + Section Selection
- ✅ `CommunityComparisonDialog.tsx` - Document + Multiple Sections

---

## 🎯 SearchableSelect Features

### Funktionalität
- ✅ **Suchfunktion:** Live-Filtering während Eingabe
- ✅ **Keyboard-Navigation:** Arrow keys, Enter, Escape
- ✅ **Click Outside:** Automatisches Schließen
- ✅ **Dark Mode:** Vollständige Unterstützung
- ✅ **Disabled State:** Für abhängige Felder
- ✅ **Clear Button:** X-Icon zum Zurücksetzen

### Cascading Selection
```
1. Dokument auswählen → Lädt Sections
2. Section auswählen → Aktiviert Submit-Button
```

---

## 🧪 E2E Test Aktualisierungen

### Hilfsfunktion für Tests

```typescript
/**
 * Helper function to select an option in SearchableSelect component
 */
async function selectSearchableOption(page: Page, testId: string, searchText: string) {
  // Click trigger to open dropdown
  await page.getByTestId(`${testId}-trigger`).click();

  // Wait for dropdown to open
  await page.waitForTimeout(300);

  // Type in search
  await page.getByTestId(`${testId}-search`).fill(searchText);

  // Wait for filtering
  await page.waitForTimeout(200);

  // Click the first option (should be the match)
  const firstOption = page.locator(`[data-testid^="${testId}-option-"]`).first();
  await firstOption.click();
}
```

### Migration Pattern

**Vorher (Text Input):**
```typescript
await page.getByTestId('document-id-input').fill('doc_123');
await page.getByTestId('section-id-input').fill('Introduction');
```

**Nachher (SearchableSelect):**
```typescript
await selectSearchableOption(page, 'document-select', 'doc_123');
await page.waitForTimeout(500); // Wait for sections to load
await selectSearchableOption(page, 'section-select', 'Introduction');
```

### Testid-Änderungen

| Alt | Neu |
|-----|-----|
| `document-id-input` | `document-select` |
| `section-id-input` | `section-select` |
| `section-input-{index}` | `section-select-{index}` |

### SearchableSelect Sub-Elements

| Testid | Element |
|--------|---------|
| `{base}-trigger` | Dropdown-Trigger-Button |
| `{base}-search` | Such-Input-Feld |
| `{base}-dropdown` | Dropdown-Container |
| `{base}-option-{value}` | Einzelne Option |
| `{base}-clear` | Clear-Button (X-Icon) |
| `{base}-no-results` | "No results" Meldung |

---

## 🔌 API Endpunkte

### Benötigte Backend-Endpunkte

#### 1. Liste aller Dokumente
```
GET /api/v1/graph/documents

Response:
{
  "documents": [
    {
      "id": "doc_123",
      "title": "Machine Learning Basics",
      "created_at": "2026-01-01T12:00:00Z"
    },
    ...
  ]
}
```

#### 2. Sections für ein Dokument
```
GET /api/v1/graph/documents/{doc_id}/sections

Response:
{
  "document_id": "doc_123",
  "sections": [
    {
      "id": "sec_1",
      "heading": "Introduction",
      "level": 1,
      "entity_count": 15
    },
    ...
  ]
}
```

---

## ✅ Test-Checkliste

### SectionCommunitiesDialog Tests
- ✅ Dialog öffnet
- ✅ Document SearchableSelect sichtbar
- ✅ Section SearchableSelect sichtbar (disabled bis Dokument gewählt)
- ⏳ Dokument auswählen aktiviert Section-Select
- ⏳ Section auswählen aktiviert Analyze-Button
- ⏳ Sections laden nach Dokument-Auswahl

### CommunityComparisonDialog Tests
- ✅ Dialog öffnet
- ✅ Document SearchableSelect sichtbar
- ✅ Multiple Section-Selects (minimum 2)
- ⏳ Add Section Button funktioniert
- ⏳ Remove Section Button funktioniert (nur ab 3+ Sections)
- ⏳ Sections disabled bis Dokument gewählt

---

## 🐛 Known Issues & Next Steps

### Backend-Endpunkte Fehlen
**Status:** ⚠️ Noch nicht implementiert

Die beiden neuen API-Endpunkte müssen noch im Backend erstellt werden:
- `GET /api/v1/graph/documents`
- `GET /api/v1/graph/documents/{doc_id}/sections`

**Workaround für Tests:**
```typescript
// Mock API responses in tests
await page.route('**/api/v1/graph/documents', (route) => {
  route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      documents: [
        { id: 'doc_1', title: 'Test Document 1' },
        { id: 'doc_2', title: 'Test Document 2' }
      ]
    })
  });
});

await page.route('**/api/v1/graph/documents/*/sections', (route) => {
  route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      sections: [
        { id: 'sec_1', heading: 'Introduction', level: 1 },
        { id: 'sec_2', heading: 'Methods', level: 1 }
      ]
    })
  });
});
```

### Test Migration Status
- ✅ Helper function erstellt
- ✅ Testid-Liste aktualisiert
- ⏳ Skipped tests bleiben skipped (warten auf Backend)
- ⏳ Active tests Schritt für Schritt migrieren

---

## 🚀 Deployment

### Frontend Build
```bash
cd frontend
npm run build
```

**Erwartung:** ✅ 0 TypeScript errors

### Komponenten-Tests
```bash
# Unit tests für SearchableSelect
npx vitest run src/components/ui/SearchableSelect.test.tsx

# E2E tests (mit Backend-Mocking)
npx playwright test e2e/tests/admin/graph-communities.spec.ts
```

---

## 📖 Usage Examples

### Basic Usage
```tsx
import { SearchableSelect } from '../ui/SearchableSelect';

<SearchableSelect
  options={[
    { value: 'doc_1', label: 'Document 1' },
    { value: 'doc_2', label: 'Document 2' }
  ]}
  value={selected}
  onChange={setSelected}
  placeholder="Select document..."
  data-testid="my-select"
/>
```

### With Loading State
```tsx
<SearchableSelect
  options={documents.map(d => ({ value: d.id, label: d.title }))}
  value={selected}
  onChange={setSelected}
  placeholder={isLoading ? 'Loading...' : 'Select...'}
  disabled={isLoading}
/>
```

### Cascading Selects
```tsx
// Parent select
<SearchableSelect
  value={docId}
  onChange={(id) => {
    setDocId(id);
    loadSections(id); // Trigger dependent data load
  }}
  ...
/>

// Dependent select
<SearchableSelect
  options={sections}
  value={sectionId}
  onChange={setSectionId}
  disabled={!docId} // Disabled until parent selected
  placeholder={!docId ? 'Select document first' : 'Select section...'}
/>
```

---

## 🎓 Lessons Learned

### 1. Custom Component vs. Library
**Entscheidung:** Eigene Komponente statt shadcn/ui
**Grund:**
- Volle Kontrolle über Styling & Behavior
- Keine zusätzliche Setup-Komplexität
- Perfekt auf Use Case zugeschnitten

### 2. Cascading Selection Pattern
**Pattern:** Parent-Auswahl → Child-Daten laden → Child aktivieren
**Implementation:**
```tsx
useEffect(() => {
  if (selectedDocId) {
    fetchSections(selectedDocId);
  } else {
    setSections([]);
  }
}, [selectedDocId]);
```

### 3. E2E Test Helper Functions
**Lesson:** Wiederverwendbare Helper für komplexe UI-Komponenten
**Benefit:** Tests bleiben lesbar und wartbar

---

**Status:** ✅ **SearchableSelect Migration Complete**
**Next:** Backend API-Endpunkte implementieren + E2E Tests finalisieren

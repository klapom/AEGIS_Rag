# Test ID Mapping: Domain Auto Discovery

## Component Test IDs (Actual)
From `frontend/src/components/admin/DomainAutoDiscovery.tsx`:

| Test ID | Element | Location |
|---------|---------|----------|
| `domain-auto-discovery` | Root container | Line 284 |
| `drop-zone` | Drag-drop upload area | Line 304 |
| `file-input` | File input (hidden) | Line 321 |
| `upload-error` | Upload error message | Line 345 |
| `uploaded-files` | Container for uploaded file list | Line 355 |
| `uploaded-file-${filename}` | Individual file card | Line 362 |
| `remove-file-${filename}` | Remove file button | Line 377 |
| `analyze-button` | Analyze documents button | Line 393 |
| `analysis-error` | Analysis error message | Line 413 |
| `suggestion-panel` | Suggestion results panel | Line 425 |
| `edit-title-input` | Title edit input | Line 451 |
| `suggested-title` | Suggested title text | Line 456 |
| `edit-description-input` | Description edit textarea | Line 483 |
| `suggested-description` | Suggested description text | Line 488 |
| `topic-${idx}` | Topic tag | Line 508 |
| `edit-button` | Start editing button | Line 523 |
| `cancel-edit-button` | Cancel editing button | Line 536 |
| `accept-button` | Accept suggestion button | Line 544 |
| `cancel-button` | Cancel auto-discovery button | Line 559 |
| `confidence-indicator` | Confidence progress bar | Line 599 |

## Test File Test IDs (Incorrect)
From `frontend/e2e/admin/domain-auto-discovery.spec.ts`:

| Used in Test | Should Be | Status |
|--------------|-----------|--------|
| `domain-discovery-upload-area` | `drop-zone` | ❌ Wrong |
| `domain-discovery-file-input` | `file-input` | ❌ Wrong |
| `domain-discovery-error` | `upload-error` or `analysis-error` | ❌ Wrong |
| `domain-discovery-max-files-error` | `upload-error` | ❌ Wrong |
| `domain-discovery-analyze-button` | `analyze-button` | ❌ Wrong |
| `domain-discovery-loading` | NOT EXISTS | ❌ Missing |
| `domain-discovery-suggestion` | `suggestion-panel` | ❌ Wrong |
| `domain-discovery-suggestion-title` | `suggested-title` | ❌ Wrong |
| `domain-discovery-suggestion-description` | `suggested-description` | ❌ Wrong |
| `domain-discovery-suggestion-confidence` | `confidence-indicator` | ❌ Wrong |
| `domain-discovery-suggestion-description-edit` | `edit-description-input` | ❌ Wrong |
| `domain-discovery-accept-button` | `accept-button` | ❌ Wrong |
| `domain-discovery-success` | NOT EXISTS | ❌ Missing |
| `domain-discovery-file-list` | `uploaded-files` | ❌ Wrong |
| `domain-discovery-file-item` | `uploaded-file-${filename}` | ❌ Wrong |
| `domain-discovery-clear-button` | NOT EXISTS | ❌ Missing |

## Fix Strategy

1. **Global Search-Replace:**
   - `domain-discovery-upload-area` → `drop-zone`
   - `domain-discovery-file-input` → `file-input`
   - `domain-discovery-analyze-button` → `analyze-button`
   - `domain-discovery-suggestion` → `suggestion-panel`
   - `domain-discovery-accept-button` → `accept-button`
   - `domain-discovery-file-list` → `uploaded-files`

2. **Context-Specific Fixes:**
   - Error messages: Use `upload-error` or `analysis-error` depending on context
   - File items: Use dynamic `uploaded-file-${filename}`
   - Missing elements: Add test IDs to component or adjust test expectations

3. **Test Cases Needing Revision:**
   - TC-46.5.5: Loading state (no test ID for loading spinner)
   - TC-46.5.7: Success message (no test ID for success state)
   - Tests expecting clear button (no clear button in component)

## Recommendation

Create a global test ID constants file to prevent future mismatches:
```typescript
// frontend/src/constants/testIds.ts
export const TEST_IDS = {
  DOMAIN_AUTO_DISCOVERY: {
    CONTAINER: 'domain-auto-discovery',
    DROP_ZONE: 'drop-zone',
    FILE_INPUT: 'file-input',
    ANALYZE_BUTTON: 'analyze-button',
    // ... etc
  },
};
```

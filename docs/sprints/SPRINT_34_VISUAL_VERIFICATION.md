# Sprint 34 Features 34.3 & 34.4 - Visual Verification Guide

**Date:** 2025-12-01
**Purpose:** Manual visual verification checklist for graph edge visualization features

## Prerequisites

1. **Backend Running:**
   ```bash
   cd C:\Projekte\AEGISRAG
   uvicorn src.api.main:app --reload --port 8000
   ```

2. **Frontend Running:**
   ```bash
   cd C:\Projekte\AEGISRAG\frontend
   npm run dev
   ```

3. **Neo4j Populated:**
   - At least one document indexed with RELATES_TO relationships
   - Can verify with: `http://localhost:7474` (Neo4j Browser)

## Visual Verification Checklist

### Feature 34.3: Edge-Type Visualization

#### 1. Edge Colors
**Location:** Admin Graph Analytics Page (`http://localhost:5173/admin/graph`)

**Expected Behavior:**
- [ ] RELATES_TO edges appear **blue** (#3B82F6)
- [ ] MENTIONED_IN edges appear **gray** (#9CA3AF)
- [ ] HAS_SECTION edges appear **green** (#10B981)
- [ ] DEFINES edges appear **amber** (#F59E0B)
- [ ] All other edges appear **light gray** (#d1d5db)

**How to Verify:**
1. Open `http://localhost:5173/admin/graph`
2. Wait for graph to load (15s max)
3. Visually inspect edge colors on canvas
4. Compare with legend colors in bottom-right corner

**Screenshot Locations:**
- Save to: `docs/sprints/sprint-34/screenshots/edge-colors.png`

#### 2. Edge Width by Weight
**Expected Behavior:**
- [ ] Thicker RELATES_TO edges have **higher weight** (closer to 1.0)
- [ ] Thinner RELATES_TO edges have **lower weight** (closer to 0.0)
- [ ] Edge width ranges from **1px to 3px**
- [ ] Non-RELATES_TO edges have **constant 1.5px width**

**How to Verify:**
1. Hover over RELATES_TO edges to see weight in tooltip
2. Compare visual thickness with weight value
3. High weight (e.g., 0.85) should be noticeably thicker than low weight (e.g., 0.15)

**Test Cases:**
- High weight (>0.7): Should be ~2.5-3px thick
- Medium weight (0.4-0.7): Should be ~1.8-2.4px thick
- Low weight (<0.4): Should be ~1.0-1.8px thick

#### 3. Legend Display
**Expected Behavior:**
- [ ] Legend appears in **bottom-right corner** of graph canvas
- [ ] Legend has **semi-transparent white background** with backdrop blur
- [ ] Legend shows **two sections**:
  - Entity Types (colored circles)
  - Relationships (colored lines)
- [ ] Relationship section includes:
  - RELATES_TO (blue line)
  - MENTIONED_IN (gray line)
  - HAS_SECTION (green line)
  - DEFINES (amber line)

**How to Verify:**
1. Check legend visibility (should always be visible)
2. Verify colors match actual edges in graph
3. Check that legend is readable over any graph background

**Screenshot Locations:**
- Save to: `docs/sprints/sprint-34/screenshots/legend.png`

### Feature 34.4: Relationship Tooltips

#### 1. Tooltip Content - RELATES_TO
**Expected Behavior:**
- [ ] Hovering over RELATES_TO edge shows tooltip
- [ ] Tooltip includes:
  - Relationship type: "RELATES_TO"
  - Weight as percentage: "(85%)" format
  - Description: LLM-generated text (if available)

**Example Tooltip:**
```
RELATES_TO (85%)
Both entities are mentioned in the context of cloud computing
```

**How to Verify:**
1. Hover mouse over blue RELATES_TO edge
2. Wait ~500ms for tooltip to appear
3. Verify all three components present
4. Check weight percentage matches visual thickness

#### 2. Tooltip Content - MENTIONED_IN
**Expected Behavior:**
- [ ] Hovering over MENTIONED_IN edge shows tooltip
- [ ] Tooltip includes:
  - Relationship type: "MENTIONED_IN"
  - No weight displayed (not applicable)
  - Optional description (rarely present)

**Example Tooltip:**
```
MENTIONED_IN
```

**How to Verify:**
1. Hover mouse over gray MENTIONED_IN edge
2. Tooltip should be simpler (no weight)

#### 3. Tooltip Content - HAS_SECTION
**Expected Behavior:**
- [ ] Hovering over HAS_SECTION edge shows tooltip
- [ ] Tooltip includes:
  - Relationship type: "HAS_SECTION"
  - No weight displayed
  - Optional description

**Example Tooltip:**
```
HAS_SECTION
```

#### 4. Tooltip Responsiveness
**Expected Behavior:**
- [ ] Tooltip appears within **~500ms** of hover
- [ ] Tooltip disappears immediately on mouse leave
- [ ] Tooltip follows mouse cursor (browser default behavior)
- [ ] Tooltip readable against any background

**How to Verify:**
1. Hover over multiple edges rapidly
2. Tooltips should appear/disappear smoothly
3. No lag or stuttering

### Feature 34.6: Edge Filtering (Bonus Verification)

#### 1. Filter Controls
**Location:** Graph analytics page sidebar or top panel

**Expected Behavior:**
- [ ] Checkbox for "Show RELATES_TO" (default: checked)
- [ ] Checkbox for "Show MENTIONED_IN" (default: checked)
- [ ] Slider for "Minimum Weight" (default: 0, range: 0-100)

**How to Verify:**
1. Locate edge filter controls
2. Verify default states
3. Test each control independently

#### 2. Filter Functionality
**Expected Behavior:**
- [ ] Unchecking "RELATES_TO" hides all blue edges
- [ ] Unchecking "MENTIONED_IN" hides all gray edges
- [ ] Increasing weight threshold hides low-weight RELATES_TO edges
- [ ] Edge count updates in graph stats (bottom-left)

**How to Verify:**
1. Note initial edge count (e.g., "Edges: 45")
2. Uncheck "RELATES_TO"
3. Verify edge count decreases
4. Verify no blue edges visible
5. Re-check "RELATES_TO"
6. Verify edges reappear

**Test Cases:**
- Filter RELATES_TO only: Should see gray MENTIONED_IN edges
- Filter MENTIONED_IN only: Should see blue RELATES_TO edges
- Weight threshold 50%: Should hide RELATES_TO edges with weight <0.5
- Weight threshold 80%: Should only show strongest relationships

## Edge Cases to Verify

### 1. Graph with No Edges
**Scenario:** No documents indexed or no relationships extracted

**Expected Behavior:**
- [ ] Empty state message: "No graph data available"
- [ ] Legend still displays (for reference)
- [ ] No errors in browser console

### 2. Graph with Only One Edge Type
**Scenario:** Only RELATES_TO edges, no MENTIONED_IN

**Expected Behavior:**
- [ ] Legend shows all edge types (not filtered)
- [ ] Only blue edges visible in graph
- [ ] Tooltips work correctly

### 3. Edges with Missing Properties
**Scenario:** RELATES_TO edge without weight or description

**Expected Behavior:**
- [ ] Edge still renders (default width 1.5px)
- [ ] Tooltip shows "RELATES_TO" without weight
- [ ] No JavaScript errors

### 4. High-Density Graph
**Scenario:** Graph with >100 edges

**Expected Behavior:**
- [ ] Legend remains readable (not obscured by edges)
- [ ] Tooltips still functional
- [ ] Performance acceptable (<100ms interaction latency)

## Browser Compatibility Verification

### Desktop Browsers
- [ ] **Chrome 120+**: All features working
- [ ] **Firefox 121+**: All features working
- [ ] **Edge 120+**: All features working
- [ ] **Safari 17+**: All features working

### Tooltip Behavior
- [ ] Chrome: Native tooltip with OS styling
- [ ] Firefox: Native tooltip with OS styling
- [ ] Edge: Native tooltip with OS styling
- [ ] Safari: Native tooltip with macOS styling

**Note:** Tooltip styling varies by browser/OS (expected behavior)

## Performance Benchmarks

### Interaction Latency
- [ ] Edge hover → Tooltip appears: **<500ms**
- [ ] Filter toggle → Graph updates: **<300ms**
- [ ] Weight slider drag → Graph updates: **<500ms** (debounced)

### Rendering Performance
- [ ] Initial graph load (50 nodes, 100 edges): **<3s**
- [ ] Pan/zoom smoothness: **60 FPS** (no stuttering)
- [ ] Filter toggle smoothness: **60 FPS**

### Memory Usage
- [ ] Initial graph load: **<100MB additional memory**
- [ ] After 10 filter toggles: **<120MB** (no memory leaks)

**How to Measure:**
1. Open Chrome DevTools → Performance tab
2. Record performance while interacting with graph
3. Check FPS, memory usage, interaction latency

## Accessibility Verification

### Keyboard Navigation
- [ ] Tab key navigates to graph container
- [ ] Arrow keys pan graph (if implemented)
- [ ] Enter key selects node (if implemented)

### Screen Reader
- [ ] Legend has proper ARIA labels
- [ ] Edge filter controls have labels
- [ ] Graph stats are readable

**Note:** Canvas-based graphs have limited screen reader support (inherent limitation)

## Console Verification

### Expected Console Output
**No Errors Expected:**
- [ ] No "Uncaught TypeError" errors
- [ ] No "Cannot read property" errors
- [ ] No "Failed to fetch" errors (with backend running)

**Acceptable Warnings:**
- Warning about bundle size (710KB, see build output)
- Warning about dynamic imports (optimization suggestion)

## Testing Artifacts

### Screenshots to Capture
1. `edge-colors.png` - Graph showing all edge types with colors
2. `legend.png` - Close-up of legend in bottom-right corner
3. `tooltip-relates-to.png` - RELATES_TO edge tooltip with weight
4. `tooltip-mentioned-in.png` - MENTIONED_IN edge tooltip
5. `edge-width-comparison.png` - High-weight vs low-weight RELATES_TO edges
6. `filter-controls.png` - Edge filter UI controls
7. `graph-stats.png` - Graph stats showing edge counts

**Save Location:**
```
docs/sprints/sprint-34/screenshots/
```

### Video Recording (Optional)
**What to Record:**
1. Full graph interaction (pan, zoom, hover)
2. Edge filter toggle (before/after)
3. Weight threshold slider adjustment
4. Node selection with edge highlighting

**Save Location:**
```
docs/sprints/sprint-34/videos/graph-interaction.mp4
```

## Sign-Off Checklist

- [ ] All edge colors match specification
- [ ] Edge widths reflect weights correctly
- [ ] Legend displays correctly
- [ ] Tooltips show all required information
- [ ] Edge filters work as expected
- [ ] No console errors during interaction
- [ ] Performance meets benchmarks
- [ ] Screenshots captured and saved
- [ ] Verification document updated with findings

## Issues Encountered

**Format:**
```
Issue #1: [Description]
Severity: [Low/Medium/High/Critical]
Reproduction: [Steps to reproduce]
Expected: [Expected behavior]
Actual: [Actual behavior]
Screenshot: [Path to screenshot]
```

**Example:**
```
Issue #1: Tooltip flickers on rapid mouse movement
Severity: Low
Reproduction: Move mouse rapidly over multiple edges
Expected: Smooth tooltip transitions
Actual: Tooltip flickers/jumps between edges
Screenshot: docs/sprints/sprint-34/issues/tooltip-flicker.png
```

## Conclusion

**Date Verified:** _____________
**Verified By:** _____________
**Status:** [ ] Pass / [ ] Pass with Issues / [ ] Fail
**Notes:**

---

**References:**
- Implementation: `frontend/src/components/graph/GraphViewer.tsx`
- Tests: `frontend/e2e/graph/graph-visualization.spec.ts`
- Status Document: `docs/sprints/SPRINT_34_FEATURES_34_3_34_4_STATUS.md`

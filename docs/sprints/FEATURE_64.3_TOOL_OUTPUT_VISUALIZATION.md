# Feature 64.3: Tool Output Visualization in Chat UI (3 SP)

**Sprint:** 64 (oder Sprint 63.10 falls Kapazität)
**Priority:** P1 (High - User-requested)
**Status:** READY
**Dependencies:** Sprint 59 Tool Framework

---

## Rationale

**User Request:** "Es sollten die Returns der Tools darstellbar sein. Wenn ein Tool etwas schreibt (bash oder python etc) dann sollte das zu debugging zwecken auch ausgegeben werden können."

**Current State:**
- ✅ Backend streams `tool_calls` with results
- ✅ Frontend receives tool call data
- ❌ Frontend shows only tool names (`tools_used: string[]`)
- ❌ **No visualization of stdout, stderr, exit_code, command/code**

**Problem:**
User sees: "Bash tool was used ✓"
User CANNOT see: What command was executed, what it returned

**Target:**
User sees complete tool execution details:
- Command/Code executed
- stdout (standard output)
- stderr (errors)
- exit_code
- Execution duration
- Collapsible for long outputs

---

## Current Implementation Analysis

### Backend (Already Works)

**File:** `src/api/v1/chat.py` (lines 262-290)

```python
class ChatResponse(BaseModel):
    """Chat API response with sources and tool call information."""

    tool_calls: list[ToolCallInfo] = Field(
        default_factory=list, description="MCP tool calls made during query processing"
    )
```

**File:** `src/api/v1/chat.py` (lines 1365-1395)

```python
def _extract_tool_calls(result: dict[str, Any]) -> list[ToolCallInfo]:
    """Extract MCP tool call information from coordinator result."""
    tool_calls: list[ToolCallInfo] = []

    metadata = result.get("metadata", {})
    tool_call_data = metadata.get("tool_calls", [])

    for call in tool_call_data:
        if isinstance(call, dict):
            tool_info = ToolCallInfo(
                tool_name=call.get("tool_name", "unknown"),
                server=call.get("server", "unknown"),
                arguments=call.get("arguments", {}),
                result=call.get("result"),  # ← Contains stdout, stderr, exit_code!
                success=call.get("success", True),
                error=call.get("error"),
            )
            tool_calls.append(tool_info)

    return tool_calls
```

**What's in `result`:**
```python
# For Bash:
{
    "stdout": "Filesystem      Size  Used Avail Use% Mounted on\n...",
    "stderr": "",
    "exit_code": 0
}

# For Python:
{
    "stdout": "Result: 4.0\n",
    "stderr": "",
    "exit_code": 0,
    "execution_time_ms": 125
}
```

### Frontend (Missing)

**Current:** `frontend/src/types/reasoning.ts` (line 147)

```typescript
export interface ReasoningData {
  // ...
  tools_used: string[];  // ❌ Only names: ["bash", "python"]
  // ...
}
```

**What's Missing:**
- No `ToolExecutionStep` type (like `RetrievalStep`)
- No `ToolExecutionStep` component (like `RetrievalStep` component)
- No details about what was executed and what it returned

---

## Implementation Plan

### Task 1: Add TypeScript Types (1 SP)

**File:** `frontend/src/types/reasoning.ts` (update)

```typescript
/**
 * Sprint 64 Feature 64.3: Tool execution details
 */
export interface ToolExecutionStep {
  /** Tool name (bash, python, etc.) */
  tool_name: string;

  /** Server that executed the tool */
  server: string;

  /** Command or code that was executed */
  input: {
    command?: string;  // For bash
    code?: string;     // For python
    arguments?: Record<string, any>;  // Other args
  };

  /** Execution result */
  output: {
    stdout?: string;
    stderr?: string;
    exit_code?: number;
    success: boolean;
    error?: string;
  };

  /** Execution duration in milliseconds */
  duration_ms?: number;

  /** ISO timestamp when tool was executed */
  timestamp: string;
}

/**
 * Update ReasoningData to include tool execution steps
 */
export interface ReasoningData {
  intent: IntentInfo;
  retrieval_steps: RetrievalStep[];

  /** @deprecated Use tool_execution_steps instead */
  tools_used: string[];

  /** Sprint 64 Feature 64.3: Detailed tool execution information */
  tool_execution_steps?: ToolExecutionStep[];

  total_duration_ms?: number;
  phase_events?: PhaseEvent[];
  four_way_results?: FourWayResults;
  // ...
}
```

### Task 2: Create ToolExecutionStep Component (1 SP)

**File:** `frontend/src/components/chat/ToolExecutionStep.tsx` (new)

```tsx
/**
 * ToolExecutionStep Component
 * Sprint 64 Feature 64.3: Display tool execution details
 *
 * Shows tool name, executed command/code, stdout, stderr, and exit code.
 * Similar to RetrievalStep but for tool executions.
 */

import { useState } from 'react';
import { Terminal, Code, ChevronDown, ChevronRight, CheckCircle, XCircle } from 'lucide-react';
import type { ToolExecutionStep as ToolExecutionStepType } from '../../types/reasoning';

interface ToolExecutionStepProps {
  step: ToolExecutionStepType;
  stepNumber: number;
  isLast?: boolean;
}

/**
 * Get icon for tool type
 */
function getToolIcon(toolName: string): React.ReactNode {
  const iconClass = 'w-4 h-4';
  switch (toolName.toLowerCase()) {
    case 'bash':
      return <Terminal className={iconClass} />;
    case 'python':
      return <Code className={iconClass} />;
    default:
      return <Terminal className={iconClass} />;
  }
}

/**
 * Get color styling for tool type
 */
function getToolColor(toolName: string): { bg: string; text: string; border: string } {
  switch (toolName.toLowerCase()) {
    case 'bash':
      return {
        bg: 'bg-slate-50',
        text: 'text-slate-700',
        border: 'border-slate-200',
      };
    case 'python':
      return {
        bg: 'bg-cyan-50',
        text: 'text-cyan-700',
        border: 'border-cyan-200',
      };
    default:
      return {
        bg: 'bg-gray-50',
        text: 'text-gray-700',
        border: 'border-gray-200',
      };
  }
}

/**
 * Format duration
 */
function formatDuration(ms: number): string {
  if (ms < 1) return '<1ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function ToolExecutionStep({ step, stepNumber, isLast = false }: ToolExecutionStepProps) {
  const [isExpanded, setIsExpanded] = useState(true); // Expanded by default for debugging
  const colors = getToolColor(step.tool_name);

  // Get input (command or code)
  const input = step.input.command || step.input.code || JSON.stringify(step.input.arguments);

  // Check if output is present
  const hasStdout = step.output.stdout && step.output.stdout.trim().length > 0;
  const hasStderr = step.output.stderr && step.output.stderr.trim().length > 0;

  return (
    <div className="relative" data-testid={`tool-execution-step-${stepNumber}`}>
      {/* Connection line to next step */}
      {!isExpanded && !isLast && (
        <div className="absolute left-[17px] top-[36px] w-0.5 h-[calc(100%-20px)] bg-gray-200" />
      )}

      <div className="flex items-start gap-3">
        {/* Step icon */}
        <div
          className={`flex-shrink-0 w-9 h-9 rounded-lg ${colors.bg} ${colors.text} flex items-center justify-center border ${colors.border}`}
        >
          {getToolIcon(step.tool_name)}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 pb-4">
          {/* Header row */}
          <div
            className="flex items-center justify-between gap-2 mb-1 cursor-pointer hover:bg-gray-50 p-1 -ml-1 rounded"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-gray-500">{stepNumber}.</span>
              <span className="font-medium text-gray-900 text-sm capitalize">
                {step.tool_name} Tool
              </span>
              {step.output.success ? (
                <CheckCircle className="w-4 h-4 text-green-600" />
              ) : (
                <XCircle className="w-4 h-4 text-red-600" />
              )}
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-gray-400" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-400" />
              )}
            </div>
            <span className="text-xs text-gray-500 flex items-center gap-1">
              {step.duration_ms && formatDuration(step.duration_ms)}
            </span>
          </div>

          {/* Expandable details */}
          {isExpanded && (
            <div className="mt-2 space-y-2">
              {/* Input (command or code) */}
              <div>
                <div className="text-xs font-medium text-gray-500 mb-1">
                  {step.input.command ? 'Command' : 'Code'}:
                </div>
                <pre className="text-xs bg-gray-900 text-gray-100 p-2 rounded overflow-x-auto font-mono">
                  {input}
                </pre>
              </div>

              {/* stdout */}
              {hasStdout && (
                <div>
                  <div className="text-xs font-medium text-gray-500 mb-1">Output:</div>
                  <pre className="text-xs bg-gray-50 text-gray-800 p-2 rounded border border-gray-200 overflow-x-auto font-mono max-h-48 overflow-y-auto">
                    {step.output.stdout}
                  </pre>
                </div>
              )}

              {/* stderr */}
              {hasStderr && (
                <div>
                  <div className="text-xs font-medium text-red-600 mb-1">Errors:</div>
                  <pre className="text-xs bg-red-50 text-red-800 p-2 rounded border border-red-200 overflow-x-auto font-mono max-h-48 overflow-y-auto">
                    {step.output.stderr}
                  </pre>
                </div>
              )}

              {/* Error message (if failed) */}
              {!step.output.success && step.output.error && (
                <div>
                  <div className="text-xs font-medium text-red-600 mb-1">Error:</div>
                  <div className="text-xs bg-red-50 text-red-800 p-2 rounded border border-red-200">
                    {step.output.error}
                  </div>
                </div>
              )}

              {/* Exit code */}
              {step.output.exit_code !== undefined && (
                <div className="flex items-center gap-4 text-xs text-gray-600">
                  <span>
                    Exit Code:{' '}
                    <span
                      className={`font-medium ${
                        step.output.exit_code === 0 ? 'text-green-600' : 'text-red-600'
                      }`}
                    >
                      {step.output.exit_code}
                    </span>
                  </span>
                  <span>
                    Server: <span className="font-medium">{step.server}</span>
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

### Task 3: Integrate into ReasoningPanel (1 SP)

**File:** `frontend/src/components/chat/ReasoningPanel.tsx` (update)

```tsx
import { ToolExecutionStep } from './ToolExecutionStep';

// In renderReasoningSteps():
<div className="space-y-3">
  {/* Intent Classification */}
  <IntentClassification intent={reasoning.intent} />

  {/* Retrieval Steps */}
  {reasoning.retrieval_steps.map((step, index) => (
    <RetrievalStep
      key={`retrieval-${index}`}
      step={step}
      isLast={
        index === reasoning.retrieval_steps.length - 1 &&
        !reasoning.tool_execution_steps?.length
      }
    />
  ))}

  {/* NEW: Tool Execution Steps (Sprint 64 Feature 64.3) */}
  {reasoning.tool_execution_steps && reasoning.tool_execution_steps.length > 0 && (
    <div className="mt-4 border-t border-gray-200 pt-4">
      <h4 className="text-sm font-medium text-gray-700 mb-3">
        Tools Executed ({reasoning.tool_execution_steps.length})
      </h4>
      {reasoning.tool_execution_steps.map((toolStep, index) => (
        <ToolExecutionStep
          key={`tool-${index}`}
          step={toolStep}
          stepNumber={reasoning.retrieval_steps.length + index + 1}
          isLast={index === reasoning.tool_execution_steps.length - 1}
        />
      ))}
    </div>
  )}
</div>
```

---

## Backend Enhancement (if needed)

**File:** `src/api/v1/chat.py` (verify)

Ensure `tool_calls` are streamed with full details:

```python
# In streaming response, emit tool execution event:
yield _format_sse_message({
    "type": "tool_execution",
    "data": {
        "tool_name": "bash",
        "input": {"command": "df -h"},
        "output": {
            "stdout": "...",
            "stderr": "",
            "exit_code": 0,
            "success": True
        },
        "duration_ms": 234,
        "timestamp": datetime.utcnow().isoformat()
    }
})
```

**Or** include in `reasoning_complete` event:

```python
yield _format_sse_message({
    "type": "reasoning_complete",
    "data": {
        "intent": {...},
        "retrieval_steps": [...],
        "tool_execution_steps": [  # NEW
            {
                "tool_name": "bash",
                "server": "local-mcp",
                "input": {"command": "df -h"},
                "output": {"stdout": "...", "stderr": "", "exit_code": 0, "success": True},
                "duration_ms": 234,
                "timestamp": "2025-12-23T19:00:00Z"
            }
        ]
    }
})
```

---

## Success Criteria

| Criterion | Target | Verification |
|-----------|--------|--------------|
| Tool execution visible in UI | 100% | Manual check |
| Stdout displayed correctly | Syntax highlighting | Frontend test |
| Stderr shown in red | Distinct styling | Frontend test |
| Exit code displayed | With color coding | Frontend test |
| Collapsible output | Expand/collapse works | UI test |
| Long output scrollable | max-h with scroll | UI test |
| Multiple tools shown | All executions listed | Integration test |

---

## Testing Strategy

### Unit Tests

**File:** `frontend/src/components/chat/ToolExecutionStep.test.tsx`

```tsx
describe('ToolExecutionStep', () => {
  it('displays bash command execution', () => {
    const step: ToolExecutionStepType = {
      tool_name: 'bash',
      server: 'local-mcp',
      input: { command: 'echo "Hello"' },
      output: { stdout: 'Hello\n', stderr: '', exit_code: 0, success: true },
      duration_ms: 50,
      timestamp: '2025-12-23T19:00:00Z',
    };

    render(<ToolExecutionStep step={step} stepNumber={1} />);

    expect(screen.getByText('Bash Tool')).toBeInTheDocument();
    expect(screen.getByText('echo "Hello"')).toBeInTheDocument();
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Exit Code: 0')).toBeInTheDocument();
  });

  it('displays python code execution', () => {
    const step: ToolExecutionStepType = {
      tool_name: 'python',
      server: 'local-mcp',
      input: { code: 'print("Hello")' },
      output: { stdout: 'Hello\n', stderr: '', exit_code: 0, success: true },
      duration_ms: 125,
      timestamp: '2025-12-23T19:00:00Z',
    };

    render(<ToolExecutionStep step={step} stepNumber={1} />);

    expect(screen.getByText('Python Tool')).toBeInTheDocument();
    expect(screen.getByText('print("Hello")')).toBeInTheDocument();
  });

  it('shows stderr in red when present', () => {
    const step: ToolExecutionStepType = {
      tool_name: 'bash',
      server: 'local-mcp',
      input: { command: 'cat nonexistent.txt' },
      output: {
        stdout: '',
        stderr: 'cat: nonexistent.txt: No such file or directory\n',
        exit_code: 1,
        success: false,
      },
      duration_ms: 25,
      timestamp: '2025-12-23T19:00:00Z',
    };

    render(<ToolExecutionStep step={step} stepNumber={1} />);

    expect(screen.getByText('Errors:')).toBeInTheDocument();
    expect(screen.getByText(/No such file or directory/)).toBeInTheDocument();
  });

  it('collapses and expands on click', () => {
    const step: ToolExecutionStepType = {
      tool_name: 'bash',
      server: 'local-mcp',
      input: { command: 'echo "test"' },
      output: { stdout: 'test\n', stderr: '', exit_code: 0, success: true },
      duration_ms: 30,
      timestamp: '2025-12-23T19:00:00Z',
    };

    render(<ToolExecutionStep step={step} stepNumber={1} />);

    // Initially expanded
    expect(screen.getByText('Command:')).toBeInTheDocument();

    // Click header to collapse
    fireEvent.click(screen.getByText('Bash Tool'));
    expect(screen.queryByText('Command:')).not.toBeInTheDocument();

    // Click again to expand
    fireEvent.click(screen.getByText('Bash Tool'));
    expect(screen.getByText('Command:')).toBeInTheDocument();
  });
});
```

### Integration Test

**File:** `tests/integration/api/test_tool_output_in_chat.py`

```python
"""Test tool execution output appears in chat response.

Sprint 64 Feature 64.3.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.mark.integration
def test_tool_execution_in_reasoning_complete():
    """Test that tool execution details are included in reasoning_complete event."""
    client = TestClient(app)

    # Send query that triggers tool use
    response = client.post(
        "/api/v1/chat/",
        json={
            "query": "What is the current date?",  # LLM should use bash tool
            "session_id": "test-session",
            "include_tool_calls": True,
        },
        stream=True,
    )

    events = []
    for line in response.iter_lines():
        if line.startswith(b"data:"):
            data = json.loads(line[6:])
            events.append(data)

    # Find reasoning_complete event
    reasoning_event = next(
        (e for e in events if e.get("type") == "reasoning_complete"), None
    )

    assert reasoning_event is not None
    reasoning = reasoning_event["data"]

    # Verify tool_execution_steps is present
    assert "tool_execution_steps" in reasoning
    assert len(reasoning["tool_execution_steps"]) > 0

    # Verify first tool execution has required fields
    tool_step = reasoning["tool_execution_steps"][0]
    assert "tool_name" in tool_step
    assert "input" in tool_step
    assert "output" in tool_step
    assert tool_step["output"]["success"] in [True, False]
```

---

## User Experience

**Before (Sprint 59):**
```
User: "What is the current date?"
Assistant: "The current date is December 23, 2025."

[Reasoning Panel]
✓ Intent: Factual
1. Qdrant Vector Search - 5 results
2. Tools Used: bash  ← Only name, no details
```

**After (Sprint 64 Feature 64.3):**
```
User: "What is the current date?"
Assistant: "The current date is December 23, 2025."

[Reasoning Panel]
✓ Intent: Factual
1. Qdrant Vector Search - 5 results

Tools Executed (1)
2. Bash Tool ✓ [50ms] [▼]
   Command:
   > date "+%Y-%m-%d"

   Output:
   2025-12-23

   Exit Code: 0 | Server: local-mcp
```

---

## Timeline

| Task | Duration | Deliverables |
|------|----------|--------------|
| 1. TypeScript Types | 0.5 day | Updated reasoning.ts with ToolExecutionStep |
| 2. ToolExecutionStep Component | 1 day | New component with syntax highlighting |
| 3. ReasoningPanel Integration | 0.5 day | Tool steps shown after retrieval steps |
| **Total** | **2 days** | **3 SP** |

---

## Alternative: Simpler Version (2 SP)

If 3 SP is too much, here's a minimal version:

**Simple ToolOutput Component (1 SP):**
```tsx
function ToolOutput({ toolCall }) {
  return (
    <div className="bg-gray-50 p-3 rounded border">
      <div className="font-medium">{toolCall.tool_name}</div>
      {toolCall.result?.stdout && (
        <pre className="text-xs mt-2">{toolCall.result.stdout}</pre>
      )}
    </div>
  );
}
```

Add to ChatMessage component after answer text.

---

**Status:** Ready for Sprint 64 (or Sprint 63.10 if priority)
**Requested by:** User
**Impact:** HIGH - Essential for debugging and transparency

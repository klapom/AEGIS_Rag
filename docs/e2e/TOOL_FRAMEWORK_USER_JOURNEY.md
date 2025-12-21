# Tool Framework User Journey

**Sprint 59**: Agentic Features & Tool Use
**Date**: 2025-12-21
**Status**: Complete

---

## Overview

This document describes the end-to-end user journeys for the Sprint 59 Tool Framework, including:
- Bash command execution with sandboxing
- Python code execution with AST validation
- Docker-based isolation
- Agentic search with multi-step reasoning

---

## Journey 1: Execute Bash Command via API

### Scenario
Data analyst wants to run a bash command to check system status.

### User Steps

1. **Send API Request**
   ```bash
   curl -X POST http://localhost:8000/api/v1/tools/execute \
     -H "Content-Type: application/json" \
     -d '{
       "tool_name": "bash",
       "parameters": {
         "command": "df -h",
         "timeout": 30
       }
     }'
   ```

2. **Receive Response**
   ```json
   {
     "result": {
       "stdout": "Filesystem      Size  Used Avail Use% Mounted on\n...",
       "stderr": "",
       "exit_code": 0,
       "success": true
     }
   }
   ```

### System Flow

```
User Request
    ↓
API Endpoint (/api/v1/tools/execute)
    ↓
ToolExecutor.execute("bash", params)
    ↓
Security Validation (bash_security.is_command_safe)
    ↓
[If requires_sandbox=True]
    ↓
DockerSandbox.run_bash(command)
    ↓
Docker Container (isolated, resource-limited)
    ↓
Command Execution
    ↓
Result Formatting
    ↓
Response to User
```

### Security Checks

- ✅ Command validated against blacklist
- ✅ Dangerous patterns detected (rm -rf, eval, sudo, etc.)
- ✅ Environment sanitized (PATH, HOME restricted)
- ✅ Timeout enforced (max 300 seconds)
- ✅ Sandbox isolation (if enabled)

### Expected Outcomes

- **Success**: Command executes, returns stdout/stderr/exit_code
- **Blocked**: Dangerous command rejected with error message
- **Timeout**: Long-running command killed after timeout
- **Error**: Permission denied, working dir not found, etc.

---

## Journey 2: Execute Python Code Safely

### Scenario
Developer wants to run Python code for data analysis.

### User Steps

1. **Send API Request**
   ```bash
   curl -X POST http://localhost:8000/api/v1/tools/execute \
     -H "Content-Type: application/json" \
     -d '{
       "tool_name": "python",
       "parameters": {
         "code": "import math\nresult = math.sqrt(16)\nprint(result)",
         "timeout": 30
       }
     }'
   ```

2. **Receive Response**
   ```json
   {
     "result": {
       "output": "4.0\n",
       "variables": {"result": 4.0},
       "success": true
     }
   }
   ```

### System Flow

```
User Request
    ↓
API Endpoint
    ↓
ToolExecutor.execute("python", params)
    ↓
AST Validation (python_security.validate_python_code)
    ↓
[Check imports, builtins, attributes]
    ↓
[If valid]
    ↓
Execute with Restricted Globals
    ↓
Capture stdout, variables
    ↓
Result Formatting
    ↓
Response to User
```

### Security Checks

- ✅ AST analysis blocks dangerous imports (os, subprocess, sys)
- ✅ Dangerous builtins blocked (eval, exec, __import__)
- ✅ Dangerous attributes blocked (__class__, __globals__)
- ✅ Restricted globals environment (safe modules only)
- ✅ Code complexity limit (max 1000 lines)
- ✅ Timeout enforced

### Allowed Modules

```python
✅ math, json, datetime, re
✅ collections, itertools, functools
✅ string, random, statistics
✅ decimal, fractions, uuid
✅ hashlib, base64

❌ os, subprocess, sys, shutil
❌ socket, ctypes, multiprocessing
❌ importlib, __builtins__
```

---

## Journey 3: Deep Research with Agentic Search

### Scenario
User asks complex question requiring multi-step research.

### User Steps

1. **Send Research Request**
   ```bash
   curl -X POST http://localhost:8000/api/v1/chat/research \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What are the latest advances in transformer architectures?",
       "max_iterations": 3
     }'
   ```

2. **Receive Streaming Response**
   ```
   data: {"event": "plan_created", "queries": ["...", "...", "..."]}
   data: {"event": "search_started", "iteration": 1}
   data: {"event": "search_completed", "results": 15}
   data: {"event": "evaluation", "sufficient": false}
   data: {"event": "search_started", "iteration": 2}
   ...
   data: {"event": "synthesis", "text": "Based on research..."}
   ```

### System Flow (LangGraph State Machine)

```
START
    ↓
plan_node (Research Planning)
    ├─ Analyze query with LLM
    ├─ Generate 3-5 search queries
    └─ Evaluate plan quality
    ↓
search_node (Multi-Source Search)
    ├─ Execute vector search (Qdrant)
    ├─ Execute graph search (Neo4j)
    ├─ Deduplicate results
    └─ Accumulate findings
    ↓
evaluate_node (Result Evaluation)
    ├─ Calculate coverage metrics
    ├─ Check if sufficient (≥5 results, score >0.5)
    ├─ Increment iteration counter
    └─ Decide: continue or synthesize?
    ↓
[If not sufficient && iteration < max]
    ↓
search_node (Continue Research)
    ↓
evaluate_node
    ↓
...

[If sufficient OR max iterations reached]
    ↓
synthesize_node (Result Synthesis)
    ├─ Format results for context
    ├─ Generate synthesis with LLM
    ├─ Extract key points
    └─ Create structured summary
    ↓
END
```

### Quality Metrics

- **Coverage**: `min(num_results / 10.0, 1.0)` → Ideal: 10+ results
- **Diversity**: `num_sources / 2.0` → Ideal: vector + graph
- **Quality**: `avg_score` → Threshold: > 0.5
- **Sufficient**: `num_results ≥ 5 AND avg_score > 0.5`

### Expected Outcomes

- **Iteration 1**: Initial searches, 5-10 results
- **Iteration 2**: Refined searches if needed, 10-20 total results
- **Iteration 3**: Final synthesis with comprehensive answer
- **Early Exit**: If sufficient quality reached before max iterations

---

## Journey 4: Tool Framework Integration in Chat

### Scenario
Chat conversation where LLM uses tools autonomously.

### User Steps

1. **Send Chat Message**
   ```bash
   curl -X POST http://localhost:8000/api/v1/chat \
     -H "Content-Type: application/json" \
     -d '{
       "messages": [
         {"role": "user", "content": "What files are in the current directory?"}
       ],
       "use_tools": true
     }'
   ```

2. **LLM Decides to Use Tool**
   ```json
   {
     "tool_calls": [
       {
         "name": "bash",
         "parameters": {"command": "ls -la"}
       }
     ]
   }
   ```

3. **Tool Execution**
   - System executes bash tool
   - Returns results to LLM
   - LLM synthesizes response

4. **Receive Final Response**
   ```json
   {
     "response": "The current directory contains the following files:\n- file1.txt\n- file2.py\n...",
     "tool_calls_made": 1
   }
   ```

### System Flow

```
User Message
    ↓
AegisLLMProxy.chat_with_tools()
    ├─ Pass available tools schema
    ├─ LLM generates response + tool calls
    └─ [If tool_calls present]
        ↓
ToolExecutor.batch_execute(tool_calls)
    ├─ Execute each tool
    ├─ Validate parameters
    ├─ Apply sandboxing if required
    └─ Collect results
    ↓
Add tool results to conversation
    ↓
LLM generates final response
    ↓
Return to user
```

---

## Testing User Journeys

### E2E Tests with Playwright

Located in: `tests/e2e/test_tool_framework_journeys.py`

```python
@pytest.mark.e2e
async def test_journey_1_bash_execution(page):
    """Test complete bash execution journey."""
    # Navigate to tool execution page
    await page.goto("http://localhost:5179/tools")

    # Select bash tool
    await page.click("text=Bash Command")

    # Enter command
    await page.fill("textarea[name='command']", "echo 'test'")

    # Execute
    await page.click("button:has-text('Execute')")

    # Wait for result
    result = await page.locator(".result-output").text_content()
    assert "test" in result
```

### Performance Expectations

| Operation | Target Latency (p95) |
|-----------|----------------------|
| Bash execution (simple) | < 500ms |
| Python execution (simple) | < 300ms |
| Research planning | < 1s |
| Single search iteration | < 2s |
| Full research workflow (3 iterations) | < 10s |
| Tool schema generation | < 50ms |

---

## Security Considerations

### Threat Model

| Threat | Mitigation |
|--------|-----------|
| **Command Injection** | Blacklist + pattern matching |
| **Resource Exhaustion** | Timeout + memory limits |
| **Data Exfiltration** | Network isolation, blocked netcat/curl |
| **Privilege Escalation** | No sudo/su, read-only filesystem |
| **Code Execution** | AST validation, restricted globals |
| **Fork Bomb** | Process limits, blocked patterns |

### Defense Layers

```
Layer 1: Input Validation (AST, blacklist)
    ↓
Layer 2: Restricted Environment (limited imports, sanitized env)
    ↓
Layer 3: Docker Sandbox (network isolation, resource limits)
    ↓
Layer 4: Timeout Enforcement (kill after max time)
    ↓
Layer 5: Result Truncation (prevent memory exhaustion)
```

---

## Troubleshooting

### Common Issues

#### 1. "Docker not installed" Error

**Symptom**: Sandbox execution fails with ImportError

**Solution**:
```bash
pip install docker
# Or disable sandboxing:
SANDBOX_ENABLED=false
```

#### 2. "Command blocked" Error

**Symptom**: Safe command rejected

**Solution**: Check security patterns in `bash_security.py`, adjust if necessary

#### 3. "Module blocked" Error

**Symptom**: Legitimate Python module blocked

**Solution**: Add to allowed list in `python_security.py`

#### 4. Research Agent Times Out

**Symptom**: Agentic search never completes

**Solution**: Reduce max_iterations or increase timeout per search

---

## Future Enhancements

- [ ] Add more built-in tools (file operations, network requests)
- [ ] Implement process-level sandboxing (without Docker)
- [ ] Add caching for research results
- [ ] Support streaming tool execution results
- [ ] Add tool usage analytics and monitoring
- [ ] Implement rate limiting per tool
- [ ] Add tool versioning and deprecation

---

**Document Version**: 1.0
**Last Updated**: 2025-12-21
**Next Review**: Sprint 60

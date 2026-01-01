# Deep Research & Tool Use Integration Design

**Date:** 2026-01-01
**Status:** Design Phase
**Author:** Infrastructure Agent + Backend Agent

## Executive Summary

Integration von Deep Research (Multi-Turn Iterative Search) und Tool Use (MCP Tools) in die AEGIS RAG Architektur nach LangGraph Best Practices.

## Current Architecture Analysis

### Existing Chat Graph (Normal Mode)
```
START → router → [hybrid_search | vector_search | graph_query | memory]
                        ↓              ↓              ↓           ↓
                     answer         answer          END         END
                        ↓              ↓
                       END            END
```

**Nodes:**
- `router`: Intent classification (hybrid/vector/graph/memory)
- `hybrid_search`: Parallel Vector + Graph search
- `vector_search`: Vector + BM25 only
- `graph_query`: Graph search only (LightRAG)
- `memory`: Graphiti temporal memory
- `answer`: LLM answer generation with citations

**State:** `AgentState` (src/agents/state.py)

### Existing Action Agent (Isolated)
```
select_tool → execute_tool → handle_result → END
```

**Location:** `src/agents/action_agent.py`
**State:** `ActionAgentState`
**Problem:** NOT integrated into main graph!

## LangGraph Best Practices (from Context7 Research)

### 1. ReAct Pattern for Tool Use
```python
# Pattern from LangGraph docs
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools))

workflow.add_conditional_edges(
    "agent",
    should_continue,  # Check last_message.tool_calls
    {"continue": "tools", "end": END}
)
workflow.add_edge("tools", "agent")  # Cycle back!
```

**Key Insights:**
- Tools as separate node AFTER agent
- Conditional edge checks if LLM requested tools
- Normal edge cycles back to agent for follow-up
- Enables multi-turn tool conversations

### 2. Supervisor Pattern for Multi-Agent
```python
# Pattern from LangGraph docs
graph.add_node("supervisor", supervisor_node)
graph.add_node("research_agent", create_react_agent())
graph.add_node("math_agent", create_math_agent())

graph.add_conditional_edges(
    "supervisor",
    route_to_agent,
    {"research_agent": "research_agent", "FINISH": END}
)
graph.add_edge("research_agent", "supervisor")  # Report back
```

**Key Insights:**
- Supervisor coordinates specialized agents
- Workers return Command(goto="supervisor")
- Enables complex delegation patterns

### 3. Subgraphs for Isolation
```python
research_subgraph = create_react_agent(
    model=llm,
    tools=research_tools,
    prompt="Research specialist system prompt"
)

main_graph.add_node("research", research_subgraph)
```

**Key Insights:**
- Isolated state management
- Reusable agent components
- Clear boundaries

## Proposed Architecture

### Option A: Two Separate Graphs (RECOMMENDED)

#### 1. Enhanced Chat Graph (with Tool Use)
```
START → router → [hybrid_search | vector_search | graph_query | memory]
                        ↓              ↓              ↓           ↓
                     answer         answer          END         END
                        ↓              ↓
                should_use_tools? should_use_tools?
                    ↓       ↓        ↓       ↓
                  tools    END     tools    END
                    ↓                ↓
                  answer          answer  (ReAct Loop)
                    ↓                ↓
                   END              END
```

**New Nodes:**
- `tools`: ToolNode with MCP tools (from ActionAgent)
- `should_use_tools`: Conditional function checking tool_calls

**Changes:**
- Remove direct `answer → END` edges
- Add `answer → should_use_tools → [tools | END]`
- Add `tools → answer` cycle for follow-up

#### 2. New Deep Research Graph (Supervisor Pattern)
```
START → supervisor → [planner | searcher | synthesizer]
            ↓              ↓         ↓           ↓
      route_decision    planning  search    synthesis
            ↓              ↓         ↓           ↓
    [continue|finish]  supervisor  supervisor  END
```

**Nodes:**
- `supervisor`: Coordinates research workflow
- `planner`: LLM task decomposition (uses LLMTask API!)
- `searcher`: Executes queries via **CoordinatorAgent reuse**
- `synthesizer`: Aggregates results (uses AnswerGenerator!)

**Key Design:**
- **Reuse existing agents** instead of duplicate code
- Supervisor delegates to planner/searcher/synthesizer
- Searcher calls `coordinator.process_query()` internally
- No duplicate search logic!

### Option B: Single Graph with Subgraphs

```
START → mode_router → [chat_mode | research_mode]
                           ↓              ↓
                      chat_graph   research_subgraph
                           ↓              ↓
                          END            END
```

**Pros:** Single entry point, unified state
**Cons:** More complex, harder to maintain
**Verdict:** NOT recommended (violates separation of concerns)

## Detailed Implementation Plan

### Phase 1: Fix Deep Research (Reuse Pattern)

**File:** `src/agents/research/research_graph.py` (new)

```python
from langgraph.graph import StateGraph, END, START
from src.agents.coordinator import get_coordinator
from src.agents.answer_generator import get_answer_generator

class ResearchSupervisorState(TypedDict):
    """Supervisor state for research workflow."""
    original_query: str
    sub_queries: list[str]
    iteration: int
    max_iterations: int
    all_contexts: list[dict]
    synthesis: str
    should_continue: bool

async def planner_node(state: ResearchSupervisorState):
    """Plan research strategy using LLMTask API."""
    from src.domains.llm_integration.models import LLMTask, TaskType
    from src.domains.llm_integration.proxy import get_aegis_llm_proxy

    proxy = get_aegis_llm_proxy()

    task = LLMTask(
        task_type=TaskType.GENERATION,
        prompt=f"Decompose this question into 3-5 search queries: {state['original_query']}",
        max_tokens=500,
        temperature=0.7
    )

    response = await proxy.generate(task)
    sub_queries = parse_plan(response.content)

    return {"sub_queries": sub_queries}

async def searcher_node(state: ResearchSupervisorState):
    """Execute searches by REUSING CoordinatorAgent."""
    coordinator = get_coordinator()  # Reuse!

    all_contexts = state.get("all_contexts", [])

    for query in state["sub_queries"]:
        # Reuse existing search infrastructure
        result = await coordinator.process_query(
            query=query,
            intent="hybrid"  # Always hybrid for research
        )
        all_contexts.extend(result.get("retrieved_contexts", []))

    return {
        "all_contexts": all_contexts,
        "iteration": state["iteration"] + 1
    }

async def synthesizer_node(state: ResearchSupervisorState):
    """Synthesize findings using AnswerGenerator."""
    generator = get_answer_generator()  # Reuse!

    synthesis = await generator.generate_with_citations(
        query=state["original_query"],
        contexts=state["all_contexts"]
    )

    return {"synthesis": synthesis}

def create_research_graph():
    """Create research supervisor graph."""
    graph = StateGraph(ResearchSupervisorState)

    # Add nodes
    graph.add_node("planner", planner_node)
    graph.add_node("searcher", searcher_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("synthesizer", synthesizer_node)

    # Build workflow
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "searcher")
    graph.add_edge("searcher", "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        should_continue_research,
        {"continue": "searcher", "synthesize": "synthesizer"}
    )
    graph.add_edge("synthesizer", END)

    return graph.compile()
```

**Benefits:**
- ✅ Reuses `CoordinatorAgent` (no duplicate search code)
- ✅ Reuses `AnswerGenerator` (no duplicate LLM code)
- ✅ Uses correct `LLMTask` API (fixes TypeError)
- ✅ Supervisor pattern for coordination
- ✅ Easy to maintain

### Phase 2: Integrate Tool Use into Chat Graph

**File:** `src/agents/graph.py` (modify)

```python
from langgraph.prebuilt import ToolNode
from src.components.mcp.client import get_mcp_client
from src.agents.tool_selector import ToolSelector

async def should_use_tools(state: dict) -> str:
    """Conditional edge: Check if LLM requested tool use."""
    messages = state.get("messages", [])
    if not messages:
        return "end"

    last_message = messages[-1]

    # Check if answer contains tool call markers
    # (Could be enhanced with LLM decision)
    answer = state.get("answer", "")
    if "[TOOL:" in answer or needs_external_data(answer):
        return "tools"

    return "end"

async def tools_node(state: dict):
    """Execute MCP tools using existing ActionAgent logic."""
    from src.agents.action_agent import ActionAgent
    from src.components.mcp.client import get_mcp_client
    from src.components.mcp.tool_executor import ToolExecutor

    client = get_mcp_client()
    executor = ToolExecutor(client)
    action_agent = ActionAgent(client, executor)

    # Extract tool request from answer
    tool_request = extract_tool_request(state.get("answer", ""))

    # Execute tool
    result = await action_agent.graph.ainvoke({
        "action": tool_request["action"],
        "parameters": tool_request["parameters"],
        "messages": []
    })

    # Add tool result to contexts for re-generation
    tool_context = {
        "text": result["tool_result"],
        "source": "tool",
        "tool_name": result["selected_tool"]
    }

    contexts = state.get("retrieved_contexts", [])
    contexts.append(tool_context)

    return {"retrieved_contexts": contexts, "needs_regeneration": True}

def create_base_graph_with_tools() -> StateGraph:
    """Enhanced graph with tool support."""
    graph = StateGraph(AgentState)

    # Existing nodes
    graph.add_node("router", router_node)
    graph.add_node("hybrid_search", hybrid_search_node)
    graph.add_node("vector_search", vector_search_node)
    graph.add_node("graph_query", graph_query_node)
    graph.add_node("memory", memory_node)
    graph.add_node("answer", llm_answer_node)

    # NEW: Tool node
    graph.add_node("tools", tools_node)

    # Existing edges
    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", route_query, {...})
    graph.add_edge("hybrid_search", "answer")
    graph.add_edge("vector_search", "answer")

    # NEW: Tool use edges (ReAct pattern)
    graph.add_conditional_edges(
        "answer",
        should_use_tools,
        {"tools": "tools", "end": END}
    )
    graph.add_edge("tools", "answer")  # Cycle back!

    return graph
```

**Benefits:**
- ✅ Reuses existing ActionAgent logic
- ✅ ReAct pattern for tool conversations
- ✅ Minimal changes to existing code
- ✅ Tool results added to contexts for re-generation

### Phase 3: Integrate Tool Use into Deep Research

**File:** `src/agents/research/research_graph.py` (enhance)

```python
def create_research_graph_with_tools():
    """Research graph with tool support."""
    graph = StateGraph(ResearchSupervisorState)

    # Standard research nodes
    graph.add_node("planner", planner_node)
    graph.add_node("searcher", searcher_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("synthesizer", synthesizer_node)

    # NEW: Tool node for research
    graph.add_node("research_tools", research_tools_node)

    # Enhanced supervisor can request tools
    graph.add_conditional_edges(
        "supervisor",
        supervisor_decision,
        {
            "continue": "searcher",
            "use_tools": "research_tools",  # NEW
            "synthesize": "synthesizer"
        }
    )
    graph.add_edge("research_tools", "supervisor")

    return graph.compile()
```

## File Structure

```
src/agents/
├── graph.py                          # Modified: Add tool use
├── research/
│   ├── research_graph.py             # NEW: Supervisor-based research
│   ├── planner.py                    # Modified: Use LLMTask API
│   ├── searcher.py                   # Modified: Reuse CoordinatorAgent
│   └── synthesizer.py                # Modified: Reuse AnswerGenerator
└── tools/
    ├── tool_integration.py           # NEW: Tool use helpers
    └── tool_decision.py              # NEW: Should use tools logic
```

## Migration Strategy

### Step 1: Fix Deep Research (No Breaking Changes)
1. Create new `research_graph.py` with supervisor pattern
2. Modify `planner.py` to use LLMTask
3. Modify `searcher.py` to call CoordinatorAgent
4. Modify `synthesizer.py` to use AnswerGenerator
5. Update `/api/v1/research/query` to use new graph
6. Test deep research in isolation

### Step 2: Add Tool Use to Chat (Feature Flag)
1. Add `tools_node` and `should_use_tools` to `graph.py`
2. Add conditional edges for tool use
3. Add feature flag `ENABLE_TOOL_USE=false` (default off)
4. Test with flag enabled
5. Enable by default after validation

### Step 3: Add Tool Use to Deep Research
1. Enhance research supervisor with tool capability
2. Add `research_tools_node`
3. Update supervisor routing
4. Test end-to-end

## Testing Strategy

### Unit Tests
- `tests/unit/agents/research/test_research_graph.py`
- `tests/unit/agents/tools/test_tool_integration.py`

### Integration Tests
- `tests/integration/test_deep_research_flow.py`
- `tests/integration/test_tool_use_in_chat.py`

### E2E Tests
- `frontend/e2e/deep-research.spec.ts`
- `frontend/e2e/tool-use.spec.ts`

## Success Criteria

### Deep Research
- ✅ Can execute multi-turn research queries
- ✅ Reuses CoordinatorAgent (no code duplication)
- ✅ Uses LLMTask API (no TypeError)
- ✅ Generates comprehensive reports
- ✅ < 30s latency for 3 iterations

### Tool Use
- ✅ Can call MCP tools from chat
- ✅ ReAct loop works (multi-turn tool conversations)
- ✅ Tool results integrated into answer
- ✅ Works in both chat and research modes
- ✅ < 5s additional latency per tool call

## Rollout Plan

1. **Week 1**: Implement Deep Research graph (Step 1)
2. **Week 2**: Add tool use to chat (Step 2)
3. **Week 3**: Add tool use to research + testing (Step 3)
4. **Week 4**: Documentation + E2E tests + rollout

## References

- LangGraph ReAct Pattern: https://langchain-ai.github.io/langgraph/how-tos/react-agent-from-scratch
- LangGraph Supervisor Pattern: https://langchain-ai.github.io/langgraph/tutorials/multi_agent/hierarchical_agent_teams
- LangGraph Subgraphs: https://langchain-ai.github.io/langgraph/concepts/agentic_concepts#subgraphs
- Existing ActionAgent: `src/agents/action_agent.py`
- Existing CoordinatorAgent: `src/agents/coordinator.py`

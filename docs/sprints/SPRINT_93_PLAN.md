# Sprint 93 Plan: Tool Composition & Skill-Tool Mapping

**Epic:** AegisRAG Agentic Framework Transformation
**Phase:** 4 of 7 (Tools)
**ADR Reference:** [ADR-049](../adr/ADR-049-agentic-framework-architecture.md)
**Prerequisite:** Sprint 92 (Context Processing & Skill Lifecycle)
**Duration:** 14-18 days
**Total Story Points:** 34 SP
**Status:** 📝 Planned

---

## Sprint Goal

Enable **advanced tool capabilities** with Skill-Tool integration:
1. **Tool Composition** - Chain multiple tools in workflows
2. **Browser Tool** - Web browsing with Playwright
3. **Skill-Tool Mapping** - Connect skills to their authorized tools
4. **Policy Guardrails** - Per-skill tool permissions

**Target Outcome:** +40% automation capability, secure skill-tool access

---

## Research Foundation

> "Für AegisRAG bedeutet dies, einen Action-Agenten zu erweitern, der Web- und OS-Tools einsetzt. Ein Browser-Tool, das ähnlich wie das ChatGPT-Browsing eine Suche durchführt und Webseiteninhalte ins LLM-Input lädt."
> — AegisRAG_Agentenframework.docx

Key Sources:
- **ALE/ROCK (Alibaba 2025):** Tool sandboxing and permissions
- **ROME (2025):** Agentic trajectory learning
- **Anthropic Agent Skills:** [Equipping Agents for the Real World](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- **Anthropic Skills Repository:** [github.com/anthropics/skills](https://github.com/anthropics/skills)
- **browser-use:** [github.com/browser-use/browser-use](https://github.com/browser-use/browser-use) - Agentic Web Browsing with LLM integration

### Existing Implementation (Sprint 67)

> **⚠️ ALREADY IMPLEMENTED:** Secure sandboxing was implemented in Sprint 67 (BubblewrapSandboxBackend).
>
> Location: `src/components/sandbox/`, `src/agents/action/`
>
> Features:
> - Linux Bubblewrap namespace isolation
> - Seccomp syscall filtering
> - Network isolation (no egress)
> - Path traversal protection
> - 32KB output truncation
>
> This sprint focuses on **Skill-Tool integration**, not reimplementing sandboxing.

---

## Features

| # | Feature | SP | Priority | Status |
|---|---------|-----|----------|--------|
| 93.1 | Tool Composition Framework | 10 | P0 | 📝 Planned |
| 93.2 | Browser Tool (Playwright) | 8 | P0 | 📝 Planned |
| 93.3 | Skill-Tool Mapping Layer | 8 | P0 | 📝 Planned |
| 93.4 | Policy Guardrails Engine | 5 | P1 | 📝 Planned |
| 93.5 | Tool Chain DSL | 3 | P2 | 📝 Planned |

---

## Feature 93.1: Tool Composition Framework (10 SP)

### Description

Enable chaining multiple tools in workflows with data passing, integrated with skill system.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           Tool Composition + Skill Integration              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User Request: "Find latest Python version and create      │
│                 a script that prints it"                   │
│                                                             │
│  Skill: research-automation                                 │
│  Authorized Tools: [web_search, parse, python_exec]        │
│                                                             │
│  Decomposed into Tool Chain:                                │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │web_search│───▶│  parse   │───▶│python_exe│              │
│  │ [query]  │    │ [result] │    │ [script] │              │
│  └──────────┘    └──────────┘    └──────────┘              │
│       │              │               │                      │
│       ▼              ▼               ▼                      │
│  "Python 3.13"  version="3.13"  print("3.13")              │
│                                                             │
│  State Passing: Each tool receives prior outputs            │
│  Permission Check: Validate skill has tool access           │
│  Error Handling: Retry or alternative path on failure       │
│  Validation: Type check between tool outputs/inputs         │
└─────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# src/agents/tools/composition.py

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

from src.agents.skills.lifecycle import SkillLifecycleManager
from src.agents.tools.policy import PolicyEngine


class ToolStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    DENIED = "denied"  # Permission denied


@dataclass
class ToolStep:
    """Single step in tool chain."""
    name: str
    tool: str
    inputs: Dict[str, Any]
    output_key: str
    status: ToolStatus = ToolStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2
    required_permission: Optional[str] = None


@dataclass
class ToolChain:
    """Chain of tools to execute."""
    id: str
    skill_name: str  # Skill that owns this chain
    steps: List[ToolStep]
    context: Dict[str, Any] = field(default_factory=dict)
    final_output_key: str = "result"


class SkillAwareToolComposer:
    """
    Compose and execute tool chains with skill permissions.

    Handles:
    - Data passing between tools
    - Skill-based permission validation
    - Error recovery and retries
    - Parallel execution where possible
    - Type validation
    """

    def __init__(
        self,
        tool_registry: Dict[str, Callable],
        skill_manager: SkillLifecycleManager,
        policy_engine: PolicyEngine,
        llm: BaseChatModel
    ):
        self.tools = tool_registry
        self.skills = skill_manager
        self.policy = policy_engine
        self.llm = llm

    async def execute_chain(
        self,
        chain: ToolChain,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute tool chain with skill permission checks.

        Args:
            chain: ToolChain to execute
            initial_context: Starting context variables

        Returns:
            Final context with all outputs
        """
        context = {**(initial_context or {}), **chain.context}

        # Validate skill has permission for all tools
        for step in chain.steps:
            if not await self.policy.can_use_tool(chain.skill_name, step.tool):
                step.status = ToolStatus.DENIED
                step.error = f"Skill '{chain.skill_name}' not authorized for tool '{step.tool}'"
                raise PermissionError(step.error)

        for step in chain.steps:
            step.status = ToolStatus.RUNNING

            try:
                # Resolve input references
                resolved_inputs = self._resolve_inputs(step.inputs, context)

                # Execute tool with permission context
                result = await self._execute_tool(
                    step.tool,
                    resolved_inputs,
                    skill_name=chain.skill_name
                )

                # Store result
                step.result = result
                step.status = ToolStatus.SUCCESS
                context[step.output_key] = result

            except Exception as e:
                step.error = str(e)

                # Retry logic
                if step.retry_count < step.max_retries:
                    step.retry_count += 1
                    step.status = ToolStatus.PENDING
                    continue

                step.status = ToolStatus.FAILED

                # Check if can continue
                if not self._can_continue(chain, step):
                    raise ToolChainError(f"Chain failed at {step.name}: {e}")

        return context

    def _resolve_inputs(
        self,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve input references from context.

        Supports:
        - Direct values: {"query": "test"}
        - Context refs: {"query": "$search_result"}
        - Nested refs: {"data": "$step1.output.text"}
        """
        resolved = {}
        for key, value in inputs.items():
            if isinstance(value, str) and value.startswith('$'):
                ref = value[1:]  # Remove $
                parts = ref.split('.')
                result = context
                for part in parts:
                    if isinstance(result, dict):
                        result = result.get(part)
                    else:
                        result = getattr(result, part, None)
                resolved[key] = result
            else:
                resolved[key] = value
        return resolved

    async def _execute_tool(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        skill_name: str
    ) -> Any:
        """Execute single tool with skill context."""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        tool = self.tools[tool_name]

        # Log tool usage for skill audit trail
        await self.policy.log_tool_usage(skill_name, tool_name, inputs)

        if asyncio.iscoroutinefunction(tool):
            return await tool(**inputs)
        else:
            return tool(**inputs)

    async def plan_chain(
        self,
        request: str,
        skill_name: str
    ) -> ToolChain:
        """
        Use LLM to plan tool chain for request.

        Args:
            request: User's request
            skill_name: Skill to use for planning

        Returns:
            ToolChain to execute
        """
        # Get tools authorized for this skill
        available_tools = await self.policy.get_authorized_tools(skill_name)
        tool_docs = self._get_tool_docs(available_tools)

        prompt = f"""Plan a tool chain to accomplish this request.

Request: {request}

Available Tools (authorized for skill '{skill_name}'):
{tool_docs}

For each step, specify:
- STEP: step_name
- TOOL: tool_name
- INPUTS: {{"param": "value" or "$prior_output"}}
- OUTPUT: output_variable_name

Use $variable to reference outputs from prior steps.
Plan minimal steps needed. Only use authorized tools.

Tool Chain:"""

        response = await self.llm.ainvoke(prompt)
        return self._parse_chain(response.content, skill_name)

    def _can_continue(self, chain: ToolChain, failed_step: ToolStep) -> bool:
        """Check if chain can continue after step failure."""
        # Check if any remaining steps depend on failed step
        for step in chain.steps:
            if step.status == ToolStatus.PENDING:
                for value in step.inputs.values():
                    if isinstance(value, str) and f"${failed_step.output_key}" in value:
                        return False
        return True
```

---

## Feature 93.2: Browser Tool (8 SP)

### Description

Full web browsing capability with two implementation options:

**Option A: browser-use (Recommended)**
- Agentic web browsing with built-in LLM integration
- Automatic action planning (click, type, scroll, extract)
- Vision-based element detection
- GitHub: [browser-use/browser-use](https://github.com/browser-use/browser-use)
- Make sure to use the latest version

**Option B: Raw Playwright**
- Direct Playwright API control
- More manual but flexible
- Better for specific workflows

### Implementation Option A: browser-use

```python
# src/agents/tools/browser.py

from browser_use import Browser, Agent
from langchain_ollama import ChatOllama

async def browse_with_agent(task: str) -> str:
    """Agentic web browsing using browser-use."""
    llm = ChatOllama(model="nemotron-3-nano")
    browser = Browser()
    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
    )
    result = await agent.run()
    await browser.close()
    return result
```

### Implementation Option B: Playwright (Direct)

```python
# src/agents/tools/browser.py

from playwright.async_api import async_playwright, Page, Browser
from typing import Dict, List, Optional
import time


class BrowserTool:
    """
    Web browsing tool using Playwright.

    Capabilities:
    - Navigate to URLs
    - Extract page content
    - Click elements
    - Fill forms
    - Take screenshots
    """

    def __init__(
        self,
        headless: bool = True,
        timeout: float = 30.0,
        user_agent: str = "AegisRAG Browser/1.0"
    ):
        self.headless = headless
        self.timeout = timeout * 1000  # Convert to ms
        self.user_agent = user_agent
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    async def __aenter__(self):
        """Start browser session."""
        playwright = await async_playwright().start()
        self._browser = await playwright.chromium.launch(headless=self.headless)
        context = await self._browser.new_context(user_agent=self.user_agent)
        self._page = await context.new_page()
        self._page.set_default_timeout(self.timeout)
        return self

    async def __aexit__(self, *args):
        """Close browser session."""
        if self._browser:
            await self._browser.close()

    async def navigate(self, url: str) -> dict:
        """Navigate to URL and return page info."""
        response = await self._page.goto(url)
        return {
            "url": self._page.url,
            "title": await self._page.title(),
            "status": response.status if response else None
        }

    async def get_content(self, selector: str = "body") -> str:
        """Extract text content from page."""
        element = await self._page.query_selector(selector)
        if element:
            return await element.inner_text()
        return ""

    async def get_links(self, limit: int = 20) -> List[dict]:
        """Extract links from page."""
        links = await self._page.query_selector_all("a[href]")
        results = []
        for link in links[:limit]:
            href = await link.get_attribute("href")
            text = await link.inner_text()
            results.append({"href": href, "text": text.strip()})
        return results

    async def click(self, selector: str) -> bool:
        """Click an element."""
        try:
            await self._page.click(selector)
            return True
        except Exception:
            return False

    async def fill_form(self, fields: Dict[str, str]) -> bool:
        """Fill form fields."""
        try:
            for selector, value in fields.items():
                await self._page.fill(selector, value)
            return True
        except Exception:
            return False

    async def screenshot(self, path: str) -> str:
        """Take screenshot."""
        await self._page.screenshot(path=path)
        return path

    async def extract_structured(self) -> dict:
        """Extract structured data from page."""
        return {
            "title": await self._page.title(),
            "url": self._page.url,
            "headings": await self._extract_headings(),
            "paragraphs": await self._extract_paragraphs(),
            "links": await self.get_links(10),
            "images": await self._extract_images()
        }

    async def _extract_headings(self) -> List[str]:
        """Extract all headings."""
        headings = []
        for tag in ["h1", "h2", "h3"]:
            elements = await self._page.query_selector_all(tag)
            for el in elements:
                text = await el.inner_text()
                headings.append(f"[{tag}] {text.strip()}")
        return headings

    async def _extract_paragraphs(self, limit: int = 10) -> List[str]:
        """Extract paragraph text."""
        elements = await self._page.query_selector_all("p")
        return [await el.inner_text() for el in elements[:limit]]

    async def _extract_images(self, limit: int = 5) -> List[dict]:
        """Extract image info."""
        images = await self._page.query_selector_all("img")
        results = []
        for img in images[:limit]:
            src = await img.get_attribute("src")
            alt = await img.get_attribute("alt") or ""
            results.append({"src": src, "alt": alt})
        return results


# Register as skill-accessible tool
@ToolRegistry.register(
    name="browser",
    description="Browse web pages, extract content, click links, fill forms",
    parameters={
        "action": {"type": "string", "enum": ["navigate", "content", "links", "click", "screenshot"]},
        "url": {"type": "string", "description": "URL to navigate to"},
        "selector": {"type": "string", "description": "CSS selector for actions"}
    },
    # Skills that can use this tool
    authorized_skills=["web_search", "research", "web_automation"]
)
async def browser_tool(
    action: str,
    url: Optional[str] = None,
    selector: Optional[str] = None,
    skill_context: Optional[Dict] = None
) -> str:
    """Execute browser action with skill context."""
    async with BrowserTool() as browser:
        if action == "navigate" and url:
            result = await browser.navigate(url)
            content = await browser.get_content()
            return f"Navigated to {result['title']}\n\n{content[:5000]}"

        elif action == "content":
            return await browser.get_content(selector or "body")

        elif action == "links":
            links = await browser.get_links()
            return "\n".join(f"- [{l['text']}]({l['href']})" for l in links)

        elif action == "click" and selector:
            success = await browser.click(selector)
            return "Clicked" if success else "Click failed"

        elif action == "screenshot" and url:
            await browser.navigate(url)
            path = f"/tmp/screenshot_{int(time.time())}.png"
            return await browser.screenshot(path)

        return "Unknown action"
```

---

## Feature 93.3: Skill-Tool Mapping Layer (8 SP)

### Description

Define and manage which tools each skill can access.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Skill-Tool Mapping                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  skills/                                                    │
│  ├── retrieval/                                             │
│  │   └── SKILL.md                                           │
│  │       tools:                                             │
│  │         - vector_search                                  │
│  │         - bm25_search                                    │
│  │         - graph_query                                    │
│  │                                                          │
│  ├── web_search/                                            │
│  │   └── SKILL.md                                           │
│  │       tools:                                             │
│  │         - browser                                        │
│  │         - web_fetch                                      │
│  │         - search_api                                     │
│  │                                                          │
│  ├── synthesis/                                             │
│  │   └── SKILL.md                                           │
│  │       tools:                                             │
│  │         - llm_generate                                   │
│  │         - summarize                                      │
│  │                                                          │
│  └── automation/                                            │
│      └── SKILL.md                                           │
│          tools:                                             │
│            - python_exec    (requires: elevated)            │
│            - file_write     (requires: elevated)            │
│            - browser                                        │
│                                                             │
│  Tool Authorization Flow:                                    │
│  ┌─────────┐  activate   ┌─────────┐  use tool  ┌────────┐ │
│  │  Skill  │ ──────────▶│ Policy  │ ─────────▶│  Tool  │  │
│  └─────────┘             │ Engine  │            └────────┘  │
│                          └────┬────┘                        │
│                               │                              │
│                          Check:                              │
│                          - Skill has tool in manifest       │
│                          - Required permission level        │
│                          - Rate limits                      │
│                          - Domain restrictions              │
└─────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# src/agents/tools/skill_mapping.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from pathlib import Path
import yaml


@dataclass
class ToolPermission:
    """Permission entry for a tool."""
    tool_name: str
    access_level: str = "standard"  # standard, elevated, admin
    rate_limit: Optional[int] = None  # calls per minute
    allowed_domains: Optional[List[str]] = None
    blocked_domains: Optional[List[str]] = None


@dataclass
class SkillToolManifest:
    """Tool manifest for a skill."""
    skill_name: str
    tools: List[ToolPermission]
    inherit_from: Optional[str] = None  # Inherit tools from another skill

    def has_tool(self, tool_name: str) -> bool:
        """Check if skill has access to tool."""
        return any(t.tool_name == tool_name for t in self.tools)

    def get_tool_permission(self, tool_name: str) -> Optional[ToolPermission]:
        """Get permission details for tool."""
        for tool in self.tools:
            if tool.tool_name == tool_name:
                return tool
        return None


class SkillToolMapper:
    """
    Map skills to their authorized tools.

    Reads tool authorizations from SKILL.md frontmatter.
    """

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self._manifests: Dict[str, SkillToolManifest] = {}
        self._tool_skill_index: Dict[str, Set[str]] = {}

    def load_manifests(self):
        """Load all skill tool manifests."""
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    manifest = self._parse_manifest(skill_dir.name, skill_md)
                    self._manifests[skill_dir.name] = manifest

                    # Build reverse index
                    for tool_perm in manifest.tools:
                        if tool_perm.tool_name not in self._tool_skill_index:
                            self._tool_skill_index[tool_perm.tool_name] = set()
                        self._tool_skill_index[tool_perm.tool_name].add(skill_dir.name)

    def _parse_manifest(
        self,
        skill_name: str,
        skill_md: Path
    ) -> SkillToolManifest:
        """Parse tool manifest from SKILL.md frontmatter."""
        content = skill_md.read_text()

        # Extract YAML frontmatter
        if content.startswith('---'):
            end_idx = content.index('---', 3)
            frontmatter = yaml.safe_load(content[3:end_idx])
        else:
            frontmatter = {}

        # Parse tools section
        tools_config = frontmatter.get('tools', [])
        tools = []

        for tool_entry in tools_config:
            if isinstance(tool_entry, str):
                tools.append(ToolPermission(tool_name=tool_entry))
            elif isinstance(tool_entry, dict):
                tools.append(ToolPermission(
                    tool_name=tool_entry.get('name'),
                    access_level=tool_entry.get('access_level', 'standard'),
                    rate_limit=tool_entry.get('rate_limit'),
                    allowed_domains=tool_entry.get('allowed_domains'),
                    blocked_domains=tool_entry.get('blocked_domains')
                ))

        return SkillToolManifest(
            skill_name=skill_name,
            tools=tools,
            inherit_from=frontmatter.get('inherit_tools_from')
        )

    def get_skill_tools(self, skill_name: str) -> List[str]:
        """Get list of tools authorized for skill."""
        manifest = self._manifests.get(skill_name)
        if not manifest:
            return []

        tools = [t.tool_name for t in manifest.tools]

        # Include inherited tools
        if manifest.inherit_from:
            inherited = self.get_skill_tools(manifest.inherit_from)
            tools.extend(t for t in inherited if t not in tools)

        return tools

    def get_tool_skills(self, tool_name: str) -> List[str]:
        """Get list of skills that can use a tool."""
        return list(self._tool_skill_index.get(tool_name, set()))

    def validate_access(
        self,
        skill_name: str,
        tool_name: str,
        required_level: str = "standard"
    ) -> bool:
        """Validate skill has required access to tool."""
        manifest = self._manifests.get(skill_name)
        if not manifest:
            return False

        permission = manifest.get_tool_permission(tool_name)
        if not permission:
            # Check inherited
            if manifest.inherit_from:
                return self.validate_access(
                    manifest.inherit_from, tool_name, required_level
                )
            return False

        # Check access level
        levels = ["standard", "elevated", "admin"]
        required_idx = levels.index(required_level)
        actual_idx = levels.index(permission.access_level)

        return actual_idx >= required_idx
```

---

## Feature 93.4: Policy Guardrails Engine (5 SP)

### Description

Safety checks and policy enforcement before tool execution.

```python
# src/agents/tools/policy.py

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import re
from datetime import datetime, timedelta
from collections import defaultdict


@dataclass
class PolicyViolation:
    """Record of policy violation."""
    skill_name: str
    tool_name: str
    violation_type: str
    details: str
    timestamp: datetime
    severity: str = "warning"  # warning, error, critical


class PolicyEngine:
    """
    Policy guardrails for skill-tool interactions.

    Based on: ALE/ROCK permission model
    """

    def __init__(self):
        # Dangerous patterns to block
        self.blocked_patterns = [
            r"rm\s+-rf",
            r"sudo\s+",
            r"chmod\s+777",
            r"curl.*\|\s*bash",
            r"eval\s*\(",
            r"__import__",
        ]

        # Domain blocklist
        self.blocked_domains = [
            "malware.com",
            "phishing.net",
        ]

        # Sensitive tools requiring elevation
        self.sensitive_tools = {
            "file_delete": "elevated",
            "system_command": "admin",
            "python_exec": "elevated",
        }

        # Rate limiting
        self._rate_limits: Dict[str, Dict[str, int]] = {}
        self._call_history: Dict[str, List[datetime]] = defaultdict(list)

        # Audit log
        self._violations: List[PolicyViolation] = []
        self._usage_log: List[Dict] = []

    async def can_use_tool(
        self,
        skill_name: str,
        tool_name: str,
        inputs: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if skill can use tool with given inputs.

        Args:
            skill_name: Name of requesting skill
            tool_name: Tool to check
            inputs: Optional tool inputs to validate

        Returns:
            True if allowed
        """
        # Check if tool requires elevation
        if tool_name in self.sensitive_tools:
            required = self.sensitive_tools[tool_name]
            # Would check skill's permission level here
            # For now, log and allow with warning
            self._violations.append(PolicyViolation(
                skill_name=skill_name,
                tool_name=tool_name,
                violation_type="sensitive_tool",
                details=f"Tool requires {required} access",
                timestamp=datetime.now(),
                severity="warning"
            ))

        # Check rate limits
        if not self._check_rate_limit(skill_name, tool_name):
            self._violations.append(PolicyViolation(
                skill_name=skill_name,
                tool_name=tool_name,
                violation_type="rate_limit",
                details="Rate limit exceeded",
                timestamp=datetime.now(),
                severity="error"
            ))
            return False

        # Check input patterns
        if inputs:
            for key, value in inputs.items():
                if isinstance(value, str):
                    for pattern in self.blocked_patterns:
                        if re.search(pattern, value, re.IGNORECASE):
                            self._violations.append(PolicyViolation(
                                skill_name=skill_name,
                                tool_name=tool_name,
                                violation_type="blocked_pattern",
                                details=f"Pattern '{pattern}' detected in {key}",
                                timestamp=datetime.now(),
                                severity="critical"
                            ))
                            return False

        # Check URLs
        if inputs and "url" in inputs:
            url = inputs["url"]
            for domain in self.blocked_domains:
                if domain in url:
                    self._violations.append(PolicyViolation(
                        skill_name=skill_name,
                        tool_name=tool_name,
                        violation_type="blocked_domain",
                        details=f"Blocked domain: {domain}",
                        timestamp=datetime.now(),
                        severity="critical"
                    ))
                    return False

        return True

    async def log_tool_usage(
        self,
        skill_name: str,
        tool_name: str,
        inputs: Dict[str, Any]
    ):
        """Log tool usage for audit trail."""
        self._usage_log.append({
            "skill": skill_name,
            "tool": tool_name,
            "inputs": {k: str(v)[:100] for k, v in inputs.items()},
            "timestamp": datetime.now().isoformat()
        })

        # Record for rate limiting
        key = f"{skill_name}:{tool_name}"
        self._call_history[key].append(datetime.now())

    async def get_authorized_tools(self, skill_name: str) -> List[str]:
        """Get tools authorized for skill (delegates to mapper)."""
        # Would integrate with SkillToolMapper
        return []

    def set_rate_limit(
        self,
        skill_name: str,
        tool_name: str,
        calls_per_minute: int
    ):
        """Set rate limit for skill-tool combination."""
        if skill_name not in self._rate_limits:
            self._rate_limits[skill_name] = {}
        self._rate_limits[skill_name][tool_name] = calls_per_minute

    def _check_rate_limit(self, skill_name: str, tool_name: str) -> bool:
        """Check if rate limit allows call."""
        limit = self._rate_limits.get(skill_name, {}).get(tool_name)
        if not limit:
            return True

        key = f"{skill_name}:{tool_name}"
        now = datetime.now()
        window_start = now - timedelta(minutes=1)

        # Clean old entries
        self._call_history[key] = [
            t for t in self._call_history[key] if t > window_start
        ]

        return len(self._call_history[key]) < limit

    def get_violations(
        self,
        skill_name: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[PolicyViolation]:
        """Get policy violations, optionally filtered."""
        violations = self._violations
        if skill_name:
            violations = [v for v in violations if v.skill_name == skill_name]
        if severity:
            violations = [v for v in violations if v.severity == severity]
        return violations

    def get_usage_report(self, skill_name: str) -> Dict:
        """Get usage report for skill."""
        skill_usage = [u for u in self._usage_log if u["skill"] == skill_name]

        tool_counts = defaultdict(int)
        for entry in skill_usage:
            tool_counts[entry["tool"]] += 1

        return {
            "skill": skill_name,
            "total_calls": len(skill_usage),
            "tools_used": dict(tool_counts),
            "violations": len([v for v in self._violations if v.skill_name == skill_name])
        }
```

---

## Feature 93.5: Tool Chain DSL (3 SP)

### Description

Declarative DSL for defining tool chains in SKILL.md.

```python
# src/agents/tools/dsl.py

class ToolChainDSL:
    """
    Declarative DSL for tool chains.

    Can be defined in SKILL.md:

    ```yaml
    chains:
      search_and_summarize:
        - step: search
          tool: web_search
          inputs:
            query: $query
        - step: extract
          tool: parse_html
          inputs:
            html: $search.result
        - step: summarize
          tool: llm_summarize
          inputs:
            text: $extract.text
        output: $summarize.result
    ```

    Or in Python:

    ```python
    chain = (
        ToolChainDSL("search_and_summarize")
        .step("search", "web_search", query="$query")
        .step("extract", "parse_html", html="$search.result")
        .step("summarize", "llm_summarize", text="$extract.text")
        .output("summarize")
    )
    ```
    """

    def __init__(self, chain_id: str, skill_name: str = "default"):
        self.chain_id = chain_id
        self.skill_name = skill_name
        self.steps: List[ToolStep] = []
        self._final_output = "result"

    def step(
        self,
        name: str,
        tool: str,
        **inputs
    ) -> 'ToolChainDSL':
        """Add step to chain."""
        self.steps.append(ToolStep(
            name=name,
            tool=tool,
            inputs=inputs,
            output_key=name
        ))
        return self

    def output(self, key: str) -> 'ToolChainDSL':
        """Set final output key."""
        self._final_output = key
        return self

    def build(self) -> ToolChain:
        """Build ToolChain."""
        return ToolChain(
            id=self.chain_id,
            skill_name=self.skill_name,
            steps=self.steps,
            final_output_key=self._final_output
        )

    @classmethod
    def from_yaml(cls, yaml_config: Dict, skill_name: str) -> 'ToolChainDSL':
        """Parse chain from YAML config."""
        chain_id = yaml_config.get('id', 'unnamed')
        dsl = cls(chain_id, skill_name)

        for step_config in yaml_config.get('steps', []):
            dsl.step(
                name=step_config['step'],
                tool=step_config['tool'],
                **step_config.get('inputs', {})
            )

        if 'output' in yaml_config:
            dsl.output(yaml_config['output'].lstrip('$'))

        return dsl
```

### Example SKILL.md with Tools

```yaml
---
name: research
version: "1.0.0"
description: Research skill for web and document search
triggers:
  - "research"
  - "find information about"
  - "look up"

tools:
  - name: web_search
    access_level: standard
    rate_limit: 30  # per minute
  - name: browser
    access_level: standard
    allowed_domains:
      - "*.wikipedia.org"
      - "*.github.com"
      - "*.arxiv.org"
  - name: llm_summarize
    access_level: standard

chains:
  deep_research:
    - step: search
      tool: web_search
      inputs:
        query: $query
    - step: browse_top
      tool: browser
      inputs:
        action: navigate
        url: $search.results[0].url
    - step: summarize
      tool: llm_summarize
      inputs:
        text: $browse_top.content
    output: $summarize.result
---

# Research Skill

This skill handles research queries by combining web search,
browsing, and summarization.

## Instructions

When the user asks for research:
1. Search the web for relevant information
2. Browse top results to extract content
3. Summarize findings

...
```

---

## Deliverables

| Artifact | Location | Description |
|----------|----------|-------------|
| Tool Composer | `src/agents/tools/composition.py` | Skill-aware chain execution |
| Browser Tool | `src/agents/tools/browser.py` | Playwright integration |
| Skill-Tool Mapper | `src/agents/tools/skill_mapping.py` | Tool authorization |
| Policy Engine | `src/agents/tools/policy.py` | Guardrails & audit |
| Chain DSL | `src/agents/tools/dsl.py` | Declarative chains |
| Tests | `tests/unit/agents/tools/` | 35+ tests |

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Tool Chaining | ❌ None | ✅ Full |
| Web Browsing | ❌ None | ✅ Full |
| Skill-Tool Auth | ❌ None | ✅ Manifest-based |
| Policy Guardrails | Basic sandbox | Multi-layer |
| Automation | Baseline | +40% |

---

**Document:** SPRINT_93_PLAN.md
**Status:** 📝 Planned
**Created:** 2026-01-13
**Updated:** 2026-01-13 (Agent Skills Integration)

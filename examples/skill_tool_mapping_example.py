"""Example: Skill-Tool Mapping Layer Usage.

Sprint 93 Feature 93.3: Skill-Tool Mapping Layer (8 SP)

This example demonstrates how to use the Skill-Tool Mapping Layer to:
1. Register tools with capabilities
2. Map skills to authorized tools
3. Discover tools dynamically based on filters
4. Check permissions before tool execution
5. Integrate with PolicyEngine for enforcement

Run:
    poetry run python examples/skill_tool_mapping_example.py
"""

import asyncio

from src.agents.tools import (
    PolicyEngine,
    SkillToolMapper,
    ToolCapability,
    check_tool_permission,
)


async def main():
    """Demonstrate Skill-Tool Mapping Layer usage."""

    print("=== Skill-Tool Mapping Layer Example ===\n")

    # Step 1: Create mapper
    print("1. Creating SkillToolMapper...")
    mapper = SkillToolMapper()

    # Step 2: Register tools with capabilities
    print("\n2. Registering tools with capabilities...\n")

    # Browser tool for web automation
    mapper.register_tool(
        "browser",
        ToolCapability(
            name="browser",
            description="Web browsing with Playwright",
            parameters={"action": "str", "url": "str", "selector": "str"},
            required_params=["action"],
            optional_params=["url", "selector"],
            return_type="str",
            async_support=True,
            rate_limit=30,
            requires_network=True,
            tags=["web", "automation"],
        ),
        required_skills=["research", "web_automation"],
    )

    # Web search tool
    mapper.register_tool(
        "web_search",
        ToolCapability(
            name="web_search",
            description="Search the web",
            parameters={"query": "str", "limit": "int"},
            required_params=["query"],
            return_type="list[dict]",
            async_support=True,
            rate_limit=60,
            requires_network=True,
            tags=["web", "search"],
        ),
        required_skills=["research", "synthesis"],
    )

    # File operations (universal access)
    mapper.register_tool(
        "file_read",
        ToolCapability(
            name="file_read",
            description="Read file contents",
            parameters={"path": "str"},
            required_params=["path"],
            return_type="str",
            async_support=False,
            requires_filesystem=True,
            tags=["file", "io"],
        ),
        required_skills=None,  # Available to all skills
    )

    # LLM generation (restricted access)
    mapper.register_tool(
        "llm_generate",
        ToolCapability(
            name="llm_generate",
            description="Generate text with LLM",
            parameters={"prompt": "str", "max_tokens": "int"},
            required_params=["prompt"],
            return_type="str",
            async_support=True,
            streaming_support=True,
            tags=["llm", "generation"],
        ),
        required_skills=["synthesis", "reflection"],
        denied_skills=["restricted_skill"],
    )

    print("✅ Registered 4 tools with capabilities\n")

    # Step 3: Check available tools for different skills
    print("3. Checking available tools for skills...\n")

    research_tools = mapper.get_available_tools("research")
    print(f"Research skill can use: {research_tools}")

    synthesis_tools = mapper.get_available_tools("synthesis")
    print(f"Synthesis skill can use: {synthesis_tools}")

    unknown_tools = mapper.get_available_tools("unknown_skill")
    print(f"Unknown skill can use: {unknown_tools}\n")

    # Step 4: Discover tools with filters
    print("4. Discovering tools with capability filters...\n")

    # Find all async tools for research
    async_tools = mapper.discover_tools("research", {"async_support": True})
    print(f"Async tools for research: {[t.name for t in async_tools]}")

    # Find web-related tools
    web_tools = mapper.discover_tools("research", {"tags": ["web"]})
    print(f"Web tools for research: {[t.name for t in web_tools]}")

    # Find tools requiring network
    network_tools = mapper.discover_tools("research", {"requires_network": True})
    print(f"Network tools for research: {[t.name for t in network_tools]}")

    # Find streaming-capable tools
    streaming_tools = mapper.discover_tools("synthesis", {"streaming_support": True})
    print(f"Streaming tools for synthesis: {[t.name for t in streaming_tools]}\n")

    # Step 5: Check permissions
    print("5. Checking tool permissions...\n")

    can_use_browser = mapper.can_skill_use_tool("research", "browser")
    print(f"Can research use browser? {can_use_browser}")

    can_use_llm = mapper.can_skill_use_tool("research", "llm_generate")
    print(f"Can research use llm_generate? {can_use_llm}")

    can_use_file = mapper.can_skill_use_tool("unknown_skill", "file_read")
    print(f"Can unknown_skill use file_read? {can_use_file}\n")

    # Step 6: Get tool capabilities
    print("6. Getting tool capability metadata...\n")

    browser_cap = mapper.get_tool_capability("browser")
    if browser_cap:
        print(f"Browser tool:")
        print(f"  Description: {browser_cap.description}")
        print(f"  Async: {browser_cap.async_support}")
        print(f"  Rate limit: {browser_cap.rate_limit}/min")
        print(f"  Tags: {browser_cap.tags}\n")

    # Step 7: Enable/disable tools dynamically
    print("7. Dynamically enabling/disabling tools...\n")

    print("Disabling browser tool...")
    mapper.disable_tool("browser")
    research_tools_after = mapper.get_available_tools("research")
    print(f"Research tools after disabling browser: {research_tools_after}")

    print("Re-enabling browser tool...")
    mapper.enable_tool("browser")
    research_tools_final = mapper.get_available_tools("research")
    print(f"Research tools after re-enabling: {research_tools_final}\n")

    # Step 8: Get reverse mapping (tool -> skills)
    print("8. Getting skills that can use each tool...\n")

    browser_skills = mapper.get_skills_for_tool("browser")
    print(f"Skills that can use browser: {browser_skills}")

    file_skills = mapper.get_skills_for_tool("file_read")
    print(f"Skills that can use file_read: {file_skills} (universal)\n")

    # Step 9: Get mapper metrics
    print("9. Getting mapper metrics...\n")

    metrics = mapper.get_metrics()
    print(f"Total tools: {metrics['total_tools']}")
    print(f"Enabled tools: {metrics['enabled_tools']}")
    print(f"Tools per skill: {metrics['tools_per_skill']}\n")

    # Step 10: Integration with PolicyEngine
    print("10. Integrating with PolicyEngine...\n")

    # Create PolicyEngine with skill registrations
    policy = PolicyEngine()
    policy.register_skill("research", ["browser", "web_search", "file_read"])
    policy.register_skill("synthesis", ["web_search", "llm_generate", "file_read"])

    # Create mapper with PolicyEngine
    mapper_with_policy = SkillToolMapper(policy_engine=policy)

    # Register same tools
    mapper_with_policy.register_tool(
        "browser",
        ToolCapability(name="browser", description="Browser"),
        required_skills=["research"],
    )

    # Check permission with async helper
    can_use = await check_tool_permission(mapper_with_policy, "research", "browser")
    print(f"Can research use browser (with policy)? {can_use}")

    # Try unauthorized access
    can_use_denied = await check_tool_permission(
        mapper_with_policy, "synthesis", "browser"
    )
    print(f"Can synthesis use browser (with policy)? {can_use_denied}\n")

    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())

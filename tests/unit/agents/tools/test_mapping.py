"""Unit tests for Skill-Tool Mapping Layer.

Sprint 93 Feature 93.3: Skill-Tool Mapping Layer (8 SP)

Test Coverage:
- ToolCapability filtering and matching
- Tool registration and unregistration
- Skill → Tool access checks
- Tool discovery with filters
- Enable/disable tools
- Reverse lookup (tool → skills)
- Metrics and stats
- PolicyEngine integration
"""

import pytest

from src.agents.tools.mapping import (
    SkillToolMapper,
    ToolCapability,
    check_tool_permission,
)
from src.agents.tools.policy import PolicyEngine

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def basic_capabilities():
    """Basic tool capabilities for testing."""
    return {
        "browser": ToolCapability(
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
        "web_search": ToolCapability(
            name="web_search",
            description="Search the web",
            parameters={"query": "str", "limit": "int"},
            required_params=["query"],
            optional_params=["limit"],
            return_type="list[dict]",
            async_support=True,
            rate_limit=60,
            requires_network=True,
            tags=["web", "search"],
        ),
        "file_read": ToolCapability(
            name="file_read",
            description="Read file contents",
            parameters={"path": "str"},
            required_params=["path"],
            return_type="str",
            async_support=False,
            requires_filesystem=True,
            tags=["file", "read"],
        ),
        "llm_generate": ToolCapability(
            name="llm_generate",
            description="Generate text with LLM",
            parameters={"prompt": "str", "max_tokens": "int"},
            required_params=["prompt"],
            optional_params=["max_tokens"],
            return_type="str",
            async_support=True,
            streaming_support=True,
            tags=["llm", "generation"],
        ),
    }


@pytest.fixture
def mapper(basic_capabilities):
    """SkillToolMapper with pre-registered tools."""
    mapper = SkillToolMapper()

    # Register tools with different skill requirements
    mapper.register_tool(
        "browser",
        basic_capabilities["browser"],
        required_skills=["research", "web_automation"],
    )

    mapper.register_tool(
        "web_search",
        basic_capabilities["web_search"],
        required_skills=["research", "synthesis"],
    )

    mapper.register_tool(
        "file_read",
        basic_capabilities["file_read"],
        required_skills=None,  # Available to all
    )

    mapper.register_tool(
        "llm_generate",
        basic_capabilities["llm_generate"],
        required_skills=["synthesis", "reflection"],
        denied_skills=["restricted_skill"],
    )

    return mapper


@pytest.fixture
def policy_engine():
    """PolicyEngine for integration tests."""
    engine = PolicyEngine()

    # Register skills
    engine.register_skill("research", ["browser", "web_search", "file_read"])
    engine.register_skill("synthesis", ["web_search", "llm_generate", "file_read"])
    engine.register_skill("admin", [], is_admin=True)

    return engine


@pytest.fixture
def mapper_with_policy(basic_capabilities, policy_engine):
    """SkillToolMapper integrated with PolicyEngine."""
    mapper = SkillToolMapper(policy_engine=policy_engine)

    # Register same tools
    mapper.register_tool(
        "browser",
        basic_capabilities["browser"],
        required_skills=["research", "web_automation"],
    )

    mapper.register_tool(
        "web_search",
        basic_capabilities["web_search"],
        required_skills=["research", "synthesis"],
    )

    mapper.register_tool(
        "file_read",
        basic_capabilities["file_read"],
        required_skills=None,
    )

    return mapper


# =============================================================================
# ToolCapability Tests
# =============================================================================


def test_tool_capability_creation(basic_capabilities):
    """Test ToolCapability dataclass creation."""
    browser = basic_capabilities["browser"]

    assert browser.name == "browser"
    assert browser.async_support is True
    assert browser.rate_limit == 30
    assert "web" in browser.tags
    assert "automation" in browser.tags
    assert browser.requires_network is True


def test_tool_capability_matches_filter_simple(basic_capabilities):
    """Test simple capability filtering."""
    browser = basic_capabilities["browser"]

    # Match async support
    assert browser.matches_filter({"async_support": True}) is True
    assert browser.matches_filter({"async_support": False}) is False

    # Match network requirement
    assert browser.matches_filter({"requires_network": True}) is True
    assert browser.matches_filter({"requires_network": False}) is False


def test_tool_capability_matches_filter_tags(basic_capabilities):
    """Test tag-based capability filtering."""
    browser = basic_capabilities["browser"]
    file_read = basic_capabilities["file_read"]

    # Single tag match
    assert browser.matches_filter({"tags": ["web"]}) is True
    assert browser.matches_filter({"tags": ["automation"]}) is True
    assert browser.matches_filter({"tags": ["database"]}) is False

    # Multiple tags (any match)
    assert browser.matches_filter({"tags": ["web", "automation"]}) is True
    assert file_read.matches_filter({"tags": ["file"]}) is True
    assert file_read.matches_filter({"tags": ["web"]}) is False


def test_tool_capability_matches_filter_combined(basic_capabilities):
    """Test combined capability filters."""
    browser = basic_capabilities["browser"]
    llm = basic_capabilities["llm_generate"]

    # Browser: async + web tags
    assert browser.matches_filter({"async_support": True, "tags": ["web"]}) is True
    assert browser.matches_filter({"async_support": False, "tags": ["web"]}) is False

    # LLM: async + streaming
    assert llm.matches_filter({"async_support": True, "streaming_support": True}) is True
    assert llm.matches_filter({"async_support": True, "streaming_support": False}) is False


# =============================================================================
# Tool Registration Tests
# =============================================================================


def test_register_tool_basic():
    """Test basic tool registration."""
    mapper = SkillToolMapper()

    capability = ToolCapability(
        name="test_tool",
        description="Test tool",
        parameters={"input": "str"},
    )

    mapper.register_tool("test_tool", capability, required_skills=["test_skill"])

    # Check internal state
    assert "test_tool" in mapper._tools
    assert mapper._tools["test_tool"].capability.name == "test_tool"
    assert "test_skill" in mapper._skill_to_tools
    assert "test_tool" in mapper._skill_to_tools["test_skill"]


def test_register_tool_all_skills():
    """Test registering tool available to all skills."""
    mapper = SkillToolMapper()

    capability = ToolCapability(name="universal_tool", description="Universal")

    mapper.register_tool("universal_tool", capability, required_skills=None)

    assert "universal_tool" in mapper._tools
    assert mapper._tools["universal_tool"].required_skills is None


def test_register_tool_with_denied_skills():
    """Test registering tool with denied skills."""
    mapper = SkillToolMapper()

    capability = ToolCapability(name="sensitive_tool", description="Sensitive")

    mapper.register_tool(
        "sensitive_tool",
        capability,
        required_skills=["admin"],
        denied_skills=["restricted"],
    )

    assert "restricted" in mapper._tools["sensitive_tool"].denied_skills


def test_unregister_tool():
    """Test tool unregistration."""
    mapper = SkillToolMapper()

    capability = ToolCapability(name="temp_tool", description="Temporary")
    mapper.register_tool("temp_tool", capability, required_skills=["test_skill"])

    # Unregister
    assert mapper.unregister_tool("temp_tool") is True
    assert "temp_tool" not in mapper._tools

    # Try unregistering non-existent tool
    assert mapper.unregister_tool("nonexistent") is False


# =============================================================================
# Access Check Tests
# =============================================================================


def test_get_available_tools_specific_skills(mapper):
    """Test getting available tools for specific skills."""
    # Research skill
    research_tools = mapper.get_available_tools("research")
    assert "browser" in research_tools
    assert "web_search" in research_tools
    assert "file_read" in research_tools  # Available to all
    assert len(research_tools) == 3

    # Synthesis skill
    synthesis_tools = mapper.get_available_tools("synthesis")
    assert "web_search" in synthesis_tools
    assert "llm_generate" in synthesis_tools
    assert "file_read" in synthesis_tools
    assert "browser" not in synthesis_tools  # Not authorized
    assert len(synthesis_tools) == 3


def test_get_available_tools_no_access(mapper):
    """Test getting tools for skill with no access."""
    unknown_tools = mapper.get_available_tools("unknown_skill")

    # Should only get universal tools (file_read)
    assert "file_read" in unknown_tools
    assert "browser" not in unknown_tools
    assert "web_search" not in unknown_tools
    assert len(unknown_tools) == 1


def test_can_skill_use_tool_authorized(mapper):
    """Test authorized skill-tool access."""
    assert mapper.can_skill_use_tool("research", "browser") is True
    assert mapper.can_skill_use_tool("research", "web_search") is True
    assert mapper.can_skill_use_tool("synthesis", "llm_generate") is True


def test_can_skill_use_tool_unauthorized(mapper):
    """Test unauthorized skill-tool access."""
    assert mapper.can_skill_use_tool("research", "llm_generate") is False
    assert mapper.can_skill_use_tool("synthesis", "browser") is False
    assert mapper.can_skill_use_tool("unknown_skill", "browser") is False


def test_can_skill_use_tool_denied(mapper):
    """Test explicitly denied skill-tool access."""
    # restricted_skill is in denied list for llm_generate
    assert mapper.can_skill_use_tool("restricted_skill", "llm_generate") is False


def test_can_skill_use_tool_universal(mapper):
    """Test universal tool access."""
    # file_read is available to all (required_skills=None)
    assert mapper.can_skill_use_tool("research", "file_read") is True
    assert mapper.can_skill_use_tool("synthesis", "file_read") is True
    assert mapper.can_skill_use_tool("unknown_skill", "file_read") is True


def test_can_skill_use_tool_nonexistent_tool(mapper):
    """Test checking access to non-existent tool."""
    assert mapper.can_skill_use_tool("research", "nonexistent") is False


def test_can_skill_use_tool_disabled_tool(mapper):
    """Test checking access to disabled tool."""
    mapper.disable_tool("browser")
    assert mapper.can_skill_use_tool("research", "browser") is False


# =============================================================================
# Tool Discovery Tests
# =============================================================================


def test_discover_tools_no_filter(mapper):
    """Test discovering all tools for a skill."""
    tools = mapper.discover_tools("research")

    assert len(tools) == 3
    tool_names = [t.name for t in tools]
    assert "browser" in tool_names
    assert "web_search" in tool_names
    assert "file_read" in tool_names


def test_discover_tools_async_filter(mapper):
    """Test discovering async tools."""
    async_tools = mapper.discover_tools("research", {"async_support": True})

    assert len(async_tools) == 2
    tool_names = [t.name for t in async_tools]
    assert "browser" in tool_names
    assert "web_search" in tool_names
    assert "file_read" not in tool_names  # Not async


def test_discover_tools_tag_filter(mapper):
    """Test discovering tools by tag."""
    web_tools = mapper.discover_tools("research", {"tags": ["web"]})

    assert len(web_tools) == 2
    tool_names = [t.name for t in web_tools]
    assert "browser" in tool_names
    assert "web_search" in tool_names


def test_discover_tools_combined_filter(mapper):
    """Test discovering tools with combined filters."""
    # Async + web tags
    tools = mapper.discover_tools("research", {"async_support": True, "tags": ["web"]})

    assert len(tools) == 2
    tool_names = [t.name for t in tools]
    assert "browser" in tool_names
    assert "web_search" in tool_names


def test_discover_tools_no_matches(mapper):
    """Test discovering tools with no matches."""
    tools = mapper.discover_tools("research", {"tags": ["database"]})
    assert len(tools) == 0


def test_discover_tools_streaming_filter(mapper):
    """Test discovering streaming tools."""
    streaming_tools = mapper.discover_tools("synthesis", {"streaming_support": True})

    assert len(streaming_tools) == 1
    assert streaming_tools[0].name == "llm_generate"


# =============================================================================
# Tool Metadata Tests
# =============================================================================


def test_get_tool_capability(mapper):
    """Test getting tool capability metadata."""
    capability = mapper.get_tool_capability("browser")

    assert capability is not None
    assert capability.name == "browser"
    assert capability.description == "Web browsing with Playwright"
    assert capability.async_support is True
    assert "web" in capability.tags


def test_get_tool_capability_nonexistent(mapper):
    """Test getting capability for non-existent tool."""
    capability = mapper.get_tool_capability("nonexistent")
    assert capability is None


def test_get_tool_handler(mapper, basic_capabilities):
    """Test getting tool handler."""

    # Register tool with handler
    def mock_handler(action: str, url: str) -> str:
        return f"Executed {action} on {url}"

    mapper.register_tool(
        "handler_tool",
        basic_capabilities["browser"],
        required_skills=["test"],
        handler=mock_handler,
    )

    handler = mapper.get_tool_handler("handler_tool")
    assert handler is not None
    assert callable(handler)
    assert handler(action="navigate", url="test.com") == "Executed navigate on test.com"


def test_get_tool_handler_no_handler(mapper):
    """Test getting handler when none registered."""
    handler = mapper.get_tool_handler("browser")
    assert handler is None


# =============================================================================
# Enable/Disable Tests
# =============================================================================


def test_enable_disable_tool(mapper):
    """Test enabling and disabling tools."""
    # Initially enabled
    assert mapper.can_skill_use_tool("research", "browser") is True

    # Disable
    assert mapper.disable_tool("browser") is True
    assert mapper.can_skill_use_tool("research", "browser") is False
    assert "browser" not in mapper.get_available_tools("research")

    # Re-enable
    assert mapper.enable_tool("browser") is True
    assert mapper.can_skill_use_tool("research", "browser") is True
    assert "browser" in mapper.get_available_tools("research")


def test_enable_disable_nonexistent(mapper):
    """Test enabling/disabling non-existent tool."""
    assert mapper.enable_tool("nonexistent") is False
    assert mapper.disable_tool("nonexistent") is False


# =============================================================================
# Reverse Lookup Tests
# =============================================================================


def test_get_skills_for_tool(mapper):
    """Test getting skills that can use a tool."""
    skills = mapper.get_skills_for_tool("browser")
    assert "research" in skills
    assert "web_automation" in skills
    assert len(skills) == 2


def test_get_skills_for_universal_tool(mapper):
    """Test getting skills for universal tool."""
    skills = mapper.get_skills_for_tool("file_read")

    # Universal tool (required_skills=None) should return all skills
    assert len(skills) > 0


def test_get_skills_for_nonexistent_tool(mapper):
    """Test getting skills for non-existent tool."""
    skills = mapper.get_skills_for_tool("nonexistent")
    assert skills == []


# =============================================================================
# Metrics Tests
# =============================================================================


def test_get_metrics(mapper):
    """Test getting mapper metrics."""
    metrics = mapper.get_metrics()

    assert metrics["total_tools"] == 4
    assert metrics["enabled_tools"] == 4
    assert metrics["disabled_tools"] == 0
    assert "total_skills" in metrics
    assert "tools_per_skill" in metrics

    # Check skill counts
    assert metrics["tools_per_skill"]["research"] == 2  # browser, web_search
    assert metrics["tools_per_skill"]["synthesis"] == 2  # web_search, llm_generate


def test_get_metrics_after_disable(mapper):
    """Test metrics after disabling tools."""
    mapper.disable_tool("browser")
    mapper.disable_tool("web_search")

    metrics = mapper.get_metrics()

    assert metrics["total_tools"] == 4
    assert metrics["enabled_tools"] == 2
    assert metrics["disabled_tools"] == 2


# =============================================================================
# PolicyEngine Integration Tests
# =============================================================================


@pytest.mark.asyncio
async def test_check_tool_permission_mapper_only():
    """Test permission check without PolicyEngine."""
    mapper = SkillToolMapper()

    capability = ToolCapability(name="test_tool", description="Test")
    mapper.register_tool("test_tool", capability, required_skills=["test_skill"])

    # Authorized
    can_use = await check_tool_permission(mapper, "test_skill", "test_tool")
    assert can_use is True

    # Unauthorized
    can_use = await check_tool_permission(mapper, "other_skill", "test_tool")
    assert can_use is False


@pytest.mark.asyncio
async def test_check_tool_permission_with_policy(mapper_with_policy):
    """Test permission check with PolicyEngine integration."""
    # Authorized in both mapper and policy
    can_use = await check_tool_permission(mapper_with_policy, "research", "browser")
    assert can_use is True

    # Authorized in mapper but not in policy
    mapper_with_policy.register_tool(
        "restricted_tool",
        ToolCapability(name="restricted_tool", description="Restricted"),
        required_skills=["research"],
    )
    can_use = await check_tool_permission(mapper_with_policy, "research", "restricted_tool")
    # Policy should deny because it's not in research's allowed_tools
    assert can_use is False


@pytest.mark.asyncio
async def test_check_tool_permission_admin_bypass(mapper_with_policy):
    """Test admin skill bypasses restrictions."""
    # Admin is registered in policy with is_admin=True
    can_use = await check_tool_permission(mapper_with_policy, "admin", "browser")
    # Mapper will deny because admin is not in browser's required_skills
    assert can_use is False


@pytest.mark.asyncio
async def test_check_tool_permission_with_inputs(mapper_with_policy):
    """Test permission check with input validation."""
    # Valid URL
    can_use = await check_tool_permission(
        mapper_with_policy,
        "research",
        "browser",
        inputs={"url": "https://example.com"},
    )
    assert can_use is True


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


def test_empty_mapper():
    """Test empty mapper behavior."""
    mapper = SkillToolMapper()

    assert mapper.get_available_tools("any_skill") == []
    assert mapper.can_skill_use_tool("any_skill", "any_tool") is False
    assert mapper.discover_tools("any_skill") == []
    assert mapper.get_tool_capability("any_tool") is None


def test_multiple_skills_same_tool(mapper):
    """Test multiple skills accessing the same tool."""
    # Both research and synthesis can use web_search
    assert mapper.can_skill_use_tool("research", "web_search") is True
    assert mapper.can_skill_use_tool("synthesis", "web_search") is True

    # Both should see it in available tools
    assert "web_search" in mapper.get_available_tools("research")
    assert "web_search" in mapper.get_available_tools("synthesis")


def test_tool_reregistration():
    """Test re-registering a tool."""
    mapper = SkillToolMapper()

    cap1 = ToolCapability(name="test_tool", description="Version 1")
    mapper.register_tool("test_tool", cap1, required_skills=["skill1"])

    # Re-register with different configuration
    cap2 = ToolCapability(name="test_tool", description="Version 2")
    mapper.register_tool("test_tool", cap2, required_skills=["skill2"])

    # Should use latest registration
    capability = mapper.get_tool_capability("test_tool")
    assert capability.description == "Version 2"

    # New skill access
    assert mapper.can_skill_use_tool("skill2", "test_tool") is True


def test_discover_tools_empty_filter():
    """Test discovery with empty filter dict."""
    mapper = SkillToolMapper()

    capability = ToolCapability(name="test_tool", description="Test")
    mapper.register_tool("test_tool", capability, required_skills=["test_skill"])

    # Empty filter should match all
    tools = mapper.discover_tools("test_skill", capability_filter={})
    assert len(tools) == 1

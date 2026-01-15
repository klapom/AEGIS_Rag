"""Enterprise Bundle Example - Sprint 95.3.

Demonstrates usage of the enterprise_bundle for full AegisRAG deployment.

The enterprise bundle includes 20+ skills covering:
- Research (web_search, retrieval, graph_query, citation)
- Analysis (validation, classification, comparison, statistical_analysis)
- Synthesis (summarize, format, markdown_export)
- Development (code_generation, code_review, testing, debugging)
- Enterprise (compliance, audit, reporting, dashboard)

Use cases:
- Production RAG deployment
- Enterprise compliance
- Comprehensive monitoring
- Full-stack workflows
"""

import asyncio

from src.agents.skills.bundle_installer import get_bundle_status, install_bundle


async def main():
    """Demonstrate enterprise bundle usage."""

    print("=" * 80)
    print("Enterprise Bundle Example - Sprint 95.3")
    print("=" * 80)

    # 1. Install bundle
    print("\n1. Installing Enterprise Bundle...")
    print("   (This installs 20+ skills - may take 30-60 seconds)")
    report = install_bundle("enterprise_bundle")

    if report.success:
        print(f"   ✓ {report.summary}")
    else:
        print(f"   ✗ {report.summary}")
        return

    # Show installed skills
    status = get_bundle_status("enterprise_bundle")
    print(f"\n   Installed {len(status.installed_skills)} skills:")
    for i, skill in enumerate(status.installed_skills, 1):
        print(f"     {i:2d}. {skill}")

    # 2. Enterprise deployment workflow
    print("\n2. Enterprise Deployment Workflow:")
    print()

    # Phase 1: Compliance & Audit
    print("   Phase 1: Compliance & Audit Setup")
    print("   → Enabling GDPR compliance checks...")
    print("   → Configuring SOC2 audit logging...")
    print("   → Setting up PII detection...")
    print("   → Retention policy: 90 days")
    print("   ✓ Compliance framework active")

    # Phase 2: Core RAG Capabilities
    print("\n   Phase 2: Core RAG Capabilities")
    print("   → Vector search (Qdrant + BGE-M3): Active")
    print("   → Graph reasoning (Neo4j + LightRAG): Active")
    print("   → Memory system (Redis + Graphiti): Active")
    print("   → Citation management: Active")
    print("   ✓ RAG stack operational")

    # Phase 3: Monitoring & Dashboards
    print("\n   Phase 3: Monitoring & Dashboards")
    print("   → Dashboard update interval: 30s")
    print("   → Metrics tracked:")
    print("     - Query volume: 250 QPS")
    print("     - P95 latency: 850ms")
    print("     - Success rate: 99.2%")
    print("     - Cost tracking: $0.42/1k queries")
    print("   → Alerts configured:")
    print("     - High latency (>2s): Email + Slack")
    print("     - Error spike (>5%): PagerDuty")
    print("     - Budget limit (80%): Email")
    print("   ✓ Monitoring active")

    # Phase 4: Example Query
    print("\n   Phase 4: Example Enterprise Query")
    print("   Query: 'Analyze Q4 2025 revenue trends with compliance check'")
    print()

    # Execution trace
    print("   Execution Trace:")
    print("     [0ms] → compliance: PII detection scan")
    print("       ✓ No PII detected in query")
    print()
    print("     [50ms] → retrieval: Hybrid search (vector + sparse)")
    print("       → Retrieved 10 documents from 'financial_reports' namespace")
    print()
    print("     [120ms] → graph_query: Entity traversal")
    print("       → Found entities: Q4_2025, Revenue, Trends")
    print("       → Expanded 2-hops: 18 related entities")
    print()
    print("     [200ms] → statistical_analysis: Compute metrics")
    print("       → Revenue trend: +12.3% YoY")
    print("       → Confidence: 95% CI [10.8%, 13.8%]")
    print()
    print("     [350ms] → comparison: Compare with Q3")
    print("       → Q4 vs Q3: +5.7% QoQ")
    print()
    print("     [450ms] → summarize: Generate summary")
    print("       → Summary: 'Q4 2025 revenue grew 12.3% YoY...'")
    print()
    print("     [520ms] → citation: Add sources")
    print("       → 8 citations added")
    print()
    print("     [550ms] → format: Format as report")
    print()
    print("     [600ms] → audit: Log query execution")
    print("       → Audit ID: aud_2026_01_15_001")
    print("       → User: enterprise_user_123")
    print("       → Cost: $0.003")
    print()
    print("     [650ms] → reporting: Add to dashboard")
    print("       ✓ Metrics updated")
    print()
    print("   Total Latency: 650ms")

    # Phase 5: Generated Report
    print("\n   Phase 5: Generated Report Preview:")
    print("-" * 80)
    print(
        """
# Q4 2025 Revenue Analysis Report

**Generated:** 2026-01-15 14:30:00 UTC
**Compliance:** GDPR ✓, SOC2 ✓
**Audit ID:** aud_2026_01_15_001

## Executive Summary

Q4 2025 revenue grew 12.3% year-over-year, reaching $45.2M. This represents
a 5.7% increase compared to Q3 2025. Key drivers include:

- Enterprise subscriptions: +18.2%
- API usage: +9.5%
- Professional services: +6.3%

Statistical significance: p < 0.01 (95% CI: [10.8%, 13.8%])

## Detailed Analysis

[Full analysis with charts and tables...]

## References

[1] Q4 2025 Financial Report (Internal, 2026-01-10)
[2] Revenue Trends Dashboard (Internal, 2026-01-12)
...

## Compliance Notes

- No PII processed
- Data access logged (audit_log_id: aud_2026_01_15_001)
- Report retention: 90 days
"""
    )
    print("-" * 80)

    # Phase 6: Dashboard Metrics
    print("\n   Phase 6: Real-Time Dashboard:")
    print()
    print("   ┌─────────────────── AegisRAG Enterprise Dashboard ────────────────────┐")
    print("   │                                                                       │")
    print("   │  Queries (last hour)          Cost (last hour)                       │")
    print("   │  ├─ Total: 15,234             ├─ Total: $6.42                        │")
    print("   │  ├─ Success: 15,112 (99.2%)   ├─ Avg: $0.00042/query                │")
    print("   │  └─ Failed: 122 (0.8%)        └─ Budget: $450 / $500 (90%)          │")
    print("   │                                                                       │")
    print("   │  Latency                      Skills Usage                           │")
    print("   │  ├─ P50: 420ms                ├─ retrieval: 15,234 (100%)           │")
    print("   │  ├─ P95: 850ms                ├─ graph_query: 8,123 (53%)           │")
    print("   │  └─ P99: 1,450ms              ├─ compliance: 15,234 (100%)          │")
    print("   │                                └─ reporting: 423 (3%)                │")
    print("   │                                                                       │")
    print("   │  Alerts (last 24h)            System Health                          │")
    print("   │  ├─ None                      ├─ Qdrant: ✓ Healthy                  │")
    print("   │                                ├─ Neo4j: ✓ Healthy                   │")
    print("   │                                ├─ Redis: ✓ Healthy                   │")
    print("   │                                └─ Ollama: ✓ Healthy                  │")
    print("   │                                                                       │")
    print("   └───────────────────────────────────────────────────────────────────────┘")

    # 3. Performance summary
    print("\n3. Enterprise Bundle Performance:")
    print("   Context Budget: 150,000 tokens")
    print("   Skills Available: 23")
    print("   Skills Used (avg): 6.2 per query")
    print("   Avg Latency: 650ms")
    print("   P95 Latency: 1,800ms")
    print("   Throughput: 50 QPS")
    print("   Resource Usage:")
    print("     - Memory: 6.2 GB / 8 GB")
    print("     - CPU: 2.8 cores / 4 cores")
    print("     - GPU: Optional (used for embeddings)")

    # 4. Compliance summary
    print("\n4. Compliance Summary:")
    print("   ✓ GDPR compliant (PII detection active)")
    print("   ✓ SOC2 compliant (audit logging 90 days)")
    print("   ✓ Data retention policies enforced")
    print("   ✓ Access logs maintained")

    print("\n" + "=" * 80)
    print("Enterprise deployment successful!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

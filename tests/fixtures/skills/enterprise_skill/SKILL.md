---
name: enterprise-skill
version: 3.0.0
description: An enterprise-grade skill with full compliance

gdpr:
  legal_basis: legitimate_interests
  purpose: Advanced analytics and reporting
  retention_days: 365
  data_categories:
    - contact
    - behavioral

permissions:
  - file_read
  - vector_search
  - graph_query

audit:
  enabled: true
  events:
    - skill.loaded
    - skill.executed
    - skill.failed
  retention_days: 2555

explainability:
  decision_logging: true
  trace_inputs: true
  trace_outputs: true
  reasoning_steps: true
---

# Enterprise Skill

This skill meets ENTERPRISE certification requirements:
- Name + Version (BASIC)
- GDPR compliance (STANDARD)
- Permission declarations (STANDARD)
- Audit integration (ENTERPRISE)
- Explainability support (ENTERPRISE)

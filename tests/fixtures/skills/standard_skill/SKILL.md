---
name: standard-skill
version: 2.0.0
description: A standard skill with GDPR and permissions

gdpr:
  legal_basis: consent
  purpose: Document retrieval and analysis
  retention_days: 90

permissions:
  - file_read
  - vector_search
---

# Standard Skill

This skill meets STANDARD certification requirements:
- Name + Version (BASIC)
- GDPR declarations
- Permission declarations
- No dangerous code patterns

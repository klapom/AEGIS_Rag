# Certification API - Example Responses

**Sprint 112 Feature 112.1: Certification Status Dashboard**

This document shows example request/response pairs for all certification endpoints.

---

## 1. GET /api/v1/certification/overview

Get certification overview with counts by level and status.

**Request:**
```bash
curl -X GET http://192.168.178.10:8000/api/v1/certification/overview
```

**Response (200 OK):**
```json
{
  "enterprise_count": 3,
  "standard_count": 4,
  "basic_count": 5,
  "uncertified_count": 3,
  "expiring_soon_count": 2,
  "expired_count": 2
}
```

---

## 2. GET /api/v1/certification/skills

Get all skill certifications (no filters).

**Request:**
```bash
curl -X GET http://192.168.178.10:8000/api/v1/certification/skills
```

**Response (200 OK):** Array of 17 skills
```json
[
  {
    "skill_name": "enterprise_skill_1",
    "version": "2.1.0",
    "level": "enterprise",
    "status": "valid",
    "valid_until": "2026-07-18T00:00:00Z",
    "last_validated": "2026-01-18T00:00:00Z",
    "checks": [
      {
        "check_name": "GDPR Article 13 Transparency",
        "category": "gdpr",
        "passed": true,
        "details": "Full transparency reporting implemented"
      },
      {
        "check_name": "ISO 27001 Security Controls",
        "category": "security",
        "passed": true,
        "details": "All security controls verified"
      },
      {
        "check_name": "7-Year Audit Trail",
        "category": "audit",
        "passed": true,
        "details": "Complete audit trail with SHA-256 chaining"
      },
      {
        "check_name": "3-Level Explainability",
        "category": "explainability",
        "passed": true,
        "details": "User/Expert/Audit explanations available"
      }
    ],
    "issues": null
  },
  {
    "skill_name": "standard_skill_1",
    "version": "1.5.2",
    "level": "standard",
    "status": "valid",
    "valid_until": "2026-04-18T00:00:00Z",
    "last_validated": "2026-01-18T00:00:00Z",
    "checks": [
      {
        "check_name": "GDPR Article 13 Transparency",
        "category": "gdpr",
        "passed": true
      },
      {
        "check_name": "Basic Security Controls",
        "category": "security",
        "passed": true
      },
      {
        "check_name": "Audit Trail",
        "category": "audit",
        "passed": true
      },
      {
        "check_name": "3-Level Explainability",
        "category": "explainability",
        "passed": false,
        "details": "Only user-level explanations implemented"
      }
    ],
    "issues": [
      "Missing expert/audit-level explanations"
    ]
  }
]
```

---

## 3. GET /api/v1/certification/skills?level=enterprise

Get only enterprise-level skills.

**Request:**
```bash
curl -X GET "http://192.168.178.10:8000/api/v1/certification/skills?level=enterprise"
```

**Response (200 OK):** Array of 3 enterprise skills
```json
[
  {
    "skill_name": "enterprise_skill_1",
    "version": "2.1.0",
    "level": "enterprise",
    "status": "valid",
    "valid_until": "2026-07-18T00:00:00Z",
    "last_validated": "2026-01-18T00:00:00Z",
    "checks": [
      {
        "check_name": "GDPR Article 13 Transparency",
        "category": "gdpr",
        "passed": true,
        "details": "Full transparency reporting implemented"
      },
      {
        "check_name": "ISO 27001 Security Controls",
        "category": "security",
        "passed": true,
        "details": "All security controls verified"
      },
      {
        "check_name": "7-Year Audit Trail",
        "category": "audit",
        "passed": true,
        "details": "Complete audit trail with SHA-256 chaining"
      },
      {
        "check_name": "3-Level Explainability",
        "category": "explainability",
        "passed": true,
        "details": "User/Expert/Audit explanations available"
      }
    ],
    "issues": null
  },
  {
    "skill_name": "enterprise_skill_2",
    "version": "2.1.0",
    "level": "enterprise",
    "status": "valid",
    "valid_until": "2026-07-18T00:00:00Z",
    "last_validated": "2026-01-18T00:00:00Z",
    "checks": [
      {
        "check_name": "GDPR Article 13 Transparency",
        "category": "gdpr",
        "passed": true,
        "details": "Full transparency reporting implemented"
      },
      {
        "check_name": "ISO 27001 Security Controls",
        "category": "security",
        "passed": true,
        "details": "All security controls verified"
      },
      {
        "check_name": "7-Year Audit Trail",
        "category": "audit",
        "passed": true,
        "details": "Complete audit trail with SHA-256 chaining"
      },
      {
        "check_name": "3-Level Explainability",
        "category": "explainability",
        "passed": true,
        "details": "User/Expert/Audit explanations available"
      }
    ],
    "issues": null
  },
  {
    "skill_name": "enterprise_skill_3",
    "version": "2.1.0",
    "level": "enterprise",
    "status": "valid",
    "valid_until": "2026-07-18T00:00:00Z",
    "last_validated": "2026-01-18T00:00:00Z",
    "checks": [
      {
        "check_name": "GDPR Article 13 Transparency",
        "category": "gdpr",
        "passed": true,
        "details": "Full transparency reporting implemented"
      },
      {
        "check_name": "ISO 27001 Security Controls",
        "category": "security",
        "passed": true,
        "details": "All security controls verified"
      },
      {
        "check_name": "7-Year Audit Trail",
        "category": "audit",
        "passed": true,
        "details": "Complete audit trail with SHA-256 chaining"
      },
      {
        "check_name": "3-Level Explainability",
        "category": "explainability",
        "passed": true,
        "details": "User/Expert/Audit explanations available"
      }
    ],
    "issues": null
  }
]
```

---

## 4. GET /api/v1/certification/skills?status=expiring_soon

Get skills with expiring certifications.

**Request:**
```bash
curl -X GET "http://192.168.178.10:8000/api/v1/certification/skills?status=expiring_soon"
```

**Response (200 OK):** Array of 2 expiring skills
```json
[
  {
    "skill_name": "basic_skill_1",
    "version": "1.0.0",
    "level": "basic",
    "status": "expiring_soon",
    "valid_until": "2026-02-12T00:00:00Z",
    "last_validated": "2026-01-18T00:00:00Z",
    "checks": [
      {
        "check_name": "GDPR Article 13 Transparency",
        "category": "gdpr",
        "passed": true
      },
      {
        "check_name": "Basic Security Controls",
        "category": "security",
        "passed": true
      },
      {
        "check_name": "Audit Trail",
        "category": "audit",
        "passed": false,
        "details": "Incomplete audit logging"
      },
      {
        "check_name": "3-Level Explainability",
        "category": "explainability",
        "passed": false
      }
    ],
    "issues": [
      "Incomplete audit trail",
      "Missing explainability"
    ]
  },
  {
    "skill_name": "basic_skill_2",
    "version": "1.0.0",
    "level": "basic",
    "status": "expiring_soon",
    "valid_until": "2026-02-12T00:00:00Z",
    "last_validated": "2026-01-18T00:00:00Z",
    "checks": [
      {
        "check_name": "GDPR Article 13 Transparency",
        "category": "gdpr",
        "passed": true
      },
      {
        "check_name": "Basic Security Controls",
        "category": "security",
        "passed": true
      },
      {
        "check_name": "Audit Trail",
        "category": "audit",
        "passed": false,
        "details": "Incomplete audit logging"
      },
      {
        "check_name": "3-Level Explainability",
        "category": "explainability",
        "passed": false
      }
    ],
    "issues": [
      "Incomplete audit trail",
      "Missing explainability"
    ]
  }
]
```

---

## 5. GET /api/v1/certification/expiring?days=30

Get skills expiring in next 30 days (default threshold).

**Request:**
```bash
curl -X GET "http://192.168.178.10:8000/api/v1/certification/expiring?days=30"
```

**Response (200 OK):** Array of 2 skills (sorted by expiration date, soonest first)
```json
[
  {
    "skill_name": "basic_skill_1",
    "version": "1.0.0",
    "level": "basic",
    "status": "expiring_soon",
    "valid_until": "2026-02-12T00:00:00Z",
    "last_validated": "2026-01-18T00:00:00Z",
    "checks": [
      {
        "check_name": "GDPR Article 13 Transparency",
        "category": "gdpr",
        "passed": true
      },
      {
        "check_name": "Basic Security Controls",
        "category": "security",
        "passed": true
      },
      {
        "check_name": "Audit Trail",
        "category": "audit",
        "passed": false,
        "details": "Incomplete audit logging"
      },
      {
        "check_name": "3-Level Explainability",
        "category": "explainability",
        "passed": false
      }
    ],
    "issues": [
      "Incomplete audit trail",
      "Missing explainability"
    ]
  },
  {
    "skill_name": "basic_skill_2",
    "version": "1.0.0",
    "level": "basic",
    "status": "expiring_soon",
    "valid_until": "2026-02-12T00:00:00Z",
    "last_validated": "2026-01-18T00:00:00Z",
    "checks": [
      {
        "check_name": "GDPR Article 13 Transparency",
        "category": "gdpr",
        "passed": true
      },
      {
        "check_name": "Basic Security Controls",
        "category": "security",
        "passed": true
      },
      {
        "check_name": "Audit Trail",
        "category": "audit",
        "passed": false,
        "details": "Incomplete audit logging"
      },
      {
        "check_name": "3-Level Explainability",
        "category": "explainability",
        "passed": false
      }
    ],
    "issues": [
      "Incomplete audit trail",
      "Missing explainability"
    ]
  }
]
```

---

## 6. GET /api/v1/certification/expiring?days=90

Get skills expiring in next 90 days.

**Request:**
```bash
curl -X GET "http://192.168.178.10:8000/api/v1/certification/expiring?days=90"
```

**Response (200 OK):** Array of 9 skills (includes basic_skill_3-5 with 60-day validity, standard skills with 90-day validity)
```json
[
  {
    "skill_name": "basic_skill_1",
    "version": "1.0.0",
    "level": "basic",
    "status": "expiring_soon",
    "valid_until": "2026-02-12T00:00:00Z",
    "last_validated": "2026-01-18T00:00:00Z",
    "checks": [...],
    "issues": ["Incomplete audit trail", "Missing explainability"]
  },
  {
    "skill_name": "basic_skill_2",
    "version": "1.0.0",
    "level": "basic",
    "status": "expiring_soon",
    "valid_until": "2026-02-12T00:00:00Z",
    "last_validated": "2026-01-18T00:00:00Z",
    "checks": [...],
    "issues": ["Incomplete audit trail", "Missing explainability"]
  },
  {
    "skill_name": "basic_skill_3",
    "version": "1.0.0",
    "level": "basic",
    "status": "valid",
    "valid_until": "2026-03-19T00:00:00Z",
    "last_validated": "2026-01-18T00:00:00Z",
    "checks": [...],
    "issues": ["Incomplete audit trail", "Missing explainability"]
  },
  {
    "skill_name": "standard_skill_1",
    "version": "1.5.2",
    "level": "standard",
    "status": "valid",
    "valid_until": "2026-04-18T00:00:00Z",
    "last_validated": "2026-01-18T00:00:00Z",
    "checks": [...],
    "issues": ["Missing expert/audit-level explanations"]
  }
]
```

---

## 7. GET /api/v1/certification/skill/{skillName}/report

Get validation report for a known skill (enterprise_skill_1).

**Request:**
```bash
curl -X GET "http://192.168.178.10:8000/api/v1/certification/skill/enterprise_skill_1/report"
```

**Response (200 OK):**
```json
{
  "skill_name": "enterprise_skill_1",
  "timestamp": "2026-01-18T00:00:00Z",
  "passed_checks": 4,
  "total_checks": 4,
  "checks": [
    {
      "check_name": "GDPR Article 13 Transparency",
      "category": "gdpr",
      "passed": true,
      "details": "Full transparency reporting implemented"
    },
    {
      "check_name": "ISO 27001 Security Controls",
      "category": "security",
      "passed": true,
      "details": "All security controls verified"
    },
    {
      "check_name": "7-Year Audit Trail",
      "category": "audit",
      "passed": true,
      "details": "Complete audit trail with SHA-256 chaining"
    },
    {
      "check_name": "3-Level Explainability",
      "category": "explainability",
      "passed": true,
      "details": "User/Expert/Audit explanations available"
    }
  ],
  "recommendations": [],
  "certification_level": "enterprise"
}
```

---

## 8. GET /api/v1/certification/skill/{skillName}/report (standard skill)

Get validation report for a standard-level skill (standard_skill_1).

**Request:**
```bash
curl -X GET "http://192.168.178.10:8000/api/v1/certification/skill/standard_skill_1/report"
```

**Response (200 OK):**
```json
{
  "skill_name": "standard_skill_1",
  "timestamp": "2026-01-18T00:00:00Z",
  "passed_checks": 3,
  "total_checks": 4,
  "checks": [
    {
      "check_name": "GDPR Article 13 Transparency",
      "category": "gdpr",
      "passed": true
    },
    {
      "check_name": "Basic Security Controls",
      "category": "security",
      "passed": true
    },
    {
      "check_name": "Audit Trail",
      "category": "audit",
      "passed": true
    },
    {
      "check_name": "3-Level Explainability",
      "category": "explainability",
      "passed": false,
      "details": "Only user-level explanations implemented"
    }
  ],
  "recommendations": [
    "Add 3-level explainability: user (simple), expert (technical), audit (complete trace)",
    "Upgrade to enterprise: Implement all explainability levels and ISO 27001 controls"
  ],
  "certification_level": "standard"
}
```

---

## 9. GET /api/v1/certification/skill/{skillName}/report (unknown skill)

Get validation report for an unknown skill (graceful handling).

**Request:**
```bash
curl -X GET "http://192.168.178.10:8000/api/v1/certification/skill/unknown_skill_123/report"
```

**Response (200 OK):** Returns uncertified report
```json
{
  "skill_name": "unknown_skill_123",
  "timestamp": "2026-01-18T00:00:00Z",
  "passed_checks": 0,
  "total_checks": 4,
  "checks": [
    {
      "check_name": "GDPR Article 13 Transparency",
      "category": "gdpr",
      "passed": false
    },
    {
      "check_name": "Basic Security Controls",
      "category": "security",
      "passed": false
    },
    {
      "check_name": "Audit Trail",
      "category": "audit",
      "passed": false
    },
    {
      "check_name": "3-Level Explainability",
      "category": "explainability",
      "passed": false
    }
  ],
  "recommendations": [
    "Implement GDPR Article 13 transparency requirements (data usage disclosure, user rights)",
    "Add security controls: input validation, rate limiting, authentication checks",
    "Implement 7-year audit trail with SHA-256 chaining (EU AI Act Article 12)",
    "Add 3-level explainability: user (simple), expert (technical), audit (complete trace)",
    "Start with basic certification: Focus on GDPR compliance and basic security"
  ],
  "certification_level": "uncertified"
}
```

---

## 10. POST /api/v1/certification/skill/{skillName}/validate

Trigger validation for a skill (standard_skill_1).

**Request:**
```bash
curl -X POST "http://192.168.178.10:8000/api/v1/certification/skill/standard_skill_1/validate"
```

**Response (200 OK):** Same format as GET /report (in Sprint 112, triggers no background tasks)
```json
{
  "skill_name": "standard_skill_1",
  "timestamp": "2026-01-18T00:00:00Z",
  "passed_checks": 3,
  "total_checks": 4,
  "checks": [
    {
      "check_name": "GDPR Article 13 Transparency",
      "category": "gdpr",
      "passed": true
    },
    {
      "check_name": "Basic Security Controls",
      "category": "security",
      "passed": true
    },
    {
      "check_name": "Audit Trail",
      "category": "audit",
      "passed": true
    },
    {
      "check_name": "3-Level Explainability",
      "category": "explainability",
      "passed": false,
      "details": "Only user-level explanations implemented"
    }
  ],
  "recommendations": [
    "Add 3-level explainability: user (simple), expert (technical), audit (complete trace)",
    "Upgrade to enterprise: Implement all explainability levels and ISO 27001 controls"
  ],
  "certification_level": "standard"
}
```

---

## Summary of Mock Data Distribution

**Total Skills:** 17

| Level | Count | Status | Valid Until | Issues |
|-------|-------|--------|-------------|--------|
| Enterprise | 3 | valid | +180 days | None (4/4 checks) |
| Standard | 4 | valid | +90 days | Missing expert/audit explanations (3/4 checks) |
| Basic | 2 | expiring_soon | +25 days | Incomplete audit + missing explainability (2/4 checks) |
| Basic | 3 | valid | +60 days | Incomplete audit + missing explainability (2/4 checks) |
| Uncertified | 3 | pending | N/A | All checks failed (0/4 checks) |
| Basic (expired) | 2 | expired | -10 days | Needs re-validation (2/4 checks) |

---

**Last Updated:** 2026-01-18
**Sprint:** 112
**Feature:** 112.1 - Certification Status Dashboard

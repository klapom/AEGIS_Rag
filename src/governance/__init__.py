"""Governance modules for AegisRAG.

Includes:
- GDPR/DSGVO compliance
- Data protection and privacy
- Consent management
- Processing records
"""

from src.governance.gdpr import (
    ConsentStore,
    DataCategory,
    GDPRComplianceGuard,
    LegalBasis,
    PIIDetector,
    ProcessingLog,
)

__all__ = [
    "ConsentStore",
    "DataCategory",
    "GDPRComplianceGuard",
    "LegalBasis",
    "PIIDetector",
    "ProcessingLog",
]

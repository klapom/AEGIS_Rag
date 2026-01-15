"""GDPR Compliance Layer Demo.

Demonstrates the GDPR/DSGVO compliance features:
- PII detection
- Consent management
- Skill activation checks
- Data redaction
- Article 17 erasure
- Article 20 data portability
"""

import asyncio
from datetime import datetime, timedelta

from src.governance.gdpr import (
    ConsentRecord,
    ConsentStore,
    DataCategory,
    GDPRComplianceGuard,
    LegalBasis,
    PIIDetector,
    ProcessingLog,
)


async def demo_pii_detection():
    """Demo: PII detection in text."""
    print("\n" + "=" * 60)
    print("1. PII DETECTION DEMO")
    print("=" * 60)

    detector = PIIDetector()

    sample_text = """
    Customer Record:
    Name: John Doe
    Email: john.doe@example.com
    Phone: (555) 123-4567
    SSN: 123-45-6789
    Credit Card: 4532-1488-0343-6467
    IBAN: DE89370400440532013000
    IP Address: 192.168.1.1
    """

    detected = detector.detect(sample_text)

    print("\nDetected PII:")
    for category, items in detected.items():
        print(f"\n  {category.value.upper()}:")
        for item in items:
            print(f"    - {item}")


async def demo_consent_management():
    """Demo: Consent record management."""
    print("\n" + "=" * 60)
    print("2. CONSENT MANAGEMENT DEMO")
    print("=" * 60)

    store = ConsentStore()

    # Grant consent
    consent = ConsentRecord(
        data_subject_id="user_12345",
        purpose="analytics_processing",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT, DataCategory.BEHAVIORAL],
        expires_at=datetime.utcnow() + timedelta(days=365),
    )
    await store.add(consent)

    print(f"\n✓ Consent granted: {consent.consent_id}")
    print(f"  Purpose: {consent.purpose}")
    print(f"  Categories: {[c.value for c in consent.data_categories]}")
    print(f"  Valid: {consent.is_valid()}")
    print(f"  Expires: {consent.expires_at.strftime('%Y-%m-%d')}")

    # Withdraw consent
    consent.withdraw(reason="User requested privacy protection")
    await store.update(consent)

    print(f"\n✓ Consent withdrawn")
    print(f"  Valid: {consent.is_valid()}")
    print(f"  Reason: {consent.withdrawal_reason}")


async def demo_skill_activation():
    """Demo: Skill activation with GDPR checks."""
    print("\n" + "=" * 60)
    print("3. SKILL ACTIVATION CHECK DEMO")
    print("=" * 60)

    consent_store = ConsentStore()
    processing_log = ProcessingLog()
    guard = GDPRComplianceGuard(consent_store, processing_log)

    # Register skill requirements
    guard.register_skill_requirements(
        skill_name="advanced_analytics",
        required_categories=[DataCategory.CONTACT, DataCategory.BEHAVIORAL],
    )

    # Try without consent
    allowed, error = await guard.check_skill_activation(
        skill_name="advanced_analytics",
        data_subject_id="user_67890",
        context={},
    )

    print(f"\n✗ Skill activation WITHOUT consent:")
    print(f"  Allowed: {allowed}")
    print(f"  Error: {error}")

    # Grant consent
    consent = ConsentRecord(
        data_subject_id="user_67890",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT, DataCategory.BEHAVIORAL],
    )
    await consent_store.add(consent)

    # Try with consent
    allowed, error = await guard.check_skill_activation(
        skill_name="advanced_analytics",
        data_subject_id="user_67890",
        context={},
    )

    print(f"\n✓ Skill activation WITH consent:")
    print(f"  Allowed: {allowed}")
    print(f"  Error: {error}")


async def demo_pii_redaction():
    """Demo: PII redaction based on allowed categories."""
    print("\n" + "=" * 60)
    print("4. PII REDACTION DEMO")
    print("=" * 60)

    consent_store = ConsentStore()
    processing_log = ProcessingLog()
    guard = GDPRComplianceGuard(consent_store, processing_log)

    text = """
    User Profile:
    Email: user@example.com
    Phone: (555) 987-6543
    SSN: 987-65-4321
    Location: 192.168.1.100
    """

    print(f"\nOriginal text:\n{text}")

    # Redact with only contact info allowed
    redacted = guard.redact_pii(
        text=text,
        allowed_categories={DataCategory.CONTACT},
    )

    print(f"\nRedacted text (CONTACT allowed):\n{redacted}")


async def demo_data_erasure():
    """Demo: Article 17 right to erasure."""
    print("\n" + "=" * 60)
    print("5. DATA ERASURE DEMO (Article 17)")
    print("=" * 60)

    consent_store = ConsentStore()
    processing_log = ProcessingLog()
    guard = GDPRComplianceGuard(consent_store, processing_log)

    # Create some data
    consent = ConsentRecord(
        data_subject_id="user_erasure",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
    )
    await consent_store.add(consent)

    print("\n✓ User data created")
    print(f"  Consents: {len(await consent_store.get_all('user_erasure'))}")

    # Request erasure
    result = await guard.handle_erasure_request("user_erasure")

    print(f"\n✓ Erasure request completed:")
    print(f"  Consents deleted: {result['consents_deleted']}")
    print(f"  Records deleted: {result['processing_records_deleted']}")
    print(f"  Timestamp: {result['erasure_timestamp']}")

    # Verify erasure
    remaining = await consent_store.get_all("user_erasure")
    print(f"\n✓ Verification: {len(remaining)} consents remaining")


async def demo_data_export():
    """Demo: Article 20 data portability."""
    print("\n" + "=" * 60)
    print("6. DATA EXPORT DEMO (Article 20)")
    print("=" * 60)

    consent_store = ConsentStore()
    processing_log = ProcessingLog()
    guard = GDPRComplianceGuard(consent_store, processing_log)

    # Create some data
    consent = ConsentRecord(
        data_subject_id="user_export",
        purpose="marketing",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT, DataCategory.BEHAVIORAL],
    )
    await consent_store.add(consent)

    # Export data
    export = await guard.export_data("user_export")

    print(f"\n✓ Data export completed:")
    print(f"  Data subject: {export['data_subject_id']}")
    print(f"  Consents: {len(export['consents'])}")
    print(f"  Processing records: {len(export['processing_records'])}")
    print(f"  Checksum: {export['checksum'][:16]}...")
    print(f"  Timestamp: {export['export_timestamp']}")


async def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("GDPR/DSGVO COMPLIANCE LAYER DEMO")
    print("AegisRAG Sprint 96 Feature 96.1")
    print("=" * 60)

    await demo_pii_detection()
    await demo_consent_management()
    await demo_skill_activation()
    await demo_pii_redaction()
    await demo_data_erasure()
    await demo_data_export()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

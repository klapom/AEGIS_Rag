"""Unit tests for GDPR compliance layer.

Tests:
- Legal bases and data categories
- PII detection (email, phone, SSN, CC, IBAN)
- Consent management (grant, expire, withdraw)
- Article 17 erasure
- Article 20 data portability
- Skill activation checks
- PII redaction
"""

from datetime import datetime, timedelta

import pytest

from src.governance.gdpr.compliance import (
    ConsentRecord,
    DataCategory,
    DataProcessingRecord,
    GDPRComplianceGuard,
    LegalBasis,
    PIIDetector,
)
from src.governance.gdpr.storage import ConsentStore, ProcessingLog


# ===== Fixtures =====


@pytest.fixture
def pii_detector() -> PIIDetector:
    """Create PII detector instance."""
    return PIIDetector()


@pytest.fixture
def consent_store() -> ConsentStore:
    """Create consent store instance."""
    store = ConsentStore()
    yield store
    store.clear()


@pytest.fixture
def processing_log() -> ProcessingLog:
    """Create processing log instance."""
    log = ProcessingLog()
    yield log
    log.clear()


@pytest.fixture
def gdpr_guard(
    consent_store: ConsentStore,
    processing_log: ProcessingLog,
    pii_detector: PIIDetector,
) -> GDPRComplianceGuard:
    """Create GDPR compliance guard."""
    return GDPRComplianceGuard(
        consent_store=consent_store,
        processing_log=processing_log,
        pii_detector=pii_detector,
    )


# ===== Legal Basis Tests =====


def test_legal_basis_enum():
    """Test legal basis enum values."""
    assert LegalBasis.CONSENT == "consent"
    assert LegalBasis.CONTRACT == "contract"
    assert LegalBasis.LEGAL_OBLIGATION == "legal_obligation"
    assert LegalBasis.VITAL_INTERESTS == "vital_interests"
    assert LegalBasis.PUBLIC_TASK == "public_task"
    assert LegalBasis.LEGITIMATE_INTERESTS == "legitimate_interests"


def test_legal_basis_count():
    """Test that all Article 6 legal bases are present."""
    assert len(LegalBasis) == 6


# ===== Data Category Tests =====


def test_data_category_standard():
    """Test standard data categories."""
    assert DataCategory.IDENTIFIER == "identifier"
    assert DataCategory.CONTACT == "contact"
    assert DataCategory.DEMOGRAPHIC == "demographic"
    assert DataCategory.FINANCIAL == "financial"
    assert DataCategory.LOCATION == "location"
    assert DataCategory.BEHAVIORAL == "behavioral"


def test_data_category_special():
    """Test special data categories (Article 9)."""
    assert DataCategory.HEALTH == "health"
    assert DataCategory.BIOMETRIC == "biometric"
    assert DataCategory.GENETIC == "genetic"
    assert DataCategory.POLITICAL == "political"
    assert DataCategory.RELIGIOUS == "religious"
    assert DataCategory.PHILOSOPHICAL == "philosophical"
    assert DataCategory.UNION_MEMBERSHIP == "union_membership"
    assert DataCategory.SEXUAL_ORIENTATION == "sexual_orientation"
    assert DataCategory.RACIAL_ETHNIC == "racial_ethnic"


def test_data_category_count():
    """Test total number of data categories."""
    assert len(DataCategory) == 15


# ===== Consent Record Tests =====


def test_consent_record_creation():
    """Test consent record creation."""
    consent = ConsentRecord(
        data_subject_id="user123",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT, DataCategory.BEHAVIORAL],
    )

    assert consent.data_subject_id == "user123"
    assert consent.purpose == "analytics"
    assert consent.legal_basis == LegalBasis.CONSENT
    assert len(consent.data_categories) == 2
    assert DataCategory.CONTACT in consent.data_categories
    assert consent.withdrawn_at is None
    assert consent.is_valid()


def test_consent_record_with_expiration():
    """Test consent record with expiration."""
    future = datetime.utcnow() + timedelta(days=30)
    consent = ConsentRecord(
        data_subject_id="user123",
        purpose="marketing",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
        expires_at=future,
    )

    assert consent.is_valid()
    assert consent.expires_at == future


def test_consent_record_expired():
    """Test expired consent record."""
    past = datetime.utcnow() - timedelta(days=1)
    consent = ConsentRecord(
        data_subject_id="user123",
        purpose="marketing",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
        expires_at=past,
    )

    assert not consent.is_valid()


def test_consent_withdrawal():
    """Test consent withdrawal."""
    consent = ConsentRecord(
        data_subject_id="user123",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.BEHAVIORAL],
    )

    assert consent.is_valid()

    consent.withdraw(reason="User requested")

    assert not consent.is_valid()
    assert consent.withdrawn_at is not None
    assert consent.withdrawal_reason == "User requested"


def test_consent_validation_with_string_categories():
    """Test consent validation with string data categories."""
    consent = ConsentRecord(
        data_subject_id="user123",
        purpose="test",
        legal_basis=LegalBasis.CONSENT,
        data_categories=["contact", "identifier"],
    )

    assert len(consent.data_categories) == 2
    assert DataCategory.CONTACT in consent.data_categories
    assert DataCategory.IDENTIFIER in consent.data_categories


# ===== Processing Record Tests =====


def test_processing_record_creation():
    """Test processing record creation."""
    record = DataProcessingRecord(
        controller_name="AegisRAG",
        processing_purpose="skill_execution",
        legal_basis=LegalBasis.LEGITIMATE_INTERESTS,
        data_categories=[DataCategory.CONTACT],
        data_subjects=["user123"],
    )

    assert record.controller_name == "AegisRAG"
    assert record.processing_purpose == "skill_execution"
    assert record.legal_basis == LegalBasis.LEGITIMATE_INTERESTS
    assert len(record.data_categories) == 1
    assert len(record.data_subjects) == 1


def test_processing_record_with_metadata():
    """Test processing record with metadata."""
    record = DataProcessingRecord(
        controller_name="AegisRAG",
        processing_purpose="skill_execution",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.BEHAVIORAL],
        data_subjects=["user123"],
        recipients=["analytics_service"],
        retention_period="30 days",
        security_measures=["encryption", "access_control"],
        metadata={"skill_name": "research_skill", "query": "test"},
    )

    assert len(record.recipients) == 1
    assert record.retention_period == "30 days"
    assert len(record.security_measures) == 2
    assert record.metadata["skill_name"] == "research_skill"


# ===== PII Detector Tests =====


def test_detect_email(pii_detector: PIIDetector):
    """Test email detection."""
    text = "Contact us at support@example.com or sales@company.co.uk"
    emails = pii_detector.detect_email(text)

    assert len(emails) == 2
    assert "support@example.com" in emails
    assert "sales@company.co.uk" in emails


def test_detect_phone_us_format(pii_detector: PIIDetector):
    """Test US phone number detection."""
    text = "Call us at (555) 123-4567 or 555-987-6543"
    phones = pii_detector.detect_phone(text)

    assert len(phones) >= 1
    # At least one phone number should be detected


def test_detect_phone_international(pii_detector: PIIDetector):
    """Test international phone number detection."""
    text = "Phone: +49 30 12345678 or +1 555 123 4567"
    phones = pii_detector.detect_phone(text)

    assert len(phones) >= 1


def test_detect_ssn(pii_detector: PIIDetector):
    """Test SSN detection."""
    text = "SSN: 123-45-6789 or 987-65-4321"
    ssns = pii_detector.detect_ssn(text)

    assert len(ssns) == 2
    assert "123-45-6789" in ssns
    assert "987-65-4321" in ssns


def test_detect_credit_card_valid(pii_detector: PIIDetector):
    """Test valid credit card detection with Luhn check."""
    # Valid test card numbers (pass Luhn algorithm)
    text = "Card: 4532-1488-0343-6467 or 5425-2334-3010-9903"
    cards = pii_detector.detect_credit_card(text)

    # Should detect at least the valid cards
    assert len(cards) >= 1


def test_detect_credit_card_invalid_luhn(pii_detector: PIIDetector):
    """Test invalid credit card rejection (Luhn check)."""
    # Invalid card number (fails Luhn)
    text = "Card: 1234-5678-9012-3456"
    cards = pii_detector.detect_credit_card(text)

    # Should not detect invalid card
    assert "1234-5678-9012-3456" not in cards


def test_detect_iban(pii_detector: PIIDetector):
    """Test IBAN detection."""
    text = "IBAN: DE89370400440532013000 or GB29NWBK60161331926819"
    ibans = pii_detector.detect_iban(text)

    assert len(ibans) == 2
    assert "DE89370400440532013000" in ibans
    assert "GB29NWBK60161331926819" in ibans


def test_detect_multiple_categories(pii_detector: PIIDetector):
    """Test detection of multiple PII categories."""
    text = """
    Contact: john.doe@example.com
    Phone: (555) 123-4567
    SSN: 123-45-6789
    Card: 4532-1488-0343-6467
    IBAN: DE89370400440532013000
    """

    detected = pii_detector.detect(text)

    # Should detect contact, identifier, and financial categories
    assert DataCategory.CONTACT in detected
    assert DataCategory.IDENTIFIER in detected
    assert DataCategory.FINANCIAL in detected


def test_detect_no_pii(pii_detector: PIIDetector):
    """Test text with no PII."""
    text = "This is a completely clean text with no personal information."
    detected = pii_detector.detect(text)

    assert len(detected) == 0


def test_detect_ip_addresses(pii_detector: PIIDetector):
    """Test IP address detection."""
    text = "Servers: 192.168.1.1 and 10.0.0.1, IPv6: 2001:0db8:85a3:0000:0000:8a2e:0370:7334"
    detected = pii_detector.detect(text)

    assert DataCategory.LOCATION in detected
    assert len(detected[DataCategory.LOCATION]) >= 2


# ===== Consent Store Tests =====


@pytest.mark.asyncio
async def test_consent_store_add_and_get(consent_store: ConsentStore):
    """Test adding and retrieving consent."""
    consent = ConsentRecord(
        data_subject_id="user123",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
    )

    await consent_store.add(consent)

    retrieved = await consent_store.get(consent.consent_id)
    assert retrieved is not None
    assert retrieved.consent_id == consent.consent_id


@pytest.mark.asyncio
async def test_consent_store_get_by_category(consent_store: ConsentStore):
    """Test retrieving consent by category."""
    consent1 = ConsentRecord(
        data_subject_id="user123",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
    )
    consent2 = ConsentRecord(
        data_subject_id="user123",
        purpose="research",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.BEHAVIORAL],
    )

    await consent_store.add(consent1)
    await consent_store.add(consent2)

    contact_consents = await consent_store.get_consents(
        data_subject_id="user123",
        data_category=DataCategory.CONTACT,
    )

    assert len(contact_consents) == 1
    assert contact_consents[0].consent_id == consent1.consent_id


@pytest.mark.asyncio
async def test_consent_store_update(consent_store: ConsentStore):
    """Test updating consent record."""
    consent = ConsentRecord(
        data_subject_id="user123",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
    )

    await consent_store.add(consent)

    # Withdraw consent
    consent.withdraw(reason="User requested")
    await consent_store.update(consent)

    retrieved = await consent_store.get(consent.consent_id)
    assert retrieved is not None
    assert not retrieved.is_valid()


@pytest.mark.asyncio
async def test_consent_store_delete(consent_store: ConsentStore):
    """Test deleting consent record."""
    consent = ConsentRecord(
        data_subject_id="user123",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
    )

    await consent_store.add(consent)
    deleted = await consent_store.delete(consent.consent_id)

    assert deleted
    retrieved = await consent_store.get(consent.consent_id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_consent_store_delete_all(consent_store: ConsentStore):
    """Test deleting all consents for a subject."""
    for i in range(3):
        consent = ConsentRecord(
            data_subject_id="user123",
            purpose=f"purpose{i}",
            legal_basis=LegalBasis.CONSENT,
            data_categories=[DataCategory.CONTACT],
        )
        await consent_store.add(consent)

    deleted_count = await consent_store.delete_all("user123")

    assert deleted_count == 3
    consents = await consent_store.get_all("user123")
    assert len(consents) == 0


# ===== Processing Log Tests =====


@pytest.mark.asyncio
async def test_processing_log_add_and_get(processing_log: ProcessingLog):
    """Test adding and retrieving processing record."""
    record = DataProcessingRecord(
        controller_name="AegisRAG",
        processing_purpose="skill_execution",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
        data_subjects=["user123"],
    )

    await processing_log.add(record)

    retrieved = await processing_log.get(record.record_id)
    assert retrieved is not None
    assert retrieved.record_id == record.record_id


@pytest.mark.asyncio
async def test_processing_log_get_by_subject(processing_log: ProcessingLog):
    """Test retrieving records by subject."""
    record1 = DataProcessingRecord(
        controller_name="AegisRAG",
        processing_purpose="skill1",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
        data_subjects=["user123"],
    )
    record2 = DataProcessingRecord(
        controller_name="AegisRAG",
        processing_purpose="skill2",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.BEHAVIORAL],
        data_subjects=["user456"],
    )

    await processing_log.add(record1)
    await processing_log.add(record2)

    records = await processing_log.get_by_subject("user123")

    assert len(records) == 1
    assert records[0].record_id == record1.record_id


@pytest.mark.asyncio
async def test_processing_log_get_by_purpose(processing_log: ProcessingLog):
    """Test retrieving records by purpose."""
    for i in range(3):
        record = DataProcessingRecord(
            controller_name="AegisRAG",
            processing_purpose="analytics",
            legal_basis=LegalBasis.CONSENT,
            data_categories=[DataCategory.BEHAVIORAL],
            data_subjects=[f"user{i}"],
        )
        await processing_log.add(record)

    records = await processing_log.get_by_purpose("analytics")

    assert len(records) == 3


@pytest.mark.asyncio
async def test_processing_log_delete_by_subject(processing_log: ProcessingLog):
    """Test deleting records by subject."""
    record1 = DataProcessingRecord(
        controller_name="AegisRAG",
        processing_purpose="skill1",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
        data_subjects=["user123"],
    )
    record2 = DataProcessingRecord(
        controller_name="AegisRAG",
        processing_purpose="skill2",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.BEHAVIORAL],
        data_subjects=["user123"],
    )

    await processing_log.add(record1)
    await processing_log.add(record2)

    deleted_count = await processing_log.delete_by_subject("user123")

    assert deleted_count == 2
    records = await processing_log.get_by_subject("user123")
    assert len(records) == 0


# ===== GDPR Guard Tests =====


@pytest.mark.asyncio
async def test_gdpr_guard_register_skill(gdpr_guard: GDPRComplianceGuard):
    """Test registering skill requirements."""
    gdpr_guard.register_skill_requirements(
        skill_name="analytics_skill",
        required_categories=[DataCategory.CONTACT, DataCategory.BEHAVIORAL],
    )

    requirements = gdpr_guard.get_skill_requirements("analytics_skill")
    assert len(requirements) == 2
    assert DataCategory.CONTACT in requirements


@pytest.mark.asyncio
async def test_gdpr_guard_skill_activation_no_requirements(
    gdpr_guard: GDPRComplianceGuard,
):
    """Test skill activation with no GDPR requirements."""
    allowed, error = await gdpr_guard.check_skill_activation(
        skill_name="public_skill",
        data_subject_id="user123",
        context={},
    )

    assert allowed
    assert error is None


@pytest.mark.asyncio
async def test_gdpr_guard_skill_activation_with_consent(
    gdpr_guard: GDPRComplianceGuard,
    consent_store: ConsentStore,
):
    """Test skill activation with valid consent."""
    # Register skill requirements
    gdpr_guard.register_skill_requirements(
        skill_name="analytics_skill",
        required_categories=[DataCategory.CONTACT],
    )

    # Grant consent
    consent = ConsentRecord(
        data_subject_id="user123",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
    )
    await consent_store.add(consent)

    # Check activation
    allowed, error = await gdpr_guard.check_skill_activation(
        skill_name="analytics_skill",
        data_subject_id="user123",
        context={},
    )

    assert allowed
    assert error is None


@pytest.mark.asyncio
async def test_gdpr_guard_skill_activation_missing_consent(
    gdpr_guard: GDPRComplianceGuard,
):
    """Test skill activation without consent."""
    # Register skill requirements
    gdpr_guard.register_skill_requirements(
        skill_name="analytics_skill",
        required_categories=[DataCategory.CONTACT],
    )

    # Check activation without consent
    allowed, error = await gdpr_guard.check_skill_activation(
        skill_name="analytics_skill",
        data_subject_id="user123",
        context={},
    )

    assert not allowed
    assert error is not None
    assert "Missing consent" in error


@pytest.mark.asyncio
async def test_gdpr_guard_skill_activation_withdrawn_consent(
    gdpr_guard: GDPRComplianceGuard,
    consent_store: ConsentStore,
):
    """Test skill activation with withdrawn consent."""
    # Register skill requirements
    gdpr_guard.register_skill_requirements(
        skill_name="analytics_skill",
        required_categories=[DataCategory.CONTACT],
    )

    # Grant and withdraw consent
    consent = ConsentRecord(
        data_subject_id="user123",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
    )
    consent.withdraw(reason="User requested")
    await consent_store.add(consent)

    # Check activation
    allowed, error = await gdpr_guard.check_skill_activation(
        skill_name="analytics_skill",
        data_subject_id="user123",
        context={},
    )

    assert not allowed
    assert error is not None


def test_gdpr_guard_redact_pii(gdpr_guard: GDPRComplianceGuard):
    """Test PII redaction."""
    text = "Contact: john.doe@example.com, Phone: (555) 123-4567, SSN: 123-45-6789"

    # Allow contact info only
    redacted = gdpr_guard.redact_pii(
        text=text,
        allowed_categories={DataCategory.CONTACT},
    )

    # Email and phone should be preserved, SSN redacted
    assert "john.doe@example.com" in redacted or "[REDACTED_CONTACT]" not in redacted
    assert "[REDACTED_IDENTIFIER]" in redacted


def test_gdpr_guard_redact_pii_all_allowed(gdpr_guard: GDPRComplianceGuard):
    """Test PII redaction with all categories allowed."""
    text = "Contact: john.doe@example.com, SSN: 123-45-6789"

    redacted = gdpr_guard.redact_pii(
        text=text,
        allowed_categories={DataCategory.CONTACT, DataCategory.IDENTIFIER},
    )

    # Nothing should be redacted
    assert "john.doe@example.com" in redacted
    assert "123-45-6789" in redacted


@pytest.mark.asyncio
async def test_gdpr_guard_erasure_request(
    gdpr_guard: GDPRComplianceGuard,
    consent_store: ConsentStore,
    processing_log: ProcessingLog,
):
    """Test Article 17 right to erasure."""
    # Add consent
    consent = ConsentRecord(
        data_subject_id="user123",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
    )
    await consent_store.add(consent)

    # Add processing record
    record = DataProcessingRecord(
        controller_name="AegisRAG",
        processing_purpose="skill_execution",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
        data_subjects=["user123"],
    )
    await processing_log.add(record)

    # Request erasure
    result = await gdpr_guard.handle_erasure_request("user123")

    assert result["data_subject_id"] == "user123"
    assert result["consents_deleted"] == 1
    assert result["processing_records_deleted"] == 1
    assert len(result["errors"]) == 0

    # Verify data is erased
    consents = await consent_store.get_all("user123")
    assert len(consents) == 0


@pytest.mark.asyncio
async def test_gdpr_guard_export_data(
    gdpr_guard: GDPRComplianceGuard,
    consent_store: ConsentStore,
    processing_log: ProcessingLog,
):
    """Test Article 20 data portability."""
    # Add consent
    consent = ConsentRecord(
        data_subject_id="user123",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
    )
    await consent_store.add(consent)

    # Add processing record
    record = DataProcessingRecord(
        controller_name="AegisRAG",
        processing_purpose="skill_execution",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
        data_subjects=["user123"],
    )
    await processing_log.add(record)

    # Export data
    export = await gdpr_guard.export_data("user123")

    assert export["data_subject_id"] == "user123"
    assert len(export["consents"]) == 1
    assert len(export["processing_records"]) == 1
    assert "checksum" in export
    assert "export_timestamp" in export


# ===== Edge Cases and Integration Tests =====


@pytest.mark.asyncio
async def test_multiple_consents_same_category(
    gdpr_guard: GDPRComplianceGuard,
    consent_store: ConsentStore,
):
    """Test multiple consents for same category."""
    # Add two consents for contact info
    consent1 = ConsentRecord(
        data_subject_id="user123",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
        expires_at=datetime.utcnow() - timedelta(days=1),  # Expired
    )
    consent2 = ConsentRecord(
        data_subject_id="user123",
        purpose="marketing",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
    )

    await consent_store.add(consent1)
    await consent_store.add(consent2)

    # Register skill
    gdpr_guard.register_skill_requirements(
        skill_name="test_skill",
        required_categories=[DataCategory.CONTACT],
    )

    # Should allow activation (second consent is valid)
    allowed, error = await gdpr_guard.check_skill_activation(
        skill_name="test_skill",
        data_subject_id="user123",
        context={},
    )

    assert allowed
    assert error is None


def test_pii_detector_edge_cases(pii_detector: PIIDetector):
    """Test PII detector edge cases."""
    # Empty text
    assert len(pii_detector.detect("")) == 0

    # Text with special characters
    text = "Email: <test@example.com>, Phone: [+1-555-123-4567]"
    detected = pii_detector.detect(text)
    assert DataCategory.CONTACT in detected

    # Multiple similar patterns
    text = "Emails: test1@example.com, test2@example.com, test3@example.com"
    emails = pii_detector.detect_email(text)
    assert len(emails) == 3


@pytest.mark.asyncio
async def test_consent_record_metadata(consent_store: ConsentStore):
    """Test consent record with metadata."""
    consent = ConsentRecord(
        data_subject_id="user123",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
        metadata={"source": "web_form", "ip": "192.168.1.1"},
    )

    await consent_store.add(consent)

    retrieved = await consent_store.get(consent.consent_id)
    assert retrieved is not None
    assert retrieved.metadata["source"] == "web_form"


@pytest.mark.asyncio
async def test_processing_record_date_filtering(processing_log: ProcessingLog):
    """Test processing record date filtering."""
    # Add records
    record1 = DataProcessingRecord(
        controller_name="AegisRAG",
        processing_purpose="skill1",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
        data_subjects=["user123"],
    )
    await processing_log.add(record1)

    # Get records with date filter
    now = datetime.utcnow()
    past = now - timedelta(hours=1)
    future = now + timedelta(hours=1)

    records = await processing_log.get_by_subject(
        "user123",
        start_date=past,
        end_date=future,
    )

    assert len(records) == 1


@pytest.mark.asyncio
async def test_consent_store_get_nonexistent(consent_store: ConsentStore):
    """Test getting nonexistent consent."""
    consent = await consent_store.get("nonexistent_id")
    assert consent is None


@pytest.mark.asyncio
async def test_consent_store_delete_nonexistent(consent_store: ConsentStore):
    """Test deleting nonexistent consent."""
    deleted = await consent_store.delete("nonexistent_id")
    assert not deleted


@pytest.mark.asyncio
async def test_processing_log_get_nonexistent(processing_log: ProcessingLog):
    """Test getting nonexistent processing record."""
    record = await processing_log.get("nonexistent_id")
    assert record is None


@pytest.mark.asyncio
async def test_processing_log_get_all_with_date_filter(processing_log: ProcessingLog):
    """Test getting all records with date filter."""
    record1 = DataProcessingRecord(
        controller_name="AegisRAG",
        processing_purpose="skill1",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
        data_subjects=["user123"],
    )
    await processing_log.add(record1)

    now = datetime.utcnow()
    past = now - timedelta(hours=1)
    future = now + timedelta(hours=1)

    records = await processing_log.get_all(start_date=past, end_date=future)
    assert len(records) == 1


@pytest.mark.asyncio
async def test_processing_log_get_by_purpose_with_dates(processing_log: ProcessingLog):
    """Test getting records by purpose with date filtering."""
    record1 = DataProcessingRecord(
        controller_name="AegisRAG",
        processing_purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
        data_subjects=["user123"],
    )
    await processing_log.add(record1)

    now = datetime.utcnow()
    past = now - timedelta(hours=1)
    future = now + timedelta(hours=1)

    records = await processing_log.get_by_purpose(
        "analytics",
        start_date=past,
        end_date=future,
    )
    assert len(records) == 1


def test_pii_detector_luhn_validation(pii_detector: PIIDetector):
    """Test Luhn algorithm validation for credit cards."""
    # Invalid card (fails Luhn)
    assert not pii_detector._validate_luhn("1234567890123456")

    # Non-numeric input
    assert not pii_detector._validate_luhn("abcd1234")

    # Empty string
    assert not pii_detector._validate_luhn("")


@pytest.mark.asyncio
async def test_gdpr_guard_skill_activation_expired_consent(
    gdpr_guard: GDPRComplianceGuard,
    consent_store: ConsentStore,
):
    """Test skill activation with expired consent."""
    # Register skill requirements
    gdpr_guard.register_skill_requirements(
        skill_name="analytics_skill",
        required_categories=[DataCategory.CONTACT],
    )

    # Grant expired consent
    consent = ConsentRecord(
        data_subject_id="user123",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
        expires_at=datetime.utcnow() - timedelta(days=1),
    )
    await consent_store.add(consent)

    # Check activation
    allowed, error = await gdpr_guard.check_skill_activation(
        skill_name="analytics_skill",
        data_subject_id="user123",
        context={},
    )

    assert not allowed
    assert error is not None
    assert "Missing consent" in error


@pytest.mark.asyncio
async def test_gdpr_guard_skill_activation_multiple_categories(
    gdpr_guard: GDPRComplianceGuard,
    consent_store: ConsentStore,
):
    """Test skill activation requiring multiple categories."""
    # Register skill with multiple requirements
    gdpr_guard.register_skill_requirements(
        skill_name="advanced_analytics",
        required_categories=[DataCategory.CONTACT, DataCategory.BEHAVIORAL],
    )

    # Grant consent for only one category
    consent = ConsentRecord(
        data_subject_id="user123",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
    )
    await consent_store.add(consent)

    # Should fail - missing BEHAVIORAL consent
    allowed, error = await gdpr_guard.check_skill_activation(
        skill_name="advanced_analytics",
        data_subject_id="user123",
        context={},
    )

    assert not allowed
    assert "behavioral" in error.lower()


@pytest.mark.asyncio
async def test_gdpr_guard_erasure_with_errors(
    gdpr_guard: GDPRComplianceGuard,
    consent_store: ConsentStore,
):
    """Test erasure request handling."""
    # Add some data
    consent = ConsentRecord(
        data_subject_id="user123",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
    )
    await consent_store.add(consent)

    # Request erasure
    result = await gdpr_guard.handle_erasure_request("user123")

    assert result["data_subject_id"] == "user123"
    assert "erasure_timestamp" in result
    assert result["consents_deleted"] >= 0


def test_consent_record_auto_generated_id():
    """Test that consent records get auto-generated IDs."""
    consent1 = ConsentRecord(
        data_subject_id="user123",
        purpose="analytics",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
    )
    consent2 = ConsentRecord(
        data_subject_id="user456",
        purpose="marketing",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
    )

    # IDs should be unique
    assert consent1.consent_id != consent2.consent_id
    assert len(consent1.consent_id) > 0


def test_processing_record_auto_generated_id():
    """Test that processing records get auto-generated IDs."""
    record1 = DataProcessingRecord(
        controller_name="AegisRAG",
        processing_purpose="skill1",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT],
        data_subjects=["user123"],
    )
    record2 = DataProcessingRecord(
        controller_name="AegisRAG",
        processing_purpose="skill2",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.BEHAVIORAL],
        data_subjects=["user456"],
    )

    # IDs should be unique
    assert record1.record_id != record2.record_id
    assert len(record1.record_id) > 0

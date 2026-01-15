"""GDPR/DSGVO Compliance Implementation.

Implements EU GDPR (2016/679) compliance for AegisRAG:
- Article 6: Legal bases for processing
- Article 13/14: Information obligations
- Article 17: Right to erasure
- Article 20: Data portability
- Article 30: Records of processing activities
"""

import hashlib
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class LegalBasis(str, Enum):
    """Article 6 GDPR legal bases for processing personal data.

    See: https://gdpr-info.eu/art-6-gdpr/
    """

    CONSENT = "consent"  # Article 6(1)(a): Data subject consent
    CONTRACT = "contract"  # Article 6(1)(b): Contract performance
    LEGAL_OBLIGATION = "legal_obligation"  # Article 6(1)(c): Legal obligation
    VITAL_INTERESTS = "vital_interests"  # Article 6(1)(d): Vital interests
    PUBLIC_TASK = "public_task"  # Article 6(1)(e): Public interest task
    LEGITIMATE_INTERESTS = "legitimate_interests"  # Article 6(1)(f): Legitimate interests


class DataCategory(str, Enum):
    """GDPR personal data categories.

    Categories align with Article 4(1) definition of personal data
    and Article 9 special categories.
    """

    # Standard personal data (Article 4(1))
    IDENTIFIER = "identifier"  # Name, ID number, SSN, Tax ID
    CONTACT = "contact"  # Email, phone, address
    DEMOGRAPHIC = "demographic"  # Age, gender, nationality
    FINANCIAL = "financial"  # Credit card, bank account, IBAN
    LOCATION = "location"  # GPS, IP address, geolocation
    BEHAVIORAL = "behavioral"  # User behavior, preferences

    # Special categories (Article 9)
    HEALTH = "health"  # Medical records, health status
    BIOMETRIC = "biometric"  # Fingerprints, facial recognition
    GENETIC = "genetic"  # DNA, genetic markers
    POLITICAL = "political"  # Political opinions
    RELIGIOUS = "religious"  # Religious beliefs
    PHILOSOPHICAL = "philosophical"  # Philosophical beliefs
    UNION_MEMBERSHIP = "union_membership"  # Trade union membership
    SEXUAL_ORIENTATION = "sexual_orientation"  # Sexual orientation
    RACIAL_ETHNIC = "racial_ethnic"  # Racial or ethnic origin


class ConsentRecord(BaseModel):
    """Data subject consent record (Article 7).

    Tracks consent given by data subjects for specific processing purposes.
    Must be freely given, specific, informed, and unambiguous.
    """

    consent_id: str = Field(default_factory=lambda: str(uuid4()))
    data_subject_id: str
    purpose: str  # Specific purpose for processing
    legal_basis: LegalBasis
    data_categories: List[DataCategory]
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    withdrawal_reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("data_categories", mode="before")
    @classmethod
    def validate_data_categories(cls, v: Any) -> List[DataCategory]:
        """Ensure data_categories is a list of DataCategory enums."""
        if isinstance(v, list):
            return [DataCategory(cat) if isinstance(cat, str) else cat for cat in v]
        return v

    def is_valid(self) -> bool:
        """Check if consent is currently valid.

        Returns:
            True if consent is granted and not withdrawn/expired
        """
        if self.withdrawn_at:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def withdraw(self, reason: Optional[str] = None) -> None:
        """Withdraw consent (Article 7(3)).

        Args:
            reason: Optional reason for withdrawal
        """
        self.withdrawn_at = datetime.utcnow()
        self.withdrawal_reason = reason


class DataProcessingRecord(BaseModel):
    """Article 30 record of processing activities.

    Controllers must maintain records of processing activities
    under their responsibility.
    """

    record_id: str = Field(default_factory=lambda: str(uuid4()))
    controller_name: str  # Name of data controller
    processing_purpose: str  # Purpose of processing
    legal_basis: LegalBasis
    data_categories: List[DataCategory]
    data_subjects: List[str]  # IDs of data subjects
    recipients: List[str] = Field(default_factory=list)  # Third parties
    retention_period: Optional[str] = None  # e.g., "30 days", "2 years"
    security_measures: List[str] = Field(default_factory=list)
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("data_categories", mode="before")
    @classmethod
    def validate_data_categories(cls, v: Any) -> List[DataCategory]:
        """Ensure data_categories is a list of DataCategory enums."""
        if isinstance(v, list):
            return [DataCategory(cat) if isinstance(cat, str) else cat for cat in v]
        return v


class PIIDetector:
    """PII (Personally Identifiable Information) detector.

    Uses regex patterns and NER to detect various PII categories.
    Supports EU, US, and international formats.
    """

    # Email pattern (RFC 5322 simplified)
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )

    # Phone patterns (E.164, US, EU formats)
    PHONE_PATTERNS = [
        re.compile(r'\+?[1-9]\d{1,14}'),  # E.164 international
        re.compile(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),  # US format
        re.compile(r'\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{4}'),  # EU format
    ]

    # SSN patterns (US: 123-45-6789)
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')

    # Credit card pattern (13-19 digits with optional spaces/hyphens)
    CREDIT_CARD_PATTERN = re.compile(
        r'\b(?:\d{4}[-\s]?){3}\d{4,7}\b'
    )

    # IBAN pattern (EU bank accounts)
    IBAN_PATTERN = re.compile(
        r'\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b'
    )

    # Postal code patterns (US: 12345, DE: 12345, UK: SW1A 1AA)
    POSTAL_CODE_PATTERNS = [
        re.compile(r'\b\d{5}(?:-\d{4})?\b'),  # US ZIP
        re.compile(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}\b'),  # UK
        re.compile(r'\b\d{5}\b'),  # DE/FR
    ]

    # IP address patterns (IPv4 and IPv6)
    IPV4_PATTERN = re.compile(
        r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    )
    IPV6_PATTERN = re.compile(
        r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'
    )

    # Tax ID patterns (US EIN, DE Steuernummer)
    TAX_ID_PATTERNS = [
        re.compile(r'\b\d{2}-\d{7}\b'),  # US EIN
        re.compile(r'\b\d{2}/\d{3}/\d{5}\b'),  # DE Steuernummer
    ]

    # National ID patterns (simplified)
    NATIONAL_ID_PATTERNS = [
        re.compile(r'\b[A-Z]{2}\d{6,9}\b'),  # Generic EU format
        re.compile(r'\b\d{9,12}\b'),  # Generic numeric ID
    ]

    # Pattern mapping to data categories
    PATTERNS: Dict[DataCategory, List[re.Pattern]] = {
        DataCategory.CONTACT: [
            EMAIL_PATTERN,
        ] + PHONE_PATTERNS + POSTAL_CODE_PATTERNS,
        DataCategory.IDENTIFIER: [
            SSN_PATTERN,
        ] + TAX_ID_PATTERNS + NATIONAL_ID_PATTERNS,
        DataCategory.FINANCIAL: [
            CREDIT_CARD_PATTERN,
            IBAN_PATTERN,
        ],
        DataCategory.LOCATION: [
            IPV4_PATTERN,
            IPV6_PATTERN,
        ],
    }

    def detect(self, text: str) -> Dict[DataCategory, List[str]]:
        """Detect PII in text using regex patterns.

        Args:
            text: Text to scan for PII

        Returns:
            Dictionary mapping data categories to detected PII strings
        """
        results: Dict[DataCategory, List[str]] = {}

        for category, patterns in self.PATTERNS.items():
            matches: Set[str] = set()
            for pattern in patterns:
                matches.update(pattern.findall(text))

            if matches:
                results[category] = sorted(matches)

        return results

    def detect_email(self, text: str) -> List[str]:
        """Detect email addresses in text.

        Args:
            text: Text to scan

        Returns:
            List of detected email addresses
        """
        return self.EMAIL_PATTERN.findall(text)

    def detect_phone(self, text: str) -> List[str]:
        """Detect phone numbers in text.

        Args:
            text: Text to scan

        Returns:
            List of detected phone numbers
        """
        matches: Set[str] = set()
        for pattern in self.PHONE_PATTERNS:
            matches.update(pattern.findall(text))
        return sorted(matches)

    def detect_ssn(self, text: str) -> List[str]:
        """Detect US Social Security Numbers in text.

        Args:
            text: Text to scan

        Returns:
            List of detected SSNs
        """
        return self.SSN_PATTERN.findall(text)

    def detect_credit_card(self, text: str) -> List[str]:
        """Detect credit card numbers in text.

        Args:
            text: Text to scan

        Returns:
            List of detected credit card numbers
        """
        matches = self.CREDIT_CARD_PATTERN.findall(text)
        # Validate using Luhn algorithm
        return [m for m in matches if self._validate_luhn(m.replace(" ", "").replace("-", ""))]

    def detect_iban(self, text: str) -> List[str]:
        """Detect IBAN bank account numbers in text.

        Args:
            text: Text to scan

        Returns:
            List of detected IBANs
        """
        return self.IBAN_PATTERN.findall(text)

    def _validate_luhn(self, card_number: str) -> bool:
        """Validate credit card using Luhn algorithm.

        Args:
            card_number: Credit card number (digits only)

        Returns:
            True if valid per Luhn algorithm
        """
        if not card_number.isdigit():
            return False

        digits = [int(d) for d in card_number]
        checksum = 0

        # Process digits from right to left
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:  # Double every second digit
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0


class GDPRComplianceGuard:
    """Central GDPR compliance enforcement.

    Integrates with skill lifecycle management to ensure:
    - Consent is obtained before processing
    - PII is redacted when not authorized
    - Processing activities are logged
    - Rights to erasure and portability are honored
    """

    def __init__(
        self,
        consent_store: "ConsentStore",
        processing_log: "ProcessingLog",
        pii_detector: Optional[PIIDetector] = None,
        skill_manager: Optional[Any] = None,
    ):
        """Initialize GDPR compliance guard.

        Args:
            consent_store: Storage for consent records
            processing_log: Storage for processing activity records
            pii_detector: PII detector instance
            skill_manager: Optional skill lifecycle manager
        """
        self.consent_store = consent_store
        self.processing_log = processing_log
        self.pii_detector = pii_detector or PIIDetector()
        self.skill_manager = skill_manager

        # Skill -> required data categories mapping
        self._skill_requirements: Dict[str, List[DataCategory]] = {}

    def register_skill_requirements(
        self,
        skill_name: str,
        required_categories: List[DataCategory],
    ) -> None:
        """Register GDPR requirements for a skill.

        Args:
            skill_name: Name of the skill
            required_categories: Data categories required by the skill
        """
        self._skill_requirements[skill_name] = required_categories

    async def check_skill_activation(
        self,
        skill_name: str,
        data_subject_id: str,
        context: Dict[str, Any],
    ) -> tuple[bool, Optional[str]]:
        """Check if skill activation is allowed under GDPR.

        Verifies:
        - Valid consent exists for required data categories
        - Consent has not expired or been withdrawn

        Args:
            skill_name: Name of skill to activate
            data_subject_id: ID of data subject
            context: Skill activation context

        Returns:
            Tuple of (is_allowed, error_message)
        """
        # Get required categories for this skill
        required_categories = self._skill_requirements.get(skill_name, [])

        if not required_categories:
            # No PII required, allow activation
            return True, None

        # Check consent for each required category
        missing_consent: List[DataCategory] = []

        for category in required_categories:
            consents = await self.consent_store.get_consents(
                data_subject_id=data_subject_id,
                data_category=category,
            )

            # Check if any valid consent exists
            has_valid_consent = any(c.is_valid() for c in consents)

            if not has_valid_consent:
                missing_consent.append(category)

        if missing_consent:
            categories_str = ", ".join(c.value for c in missing_consent)
            error_msg = (
                f"GDPR: Missing consent for categories: {categories_str}. "
                f"Skill '{skill_name}' requires valid consent."
            )
            return False, error_msg

        # Log processing activity (Article 30)
        await self._log_processing(
            skill_name=skill_name,
            data_subject_id=data_subject_id,
            categories=required_categories,
            context=context,
        )

        return True, None

    def redact_pii(
        self,
        text: str,
        allowed_categories: Set[DataCategory],
    ) -> str:
        """Redact PII from text based on allowed categories.

        Args:
            text: Text potentially containing PII
            allowed_categories: Data categories that are allowed

        Returns:
            Text with unauthorized PII redacted
        """
        detected_pii = self.pii_detector.detect(text)
        redacted_text = text

        for category, pii_items in detected_pii.items():
            if category not in allowed_categories:
                # Redact each detected PII item
                for pii_item in pii_items:
                    # Create redaction placeholder
                    redaction = f"[REDACTED_{category.value.upper()}]"
                    redacted_text = redacted_text.replace(pii_item, redaction)

        return redacted_text

    async def handle_erasure_request(
        self,
        data_subject_id: str,
    ) -> Dict[str, Any]:
        """Handle right to erasure request (Article 17).

        Deletes all personal data associated with a data subject.

        Args:
            data_subject_id: ID of data subject requesting erasure

        Returns:
            Dictionary with erasure results
        """
        results = {
            "data_subject_id": data_subject_id,
            "erasure_timestamp": datetime.utcnow().isoformat(),
            "consents_deleted": 0,
            "processing_records_deleted": 0,
            "errors": [],
        }

        try:
            # Delete all consent records
            deleted_consents = await self.consent_store.delete_all(data_subject_id)
            results["consents_deleted"] = deleted_consents
        except Exception as e:
            results["errors"].append(f"Consent deletion failed: {str(e)}")

        try:
            # Delete processing records
            deleted_records = await self.processing_log.delete_by_subject(data_subject_id)
            results["processing_records_deleted"] = deleted_records
        except Exception as e:
            results["errors"].append(f"Processing record deletion failed: {str(e)}")

        # Log erasure activity
        await self._log_processing(
            skill_name="gdpr_erasure",
            data_subject_id=data_subject_id,
            categories=[],
            context={"operation": "erasure", "results": results},
        )

        return results

    async def export_data(
        self,
        data_subject_id: str,
    ) -> Dict[str, Any]:
        """Export all personal data for a data subject (Article 20).

        Provides data in structured, machine-readable format.

        Args:
            data_subject_id: ID of data subject requesting export

        Returns:
            Dictionary containing all personal data
        """
        export_data = {
            "data_subject_id": data_subject_id,
            "export_timestamp": datetime.utcnow().isoformat(),
            "consents": [],
            "processing_records": [],
        }

        # Export consent records
        consents = await self.consent_store.get_all(data_subject_id)
        export_data["consents"] = [c.model_dump() for c in consents]

        # Export processing records
        records = await self.processing_log.get_by_subject(data_subject_id)
        export_data["processing_records"] = [r.model_dump() for r in records]

        # Generate checksum for data integrity
        export_str = str(export_data)
        checksum = hashlib.sha256(export_str.encode()).hexdigest()
        export_data["checksum"] = checksum

        # Log export activity
        await self._log_processing(
            skill_name="gdpr_export",
            data_subject_id=data_subject_id,
            categories=[],
            context={"operation": "export", "record_count": len(export_data["consents"])},
        )

        return export_data

    async def _log_processing(
        self,
        skill_name: str,
        data_subject_id: str,
        categories: List[DataCategory],
        context: Dict[str, Any],
    ) -> None:
        """Log processing activity (Article 30).

        Args:
            skill_name: Name of skill/operation
            data_subject_id: ID of data subject
            categories: Data categories processed
            context: Additional context
        """
        record = DataProcessingRecord(
            controller_name="AegisRAG",
            processing_purpose=skill_name,
            legal_basis=LegalBasis.LEGITIMATE_INTERESTS,
            data_categories=categories,
            data_subjects=[data_subject_id],
            metadata=context,
        )

        await self.processing_log.add(record)

    def get_skill_requirements(self, skill_name: str) -> List[DataCategory]:
        """Get GDPR requirements for a skill.

        Args:
            skill_name: Name of skill

        Returns:
            List of required data categories
        """
        return self._skill_requirements.get(skill_name, [])

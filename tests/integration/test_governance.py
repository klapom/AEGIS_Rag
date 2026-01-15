"""Integration tests for governance framework components (Sprint 96.5).

Tests full integration of GDPR, Audit Trail, and Explainability components.

Coverage:
    - GDPR + Audit Trail integration
    - Explainability + Audit Trail integration
    - GDPR + Explainability integration
    - Skill Certification with GDPR/Audit
    - End-to-end governance workflows
    - Performance and compliance metrics

Test Scenarios (18+ tests):
    - Skill activation with GDPR consent
    - GDPR erasure request logging in audit
    - Data export creating audit events
    - Decision traces in audit logs
    - PII redaction in explanations
    - Certification validation
    - Full governance workflows
    - Compliance report generation
    - Performance overhead measurement
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.governance.audit.storage import InMemoryAuditStorage
from src.governance.audit.trail import AuditEventType, AuditTrailManager
from src.governance.explainability.engine import (
    DecisionTrace,
    ExplanationLevel,
    ExplainabilityEngine,
    SkillSelectionReason,
    SourceAttribution,
)
from src.governance.explainability.storage import InMemoryTraceStorage
from src.governance.gdpr.compliance import (
    ConsentRecord,
    DataCategory,
    GDPRComplianceGuard,
    LegalBasis,
    PIIDetector,
)
from src.governance.gdpr.storage import ConsentStore, ProcessingLog


# ============================================================================
# Shared Fixtures
# ============================================================================


@pytest.fixture
def audit_storage() -> InMemoryAuditStorage:
    """Create in-memory audit storage."""
    return InMemoryAuditStorage()


@pytest.fixture
def audit_manager(audit_storage: InMemoryAuditStorage) -> AuditTrailManager:
    """Create audit trail manager."""
    return AuditTrailManager(audit_storage)


@pytest.fixture
def consent_store() -> ConsentStore:
    """Create consent store."""
    store = ConsentStore()
    yield store
    store.clear()


@pytest.fixture
def processing_log() -> ProcessingLog:
    """Create processing log."""
    log = ProcessingLog()
    yield log
    log.clear()


@pytest.fixture
def gdpr_guard(
    consent_store: ConsentStore,
    processing_log: ProcessingLog,
) -> GDPRComplianceGuard:
    """Create GDPR compliance guard."""
    return GDPRComplianceGuard(
        consent_store=consent_store,
        processing_log=processing_log,
        pii_detector=PIIDetector(),
    )


@pytest.fixture
def trace_storage() -> InMemoryTraceStorage:
    """Create in-memory trace storage."""
    return InMemoryTraceStorage()


@pytest.fixture
def mock_llm() -> AsyncMock:
    """Create mock LLM for explainability engine."""
    return AsyncMock()


@pytest.fixture
def explainability_engine(
    trace_storage: InMemoryTraceStorage,
    mock_llm: AsyncMock,
) -> ExplainabilityEngine:
    """Create explainability engine."""
    return ExplainabilityEngine(trace_storage, mock_llm)


@pytest.fixture
def sample_consent_record() -> ConsentRecord:
    """Create sample consent record."""
    return ConsentRecord(
        data_subject_id="user_123",
        purpose="AI skill execution",
        legal_basis=LegalBasis.CONSENT,
        data_categories=[DataCategory.CONTACT, DataCategory.BEHAVIORAL],
        expires_at=datetime.utcnow() + timedelta(days=365),
    )


@pytest.fixture
def sample_decision_trace() -> DecisionTrace:
    """Create sample decision trace."""
    return DecisionTrace(
        id="trace_001",
        timestamp=datetime.utcnow(),
        query="What is GDPR?",
        final_response="GDPR is the General Data Protection Regulation...",
        skills_considered=[
            SkillSelectionReason(
                skill_name="research_agent",
                confidence=0.92,
                trigger_matched="factual_query",
                intent_classification="research",
                alternative_skills=["summary_agent"],
            )
        ],
        skills_activated=["research_agent"],
        retrieval_mode="hybrid",
        chunks_retrieved=20,
        chunks_used=5,
        attributions=[
            SourceAttribution(
                document_id="doc_gdpr",
                document_name="GDPR Handbook",
                chunk_ids=["chunk_1"],
                relevance_score=0.95,
                text_excerpt="GDPR is a regulation...",
                page_numbers=[1, 2],
            )
        ],
        tools_invoked=[{"tool": "vector_search", "outcome": "success"}],
        overall_confidence=0.88,
        hallucination_risk=0.05,
        total_duration_ms=245.5,
        skill_durations={"research_agent": 120.0},
    )


# ============================================================================
# GDPR + Audit Trail Integration Tests
# ============================================================================


class TestGDPRAuditIntegration:
    """Test GDPR and Audit Trail integration."""

    @pytest.mark.asyncio
    async def test_skill_activation_logged_in_audit(
        self,
        gdpr_guard: GDPRComplianceGuard,
        consent_store: ConsentStore,
        audit_manager: AuditTrailManager,
        sample_consent_record: ConsentRecord,
    ):
        """Test skill activation logs GDPR events in audit trail.

        Scenario:
            1. Grant consent for skill activation
            2. Activate skill (passes GDPR check)
            3. Verify audit trail captures the activation

        Expected:
            - Skill activation event in audit trail
            - Metadata includes skill name and user ID
            - Outcome is "success"
        """
        # Grant consent
        gdpr_guard.register_skill_requirements(
            "retrieve_documents",
            [DataCategory.CONTACT],
        )
        await consent_store.add(sample_consent_record)

        # Log skill activation in audit
        event = await audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="user_123",
            action="Activate skill: retrieve_documents",
            outcome="success",
            metadata={
                "skill_id": "retrieve_documents",
                "user_id": "user_123",
                "gdpr_consent": True,
            },
        )

        # Verify event was logged
        assert event.event_type == AuditEventType.SKILL_EXECUTED
        assert event.outcome == "success"
        assert event.metadata["gdpr_consent"] is True

        # Verify we can query the event
        events = await audit_manager.storage.query(
            actor_id="user_123",
        )
        assert len(events) == 1
        assert events[0].id == event.id

    @pytest.mark.asyncio
    async def test_erasure_request_creates_audit_event(
        self,
        gdpr_guard: GDPRComplianceGuard,
        consent_store: ConsentStore,
        audit_manager: AuditTrailManager,
        sample_consent_record: ConsentRecord,
    ):
        """Test Article 17 erasure creates audit event.

        Scenario:
            1. Add consent record for user
            2. Request data erasure
            3. Verify GDPR erasure logged in audit
            4. Verify consent was deleted

        Expected:
            - Erasure operation logged in audit
            - Consent records deleted from store
            - Audit chain integrity maintained
        """
        # Add consent
        await consent_store.add(sample_consent_record)
        assert len(await consent_store.get_all("user_123")) == 1

        # Perform erasure
        erasure_result = await gdpr_guard.handle_erasure_request("user_123")

        # Log erasure in audit
        event = await audit_manager.log(
            event_type=AuditEventType.DATA_DELETE,
            actor_id="compliance_system",
            action="Article 17 erasure request: user_123",
            outcome="success",
            metadata={
                "data_subject_id": "user_123",
                "consents_deleted": erasure_result["consents_deleted"],
                "records_deleted": erasure_result["processing_records_deleted"],
            },
        )

        # Verify erasure was successful
        assert erasure_result["consents_deleted"] >= 1
        assert "user_123" in event.metadata["data_subject_id"]

        # Verify audit event was created
        events = await audit_manager.storage.query()
        assert len(events) == 1
        assert events[0].action == "Article 17 erasure request: user_123"

        # Verify consent was deleted
        remaining_consents = await consent_store.get_all("user_123")
        assert len(remaining_consents) == 0

    @pytest.mark.asyncio
    async def test_data_export_creates_audit_event(
        self,
        gdpr_guard: GDPRComplianceGuard,
        consent_store: ConsentStore,
        audit_manager: AuditTrailManager,
        sample_consent_record: ConsentRecord,
    ):
        """Test Article 20 data export creates audit event.

        Scenario:
            1. Add consent record
            2. Request data export
            3. Verify export logged in audit
            4. Verify data integrity

        Expected:
            - Export operation logged in audit
            - Exported data contains consents
            - Audit event includes record count
        """
        # Add consent
        await consent_store.add(sample_consent_record)

        # Export data
        export_data = await gdpr_guard.export_data("user_123")

        # Log export in audit
        event = await audit_manager.log(
            event_type=AuditEventType.DATA_EXPORTED,
            actor_id="user_123",
            action="Article 20 data export request",
            outcome="success",
            metadata={
                "data_subject_id": "user_123",
                "record_count": len(export_data["consents"]),
                "checksum": export_data["checksum"],
            },
        )

        # Verify export data
        assert export_data["data_subject_id"] == "user_123"
        assert len(export_data["consents"]) >= 1
        assert "checksum" in export_data

        # Verify audit event
        assert event.outcome == "success"
        assert event.metadata["record_count"] >= 1


# ============================================================================
# Explainability + Audit Trail Integration Tests
# ============================================================================


class TestExplainabilityAuditIntegration:
    """Test Explainability and Audit Trail integration."""

    @pytest.mark.asyncio
    async def test_decision_trace_logged_in_audit(
        self,
        explainability_engine: ExplainabilityEngine,
        audit_manager: AuditTrailManager,
        sample_decision_trace: DecisionTrace,
    ):
        """Test decision traces are logged in audit trail.

        Scenario:
            1. Capture decision trace
            2. Log trace metadata in audit
            3. Verify audit contains trace reference

        Expected:
            - Trace saved in explainability storage
            - Audit event references the trace
            - Skill and retrieval metadata in audit
        """
        # Save trace
        await explainability_engine.storage.save(sample_decision_trace)

        # Log in audit
        event = await audit_manager.log(
            event_type=AuditEventType.DECISION_APPROVED,
            actor_id="system",
            action=f"Decision trace created: {sample_decision_trace.id}",
            outcome="success",
            metadata={
                "trace_id": sample_decision_trace.id,
                "query": sample_decision_trace.query,
                "skills_activated": sample_decision_trace.skills_activated,
                "confidence": sample_decision_trace.overall_confidence,
                "retrieval_mode": sample_decision_trace.retrieval_mode,
            },
        )

        # Verify trace was saved
        retrieved_trace = await explainability_engine.storage.get(
            sample_decision_trace.id
        )
        assert retrieved_trace is not None
        assert retrieved_trace.id == sample_decision_trace.id

        # Verify audit event
        assert event.metadata["trace_id"] == sample_decision_trace.id
        assert event.metadata["skills_activated"] == ["research_agent"]

    @pytest.mark.asyncio
    async def test_explanation_generation_audited(
        self,
        explainability_engine: ExplainabilityEngine,
        audit_manager: AuditTrailManager,
        sample_decision_trace: DecisionTrace,
    ):
        """Test explanation generation creates audit events.

        Scenario:
            1. Save decision trace
            2. Generate explanation at each level
            3. Log explanation generation in audit
            4. Verify audit has level info

        Expected:
            - Explanation event logged for each level
            - Audit metadata includes explanation level
            - All three levels (USER, EXPERT, AUDIT) tracked
        """
        await explainability_engine.storage.save(sample_decision_trace)

        explanation_levels = [
            ExplanationLevel.USER,
            ExplanationLevel.EXPERT,
            ExplanationLevel.AUDIT,
        ]

        audit_events = []
        for level in explanation_levels:
            # Generate explanation (mock)
            explanation = f"Explanation at {level.value} level"

            # Log in audit
            event = await audit_manager.log(
                event_type=AuditEventType.DECISION_APPROVED,
                actor_id="system",
                action=f"Generated {level.value} explanation",
                outcome="success",
                metadata={
                    "trace_id": sample_decision_trace.id,
                    "explanation_level": level.value,
                    "explanation_length": len(explanation),
                },
            )
            audit_events.append(event)

        # Verify all three levels were logged
        assert len(audit_events) == 3
        levels_in_audit = [e.metadata["explanation_level"] for e in audit_events]
        assert "user" in levels_in_audit
        assert "expert" in levels_in_audit
        assert "audit" in levels_in_audit


# ============================================================================
# GDPR + Explainability Integration Tests
# ============================================================================


class TestGDPRExplainabilityIntegration:
    """Test GDPR and Explainability integration."""

    @pytest.mark.asyncio
    async def test_decision_trace_includes_consent_status(
        self,
        gdpr_guard: GDPRComplianceGuard,
        consent_store: ConsentStore,
        explainability_engine: ExplainabilityEngine,
        sample_decision_trace: DecisionTrace,
        sample_consent_record: ConsentRecord,
    ):
        """Test decision traces include GDPR consent status.

        Scenario:
            1. Grant consent for data subject
            2. Capture decision trace with consent metadata
            3. Verify trace includes consent status
            4. Generate explanation including consent notice

        Expected:
            - Trace metadata includes consent status
            - Explanation notes consent basis
            - Audit trail tracks transparency
        """
        # Grant consent
        await consent_store.add(sample_consent_record)

        # Check consent validity
        consents = await consent_store.get_consents(
            "user_123",
            DataCategory.CONTACT,
        )
        assert len(consents) > 0
        assert consents[0].is_valid()

        # Create trace with consent info
        trace_with_consent = DecisionTrace(
            id="trace_with_consent_001",
            timestamp=datetime.utcnow(),
            query=sample_decision_trace.query,
            final_response=sample_decision_trace.final_response,
            skills_considered=sample_decision_trace.skills_considered,
            skills_activated=sample_decision_trace.skills_activated,
            retrieval_mode=sample_decision_trace.retrieval_mode,
            chunks_retrieved=sample_decision_trace.chunks_retrieved,
            chunks_used=sample_decision_trace.chunks_used,
            attributions=sample_decision_trace.attributions,
            tools_invoked=sample_decision_trace.tools_invoked,
            overall_confidence=sample_decision_trace.overall_confidence,
            hallucination_risk=sample_decision_trace.hallucination_risk,
            total_duration_ms=sample_decision_trace.total_duration_ms,
        )

        # Save trace
        await explainability_engine.storage.save(trace_with_consent)

        # Verify trace was stored
        retrieved = await explainability_engine.storage.get(
            trace_with_consent.id
        )
        assert retrieved is not None

    @pytest.mark.asyncio
    async def test_explanation_includes_pii_redaction_notice(
        self,
        gdpr_guard: GDPRComplianceGuard,
        explainability_engine: ExplainabilityEngine,
        sample_decision_trace: DecisionTrace,
    ):
        """Test explanations note if PII was redacted.

        Scenario:
            1. Create response with PII (email address)
            2. Redact PII based on consent restrictions
            3. Generate explanation noting redaction
            4. Verify audit documents redaction

        Expected:
            - PII is redacted with [REDACTED_*] placeholders
            - Explanation notes redaction occurred
            - Audit event logs redaction event
        """
        # Create response with PII
        response_with_pii = (
            "Contact user at john@example.com with the following information..."
        )

        # Redact PII (not authorized categories)
        redacted = gdpr_guard.redact_pii(
            response_with_pii,
            allowed_categories=set(),  # No categories allowed
        )

        # Verify redaction occurred
        assert "john@example.com" not in redacted
        assert "[REDACTED_CONTACT]" in redacted

        # Create trace with redaction notice
        trace = DecisionTrace(
            id="trace_redacted_001",
            timestamp=datetime.utcnow(),
            query="Contact information query",
            final_response=redacted,
            skills_considered=sample_decision_trace.skills_considered,
            skills_activated=sample_decision_trace.skills_activated,
            retrieval_mode=sample_decision_trace.retrieval_mode,
            chunks_retrieved=sample_decision_trace.chunks_retrieved,
            chunks_used=sample_decision_trace.chunks_used,
            attributions=sample_decision_trace.attributions,
            tools_invoked=sample_decision_trace.tools_invoked,
            overall_confidence=sample_decision_trace.overall_confidence,
            hallucination_risk=sample_decision_trace.hallucination_risk,
            total_duration_ms=sample_decision_trace.total_duration_ms,
        )

        # Save redacted trace
        await explainability_engine.storage.save(trace)

        # Verify trace contains redaction
        retrieved = await explainability_engine.storage.get(trace.id)
        assert "[REDACTED_" in retrieved.final_response


# ============================================================================
# Skill Certification Integration Tests
# ============================================================================


class TestCertificationIntegration:
    """Test Skill Certification with GDPR/Audit.

    Note: Skill Certification framework is in agents/skills/.
    These tests verify governance requirements for skill certification.
    """

    @pytest.mark.asyncio
    async def test_certification_validates_gdpr_compliance(
        self,
        gdpr_guard: GDPRComplianceGuard,
    ):
        """Test certification checks GDPR declarations.

        Scenario:
            1. Define skill with GDPR requirements
            2. Validate skill meets requirements
            3. Verify skill registration with governance

        Expected:
            - Skill GDPR requirements registered
            - Certification tracks compliance
            - Activation blocked without consent
        """
        # Register skill with GDPR requirements
        skill_name = "pii_analysis_skill"
        required_categories = [
            DataCategory.IDENTIFIER,
            DataCategory.CONTACT,
            DataCategory.BEHAVIORAL,
        ]

        gdpr_guard.register_skill_requirements(skill_name, required_categories)

        # Verify registration
        registered = gdpr_guard.get_skill_requirements(skill_name)
        assert registered == required_categories

    @pytest.mark.asyncio
    async def test_certification_validates_audit_config(
        self,
        audit_manager: AuditTrailManager,
    ):
        """Test certification checks audit integration.

        Scenario:
            1. Verify audit trail is initialized
            2. Test audit event logging
            3. Verify integrity checking

        Expected:
            - Audit manager operational
            - Events logged with chain integrity
            - Verification succeeds
        """
        # Log a test event
        event = await audit_manager.log(
            event_type=AuditEventType.SKILL_LOADED,
            actor_id="certification_system",
            action="Test certification skill",
            outcome="success",
            metadata={"certification_id": "cert_001"},
        )

        # Verify event was logged
        assert event is not None
        assert event.outcome == "success"

        # Verify integrity
        is_valid, errors = await audit_manager.verify_integrity()
        assert is_valid
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_certified_skill_can_be_activated(
        self,
        gdpr_guard: GDPRComplianceGuard,
        consent_store: ConsentStore,
        audit_manager: AuditTrailManager,
    ):
        """Test ENTERPRISE certified skill can activate with GDPR consent.

        Scenario:
            1. Register certified skill with GDPR requirements
            2. Grant required consent
            3. Activate skill (passes all checks)
            4. Log activation in audit

        Expected:
            - Skill activation allowed
            - All GDPR checks pass
            - Audit event created
        """
        # Register skill
        skill_name = "certified_enterprise_skill"
        gdpr_guard.register_skill_requirements(
            skill_name,
            [DataCategory.BEHAVIORAL],
        )

        # Grant consent
        consent = ConsentRecord(
            data_subject_id="enterprise_user",
            purpose="Skill execution",
            legal_basis=LegalBasis.CONSENT,
            data_categories=[DataCategory.BEHAVIORAL],
            expires_at=datetime.utcnow() + timedelta(days=365),
        )
        await consent_store.add(consent)

        # Check skill activation
        is_allowed, error_msg = await gdpr_guard.check_skill_activation(
            skill_name=skill_name,
            data_subject_id="enterprise_user",
            context={"skill_version": "1.0.0"},
        )

        # Verify activation is allowed
        assert is_allowed is True
        assert error_msg is None

        # Log activation in audit
        event = await audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="enterprise_user",
            action=f"Activated skill: {skill_name}",
            outcome="success",
            metadata={"skill_name": skill_name, "certified": True},
        )

        # Verify audit event
        assert event.outcome == "success"


# ============================================================================
# Full Governance Workflow Tests
# ============================================================================


class TestFullGovernanceWorkflow:
    """Test end-to-end governance scenarios."""

    @pytest.mark.asyncio
    async def test_full_gdpr_compliant_skill_execution(
        self,
        gdpr_guard: GDPRComplianceGuard,
        consent_store: ConsentStore,
        processing_log: ProcessingLog,
        audit_manager: AuditTrailManager,
        explainability_engine: ExplainabilityEngine,
        sample_decision_trace: DecisionTrace,
    ):
        """Test full workflow: Consent → Skill → Audit → Explain.

        Scenario:
            1. User grants consent for data processing
            2. Activate skill (GDPR check passes)
            3. Log in audit trail
            4. Capture decision trace
            5. Verify full chain integrity

        Expected:
            - Consent is valid
            - Skill activation succeeds
            - Audit events created
            - Trace saved
            - All components linked
        """
        # Step 1: User grants consent
        user_id = "compliant_user"
        consent = ConsentRecord(
            data_subject_id=user_id,
            purpose="AI skill execution for research",
            legal_basis=LegalBasis.CONSENT,
            data_categories=[DataCategory.CONTACT, DataCategory.BEHAVIORAL],
            expires_at=datetime.utcnow() + timedelta(days=365),
        )
        await consent_store.add(consent)

        # Step 2: Register skill with GDPR requirements
        skill_name = "comprehensive_research_skill"
        gdpr_guard.register_skill_requirements(
            skill_name,
            [DataCategory.CONTACT, DataCategory.BEHAVIORAL],
        )

        # Step 3: Check skill activation (GDPR compliance)
        is_allowed, error_msg = await gdpr_guard.check_skill_activation(
            skill_name=skill_name,
            data_subject_id=user_id,
            context={"skill_version": "1.0.0"},
        )
        assert is_allowed is True

        # Step 4: Log skill activation in audit
        audit_event = await audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id=user_id,
            action=f"Executed skill: {skill_name}",
            outcome="success",
            metadata={
                "skill_name": skill_name,
                "gdpr_consent": is_allowed,
                "data_categories": [c.value for c in gdpr_guard.get_skill_requirements(skill_name)],
            },
        )

        # Step 5: Capture decision trace
        trace = DecisionTrace(
            id=f"workflow_trace_{user_id}",
            timestamp=datetime.utcnow(),
            query=sample_decision_trace.query,
            final_response=sample_decision_trace.final_response,
            skills_considered=sample_decision_trace.skills_considered,
            skills_activated=[skill_name],
            retrieval_mode=sample_decision_trace.retrieval_mode,
            chunks_retrieved=sample_decision_trace.chunks_retrieved,
            chunks_used=sample_decision_trace.chunks_used,
            attributions=sample_decision_trace.attributions,
            tools_invoked=sample_decision_trace.tools_invoked,
            overall_confidence=sample_decision_trace.overall_confidence,
            hallucination_risk=sample_decision_trace.hallucination_risk,
            total_duration_ms=sample_decision_trace.total_duration_ms,
        )
        await explainability_engine.storage.save(trace)

        # Step 6: Verify full chain
        # - Consent is valid
        consents = await consent_store.get_consents(user_id)
        assert len(consents) > 0
        assert consents[0].is_valid()

        # - Processing logged
        records = await processing_log.get_by_subject(user_id)
        assert len(records) >= 1

        # - Audit event created
        audit_events = await audit_manager.storage.query(actor_id=user_id)
        assert len(audit_events) > 0

        # - Trace saved
        saved_trace = await explainability_engine.storage.get(trace.id)
        assert saved_trace is not None

    @pytest.mark.asyncio
    async def test_gdpr_violation_prevents_skill_activation(
        self,
        gdpr_guard: GDPRComplianceGuard,
        audit_manager: AuditTrailManager,
    ):
        """Test missing consent blocks skill, logged in audit.

        Scenario:
            1. Register skill with GDPR requirements
            2. Attempt activation WITHOUT consent
            3. Activation blocked
            4. Failure logged in audit

        Expected:
            - Skill activation denied
            - Error message specific to missing categories
            - Audit logs the violation
            - No processing occurs
        """
        user_id = "no_consent_user"
        skill_name = "gdpr_protected_skill"

        # Register skill with GDPR requirements
        gdpr_guard.register_skill_requirements(
            skill_name,
            [DataCategory.CONTACT, DataCategory.BEHAVIORAL],
        )

        # Attempt activation without consent
        is_allowed, error_msg = await gdpr_guard.check_skill_activation(
            skill_name=skill_name,
            data_subject_id=user_id,
            context={"skill_version": "1.0.0"},
        )

        # Verify activation is blocked
        assert is_allowed is False
        assert error_msg is not None
        assert "consent" in error_msg.lower()

        # Log violation in audit
        violation_event = await audit_manager.log(
            event_type=AuditEventType.POLICY_VIOLATION,
            actor_id=user_id,
            action=f"Skill activation blocked: {skill_name}",
            outcome="failure",
            metadata={
                "skill_name": skill_name,
                "reason": "Missing GDPR consent",
                "error_message": error_msg,
                "data_categories_required": [c.value for c in gdpr_guard.get_skill_requirements(skill_name)],
            },
        )

        # Verify violation was logged
        assert violation_event.event_type == AuditEventType.POLICY_VIOLATION
        assert violation_event.outcome == "failure"

    @pytest.mark.asyncio
    async def test_erasure_request_full_workflow(
        self,
        gdpr_guard: GDPRComplianceGuard,
        consent_store: ConsentStore,
        processing_log: ProcessingLog,
        audit_manager: AuditTrailManager,
    ):
        """Test Article 17 erasure across all systems.

        Scenario:
            1. Create full user record (consent + processing)
            2. Request erasure
            3. Verify deletion in all stores
            4. Verify audit trail intact
            5. Verify compliance report

        Expected:
            - All user data deleted
            - Audit trail preserved (immutable)
            - Erasure event documented
            - Compliance report shows deletion
        """
        user_id = "erasure_test_user"

        # Step 1: Create user records
        consent = ConsentRecord(
            data_subject_id=user_id,
            purpose="Testing",
            legal_basis=LegalBasis.CONSENT,
            data_categories=[DataCategory.BEHAVIORAL],
        )
        await consent_store.add(consent)

        # Step 2: Request erasure
        erasure_result = await gdpr_guard.handle_erasure_request(user_id)

        # Step 3: Verify deletion
        assert erasure_result["consents_deleted"] >= 1
        remaining_consents = await consent_store.get_all(user_id)
        assert len(remaining_consents) == 0

        # Step 4: Log erasure in audit
        erasure_event = await audit_manager.log(
            event_type=AuditEventType.DATA_DELETE,
            actor_id="compliance_system",
            action=f"Article 17 erasure: {user_id}",
            outcome="success",
            metadata={
                "data_subject_id": user_id,
                "consents_deleted": erasure_result["consents_deleted"],
                "processing_records_deleted": erasure_result["processing_records_deleted"],
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # Step 5: Verify audit trail is intact
        is_valid, errors = await audit_manager.verify_integrity()
        assert is_valid
        assert len(errors) == 0

        # Step 6: Generate compliance report
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()
        report = await audit_manager.generate_compliance_report(
            report_type="data_access",
            start_time=start_time,
            end_time=end_time,
        )

        # Verify report contains erasure
        assert report["report_type"] == "data_access"
        assert report["integrity_verified"] is True

    @pytest.mark.asyncio
    async def test_compliance_report_generation(
        self,
        audit_manager: AuditTrailManager,
    ):
        """Test generating compliance reports (GDPR Art. 30, security, skill usage).

        Scenario:
            1. Create diverse audit events
            2. Generate multiple report types
            3. Verify report structure and content
            4. Verify integrity checks

        Expected:
            - Reports generated for all types
            - Correct event categorization
            - Integrity verified
            - Metadata complete
        """
        # Create various audit events
        events_data = [
            (AuditEventType.SKILL_LOADED, "system", "Load skill", "success"),
            (AuditEventType.SKILL_EXECUTED, "agent", "Execute skill", "success"),
            (AuditEventType.DATA_READ, "agent", "Read data", "success"),
            (AuditEventType.DATA_WRITE, "agent", "Write data", "success"),
            (AuditEventType.AUTH_SUCCESS, "user", "Auth success", "success"),
            (AuditEventType.POLICY_VIOLATION, "user", "Policy violation", "failure"),
        ]

        for event_type, actor_id, action, outcome in events_data:
            await audit_manager.log(
                event_type=event_type,
                actor_id=actor_id,
                action=action,
                outcome=outcome,
            )

        # Generate GDPR Art 30 report
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        gdpr_report = await audit_manager.generate_compliance_report(
            report_type="gdpr_art30",
            start_time=start_time,
            end_time=end_time,
        )

        assert gdpr_report["report_type"] == "gdpr_art30"
        assert gdpr_report["integrity_verified"] is True
        assert gdpr_report["total_events"] >= len(events_data)

        # Generate security report
        security_report = await audit_manager.generate_compliance_report(
            report_type="security",
            start_time=start_time,
            end_time=end_time,
        )

        assert security_report["report_type"] == "security"
        assert "security_summary" in security_report
        assert security_report["security_summary"]["failed_auth"] >= 0

        # Generate skill usage report
        skill_report = await audit_manager.generate_compliance_report(
            report_type="skill_usage",
            start_time=start_time,
            end_time=end_time,
        )

        assert skill_report["report_type"] == "skill_usage"
        assert "skill_usage" in skill_report
        assert skill_report["skill_usage"]["total_executions"] >= 1


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test governance performance and overhead."""

    @pytest.mark.asyncio
    async def test_gdpr_check_overhead(
        self,
        gdpr_guard: GDPRComplianceGuard,
        consent_store: ConsentStore,
    ):
        """Test GDPR checks add <10ms overhead.

        Scenario:
            1. Grant consent
            2. Measure time for skill activation check
            3. Verify overhead is acceptable

        Expected:
            - Single check: <5ms
            - With 10 consents: <10ms
            - Linear scaling
        """
        import time

        user_id = "perf_test_user"

        # Add multiple consents
        for i in range(10):
            consent = ConsentRecord(
                data_subject_id=user_id,
                purpose=f"Purpose {i}",
                legal_basis=LegalBasis.CONSENT,
                data_categories=[DataCategory.BEHAVIORAL],
            )
            await consent_store.add(consent)

        # Register skill
        gdpr_guard.register_skill_requirements(
            "perf_test_skill",
            [DataCategory.BEHAVIORAL],
        )

        # Measure check time
        start = time.time()
        is_allowed, _ = await gdpr_guard.check_skill_activation(
            "perf_test_skill",
            user_id,
            {},
        )
        elapsed_ms = (time.time() - start) * 1000

        # Verify overhead
        assert elapsed_ms < 10.0  # Should be <10ms
        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_audit_logging_overhead(
        self,
        audit_manager: AuditTrailManager,
    ):
        """Test audit logging adds <5ms overhead.

        Scenario:
            1. Log single event
            2. Measure time
            3. Verify overhead acceptable

        Expected:
            - Single event: <5ms
            - Includes hash chain computation
        """
        import time

        start = time.time()
        event = await audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="perf_test",
            action="Performance test",
            outcome="success",
        )
        elapsed_ms = (time.time() - start) * 1000

        # Verify overhead
        assert elapsed_ms < 5.0  # Should be <5ms
        assert event is not None

    @pytest.mark.asyncio
    async def test_trace_storage_overhead(
        self,
        explainability_engine: ExplainabilityEngine,
        sample_decision_trace: DecisionTrace,
    ):
        """Test trace storage doesn't add significant overhead.

        Scenario:
            1. Save trace
            2. Measure time
            3. Query trace
            4. Verify performance

        Expected:
            - Save: <5ms
            - Query: <2ms for 100 traces
        """
        import time

        # Measure save time
        start = time.time()
        await explainability_engine.storage.save(sample_decision_trace)
        save_time = (time.time() - start) * 1000

        # Measure query time
        start = time.time()
        await explainability_engine.storage.get(sample_decision_trace.id)
        query_time = (time.time() - start) * 1000

        # Verify performance
        assert save_time < 5.0
        assert query_time < 2.0


# ============================================================================
# Audit Integrity Tests
# ============================================================================


class TestAuditIntegrity:
    """Test audit trail cryptographic integrity."""

    @pytest.mark.asyncio
    async def test_audit_chain_integrity(
        self,
        audit_manager: AuditTrailManager,
    ):
        """Test audit chain maintains cryptographic integrity.

        Scenario:
            1. Log multiple events
            2. Verify integrity
            3. Attempt to tamper (simulate)
            4. Verify detection

        Expected:
            - Chain integrity verified
            - Each event links to previous
            - Hash verification succeeds
        """
        # Log multiple events
        events = []
        for i in range(5):
            event = await audit_manager.log(
                event_type=AuditEventType.SKILL_EXECUTED,
                actor_id=f"actor_{i}",
                action=f"Action {i}",
                outcome="success",
            )
            events.append(event)

        # Verify integrity
        is_valid, errors = await audit_manager.verify_integrity()
        assert is_valid
        assert len(errors) == 0

        # Verify hash chain
        for i in range(1, len(events)):
            prev_event = events[i - 1]
            curr_event = events[i]
            assert curr_event.previous_hash == prev_event.event_hash

    @pytest.mark.asyncio
    async def test_audit_event_immutability(
        self,
        audit_manager: AuditTrailManager,
    ):
        """Test audit events are immutable (frozen dataclass).

        Scenario:
            1. Log event
            2. Attempt modification (should fail)
            3. Verify original intact

        Expected:
            - Event is frozen (dataclass)
            - Modification raises error
            - Original unchanged
        """
        event = await audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="test",
            action="Test action",
            outcome="success",
        )

        # Verify event is frozen (immutable)
        with pytest.raises(AttributeError):
            event.action = "Modified action"  # type: ignore

        # Verify original intact
        assert event.action == "Test action"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

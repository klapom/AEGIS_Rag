"""Hallucination monitoring and logging for generated answers.

Sprint Context:
    - Sprint 90 (2026-01-14): Feature 90.3 - Hallucination Monitoring & Logging (8 SP)

Implements active hallucination detection with comprehensive logging.

Process:
    1. Extract factual claims from answer
    2. Verify each claim against contexts
    3. Calculate hallucination score
    4. Log results with severity levels

Packaged as: skills/hallucination_monitor/

Example:
    >>> from src.agents.skills.hallucination_monitor import HallucinationMonitor
    >>> from src.components.llm_proxy import get_aegis_llm_proxy
    >>> import structlog
    >>>
    >>> llm = get_aegis_llm_proxy()
    >>> logger = structlog.get_logger(__name__)
    >>> monitor = HallucinationMonitor(llm, logger)
    >>>
    >>> report = await monitor.check(
    ...     answer="Earth is flat and rotates around the sun.",
    ...     contexts=["Earth is a sphere that orbits the sun."]
    ... )
    >>> report.hallucination_score
    0.5  # 1 out of 2 claims unsupported
    >>> report.unsupported_claims
    ['Earth is flat']

Notes:
    - Uses LLM for claim extraction and verification
    - Tracks metrics (total checks, hallucinations detected)
    - Logs with severity: PASS (<10%), WARN (10-30%), FAIL (>30%)
    - Comprehensive logging for analysis

See Also:
    - docs/sprints/SPRINT_90_PLAN.md: Implementation details
    - src/agents/skills/reflection.py: Related validation skill
"""

from dataclasses import dataclass
from typing import Dict, List

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class Claim:
    """A factual claim extracted from answer.

    Attributes:
        text: Claim text
        index: Position in answer (for tracking)

    Example:
        >>> claim = Claim(text="Earth is a sphere", index=0)
    """

    text: str
    index: int


@dataclass
class ClaimVerification:
    """Result of verifying a claim against contexts.

    Attributes:
        claim: Original claim
        is_supported: Whether claim is supported by contexts
        evidence: Supporting evidence from contexts (if supported)
        reasoning: LLM reasoning for verification

    Example:
        >>> verification = ClaimVerification(
        ...     claim=Claim("Earth is a sphere", 0),
        ...     is_supported=True,
        ...     evidence="Earth is a sphere that orbits...",
        ...     reasoning="Claim matches context statement."
        ... )
    """

    claim: Claim
    is_supported: bool
    evidence: str
    reasoning: str


@dataclass
class HallucinationReport:
    """Hallucination check report.

    Attributes:
        answer: Original answer
        claims: Extracted claims
        verifications: Verification results for each claim
        hallucination_score: Proportion of unsupported claims (0.0-1.0)
        unsupported_claims: List of unsupported claim texts

    Example:
        >>> report = HallucinationReport(
        ...     answer="Earth is flat and rotates.",
        ...     claims=[Claim("Earth is flat", 0), Claim("Earth rotates", 1)],
        ...     verifications=[...],
        ...     hallucination_score=0.5,
        ...     unsupported_claims=["Earth is flat"]
        ... )
    """

    answer: str
    claims: List[Claim]
    verifications: List[ClaimVerification]
    hallucination_score: float
    unsupported_claims: List[str]


class HallucinationMonitor:
    """Monitor and log hallucinations in generated answers.

    Packaged as: skills/hallucination_monitor/

    Attributes:
        llm: Language model for claim extraction and verification
        logger: Structured logger for comprehensive logging
        _metrics: Accumulated metrics

    Example:
        >>> from src.agents.skills.hallucination_monitor import HallucinationMonitor
        >>> from src.components.llm_proxy import get_aegis_llm_proxy
        >>> import structlog
        >>>
        >>> llm = get_aegis_llm_proxy()
        >>> logger = structlog.get_logger(__name__)
        >>> monitor = HallucinationMonitor(llm, logger)
        >>>
        >>> report = await monitor.check(
        ...     answer="The sky is blue due to Rayleigh scattering.",
        ...     contexts=["Rayleigh scattering causes blue sky..."]
        ... )
        >>> report.hallucination_score
        0.0  # All claims supported
    """

    def __init__(self, llm, logger: structlog.BoundLogger):
        """Initialize hallucination monitor.

        Args:
            llm: Language model for claim extraction and verification
            logger: Structured logger for logging
        """
        self.llm = llm
        self.logger = logger
        self._metrics = {
            "total_checks": 0,
            "hallucinations_detected": 0,
            "claims_verified": 0,
            "claims_unsupported": 0,
        }

    async def check(
        self, answer: str, contexts: List[str]
    ) -> HallucinationReport:
        """Check answer for hallucinations.

        Args:
            answer: Answer to check
            contexts: Retrieved contexts for verification

        Returns:
            HallucinationReport with verification results

        Example:
            >>> report = await monitor.check(
            ...     answer="Python was created in 1991.",
            ...     contexts=["Python was released in 1991 by Guido..."]
            ... )
            >>> report.hallucination_score
            0.0
        """
        self._metrics["total_checks"] += 1

        # Extract claims
        claims = await self._extract_claims(answer)

        # Verify each claim
        verifications = []
        for claim in claims:
            result = await self._verify_claim(claim, contexts)
            verifications.append(result)

            if result.is_supported:
                self._metrics["claims_verified"] += 1
            else:
                self._metrics["claims_unsupported"] += 1

        # Calculate score
        unsupported = [v for v in verifications if not v.is_supported]
        score = len(unsupported) / len(claims) if claims else 0.0

        if score > 0.1:
            self._metrics["hallucinations_detected"] += 1

        # Log
        self._log_check(answer, claims, verifications, score)

        return HallucinationReport(
            answer=answer,
            claims=claims,
            verifications=verifications,
            hallucination_score=score,
            unsupported_claims=[v.claim.text for v in unsupported],
        )

    async def _extract_claims(self, answer: str) -> List[Claim]:
        """Extract factual claims from answer.

        Args:
            answer: Answer text

        Returns:
            List of extracted claims

        Example:
            >>> claims = await monitor._extract_claims(
            ...     "Water freezes at 0°C. Ice floats on water."
            ... )
            >>> len(claims)
            2
        """
        extract_prompt = f"""Extract all factual claims from this answer.

Answer:
{answer}

List each claim on a separate line, numbered:
1. [first claim]
2. [second claim]
...

Claims:"""

        self.logger.debug("hallucination_extract_claims_start")

        # Invoke LLM
        response = await self.llm.ainvoke(extract_prompt)

        # Handle different response types
        if hasattr(response, "content"):
            claims_text = response.content
        elif isinstance(response, dict):
            claims_text = response.get("content", str(response))
        else:
            claims_text = str(response)

        # Parse claims
        claims = []
        for i, line in enumerate(claims_text.split("\n")):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                # Remove numbering/bullets
                claim_text = line.lstrip("0123456789.-) ").strip()
                if claim_text:
                    claims.append(Claim(text=claim_text, index=i))

        self.logger.debug("hallucination_extract_claims_complete", count=len(claims))
        return claims

    async def _verify_claim(
        self, claim: Claim, contexts: List[str]
    ) -> ClaimVerification:
        """Verify a claim against contexts.

        Args:
            claim: Claim to verify
            contexts: Retrieved contexts

        Returns:
            ClaimVerification result

        Example:
            >>> verification = await monitor._verify_claim(
            ...     Claim("Water freezes at 0°C", 0),
            ...     ["Water freezes at 0 degrees Celsius..."]
            ... )
            >>> verification.is_supported
            True
        """
        verify_prompt = f"""Verify if this claim is supported by the contexts.

Claim:
{claim.text}

Contexts:
{self._format_contexts(contexts)}

Is the claim supported by the contexts?
Answer with:
SUPPORTED: yes/no
EVIDENCE: [quote from context if supported, or "none" if not]
REASONING: [explain why claim is/isn't supported]

Verification:"""

        self.logger.debug("hallucination_verify_claim_start", claim=claim.text)

        # Invoke LLM
        response = await self.llm.ainvoke(verify_prompt)

        # Handle different response types
        if hasattr(response, "content"):
            verification_text = response.content
        elif isinstance(response, dict):
            verification_text = response.get("content", str(response))
        else:
            verification_text = str(response)

        # Parse verification
        is_supported = "SUPPORTED: yes" in verification_text.lower()

        # Extract evidence
        evidence = ""
        if "EVIDENCE:" in verification_text:
            evidence_start = verification_text.find("EVIDENCE:") + len("EVIDENCE:")
            evidence_end = verification_text.find("REASONING:", evidence_start)
            if evidence_end == -1:
                evidence = verification_text[evidence_start:].strip()
            else:
                evidence = verification_text[evidence_start:evidence_end].strip()

        # Extract reasoning
        reasoning = ""
        if "REASONING:" in verification_text:
            reasoning_start = verification_text.find("REASONING:") + len("REASONING:")
            reasoning = verification_text[reasoning_start:].strip()

        self.logger.debug(
            "hallucination_verify_claim_complete",
            claim=claim.text,
            supported=is_supported,
        )

        return ClaimVerification(
            claim=claim,
            is_supported=is_supported,
            evidence=evidence,
            reasoning=reasoning,
        )

    def _format_contexts(self, contexts: List[str]) -> str:
        """Format contexts with numbered list.

        Args:
            contexts: List of context strings

        Returns:
            Formatted contexts string
        """
        return "\n\n".join(f"[{i+1}] {ctx}" for i, ctx in enumerate(contexts))

    def _log_check(
        self,
        answer: str,
        claims: List[Claim],
        verifications: List[ClaimVerification],
        score: float,
    ):
        """Log hallucination check results.

        Args:
            answer: Original answer
            claims: Extracted claims
            verifications: Verification results
            score: Hallucination score
        """
        verdict = "PASS" if score < 0.1 else "WARN" if score < 0.3 else "FAIL"

        self.logger.info(
            "hallucination_check",
            extra={
                "answer_length": len(answer),
                "num_claims": len(claims),
                "num_verified": sum(1 for v in verifications if v.is_supported),
                "num_unsupported": sum(
                    1 for v in verifications if not v.is_supported
                ),
                "hallucination_score": score,
                "verdict": verdict,
            },
        )

        # Log unsupported claims at WARN/ERROR level
        if score >= 0.1:
            unsupported = [
                v.claim.text for v in verifications if not v.is_supported
            ]
            if score >= 0.3:
                self.logger.error(
                    "hallucination_detected",
                    score=score,
                    unsupported_claims=unsupported,
                )
            else:
                self.logger.warning(
                    "hallucination_detected",
                    score=score,
                    unsupported_claims=unsupported,
                )

    def get_metrics(self) -> Dict[str, int]:
        """Get accumulated metrics.

        Returns:
            Dict with metrics (total_checks, hallucinations_detected, etc.)

        Example:
            >>> metrics = monitor.get_metrics()
            >>> metrics
            {
                'total_checks': 100,
                'hallucinations_detected': 5,
                'claims_verified': 450,
                'claims_unsupported': 30
            }
        """
        return self._metrics.copy()

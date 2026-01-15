"""GDPR storage interfaces and mock implementations.

Provides storage for consent records and processing logs.
Mock implementations are provided for testing; production
implementations would use Redis or a dedicated database.
"""

from datetime import datetime
from typing import Dict, List, Optional

from src.governance.gdpr.compliance import (
    ConsentRecord,
    DataCategory,
    DataProcessingRecord,
)


class ConsentStore:
    """Storage for consent records.

    Mock implementation using in-memory dictionary.
    Production implementation would use Redis with TTL.
    """

    def __init__(self) -> None:
        """Initialize consent store."""
        # data_subject_id -> List[ConsentRecord]
        self._consents: Dict[str, List[ConsentRecord]] = {}

    async def add(self, consent: ConsentRecord) -> None:
        """Add a consent record.

        Args:
            consent: Consent record to add
        """
        if consent.data_subject_id not in self._consents:
            self._consents[consent.data_subject_id] = []

        self._consents[consent.data_subject_id].append(consent)

    async def get(self, consent_id: str) -> Optional[ConsentRecord]:
        """Get consent record by ID.

        Args:
            consent_id: Consent record ID

        Returns:
            Consent record or None if not found
        """
        for consents in self._consents.values():
            for consent in consents:
                if consent.consent_id == consent_id:
                    return consent
        return None

    async def get_consents(
        self,
        data_subject_id: str,
        data_category: Optional[DataCategory] = None,
    ) -> List[ConsentRecord]:
        """Get consent records for a data subject.

        Args:
            data_subject_id: ID of data subject
            data_category: Optional category filter

        Returns:
            List of consent records
        """
        consents = self._consents.get(data_subject_id, [])

        if data_category:
            consents = [
                c for c in consents
                if data_category in c.data_categories
            ]

        return consents

    async def get_all(self, data_subject_id: str) -> List[ConsentRecord]:
        """Get all consent records for a data subject.

        Args:
            data_subject_id: ID of data subject

        Returns:
            List of all consent records
        """
        return self._consents.get(data_subject_id, [])

    async def update(self, consent: ConsentRecord) -> None:
        """Update an existing consent record.

        Args:
            consent: Updated consent record
        """
        consents = self._consents.get(consent.data_subject_id, [])

        for i, existing in enumerate(consents):
            if existing.consent_id == consent.consent_id:
                consents[i] = consent
                return

        # Not found, add as new
        await self.add(consent)

    async def delete(self, consent_id: str) -> bool:
        """Delete a consent record.

        Args:
            consent_id: ID of consent to delete

        Returns:
            True if deleted, False if not found
        """
        for data_subject_id, consents in self._consents.items():
            for i, consent in enumerate(consents):
                if consent.consent_id == consent_id:
                    del self._consents[data_subject_id][i]
                    return True
        return False

    async def delete_all(self, data_subject_id: str) -> int:
        """Delete all consent records for a data subject.

        Args:
            data_subject_id: ID of data subject

        Returns:
            Number of records deleted
        """
        count = len(self._consents.get(data_subject_id, []))
        if data_subject_id in self._consents:
            del self._consents[data_subject_id]
        return count

    def clear(self) -> None:
        """Clear all consent records (for testing)."""
        self._consents.clear()


class ProcessingLog:
    """Storage for processing activity records.

    Mock implementation using in-memory list.
    Production implementation would use Redis or time-series DB.
    """

    def __init__(self) -> None:
        """Initialize processing log."""
        self._records: List[DataProcessingRecord] = []

    async def add(self, record: DataProcessingRecord) -> None:
        """Add a processing record.

        Args:
            record: Processing record to add
        """
        self._records.append(record)

    async def get(self, record_id: str) -> Optional[DataProcessingRecord]:
        """Get processing record by ID.

        Args:
            record_id: Record ID

        Returns:
            Processing record or None if not found
        """
        for record in self._records:
            if record.record_id == record_id:
                return record
        return None

    async def get_by_subject(
        self,
        data_subject_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[DataProcessingRecord]:
        """Get processing records for a data subject.

        Args:
            data_subject_id: ID of data subject
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of processing records
        """
        records = [
            r for r in self._records
            if data_subject_id in r.data_subjects
        ]

        if start_date:
            records = [r for r in records if r.processed_at >= start_date]

        if end_date:
            records = [r for r in records if r.processed_at <= end_date]

        return records

    async def get_by_purpose(
        self,
        purpose: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[DataProcessingRecord]:
        """Get processing records by purpose.

        Args:
            purpose: Processing purpose
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of processing records
        """
        records = [
            r for r in self._records
            if r.processing_purpose == purpose
        ]

        if start_date:
            records = [r for r in records if r.processed_at >= start_date]

        if end_date:
            records = [r for r in records if r.processed_at <= end_date]

        return records

    async def get_all(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[DataProcessingRecord]:
        """Get all processing records.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of all processing records
        """
        records = self._records.copy()

        if start_date:
            records = [r for r in records if r.processed_at >= start_date]

        if end_date:
            records = [r for r in records if r.processed_at <= end_date]

        return records

    async def delete_by_subject(self, data_subject_id: str) -> int:
        """Delete all processing records for a data subject.

        Args:
            data_subject_id: ID of data subject

        Returns:
            Number of records deleted
        """
        original_count = len(self._records)
        self._records = [
            r for r in self._records
            if data_subject_id not in r.data_subjects
        ]
        return original_count - len(self._records)

    def clear(self) -> None:
        """Clear all processing records (for testing)."""
        self._records.clear()

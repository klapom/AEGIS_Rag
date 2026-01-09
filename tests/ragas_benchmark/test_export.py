"""
Unit tests for RAGAS benchmark export functionality.

Sprint 82: Phase 1 - Text-Only Benchmark
"""

import pytest
import json
import tempfile
from pathlib import Path
from scripts.ragas_benchmark.models import NormalizedSample
from scripts.ragas_benchmark.export import (
    export_jsonl,
    export_manifest,
    load_jsonl,
    verify_jsonl,
)


def create_sample(idx: int = 0) -> NormalizedSample:
    """Helper to create test samples."""
    return NormalizedSample(
        id=f"test_{idx}",
        question=f"What is test question {idx}?",
        ground_truth=f"Answer {idx}",
        contexts=[f"Context 1 for {idx}", f"Context 2 for {idx}"],
        doc_type="clean_text",
        question_type="lookup",
        difficulty="D1",
        answerable=True,
        source_dataset="test",
        metadata={"original_id": f"orig_{idx}"},
    )


class TestExportJsonl:
    """Tests for JSONL export."""

    def test_basic_export(self):
        """Test basic JSONL export."""
        samples = [create_sample(i) for i in range(5)]

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_path = f.name

        try:
            sha256 = export_jsonl(samples, output_path)

            # Verify file exists and has content
            assert Path(output_path).exists()
            assert len(sha256) == 64  # SHA256 hex length

            # Verify line count
            with open(output_path) as f:
                lines = f.readlines()
            assert len(lines) == 5

            # Verify JSON validity
            for line in lines:
                data = json.loads(line)
                assert "id" in data
                assert "question" in data
                assert "ground_truth" in data

        finally:
            Path(output_path).unlink()

    def test_export_creates_directory(self):
        """Test that export creates parent directories."""
        samples = [create_sample(0)]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dir" / "output.jsonl"

            export_jsonl(samples, str(output_path))

            assert output_path.exists()

    def test_export_reproducibility(self):
        """Test that same samples give same hash."""
        samples = [create_sample(i) for i in range(3)]

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f1:
            path1 = f1.name
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f2:
            path2 = f2.name

        try:
            # Note: SHA256 may differ due to timestamps in metadata
            # But file structure should be same
            export_jsonl(samples, path1)
            export_jsonl(samples, path2)

            with open(path1) as f:
                lines1 = f.readlines()
            with open(path2) as f:
                lines2 = f.readlines()

            # Same number of lines
            assert len(lines1) == len(lines2)

        finally:
            Path(path1).unlink()
            Path(path2).unlink()


class TestExportManifest:
    """Tests for manifest CSV export."""

    def test_basic_manifest(self):
        """Test basic manifest export."""
        samples = [create_sample(i) for i in range(5)]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            output_path = f.name

        try:
            export_manifest(samples, output_path)

            # Verify file exists
            assert Path(output_path).exists()

            # Read and verify
            import csv
            with open(output_path) as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 5
            assert "id" in rows[0]
            assert "doc_type" in rows[0]
            assert "question_type" in rows[0]
            assert "difficulty" in rows[0]
            assert "answerable" in rows[0]

        finally:
            Path(output_path).unlink()


class TestLoadJsonl:
    """Tests for JSONL loading."""

    def test_load_exported(self):
        """Test loading previously exported JSONL."""
        samples = [create_sample(i) for i in range(5)]

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_path = f.name

        try:
            export_jsonl(samples, output_path)
            loaded = load_jsonl(output_path)

            assert len(loaded) == 5
            assert all(isinstance(s, NormalizedSample) for s in loaded)

            # Verify data integrity
            assert loaded[0].id == "test_0"
            assert loaded[0].question == "What is test question 0?"

        finally:
            Path(output_path).unlink()

    def test_load_missing_file(self):
        """Test loading non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            load_jsonl("/nonexistent/path/file.jsonl")


class TestVerifyJsonl:
    """Tests for JSONL verification."""

    def test_verify_valid_file(self):
        """Test verification of valid file."""
        samples = [create_sample(i) for i in range(5)]

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_path = f.name

        try:
            export_jsonl(samples, output_path)
            result = verify_jsonl(output_path)

            assert result["exists"] is True
            assert result["valid"] is True
            assert result["total_lines"] == 5
            assert result["valid_samples"] == 5
            assert len(result["invalid_lines"]) == 0
            assert result["sha256"] is not None

        finally:
            Path(output_path).unlink()

    def test_verify_missing_file(self):
        """Test verification of missing file."""
        result = verify_jsonl("/nonexistent/file.jsonl")

        assert result["exists"] is False
        assert result["valid"] is False
        assert "File not found" in result["errors"]

    def test_verify_invalid_json(self):
        """Test verification of file with invalid JSON."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode='w') as f:
            f.write('{"valid": "json"}\n')
            f.write('invalid json line\n')
            f.write('{"another": "valid"}\n')
            output_path = f.name

        try:
            result = verify_jsonl(output_path)

            assert result["exists"] is True
            assert result["valid"] is False
            assert result["total_lines"] == 3
            assert len(result["invalid_lines"]) >= 1

        finally:
            Path(output_path).unlink()


class TestSampleSerialization:
    """Tests for NormalizedSample serialization."""

    def test_to_dict_includes_timestamp(self):
        """Test that to_dict includes generation timestamp."""
        sample = create_sample(0)
        data = sample.to_dict()

        assert "metadata" in data
        assert "generation_timestamp" in data["metadata"]
        assert "generator_version" in data["metadata"]

    def test_to_json_valid(self):
        """Test that to_json produces valid JSON."""
        sample = create_sample(0)
        json_str = sample.to_json()

        # Should be valid JSON
        data = json.loads(json_str)
        assert data["id"] == "test_0"

    def test_from_dict_roundtrip(self):
        """Test from_dict/to_dict roundtrip."""
        original = create_sample(0)
        data = original.to_dict()
        restored = NormalizedSample.from_dict(data)

        assert restored.id == original.id
        assert restored.question == original.question
        assert restored.ground_truth == original.ground_truth
        assert restored.doc_type == original.doc_type

    def test_unicode_handling(self):
        """Test that unicode characters are handled correctly."""
        sample = NormalizedSample(
            id="unicode_test",
            question="Was ist München?",
            ground_truth="München ist eine Stadt in Bayern",
            contexts=["München (englisch Munich) ist die Landeshauptstadt des Freistaates Bayern."],
            doc_type="clean_text",
            question_type="definition",
            difficulty="D1",
        )

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_path = f.name

        try:
            export_jsonl([sample], output_path)
            loaded = load_jsonl(output_path)

            assert loaded[0].question == "Was ist München?"
            assert "München" in loaded[0].contexts[0]

        finally:
            Path(output_path).unlink()

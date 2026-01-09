"""
Export utilities for RAGAS benchmark datasets.

Provides:
- JSONL export for AegisRAG evaluation
- CSV manifest for audit/reproducibility
- SHA256 checksums for integrity verification

Sprint 82: Phase 1 - Text-Only Benchmark
"""

import json
import csv
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .models import NormalizedSample, SamplingStats

logger = logging.getLogger(__name__)


def export_jsonl(
    samples: List[NormalizedSample],
    output_path: str,
    pretty: bool = False
) -> str:
    """
    Export samples to JSONL format.

    JSONL (JSON Lines) format: one JSON object per line.
    This is the standard format for RAGAS evaluation datasets.

    Args:
        samples: List of NormalizedSample objects
        output_path: Path to output file
        pretty: If True, format JSON with indentation (not JSONL compliant)

    Returns:
        SHA256 hash of output file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Exporting {len(samples)} samples to {output_path}")

    with open(output_path, 'w', encoding='utf-8') as f:
        for sample in samples:
            if pretty:
                json_str = json.dumps(sample.to_dict(), ensure_ascii=False, indent=2)
            else:
                json_str = sample.to_json()
            f.write(json_str + '\n')

    # Calculate SHA256
    sha256_hash = _calculate_sha256(output_path)

    logger.info(f"Export complete: {output_path}")
    logger.info(f"SHA256: {sha256_hash}")

    return sha256_hash


def export_manifest(
    samples: List[NormalizedSample],
    output_path: str
) -> None:
    """
    Export manifest CSV for audit/reproducibility.

    The manifest provides a quick overview of all samples
    without the full context data.

    Args:
        samples: List of NormalizedSample objects
        output_path: Path to output CSV file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Exporting manifest to {output_path}")

    fieldnames = [
        'id',
        'doc_type',
        'question_type',
        'difficulty',
        'answerable',
        'source_dataset',
        'original_id',
        'question_length',
        'context_count',
        'total_context_length',
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for sample in samples:
            row = {
                'id': sample.id,
                'doc_type': sample.doc_type,
                'question_type': sample.question_type,
                'difficulty': sample.difficulty,
                'answerable': sample.answerable,
                'source_dataset': sample.source_dataset,
                'original_id': sample.metadata.get('original_id', ''),
                'question_length': len(sample.question),
                'context_count': len(sample.contexts),
                'total_context_length': sum(len(c) for c in sample.contexts),
            }
            writer.writerow(row)

    logger.info(f"Manifest exported: {output_path}")


def export_statistics_report(
    samples: List[NormalizedSample],
    output_path: str,
    dataset_name: str = "RAGAS Phase 1"
) -> None:
    """
    Export detailed statistics report.

    Args:
        samples: List of samples
        output_path: Path to output report file
        dataset_name: Name for the report header
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Collect statistics
    stats = SamplingStats()
    for sample in samples:
        stats.add_sample(sample)

    # Generate report
    timestamp = datetime.utcnow().isoformat() + "Z"

    report_lines = [
        f"# {dataset_name} Statistics Report",
        f"Generated: {timestamp}",
        "",
        "## Summary",
        "",
        f"- **Total Samples:** {stats.total_samples}",
        f"- **Answerable:** {stats.answerable_count} ({stats.answerable_count/max(1,stats.total_samples)*100:.1f}%)",
        f"- **Unanswerable:** {stats.unanswerable_count} ({stats.unanswerable_count/max(1,stats.total_samples)*100:.1f}%)",
        "",
        "## Document Types",
        "",
        "| Doc Type | Count | Percentage |",
        "|----------|-------|------------|",
    ]

    for doc_type, count in sorted(stats.doc_type_counts.items()):
        pct = count / max(1, stats.total_samples) * 100
        report_lines.append(f"| {doc_type} | {count} | {pct:.1f}% |")

    report_lines.extend([
        "",
        "## Question Types",
        "",
    ])

    for doc_type, qtypes in sorted(stats.question_type_counts.items()):
        report_lines.append(f"### {doc_type}")
        report_lines.append("")
        report_lines.append("| Question Type | Count | Percentage |")
        report_lines.append("|---------------|-------|------------|")

        doc_total = stats.doc_type_counts.get(doc_type, 1)
        for qtype, count in sorted(qtypes.items()):
            pct = count / max(1, doc_total) * 100
            report_lines.append(f"| {qtype} | {count} | {pct:.1f}% |")

        report_lines.append("")

    report_lines.extend([
        "## Difficulty Distribution",
        "",
        "| Difficulty | Count | Percentage |",
        "|------------|-------|------------|",
    ])

    for diff, count in sorted(stats.difficulty_counts.items()):
        pct = count / max(1, stats.total_samples) * 100
        report_lines.append(f"| {diff} | {count} | {pct:.1f}% |")

    if stats.dropped_samples > 0:
        report_lines.extend([
            "",
            "## Dropped Samples",
            "",
            f"Total dropped: {stats.dropped_samples}",
            "",
            "| Reason | Count |",
            "|--------|-------|",
        ])
        for reason, count in sorted(stats.drop_reasons.items()):
            report_lines.append(f"| {reason} | {count} |")

    # Write report
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    logger.info(f"Statistics report exported: {output_path}")


def load_jsonl(input_path: str) -> List[NormalizedSample]:
    """
    Load samples from JSONL file.

    Args:
        input_path: Path to JSONL file

    Returns:
        List of NormalizedSample objects
    """
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"JSONL file not found: {input_path}")

    samples = []

    with open(input_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                sample = NormalizedSample.from_dict(data)
                samples.append(sample)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON on line {line_num}: {e}")
            except Exception as e:
                logger.warning(f"Failed to parse sample on line {line_num}: {e}")

    logger.info(f"Loaded {len(samples)} samples from {input_path}")
    return samples


def verify_jsonl(input_path: str) -> Dict[str, Any]:
    """
    Verify JSONL file integrity and format.

    Args:
        input_path: Path to JSONL file

    Returns:
        Dict with verification results
    """
    input_path = Path(input_path)

    result = {
        "file_path": str(input_path),
        "exists": input_path.exists(),
        "valid": False,
        "total_lines": 0,
        "valid_samples": 0,
        "invalid_lines": [],
        "sha256": None,
        "errors": [],
    }

    if not result["exists"]:
        result["errors"].append("File not found")
        return result

    # Calculate SHA256
    result["sha256"] = _calculate_sha256(input_path)

    # Validate each line
    with open(input_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            result["total_lines"] += 1
            line = line.strip()

            if not line:
                continue

            try:
                data = json.loads(line)

                # Check required fields
                required = ["id", "question", "ground_truth", "contexts",
                           "doc_type", "question_type", "difficulty"]
                missing = [f for f in required if f not in data]

                if missing:
                    result["invalid_lines"].append({
                        "line": line_num,
                        "error": f"Missing fields: {missing}"
                    })
                else:
                    result["valid_samples"] += 1

            except json.JSONDecodeError as e:
                result["invalid_lines"].append({
                    "line": line_num,
                    "error": str(e)
                })

    # Determine overall validity
    result["valid"] = (
        result["valid_samples"] > 0 and
        len(result["invalid_lines"]) == 0
    )

    return result


def _calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of file."""
    sha256 = hashlib.sha256()

    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)

    return sha256.hexdigest()


def print_distribution_summary(samples: List[NormalizedSample]) -> None:
    """
    Print human-readable distribution summary to console.

    Args:
        samples: List of samples to summarize
    """
    stats = SamplingStats()
    for sample in samples:
        stats.add_sample(sample)

    print(stats.to_report())

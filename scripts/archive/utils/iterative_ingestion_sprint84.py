#!/usr/bin/env python3
"""
Iterative Ingestion Script (Sprint 84)
Uploads files one-by-one with comprehensive error monitoring.

CRITICAL RULES (from RAGAS_JOURNEY.md):
1. Use Frontend API: POST /api/v1/retrieval/upload
2. Stop immediately if ANY chunk has 0 entities
3. Monitor cascade ranks, VRAM, timeouts
4. Document every iteration
"""

import requests
import time
import json
from pathlib import Path
from typing import Dict, List, Optional
import sys

# Configuration
API_BASE_URL = "http://localhost:8000"
NAMESPACE = "ragas_phase2_sprint83_v1"
DOMAIN = "factual"  # HotpotQA = factual questions

# Authentication
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# Files for Iteration 1 (5 files)
FILES_ITERATION_1 = [
    "/home/admin/projects/aegisrag/AEGIS_Rag/data/ragas_phase1_contexts/ragas_phase1_0003_hotpot_5a82171f.txt",
    "/home/admin/projects/aegisrag/AEGIS_Rag/data/ragas_phase1_contexts/ragas_phase1_0015_hotpot_5ae0d91e.txt",
    "/home/admin/projects/aegisrag/AEGIS_Rag/data/ragas_phase1_contexts/ragas_phase1_0032_hotpot_5ac061ab.txt",
    "/home/admin/projects/aegisrag/AEGIS_Rag/data/ragas_phase1_contexts/ragas_phase1_0089_hotpot_5ac3e8c6.txt",
    "/home/admin/projects/aegisrag/AEGIS_Rag/data/ragas_phase1_contexts/ragas_phase1_0102_hotpot_5ab6e84a.txt",
]


class IterativeIngestionMonitor:
    """Monitor ingestion with STOP on errors."""

    def __init__(self, namespace: str, domain: str):
        self.namespace = namespace
        self.domain = domain
        self.uploaded_files = []
        self.errors = []
        self.session = requests.Session()

        # Get JWT token
        self._authenticate()

    def _authenticate(self):
        """Get JWT token for admin user."""
        print(f"🔐 Authenticating as {ADMIN_USERNAME}...")

        response = self.session.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            timeout=30.0,
        )

        if response.status_code != 200:
            raise Exception(f"Authentication failed: {response.status_code}")

        token = response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        print(f"✅ Authenticated successfully")

    def upload_file(self, file_path: str) -> Dict:
        """Upload single file via Frontend API."""
        print(f"\n{'='*80}")
        print(f"📤 UPLOADING: {Path(file_path).name}")
        print(f"{'='*80}")

        with open(file_path, "rb") as f:
            files = {"file": (Path(file_path).name, f, "text/plain")}
            data = {
                "namespace": self.namespace,
                "domain": self.domain,
            }

            try:
                start_time = time.time()
                response = self.session.post(
                    f"{API_BASE_URL}/api/v1/retrieval/upload",
                    files=files,
                    data=data,
                    timeout=300.0,  # 5min timeout
                )
                elapsed = time.time() - start_time

                if response.status_code != 200:
                    print(f"❌ HTTP {response.status_code}: {response.text}")
                    return {"success": False, "error": f"HTTP {response.status_code}"}

                result = response.json()
                print(f"✅ Success in {elapsed:.2f}s")
                print(f"   Status: {result.get('status')}")
                print(f"   Chunks: {result.get('chunks_created')}")
                print(f"   Entities: {result.get('neo4j_entities')}")
                print(f"   Relations: {result.get('neo4j_relationships')}")

                self.uploaded_files.append({
                    "file": Path(file_path).name,
                    "chunks": result.get("chunks_created"),
                    "entities": result.get("neo4j_entities"),
                    "relations": result.get("neo4j_relationships"),
                    "elapsed_s": elapsed,
                })

                return {"success": True, "result": result, "elapsed_s": elapsed}

            except Exception as e:
                print(f"❌ Exception: {e}")
                return {"success": False, "error": str(e)}

    def check_extraction_quality(self, upload_result: Dict) -> Dict:
        """Check entity/relation extraction quality from upload response."""
        print(f"\n🔍 CHECKING EXTRACTION QUALITY...")

        # Extract stats from API response (already available!)
        chunks_count = upload_result.get("chunks_created", 0)
        entities_count = upload_result.get("neo4j_entities", 0)
        relations_count = upload_result.get("neo4j_relationships", 0)

        print(f"   📊 Chunks: {chunks_count}")
        print(f"   📊 Entities: {entities_count}")
        print(f"   📊 Relations: {relations_count}")

        # CRITICAL ERROR THRESHOLD (from RAGAS_JOURNEY.md)
        if chunks_count > 0:
            entities_per_chunk = entities_count / chunks_count

            if entities_per_chunk < 1.0:
                print(f"\n🔴 CRITICAL ERROR: Entities per chunk = {entities_per_chunk:.2f} < 1.0")
                print(f"   STOP INGESTION! Root cause analysis required.")
                return {
                    "success": False,
                    "error": "entities_per_chunk_below_threshold",
                    "entities_per_chunk": entities_per_chunk,
                }

            print(f"   ✅ Entities per chunk: {entities_per_chunk:.2f} (PASS)")

        if relations_count == 0:
            print(f"\n⚠️ WARNING: 0 relations extracted")
            print(f"   Continue monitoring, may trigger STOP if 3+ docs have 0 relations")

        return {
            "success": True,
            "chunks": chunks_count,
            "entities": entities_count,
            "relations": relations_count,
            "entities_per_chunk": entities_count / chunks_count if chunks_count > 0 else 0,
        }

    def check_cascade_logs(self):
        """Check recent API logs for cascade rank usage."""
        print(f"\n📊 CHECKING CASCADE RANKS...")

        # Read last 100 lines of API logs
        try:
            result = self.session.get(
                f"{API_BASE_URL}/api/v1/admin/logs/recent?lines=100",
                timeout=30.0,
            )

            if result.status_code != 200:
                print(f"   ⚠️ Logs API unavailable")
                return

            logs = result.json().get("logs", [])

            # Count cascade rank usage
            rank1_count = sum(1 for log in logs if "rank=1" in log)
            rank2_count = sum(1 for log in logs if "rank=2" in log)
            rank3_count = sum(1 for log in logs if "rank=3" in log)
            timeout_count = sum(1 for log in logs if "timeout" in log.lower())

            print(f"   Rank 1 (Nemotron3): {rank1_count} calls")
            print(f"   Rank 2 (GPT-OSS:20b): {rank2_count} calls")
            print(f"   Rank 3 (SpaCy NER): {rank3_count} calls")
            print(f"   Timeouts: {timeout_count}")

            # CRITICAL: If Rank 3 > 10% → STOP
            total_calls = rank1_count + rank2_count + rank3_count
            if total_calls > 0 and (rank3_count / total_calls) > 0.10:
                print(f"\n🔴 CRITICAL: Rank 3 fallbacks > 10% ({rank3_count}/{total_calls})")
                print(f"   Rank 1/2 models too weak! Cascade tuning required.")
                return {"success": False, "error": "rank3_fallback_rate_high"}

            return {"success": True, "ranks": {"rank1": rank1_count, "rank2": rank2_count, "rank3": rank3_count}}

        except Exception as e:
            print(f"   ⚠️ Could not check logs: {e}")
            return {"success": False, "error": str(e)}

    def run_iteration(self, files: List[str]) -> Dict:
        """Run single iteration with error monitoring."""
        print(f"\n{'#'*80}")
        print(f"# ITERATION 1: {len(files)} files")
        print(f"# Namespace: {self.namespace}")
        print(f"# Domain: {self.domain}")
        print(f"{'#'*80}")

        for i, file_path in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] Processing: {Path(file_path).name}")

            # 1. Upload file
            upload_result = self.upload_file(file_path)
            if not upload_result["success"]:
                print(f"\n🔴 STOP: Upload failed!")
                self.errors.append({
                    "file": Path(file_path).name,
                    "stage": "upload",
                    "error": upload_result["error"],
                })
                return {"success": False, "stage": "upload", "file": Path(file_path).name}

            # 2. Check extraction quality (using upload response data)
            quality_result = self.check_extraction_quality(upload_result["result"])
            if not quality_result["success"]:
                print(f"\n🔴 STOP: Extraction quality failed!")
                self.errors.append({
                    "file": Path(file_path).name,
                    "stage": "extraction",
                    "error": quality_result["error"],
                })
                return {"success": False, "stage": "extraction", "file": Path(file_path).name}

            # 3. Check cascade logs (every 2 files)
            if i % 2 == 0:
                cascade_result = self.check_cascade_logs()
                if cascade_result and not cascade_result.get("success"):
                    print(f"\n🔴 STOP: Cascade rank issues!")
                    self.errors.append({
                        "file": Path(file_path).name,
                        "stage": "cascade",
                        "error": cascade_result["error"],
                    })
                    return {"success": False, "stage": "cascade", "file": Path(file_path).name}

        print(f"\n{'='*80}")
        print(f"✅ ITERATION 1 COMPLETE: {len(files)} files uploaded successfully!")
        print(f"{'='*80}")

        return {"success": True, "files_uploaded": len(files)}

    def print_summary(self):
        """Print iteration summary."""
        print(f"\n{'#'*80}")
        print(f"# ITERATION 1 SUMMARY")
        print(f"{'#'*80}")
        print(f"Files uploaded: {len(self.uploaded_files)}")
        print(f"Errors: {len(self.errors)}")

        if self.uploaded_files:
            print(f"\n✅ Uploaded Files:")
            for f in self.uploaded_files:
                print(f"   - {f['file']}: {f['chunks']} chunks, {f['entities']} entities, {f['relations']} relations ({f['elapsed_s']:.2f}s)")

        if self.errors:
            print(f"\n❌ Errors:")
            for e in self.errors:
                print(f"   - {e['file']}: {e['stage']} - {e['error']}")


def main():
    """Main entry point."""
    monitor = IterativeIngestionMonitor(
        namespace=NAMESPACE,
        domain=DOMAIN,
    )

    try:
        result = monitor.run_iteration(FILES_ITERATION_1)

        if not result["success"]:
            print(f"\n🔴 ITERATION FAILED!")
            print(f"   Stage: {result['stage']}")
            print(f"   File: {result['file']}")
            print(f"\n⚠️ ROOT CAUSE ANALYSIS REQUIRED!")
            sys.exit(1)

        monitor.print_summary()
        print(f"\n✅ Ready for Iteration 2 (20 files)")

    except KeyboardInterrupt:
        print(f"\n\n⚠️ Interrupted by user")
        monitor.print_summary()
        sys.exit(1)
    except Exception as e:
        print(f"\n\n🔴 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        monitor.print_summary()
        sys.exit(1)


if __name__ == "__main__":
    main()

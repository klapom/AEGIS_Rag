#!/usr/bin/env python3
"""
Grafana Dashboard Validator

Validates all dashboard JSON files for:
- Valid JSON syntax
- Required fields (uid, title, schemaVersion)
- Panel structure integrity
- PromQL query syntax (basic validation)
- Data source references

Usage:
    python scripts/validate_dashboards.py
    python scripts/validate_dashboards.py --dashboard 1-executive-overview.json
    python scripts/validate_dashboards.py --verbose
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse


class DashboardValidator:
    """Validates Grafana dashboard JSON files."""

    REQUIRED_DASHBOARD_FIELDS = {"uid", "title", "schemaVersion", "panels"}
    REQUIRED_PANEL_FIELDS = {"id", "title", "type", "gridPos"}
    VALID_PANEL_TYPES = {
        "timeseries", "stat", "gauge", "piechart", "table",
        "graph", "heatmap", "histogram", "state-timeline"
    }
    REQUIRED_GRID_POS_FIELDS = {"h", "w", "x", "y"}

    def __init__(self, dashboards_dir: Path, verbose: bool = False):
        self.dashboards_dir = dashboards_dir
        self.verbose = verbose
        self.errors = []
        self.warnings = []
        self.info = []

    def log_error(self, message: str, dashboard: str = "", panel_id: int = None):
        """Log validation error."""
        context = f"[{dashboard}" + (f":Panel{panel_id}]" if panel_id else "]")
        msg = f"ERROR {context} {message}"
        self.errors.append(msg)
        if self.verbose:
            print(f"  ✗ {msg}")

    def log_warning(self, message: str, dashboard: str = "", panel_id: int = None):
        """Log validation warning."""
        context = f"[{dashboard}" + (f":Panel{panel_id}]" if panel_id else "]")
        msg = f"WARNING {context} {message}"
        self.warnings.append(msg)
        if self.verbose:
            print(f"  ⚠ {msg}")

    def log_info(self, message: str):
        """Log info message."""
        if self.verbose:
            print(f"  ℹ {message}")
        self.info.append(message)

    def validate_json_syntax(self, file_path: Path) -> bool:
        """Validate JSON syntax."""
        try:
            with open(file_path, 'r') as f:
                json.load(f)
            self.log_info(f"Valid JSON syntax")
            return True
        except json.JSONDecodeError as e:
            self.log_error(f"Invalid JSON: {e}", file_path.name)
            return False
        except Exception as e:
            self.log_error(f"Failed to read file: {e}", file_path.name)
            return False

    def validate_dashboard_structure(self, dashboard: Dict, file_name: str) -> bool:
        """Validate dashboard top-level structure."""
        if "dashboard" not in dashboard:
            self.log_error("Missing 'dashboard' wrapper", file_name)
            return False

        db = dashboard["dashboard"]

        # Check required fields
        for field in self.REQUIRED_DASHBOARD_FIELDS:
            if field not in db:
                self.log_error(f"Missing required field: {field}", file_name)
                return False

        # Validate field types
        if not isinstance(db.get("uid"), str):
            self.log_error("Field 'uid' must be string", file_name)
            return False

        if not isinstance(db.get("title"), str):
            self.log_error("Field 'title' must be string", file_name)
            return False

        if not isinstance(db.get("panels"), list):
            self.log_error("Field 'panels' must be array", file_name)
            return False

        self.log_info(f"Dashboard structure valid: uid={db['uid']}, panels={len(db['panels'])}")
        return True

    def validate_panels(self, dashboard: Dict, file_name: str) -> bool:
        """Validate all panels in dashboard."""
        db = dashboard["dashboard"]
        panels = db.get("panels", [])

        if not panels:
            self.log_warning("Dashboard has no panels", file_name)
            return True

        all_valid = True

        for idx, panel in enumerate(panels):
            if not isinstance(panel, dict):
                self.log_error(f"Panel {idx} is not a dict", file_name, idx)
                all_valid = False
                continue

            # Check required fields
            for field in self.REQUIRED_PANEL_FIELDS:
                if field not in panel:
                    self.log_error(f"Panel missing '{field}'", file_name, panel.get("id"))
                    all_valid = False

            # Validate gridPos
            grid_pos = panel.get("gridPos", {})
            if not isinstance(grid_pos, dict):
                self.log_error(f"gridPos is not dict", file_name, panel.get("id"))
                all_valid = False
            else:
                for field in self.REQUIRED_GRID_POS_FIELDS:
                    if field not in grid_pos:
                        self.log_warning(f"gridPos missing '{field}'", file_name, panel.get("id"))

            # Validate panel type
            panel_type = panel.get("type")
            if panel_type not in self.VALID_PANEL_TYPES:
                self.log_warning(f"Unknown panel type: {panel_type}", file_name, panel.get("id"))

            # Check for targets with PromQL
            targets = panel.get("targets", [])
            if not targets:
                self.log_warning(f"Panel has no targets", file_name, panel.get("id"))
            else:
                for t_idx, target in enumerate(targets):
                    if "expr" in target:
                        # Basic PromQL validation
                        expr = target["expr"]
                        if not self._validate_promql(expr):
                            self.log_warning(f"Suspicious PromQL: {expr[:50]}...",
                                           file_name, panel.get("id"))

            # Check datasource reference
            if "datasource" not in panel and "targets" in panel:
                self.log_warning(f"No datasource specified", file_name, panel.get("id"))

        return all_valid

    def _validate_promql(self, expr: str) -> bool:
        """Basic PromQL syntax validation."""
        # Simple heuristics
        if not expr.strip():
            return False
        if expr.count("(") != expr.count(")"):
            return False
        if expr.count("{") != expr.count("}"):
            return False
        return True

    def validate_file(self, file_path: Path) -> Tuple[bool, Dict]:
        """Validate single dashboard file."""
        print(f"\nValidating: {file_path.name}")
        self.errors.clear()
        self.warnings.clear()
        self.info.clear()

        # Validate JSON syntax
        if not self.validate_json_syntax(file_path):
            return False, self._get_results()

        # Parse JSON
        with open(file_path, 'r') as f:
            dashboard = json.load(f)

        # Validate structure
        if not self.validate_dashboard_structure(dashboard, file_path.name):
            return False, self._get_results()

        # Validate panels
        self.validate_panels(dashboard, file_path.name)

        return len(self.errors) == 0, self._get_results()

    def validate_all(self) -> Dict[str, Tuple[bool, Dict]]:
        """Validate all dashboards in directory."""
        results = {}
        json_files = sorted(self.dashboards_dir.glob("*.json"))

        if not json_files:
            print(f"No JSON files found in {self.dashboards_dir}")
            return results

        for file_path in json_files:
            valid, details = self.validate_file(file_path)
            results[file_path.name] = (valid, details)

        return results

    def _get_results(self) -> Dict:
        """Get validation results."""
        return {
            "errors": self.errors.copy(),
            "warnings": self.warnings.copy(),
            "info": self.info.copy(),
        }

    @staticmethod
    def print_summary(results: Dict[str, Tuple[bool, Dict]]):
        """Print validation summary."""
        print("\n" + "="*80)
        print("VALIDATION SUMMARY")
        print("="*80)

        total = len(results)
        passed = sum(1 for valid, _ in results.values() if valid)
        failed = total - passed

        print(f"\nTotal Dashboards: {total}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {failed} ✗")

        if failed > 0:
            print("\nFailed Dashboards:")
            for name, (valid, details) in results.items():
                if not valid:
                    print(f"  - {name}")
                    for error in details["errors"]:
                        print(f"    {error}")

        # Print warnings
        total_warnings = sum(len(details["warnings"]) for _, details in results.values())
        if total_warnings > 0:
            print(f"\nWarnings ({total_warnings}):")
            for name, (_, details) in results.items():
                for warning in details["warnings"]:
                    print(f"  - {warning}")

        print("\n" + "="*80)
        return failed == 0


def main():
    parser = argparse.ArgumentParser(
        description="Validate Grafana dashboard JSON files"
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path(__file__).parent.parent / "config" / "grafana" / "dashboards",
        help="Dashboards directory (default: config/grafana/dashboards/)"
    )
    parser.add_argument(
        "--dashboard",
        type=str,
        help="Validate specific dashboard file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if not args.dir.exists():
        print(f"Error: Directory not found: {args.dir}")
        sys.exit(1)

    validator = DashboardValidator(args.dir, verbose=args.verbose)

    if args.dashboard:
        # Validate single dashboard
        file_path = args.dir / args.dashboard
        if not file_path.exists():
            print(f"Error: Dashboard not found: {file_path}")
            sys.exit(1)
        valid, results = validator.validate_file(file_path)
        if not valid:
            print(f"\n✗ Validation FAILED")
            for error in results["errors"]:
                print(f"  ERROR: {error}")
            sys.exit(1)
        else:
            print(f"\n✓ Validation PASSED")
            sys.exit(0)
    else:
        # Validate all dashboards
        results = validator.validate_all()
        success = DashboardValidator.print_summary(results)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

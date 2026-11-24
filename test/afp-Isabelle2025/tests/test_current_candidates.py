#!/usr/bin/env python3
"""Current candidate scopes cannot bypass coverage gates or retain replaced failures."""

import _paths  # Locate AFP tools independently of cwd and unittest discovery.
from pathlib import Path
import copy
import tempfile
import unittest
from unittest.mock import patch

import afp_common as common
import full


class CurrentCandidateTests(unittest.TestCase):
    def fixture(self, root):
        # The current run has one known and one blocked scope. No candidate
        # handoff can bypass the scan checkpoint or remove the blocked row.
        from state import State
        base = root / "run"
        State(base)
        result = {"entries": {
            "A": {"scan": {"status": "passed", "theories": ["A.thy"], "semantic_identity": "A"}},
            "B": {"scan": {"status": "blocked", "theories": [], "semantic_identity": "B"}}}}
        exports = {"A": {"A.thy": ["A.f"]}, "B": {}}
        common.write_record(base / "scan-checkpoint.json", {"passed": False,
                            "scan_signature": full.scan_signature(result, exports)})
        return base, result, exports

    def test_partial_scan_preserves_rows_and_cannot_bypass_checkpoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            base, result, exports = self.fixture(Path(temporary))
            with self.assertRaisesRegex(ValueError, "passing scan-checkpoint"):
                full.require_scan_gate(base, result, exports)
            self.assertEqual(set(result["entries"]), {"A", "B"})
            self.assertEqual(result["entries"]["B"]["scan"]["status"], "blocked")
            self.assertFalse((base / "baseline").exists())

    def test_candidate_or_scan_mutation_invalidates_the_checkpoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            base, result, exports = self.fixture(Path(temporary))
            common.write_record(base / "scan-checkpoint.json", {"passed": True,
                                "scan_signature": full.scan_signature(result, exports)})
            full.require_scan_gate(base, result, exports)
            changed = copy.deepcopy(exports); changed["A"]["A.thy"].append("A.g")
            with self.assertRaises(ValueError):
                full.require_scan_gate(base, result, changed)
            result["entries"]["B"]["scan"]["status"] = "passed"
            with self.assertRaises(ValueError):
                full.require_scan_gate(base, result, exports)

    def test_missing_current_run_is_rejected_before_loading_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            with self.assertRaisesRegex(ValueError, "Initialize"):
                full.load(base)
            self.assertFalse((base / "results.json").exists())


class InheritedScanReportTests(unittest.TestCase):
    def record(self, root, status, receipt):
        # Saved receipts distinguish validation errors after successful native
        # commands from blocked sessions that never started a command.
        from state import State
        base = root / "run"
        State(base).put("receipt/u", receipt)
        scan = {"status": status, "unit_ids": {"A": "u"},
                "loading": [], "inspections": []}
        result = {"entries": {"A": {"scan": scan}}}
        return base, {"order": ["A"]}, result

    def test_receipt_validation_failure_has_its_own_complete_evidence(self):
        # A successful HOL build is not a HOL error when the scanner rejects
        # the loaded context coverage afterwards.
        import full_report
        import full_audit
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(common, "PROJECT", root):
                base, data, result = self.record(
                    root, "failed", {"error": "loaded theories do not cover required session context"})
                events = list(full_report.failure_events(base, data, result))
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]["stage"], "receipt_validation")
                self.assertTrue(events[0]["full_message_available"])
                self.assertEqual(full_report.category(events[0]["error"])[0], "scan_coverage")
                self.assertEqual(list(full_audit.required_failure_inventory(base, data, result)),
                                 [full_audit.failure_key(events[0])])

    def test_replaced_export_failure_is_absent_from_current_report(self):
        # Correcting a serializer configuration must preserve the old exception
        # and its log even after the candidate now has a newer result.
        import full_report
        import full_audit
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(common, "PROJECT", root):
                base, data, result = self.record(root, "passed", {})
                witness = root / "old.xml"
                witness.write_text('<attempt><error>No code equations for A.f</error></attempt>')
                (root / "old.log").write_text("old serializer command")
                result["entries"]["A"]["full_export_history"] = [{
                    "runs": [{"command": {"status": "passed", "log": "old.log"},
                              "attempts": [{"status": "failed", "stage": "frontend",
                                            "target": "frontend", "constants": ["A.f"],
                                            "evidence": "old.xml"}]}]}]
                events = list(full_report.failure_events(base, data, result))
                self.assertEqual(events, [])
                self.assertEqual(full_audit.required_failure_inventory(base, data, result), {})

    def test_dependency_only_receipt_names_the_real_prerequisite(self):
        # No phantom failed command should be counted for a pure dependency
        # block; its sole event must explain the actual Native_Word cause.
        import full_report
        import full_audit
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(common, "PROJECT", root):
                base, data, result = self.record(root, "blocked",
                                                {"dependencies": ["Native_Word"]})
                result["entries"]["A"]["scan"]["loading"] = [
                    {"session": "A", "status": "blocked_dependency"}]
                events = list(full_report.failure_events(base, data, result))
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]["stage"], "dependency")
                self.assertIn("Native_Word", events[0]["error"])
                self.assertEqual(full_report.category(events[0]["error"])[0], "dependency")
                self.assertEqual(list(full_audit.required_failure_inventory(base, data, result)),
                                 [full_audit.failure_key(events[0])])


if __name__ == "__main__":
    unittest.main()

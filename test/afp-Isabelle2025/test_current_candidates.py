#!/usr/bin/env python3
"""A selected partial scan is an explicit scope, never a successful full scan."""
from pathlib import Path
import copy
import tempfile
import unittest
from unittest.mock import patch

import afp_common as common
import full


class CurrentCandidateTests(unittest.TestCase):
    def fixture(self, root):
        # One loaded entry and one unknown entry exercise the continuation
        # boundary. The unknown entry must survive with no invented candidates.
        source, base = root / "scan", root / "downstream"
        data = {"order": ["A", "B"], "entries": {
            "A": {"theories": [{"path": "A.thy"}]},
            "B": {"theories": [{"path": "B.thy"}]}}}
        result = {"environment": {"afp_root": str(root / "afp"), "proofs": "checked"},
                  "entries": {
                      "A": {"scan": {"status": "passed", "theories": ["A.thy"],
                                     "semantic_identity": "A"}},
                      "B": {"scan": {"status": "blocked", "theories": [],
                                     "unit_states": {"B": "blocked_dependency"},
                                     "semantic_identity": "B"}}}}
        exports = {"A": {"A.thy": ["A.f"]}, "B": {"B.thy": []}}
        common.write_json(source / "snapshots/current.json",
                          {"results": result, "exports": exports})
        common.write_json(source / "scan-current.json", {
            "snapshot": "snapshots/current.json",
            "sha256": full.file_digest(source / "snapshots/current.json")})
        common.write_json(source / "manifest.json", data)
        common.write_json(source / "scan-checkpoint.json", {"passed": False})
        common.write_json(source / "source-inputs.json", {"afp": {}})
        return source, base, result, exports

    def test_partial_snapshot_has_separate_contract_and_preserves_every_row(self):
        # Accepting current candidates must not forge a successful scan gate,
        # drop blocked entries, or reload the mutable global manifest.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(common, "PROJECT", root), patch.object(common, "HERE", root / "tools"):
                source, base, original, exports = self.fixture(root)
                contract = full.initialize_candidates(base, source)
                data, result, actual = full.load(base)
                self.assertFalse(contract["scan_complete"])
                self.assertEqual(contract["scan_counts"], {"passed": 1, "blocked": 1})
                self.assertEqual(result["entries"], original["entries"])
                self.assertEqual(actual, exports)
                self.assertFalse((base / "scan-checkpoint.json").exists())
                full.require_scan_gate(base, result, actual)
                self.assertEqual(set(data["entries"]), {"A", "B"})
                with self.assertRaises(ValueError):
                    full.initialize_candidates(base, source)

    def test_candidate_or_scan_mutation_invalidates_the_accepted_boundary(self):
        # A continuation cannot silently enlarge its candidates or turn an
        # unknown upstream entry into a success after accepting the snapshot.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(common, "PROJECT", root), patch.object(common, "HERE", root / "tools"):
                source, base, _, _ = self.fixture(root)
                full.initialize_candidates(base, source)
                _, result, exports = full.load(base)
                changed = copy.deepcopy(exports)
                changed["A"]["A.thy"].append("A.g")
                with self.assertRaises(ValueError):
                    full.require_scan_gate(base, result, changed)
                result["entries"]["B"]["scan"]["status"] = "passed"
                with self.assertRaises(ValueError):
                    full.require_scan_gate(base, result, exports)

    def test_snapshot_digest_is_checked_before_any_import(self):
        # A stale pointer cannot import a newer or partially written snapshot.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(common, "PROJECT", root), patch.object(common, "HERE", root / "tools"):
                source, base, _, _ = self.fixture(root)
                with (source / "snapshots/current.json").open("a") as stream:
                    stream.write(" ")
                with self.assertRaises(ValueError):
                    full.initialize_candidates(base, source)
                self.assertFalse((base / "results.json").exists())


class InheritedScanReportTests(unittest.TestCase):
    def record(self, root, status, receipt):
        # Saved receipts distinguish validation errors after successful native
        # commands from blocked sessions that never started a command.
        base = root / "downstream"
        path = base / "baseline/receipts/u.json"
        common.write_json(path, receipt)
        common.write_json(base / "baseline/receipt-index.json",
                          {"u": {"receipt": common.relative(path)}})
        scan = {"status": status, "unit_ids": {"A": "u"},
                "loading": [], "inspections": []}
        result = {"entries": {"A": {"scan": scan}}}
        common.write_json(base / "results.json", result)
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

    def test_replaced_export_failure_remains_historical_with_full_xml(self):
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
                self.assertEqual(len(events), 1)
                self.assertTrue(events[0]["historical"])
                self.assertEqual(events[0]["error"], "No code equations for A.f")
                self.assertEqual(list(full_audit.required_failure_inventory(base, data, result)),
                                 [full_audit.failure_key(events[0])])

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

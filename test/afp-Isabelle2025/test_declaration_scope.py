#!/usr/bin/env python3
"""Source identity regressions for same-name declarations in independent branches."""
import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import afp_common as common
import declaration_scope
import full
import full_audit
import full_report


class DeclarationScopeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        self.base = self.project / "full"
        self.work = self.base / "exports/E/S/attempt-0001"
        self.work.mkdir(parents=True)
        self.patch = patch.object(common, "PROJECT", self.project)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.info = {"theories": [{"path": path + ".thy", "name": "E." + path} for path in ("A", "B")]}
        self.data = {"order": ["E"], "entries": {"E": self.info}}
        self.scope = {"A.thy": ["Locale.shared", "A.other"], "B.thy": ["Locale.shared"]}
        self.scan = {"status": "passed", "theories": ["A.thy", "B.thy"], "contexts": {
            "S": {"E.A": ["E.A"], "E.B": ["E.B"]}}}
        (self.work / "loaded.xml").write_text('<loaded><theory>E.A</theory><theory>E.B</theory></loaded>')
        (self.work / "process.log").write_text("finished")
        for number, parent in ((1, "E.A"), (2, "E.B")):
            path = self.work / ("contexts/branch" + str(number) + ".xml")
            path.parent.mkdir(exist_ok=True)
            path.write_text('<context><theory>' + parent + '</theory>'
                            '<constant name="Locale.shared"/><constant name="A.other"/></context>')
        for target in full.TARGETS:
            self.attempt("branch1", "all", target, "passed", ["Locale.shared", "A.other"])
        # The failing branch first rejects a group, then isolates the repeated
        # name. The other branch's success answers the deduplicated query only.
        self.attempt("branch2", "all", "frontend", "failed", ["Locale.shared", "A.other"])
        self.singleton = self.attempt("branch2", "allL", "frontend", "failed", ["Locale.shared"])
        self.refresh()

    def attempt(self, context, batch, target, status, constants, stage=None):
        node = ET.Element("attempt", context=context, batch=batch, target=target, status=status, seconds="0.001",
                          stage=stage or ("frontend" if target == "frontend" else "target_preparation_or_serialization"))
        for name in constants:
            ET.SubElement(node, "constant", name=name)
        if target in {"frontend", "context"}:
            for language in full.TARGETS:
                ET.SubElement(node, "language").text = language
        if status == "failed":
            ET.SubElement(node, "error").text = "No code equations for Locale.shared"
        else:
            ET.SubElement(node, "library_only").text = "true"
        path = self.work / "attempts" / context / batch / (target + ".xml")
        path.parent.mkdir(parents=True, exist_ok=True)
        ET.ElementTree(node).write(path, encoding="unicode")
        return path

    def refresh(self):
        run = {"session": "S", "directory": common.relative(self.work), "finished": True,
               "command": {"status": "passed", "log": common.relative(self.work / "process.log")},
               "attempts": full.collect_attempts(self.work)}
        self.record = {"scan": self.scan, "full_export": {
            "status": "complete", "runs": [run], "artifacts": [],
            "candidates": full.resolve_candidates(common.candidates(self.scope), [run]),
            "languages": {target: "passed" for target in full.TARGETS}}}
        self.result = {"entries": {"E": self.record}}
        common.write_json(self.base / "results.json", self.result)
        common.write_json(self.base / "exports.json", {"E": self.scope})

    def rows(self):
        return {(row["theory"], row["constant"]): row for row in declaration_scope.rows(
            "E", self.info, self.record, self.scope)}

    def audit_report(self):
        audit = {"passed": True, "issues": [], "checks": {}, "issue_counts": {}}
        full_audit.audit_reports(self.base, self.data, self.result, {"E": self.scope}, audit)
        return audit

    def test_source_rows_preserve_independent_outcomes_and_report_audit_rejects_borrowed_success(self):
        # Both sources must remain visible although the per-entry name succeeds.
        # Editing one declaration to borrow the other's valid XML must be caught
        # even after adjusting the summary totals to agree with the forged CSV.
        rows = self.rows()
        self.assertEqual(len(rows), 3)
        self.assertEqual(self.record["full_export"]["candidates"]["Locale.shared"]["Go"]["status"], "passed")
        self.assertEqual(rows[("A.thy", "Locale.shared")]["Go"], "passed")
        self.assertEqual(rows[("B.thy", "Locale.shared")]["Go"], "failed")
        summary = full_report.build_report(self.base, self.data, self.result, {"E": self.scope}, verified=True)
        self.assertEqual(summary["candidate_references"], 2)
        self.assertEqual(summary["source_declarations"], 3)
        self.assertTrue(self.audit_report()["passed"])
        path = self.base / "report/declarations.csv"
        with path.open() as stream:
            reported = list(csv.DictReader(stream))
        first = next(row for row in reported if row["theory"] == "A.thy" and row["constant"] == "Locale.shared")
        second = next(row for row in reported if row["theory"] == "B.thy")
        for target in full.TARGETS:
            second[target] = first[target]
            second[target + "_evidence"] = first[target + "_evidence"]
            summary["declaration_statuses"][target] = {"passed": 3}
        full_report.write_csv(path, list(reported[0]), reported)
        common.write_json(self.base / "report/summary.json", summary)
        self.assertEqual(self.audit_report()["issue_counts"]["declaration report matches source witness"], 6)

    def test_failed_group_is_not_reinterpreted_as_singleton_source_failure(self):
        # Removing isolation leaves a failed group with two constants. Source
        # filtering may select the branch, but must preserve that entire group.
        self.singleton.unlink()
        self.refresh()
        self.assertEqual(self.rows()[("B.thy", "Locale.shared")]["Go"], "blocked")
        witnesses = full_audit.declaration_witnesses(self.info, self.record, self.scope)
        self.assertFalse(witnesses[("B.thy", "Locale.shared")]["targets"]["Go"]["failed"])
        # A forged in-memory context label cannot change the original XML parent.
        for attempt in self.record["full_export"]["runs"][0]["attempts"]:
            if attempt["context"] == "branch1":
                attempt["context"] = "branch2"
        self.assertEqual(self.rows()[("B.thy", "Locale.shared")]["Go"], "passed")
        witnesses = full_audit.declaration_witnesses(self.info, self.record, self.scope)
        self.assertFalse(witnesses[("B.thy", "Locale.shared")]["targets"]["Go"]["passed"])

    def test_loading_failure_requires_exact_scanned_ancestry_and_loaded_order(self):
        # Failed branch construction has no context XML. Recover its source only
        # when the frozen maximal ancestry exactly accounts for loaded originals.
        (self.work / "contexts/branch2.xml").unlink()
        self.singleton.unlink()
        self.attempt("branch2", "loading", "context", "failed", ["Locale.shared", "A.other"], "context_loading")
        self.refresh()
        self.assertEqual(self.rows()[("B.thy", "Locale.shared")]["Scala"], "failed")
        witnesses = full_audit.declaration_witnesses(self.info, self.record, self.scope)
        self.assertTrue(witnesses[("B.thy", "Locale.shared")]["targets"]["Scala"]["failed"])
        (self.work / "loaded.xml").write_text(
            '<loaded><theory>E.A</theory><theory>E.B</theory><theory>E.Unscanned</theory></loaded>')
        self.assertEqual(self.rows()[("B.thy", "Locale.shared")]["Scala"], "blocked")

    def test_declaration_audit_rejects_omitted_source_even_if_candidate_count_unchanged(self):
        # Name-level counts do not detect a missing second source row. The audit
        # compares the exact (entry, source path, constant) multiset independently.
        full_report.build_report(self.base, self.data, self.result, {"E": self.scope}, verified=True)
        path = self.base / "report/declarations.csv"
        with path.open() as stream:
            rows = list(csv.DictReader(stream))
        full_report.write_csv(path, list(rows[0]), [row for row in rows if row["theory"] != "B.thy"])
        self.assertIn("exactly one report row per source declaration", self.audit_report()["issue_counts"])


if __name__ == "__main__":
    unittest.main()

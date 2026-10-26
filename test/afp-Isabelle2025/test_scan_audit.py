#!/usr/bin/env python3
"""Independent audit evidence for scan coverage failures after successful loading."""
from pathlib import Path
import copy
import tempfile
import unittest
from unittest.mock import patch

import afp_common as common
import full
import full_audit


class ScanCoverageAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        context = patch.object(common, "PROJECT", self.project)
        context.start()
        self.addCleanup(context.stop)
        self.base = self.project / "full"
        self.data = {"order": ["E"], "entries": {"E": {"theories": [
            {"path": "A.thy"}, {"path": "B.thy"}]}}}
        self.scan = {"status": "failed", "theories": ["A.thy"],
                     "missing_theories": [{"path": "B.thy"}],
                     "loading": [{"session": "S", "status": "passed"}],
                     "inspections": [{"session": "S", "status": "passed"}]}
        self.result = {"entries": {"E": {"scan": self.scan}}}
        self.exports = {"E": {}}
        common.write_json(self.base / "results.json", self.result)
        common.write_json(self.base / "exports.json", self.exports)

    def cause_issues(self):
        # This deliberately small fixture checks only the cause predicate;
        # unrelated archive-size and unfinished downstream checks remain active.
        with patch.object(full, "serializer_signature", return_value="serializer"):
            audit = full_audit.audit_data(self.base, self.data, self.result, self.exports)
        return audit["issue_counts"].get("scan failure has direct cause", 0)

    def test_post_load_coverage_rejection_keeps_its_failed_status(self):
        # Successful commands do not cover a required theory absent from the
        # accepted catalog. An exact recorded gap explains the scan failure.
        original = copy.deepcopy(self.result)
        self.assertEqual(self.cause_issues(), 0)
        self.assertEqual(self.result, original)
        self.assertEqual(self.scan["status"], "failed")

    def test_missing_list_must_match_the_actual_manifest_gap(self):
        # A list naming a loaded theory, omitting the real missing theory, or
        # claiming missing coverage after full discovery cannot witness failure.
        invalid = [(["A.thy"], [{"path": "A.thy"}]),
                   (["A.thy"], []),
                   (["A.thy", "B.thy"], [{"path": "B.thy"}])]
        for loaded, missing in invalid:
            with self.subTest(loaded=loaded, missing=missing):
                self.scan.update(theories=loaded, missing_theories=missing)
                self.assertEqual(self.cause_issues(), 1)

    def test_unknown_scope_requires_its_own_failure_evidence(self):
        # An unexplained blocked scan must not become an evidenced validation
        # failure merely because its candidate catalog has incomplete coverage.
        self.scan["status"] = "blocked"
        self.assertEqual(self.cause_issues(), 1)


if __name__ == "__main__":
    unittest.main()

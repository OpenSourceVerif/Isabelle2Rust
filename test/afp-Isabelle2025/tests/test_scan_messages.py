#!/usr/bin/env python3
"""Current diagnostics remain bound to committed scan receipts and original logs."""

import _paths  # Locate AFP tools independently of cwd and unittest discovery.
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import afp_common as common
import scan_evidence
from state import State
import full
import full_audit
import full_report


class CurrentMessageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        context = patch.object(common, "PROJECT", self.project)
        context.start()
        self.addCleanup(context.stop)
        self.base = self.project / "run"
        self.source = self.base
        self.state = State(self.base)
        self.archive = self.source / "units/u/attempt-0001/scan-messages"
        self.archive.mkdir(parents=True)
        self.body = "long original compiler context\n" * 100 + "Error: Unbound module Pervasives\n"
        self.log = self.archive / "messages.txt"
        self.log.write_text(self.body)
        self.load = self.source / "units/u/attempt-0001/load.log"
        self.load.write_text("Code check failed for OCaml")
        self.index = self.archive / "index.json"
        common.write_record(self.index, {"S": {"status": "passed", "origin_verified": True,
            "command": {"status": "passed", "log": common.relative(self.log)},
            "messages_sha256": full.file_digest(self.log)}})
        self.state.put("receipt/u", {"status": "unresolved_infrastructure",
                                       "directory": "units/u/attempt-0001"})
        scan = {"status": "failed", "theories": [], "unit_ids": {"S": "u"}, "loading": [{
            "status": "failed", "session": "S", "failed_sessions": ["S"], "log": common.relative(self.load)}]}
        self.data = {"order": ["E"], "entries": {"E": {"theories": [{"path": "A.thy"}]}}}
        self.result = {"entries": {"E": {"scan": scan}}}
        self.exports = {"E": {}}

    def audit_report(self):
        audit = {"passed": True, "issues": [], "checks": {}, "issue_counts": {}}
        full_audit.audit_reports(self.base, self.data, self.result, self.exports, audit)
        return audit

    def test_committed_receipt_retains_full_messages_until_replacement_commit(self):
        # A later successful scanner head must not replace the failed command's
        # compiler details. The full old body exceeds the bounded excerpt length.
        common.write_record(self.source / "units/u/attempt-0002/attempt.json", {"status": "running"})
        events = list(full_report.failure_events(self.base, self.data, self.result))
        self.assertEqual(len(events), 1)
        self.assertIn(self.body, events[0]["error"])
        self.assertIn(common.relative(self.log), events[0]["evidence"])
        self.assertTrue(events[0]["full_message_available"])
        self.assertEqual(self.result["entries"]["E"]["scan"]["status"], "failed")

    def test_changed_message_log_is_not_used_as_failure_evidence(self):
        # The receipt pins the archive index hash; even a plausible replacement
        # with the same session must not become accepted full-message evidence.
        self.log.write_text(self.body + "changed")
        messages = scan_evidence.messages(self.base, self.result["entries"]["E"]["scan"])
        self.assertFalse(messages["S"]["receipt_index_verified"])
        event = next(full_report.failure_events(self.base, self.data, self.result))
        self.assertFalse(event["full_message_available"])
        self.assertNotIn(common.relative(self.log), event["evidence"])

    def test_independent_report_audit_detects_shortened_body_with_consistent_hash(self):
        # Keeping a correct log link and recomputing the catalog hash is not
        # enough: audit the actual full failed-session body against the catalog.
        full_report.build_report(self.base, self.data, self.result, self.exports, verified=True)
        self.assertTrue(self.audit_report()["passed"])
        path = self.base / "report/failures.jsonl"
        import json
        event = json.loads(path.read_text())
        event["error"] = self.load.read_text()
        event["error_sha256"] = full.digest(event["error"].encode())
        path.write_text(json.dumps(event) + "\n")
        self.assertEqual(self.audit_report()["issue_counts"][
            "failure catalog includes full failed-session messages"], 1)


if __name__ == "__main__":
    unittest.main()

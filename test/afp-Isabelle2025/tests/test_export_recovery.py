#!/usr/bin/env python3
"""Resource recovery tests: partition export requests, never source outcomes."""

import _paths  # Locate AFP tools independently of cwd and unittest discovery.
import collections
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import afp_common as common
import full
import full_audit
import full_report


class ExportRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        self.base = self.project / "full"
        self.base.mkdir()
        for context in (patch.object(common, "PROJECT", self.project),
                        patch.object(full, "serializer_signature", return_value="serializer")):
            context.start()
            self.addCleanup(context.stop)
        self.info = {"theories": [{"path": "A.thy", "name": "E.A"}]}
        self.record = {"scan": {"status": "passed", "theories": ["A.thy"],
                                "loading": [{"status": "passed", "session": "S"}]}}
        self.args = SimpleNamespace(export_batch_size=0)
        self.sizes = []
        self.capacity = 2

    def command(self, session, work, args, env):
        names = (work / "scope.txt").read_text().splitlines()
        self.sizes.append(len(names))
        failed = len(names) > self.capacity
        log = work / "process.log"
        log.write_text("Run out of store - interrupting threads" if failed else "finished")
        if not failed:
            (work / "finished.xml").write_text("<finished/>")
            for target in full.TARGETS:
                node = ET.Element("attempt", context="merged", batch="all", target=target,
                                  status="passed", stage="target_preparation_or_serialization", seconds="0.001")
                for name in names:
                    ET.SubElement(node, "constant", name=name)
                ET.SubElement(node, "library_only").text = "true"
                path = work / "attempts/merged/all" / (target + ".xml")
                path.parent.mkdir(parents=True, exist_ok=True)
                ET.ElementTree(node).write(path, encoding="unicode")
        return {"status": "failed" if failed else "passed", "log": common.relative(log)}

    def export(self, count):
        scope = {"A.thy": [f"A.c{index:03}" for index in range(count)]}
        with patch.object(full, "export_command", side_effect=self.command):
            full.export_entry("E", self.info, self.record, scope, self.base, self.args, {})
        return scope

    def test_native_memory_failure_splits_in_fresh_processes_and_preserves_failed_commands(self):
        # A heap failure before the first XML yields no candidate verdict. Split
        # all members until four disjoint successful scopes cover the eight names.
        scope = self.export(8)
        stage = self.record["full_export"]
        self.assertEqual(self.sizes, [8, 4, 2, 2, 4, 2, 2])
        self.assertEqual(stage["status"], "complete")
        self.assertEqual([len(run["scope"]) for run in stage["runs"]], [2] * 4)
        self.assertNotIn("full_export_history", self.record)
        progress = common.read_record(self.base / "export-progress/E.json")
        self.assertEqual(len(progress["retries"]), 1)
        self.assertEqual(len(list((self.base / "exports/E/S").glob("attempt-*"))), 5)
        result = {"entries": {"E": self.record}}
        self.assertTrue(full.export_checkpoint(self.base, {"order": ["E"]}, result, {"E": scope})["passed"])
        events = list(full_report.failure_events(self.base, {"order": ["E"]}, result))
        self.assertEqual(events, [])
        self.assertEqual(full_audit.required_failure_inventory(self.base, {"order": ["E"]}, result),
                         collections.Counter(map(full_audit.failure_key, events)))

    def test_prior_exhausting_aggregate_is_not_repeated(self):
        # Resumption uses its durable resource diagnosis to cap the initial
        # requests. The same eighty-name aggregate must not consume the heap again.
        log = self.base / "previous.log"
        log.write_text("Run out of store - interrupting threads")
        self.record["full_export"] = {"status": "blocked", "runs": [{
            "command": {"status": "failed", "log": common.relative(log)}, "attempts": []}]}
        self.capacity = 100
        self.export(80)
        self.assertEqual(self.sizes, [32, 32, 16])
        self.assertEqual(self.record["full_export"]["status"], "complete")

    def test_exhausting_singleton_remains_resource_blockage(self):
        # A one-name request cannot be split further. Its process log is kept,
        # its candidate cells remain unresolved, and the export gate must fail.
        self.capacity = 0
        scope = self.export(1)
        self.assertEqual(self.sizes, [1])
        stage = self.record["full_export"]
        self.assertEqual(stage["status"], "blocked")
        self.assertTrue(all(value["status"] == "blocked" for value in stage["candidates"]["A.c000"].values()))
        gate = full.export_checkpoint(self.base, {"order": ["E"]}, {"entries": {"E": self.record}}, {"E": scope})
        self.assertFalse(gate["passed"])
        self.assertTrue(any(problem["reason"] == "incomplete process" for problem in gate["problems"]))


if __name__ == "__main__":
    unittest.main()

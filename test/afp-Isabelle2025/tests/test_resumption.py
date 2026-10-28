#!/usr/bin/env python3
"""Command evidence must survive interruption before a whole AFP entry finishes."""

import _paths  # Locate AFP tools independently of cwd and unittest discovery.
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import afp_common as common
import full
import full_audit
import full_report


class ResumptionTests(unittest.TestCase):
    def test_live_identity_is_durable_before_entry_checkpoint(self):
        # A multi-hour Isabelle session has no completed entry result yet.
        # Verify the live marker from a real child before it exits, then its
        # terminal outcome, without running any generated program.
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            log = project / "proof.log"
            record = log.with_suffix(".log.json")
            observed = []
            sleep = time.sleep
            def observe(_seconds):
                value = json.loads(record.read_text())
                self.assertEqual(value["status"], "running")
                self.assertEqual(value["identity"], list(common.process_identity(value["pid"])))
                self.assertTrue(value["boot_id"])
                observed.append(value["pid"])
                sleep(0.01)
            args = SimpleNamespace(timeout=0, min_available_mb=0)
            clock = SimpleNamespace(monotonic=time.monotonic, sleep=observe)
            with patch.object(common, "PROJECT", project), patch.object(common, "time", clock):
                outcome = common.command(
                    [sys.executable, "-c", "import time; time.sleep(0.1)"], log, args, dict(os.environ))
            saved = json.loads(record.read_text())
            self.assertTrue(observed)
            self.assertEqual(saved, json.loads(json.dumps(outcome)))
            self.assertEqual(saved["status"], "passed")
            self.assertIn("finished", saved)

    def test_interrupt_records_terminal_state_and_stops_child(self):
        # Losing the outer interaction must not leave a child proving or
        # compiling silently. The record preserves its exact birth identity.
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            log = project / "proof.log"
            args = SimpleNamespace(timeout=0, min_available_mb=0)
            # Replace only the executor's clock: subprocess.wait must retain
            # its real sleep so descendant termination can finish and reap.
            def interrupt(_seconds):
                raise KeyboardInterrupt
            clock = SimpleNamespace(monotonic=time.monotonic, sleep=interrupt)
            with patch.object(common, "PROJECT", project), patch.object(common, "time", clock):
                with self.assertRaises(KeyboardInterrupt):
                    common.command([sys.executable, "-c", "import time; time.sleep(60)"],
                                   log, args, dict(os.environ))
            saved = json.loads(log.with_suffix(".log.json").read_text())
            self.assertEqual(saved["status"], "interrupted")
            self.assertEqual(saved["interruption"], "KeyboardInterrupt")
            self.assertIsNone(common.process_identity(saved["pid"]))
            self.assertIsNotNone(saved["returncode"])
            self.assertIn("finished", saved)

    def test_host_interruption_is_retained_without_becoming_a_candidate_failure(self):
        # A host can stop before an entry result is written. It is an archived
        # infrastructure event, with the raw partial output and recovery facts.
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            base = project / "full"
            recovery = base / "recovery/boot-1"
            recovery.mkdir(parents=True)
            (recovery / "observation.json").write_text('{"process_missing": true}')
            (recovery / "interruption.log").write_text("Infrastructure interruption: host_restart")
            common.write_json(recovery / "result.json", {
                "entry": "@execution/main_scan", "phase": "scan", "status": "interrupted",
                "log": "full/recovery/boot-1/interruption.log",
                "evidence": ["full/recovery/boot-1/observation.json"]})
            data = {"order": []}
            result = {"entries": {}}
            with patch.object(common, "PROJECT", project):
                events = list(full_report.failure_events(base, data, result))
                self.assertEqual(len(events), 1)
                self.assertTrue(events[0]["historical"])
                self.assertEqual(events[0]["constants"], [])
                self.assertEqual(full_report.category(events[0]["error"])[0], "infrastructure")
                self.assertTrue(full.infrastructure("interrupted"))
                self.assertEqual(list(full_audit.required_failure_inventory(base, data, result)),
                                 [full_audit.failure_key(events[0])])


if __name__ == "__main__":
    unittest.main()

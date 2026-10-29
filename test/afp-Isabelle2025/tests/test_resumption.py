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

    def test_new_command_replaces_interruption_without_accumulating_history(self):
        # The same command slot keeps its latest outcome. An earlier host loss
        # must neither become a candidate failure nor remain a growing archive.
        from state import State
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); state = State(base); log = base / "proof.log"
            common.write_record(log.with_suffix(".log.json"), {"status": "interrupted", "reason": "host_restart"})
            args = SimpleNamespace(timeout=0, min_available_mb=0)
            with patch.object(common, "PROJECT", base):
                outcome = common.command([sys.executable, "-c", "pass"], log, args, dict(os.environ))
            self.assertEqual(outcome["status"], "passed")
            self.assertEqual(state.get("proof.log.json")["status"], "passed")
            self.assertEqual(state.keys(), ["proof.log.json"])
            self.assertFalse(log.with_suffix(".log.json").exists())
            self.assertEqual(list(full_report.failure_events(base, {"order": []}, {"entries": {}})), [])
            self.assertEqual(full_audit.required_failure_inventory(base, {"order": []}, {"entries": {}}), {})


class CompileResumptionTests(unittest.TestCase):
    def test_checkpoint_loss_reuses_completed_stage1_and_finishes_remaining_stages(self):
        # A driver can stop immediately after its durable stage-1 checkpoint.
        # Resume must retain that result and run each remaining native stage once.
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source/Cargo.toml"
            source.parent.mkdir(); source.write_text("source")
            record = {}
            checked = {"status": "passed", "checks": [{"status": "passed", "returncode": 0}]}
            def checkpoint():
                item = record["full_compile"][str(source)]
                if item.get("stage1_compile") and not item.get("optimization"):
                    raise KeyboardInterrupt
            def optimize(argv, log, args, env):
                out = Path(argv[-1]); out.mkdir(parents=True)
                (out / "Cargo.toml").write_text("optimized")
                return {"status": "passed", "returncode": 0, "log": str(log)}
            with patch.object(full, "rust_manifests", return_value=[str(source)]), \
                 patch.object(full, "compile_crates", return_value=checked) as compile, \
                 patch.object(full, "completed_command", side_effect=optimize) as optimize:
                with self.assertRaises(KeyboardInterrupt):
                    full.compile_entry("E", record, base, None, {}, base / "optimizer", checkpoint)
                full.compile_entry("E", record, base, None, {}, base / "optimizer")
                self.assertEqual([call.args[1] for call in compile.call_args_list], ["stage1", "stage2"])
                self.assertEqual(optimize.call_count, 1)
                self.assertTrue(full.compile_checkpoint(base, {"entries": {"E": record}})["passed"])

    def test_timeout_is_retried_without_repeating_completed_optimizer(self):
        # A timeout has a process exit but no compiler verdict. It cannot make
        # the crate complete or suppress the next compilation attempt.
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "Cargo.toml"; source.write_text("source")
            out = base / "rust-stage2/E/current"; out.mkdir(parents=True)
            (out / "Cargo.toml").write_text("optimized")
            passed = {"status": "passed", "checks": [{"status": "passed"}]}
            item = {"directory": str(base / "compilation/E/current"), "stage2": str(out),
                    "stage1_compile": {"status": "failed", "checks": [{"status": "timeout"}]},
                    "optimization": {"status": "passed"}, "stage2_compile": passed, "complete": True}
            record = {"full_compile": {str(source): item}}
            with patch.object(full, "rust_manifests", return_value=[str(source)]):
                self.assertFalse(full.compile_checkpoint(base, {"entries": {"E": record}})["passed"])
                with patch.object(full, "compile_crates", return_value=passed) as compile, \
                     patch.object(full, "completed_command") as optimize:
                    full.compile_entry("E", record, base, None, {}, base / "optimizer")
                compile.assert_called_once(); optimize.assert_not_called()
                self.assertTrue(full.compile_checkpoint(base, {"entries": {"E": record}})["passed"])
                item["stage2_compile"] = {"status": "passed", "checks": []}
                self.assertFalse(full.compile_checkpoint(base, {"entries": {"E": record}})["passed"])

    def test_exited_command_is_adopted_before_phase_checkpoint(self):
        # An actual exited child's durable command record survives even when
        # the enclosing crate checkpoint has not been written yet.
        from state import State
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); State(base)
            log = base / "compiler.log"
            args = SimpleNamespace(timeout=0, min_available_mb=0)
            argv = [sys.executable, "-c", "print('compiled')"]
            first = full.completed_command(argv, log, args, dict(os.environ))
            with patch.object(common, "command") as execute:
                second = full.completed_command(argv, log, args, dict(os.environ))
            execute.assert_not_called()
            self.assertEqual(first["status"], second["status"])
            self.assertEqual(first["pid"], second["pid"])


if __name__ == "__main__":
    unittest.main()

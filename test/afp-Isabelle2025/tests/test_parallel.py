"""Parallel entry workers must preserve checkpoints, cache isolation and child cleanup."""
import _paths
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import afp
import afp_common as common
import full
import scan_frozen
from result_store import EntryStore
from state import State


class ParallelEntryTests(unittest.TestCase):
    def test_workers_commit_private_records_and_reuse_bounded_slots(self):
        # Force two mutable entry records to coexist across multiple commits.
        # A shared one-record EntryStore would evict one and publish stale data.
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            names = [f"E{i}" for i in range(6)]
            scans = {name: {"scan": {}} for name in names}
            scopes = {name: {} for name in names}
            result = {"entries": EntryStore(base, scans, scopes)}
            result["entries"][names[-1]]  # Prime the coordinator's stale cache.
            barrier = threading.Barrier(2)
            used = []
            lock = threading.Lock()
            def action(entry, record, checkpoint, slot, options):
                record["full_compile"] = {"marker": {"entry": entry, "step": 1}}
                checkpoint()
                barrier.wait(timeout=10)
                record["full_compile"]["marker"]["step"] = 2
                with lock:
                    used.append((entry, full.compilation_environment({}, base, slot)["CARGO_TARGET_DIR"]))
            full.parallel_entries(base, result, scopes, names, 2, SimpleNamespace(), action)
            state = State(base)
            for name in names:
                expected = {"entry": name, "step": 2}
                self.assertEqual(state.get("entry/" + name)["full_compile"]["marker"], expected)
                self.assertEqual(result["entries"][name]["full_compile"]["marker"], expected)
            self.assertEqual(len({target for _, target in used}), 2)
            self.assertEqual(len(used), 6)

    def test_failure_cancels_live_native_sibling_and_stops_scheduling(self):
        # An exceptional worker must stop a real sleeping subprocess, retain
        # its interrupted receipt and never dispatch the queued third entry.
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            scans = {name: {"scan": {}} for name in ("sleep", "fail", "queued")}
            scopes = {name: {} for name in scans}
            result = {"entries": EntryStore(base, scans, scopes)}
            started = []
            args = SimpleNamespace(timeout=0, min_available_mb=0)
            def action(entry, record, checkpoint, slot, options):
                started.append(entry)
                if entry == "fail":
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        receipt = State(base).get("sleep.log.json", {})
                        if receipt.get("status") == "running" and common.identity_matches(receipt):
                            raise ValueError("controlled worker failure")
                        time.sleep(0.01)
                    raise AssertionError("sibling did not start")
                common.command([sys.executable, "-c", "import time; time.sleep(60)"],
                               base / "sleep.log", options, dict(os.environ))
            with self.assertRaisesRegex(ValueError, "controlled worker failure"):
                full.parallel_entries(base, result, scopes, list(scans), 2, args, action)
            saved = State(base).get("sleep.log.json")
            self.assertEqual(saved["status"], "interrupted")
            self.assertIsNotNone(saved["returncode"])
            self.assertFalse(common.identity_matches(saved))
            self.assertNotIn("queued", started)
            self.assertFalse(State(base).keys("entry/"))

    def test_request_marker_excludes_another_live_export(self):
        # A recovered request can be dead while another entry is exporting.
        # Only that request's marker may prevent retry; the shared run cannot.
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            options = SimpleNamespace(timeout=0, min_available_mb=0)
            observations = []
            def inspect(_seconds):
                if observations:
                    time.sleep(0.01)
                    return
                observations.append(scan_frozen.active_children(base))
                self.assertTrue(observations[-1])
                self.assertTrue(scan_frozen.active_children(base / "A", "AFP_EXPORT_REQUEST"))
                self.assertFalse(scan_frozen.active_children(base / "B", "AFP_EXPORT_REQUEST"))
                time.sleep(0.01)
            clock = SimpleNamespace(monotonic=time.monotonic, sleep=inspect)
            env = dict(os.environ, AFP_EXPORT_REQUEST=str(base / "A"))
            State(base)
            with patch.object(common, "time", clock):
                common.command([sys.executable, "-c", "import time; time.sleep(0.2)"],
                               base / "process.log", options, env)
            self.assertTrue(observations)

    def test_duplicate_entries_and_invalid_workers_are_rejected(self):
        # Duplicate work could concurrently mutate the same export directory.
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for entries, workers in ((["E", "E"], 2), (["E"], 0)):
                with self.assertRaises(ValueError):
                    full.parallel_entries(base, {"entries": {}}, {}, entries,
                                          workers, SimpleNamespace(), lambda *args: None)


class SchedulerConfigurationTests(unittest.TestCase):
    def test_server_options_reach_build_export_and_cargo(self):
        # Resource budgets must survive the top-level subprocess boundary.
        scheduler = dict(build_jobs=8, threads=8, parallel_proofs=2,
                         export_workers=8, compile_workers=8, cargo_jobs=8)
        args = common.arguments("test").parse_args(afp.runtime_arguments({"scheduler": scheduler}))
        for key, value in scheduler.items():
            self.assertEqual(getattr(args, key), value)
        self.assertEqual(common.build_options(args)[:6],
                         ["-j", "8", "-o", "threads=8", "-o", "parallel_proofs=2"])
        with tempfile.TemporaryDirectory() as temporary, patch.object(common, "command") as command:
            args.afp = Path(temporary)
            full.export_command("HOL", Path(temporary), args, {})
            argv = command.call_args.args[0]
            self.assertIn("threads=8", argv)
            self.assertIn("parallel_proofs=2", argv)
            self.assertEqual(command.call_args.args[3]["AFP_EXPORT_REQUEST"], temporary)
        defaults = common.arguments("test").parse_args(afp.runtime_arguments({}))
        self.assertEqual(defaults.cargo_jobs, 1)
        self.assertEqual(defaults.export_workers, 1)
        for name in ("build_jobs", "threads", "export_workers", "compile_workers", "cargo_jobs"):
            invalid = common.arguments("test").parse_args([])
            setattr(invalid, name, 0)
            with patch.object(common.subprocess, "check_output") as execute:
                with self.assertRaisesRegex(ValueError, "must be positive"):
                    common.environment(invalid)
                execute.assert_not_called()

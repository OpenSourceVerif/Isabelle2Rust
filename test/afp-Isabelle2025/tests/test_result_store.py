"""Current entry state: atomic replacement, bounded storage and evidence checks."""
import _paths
import copy
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import afp_common as common
import full
from result_store import EntryStore
from state import State


class ResultStoreTests(unittest.TestCase):
    def store(self, root):
        base = root / "experiment"
        scans = {e: {"scan": {"status": "passed", "theories": [e + ".thy"], "semantic_identity": e}} for e in ("A", "B")}
        scopes = {e: {e + ".thy": [e + ".f"]} for e in scans}
        store = EntryStore(base, scans, scopes)
        records = {e: dict(copy.deepcopy(scans[e]), full_export={"status": "no_candidates", "runs": [], "candidates": {}, "languages": {"Go": "pending"}}) for e in scans}
        for entry, record in records.items():
            store[entry] = record
            store.commit(entry)
        return base, store, scans, scopes, records

    def test_all_result_fields_survive_lazy_load_and_working_set_eviction(self):
        # Reading another entry must not discard committed phase results.
        with tempfile.TemporaryDirectory() as temporary, patch.object(common, "PROJECT", Path(temporary)):
            base, store, scans, scopes, records = self.store(Path(temporary))
            reader = EntryStore(base, scans, scopes)
            for entry in ("A", "B", "A"):
                self.assertEqual(reader[entry], records[entry])
            self.assertNotIn("scan", State(base).get("entry/A"))
            self.assertFalse((base / "results.json").exists())
            self.assertFalse((base / "entry-results").exists())

    def test_uncommitted_update_cannot_break_previous_committed_result(self):
        # Real SIGKILL inside a SQLite transaction must roll back all changed
        # rows, rather than exposing an entry from one generation and a gate from another.
        with tempfile.TemporaryDirectory() as temporary:
            state = State(temporary)
            state.update({"entry/A": {"value": 1}, "gate": {"value": 1}})
            script = """import os,signal,sqlite3,sys
c=sqlite3.connect(sys.argv[1]);c.execute('BEGIN IMMEDIATE')
c.execute('UPDATE records SET value=? WHERE key=?', ('{\"value\":2}', 'entry/A'))
os.kill(os.getpid(),signal.SIGKILL)
"""
            run = subprocess.run([sys.executable, "-B", "-c", script, str(Path(temporary) / "state.sqlite3")])
            self.assertEqual(run.returncode, -signal.SIGKILL)
            self.assertEqual(state.get("entry/A"), {"value": 1})
            self.assertEqual(state.get("gate"), {"value": 1})

    def test_repeated_publication_keeps_only_latest_rows(self):
        # Replace the former migration/history assertion with the required
        # latest-only invariant: row count stays fixed across many commits.
        with tempfile.TemporaryDirectory() as temporary, patch.object(common, "PROJECT", Path(temporary)):
            base, store, scans, scopes, records = self.store(Path(temporary))
            for number in range(20):
                store["A"]["full_export"]["languages"]["Go"] = str(number)
                store.commit("A")
            self.assertEqual(State(base).keys(), ["entry/A", "entry/B"])
            self.assertEqual(EntryStore(base, scans, scopes)["A"]["full_export"]["languages"]["Go"], "19")
            self.assertEqual(list(base.iterdir()), [base / "state.sqlite3"])

    def test_changed_native_evidence_cannot_pass_export_checkpoint(self):
        # The source digest is retained even though candidate views are derived.
        with tempfile.TemporaryDirectory() as temporary, patch.object(common, "PROJECT", Path(temporary)):
            base = Path(temporary); artifact = base / "code.rs"; artifact.write_text("original")
            record = {"scan": {"status": "passed"}}
            scope = {"A.thy": ["A.f"]}
            record["full_export"] = {"status": "complete", "runs": [], "scope_sha256": full.scope_digest(scope),
                "scan_sha256": full.entry_scan_signature(record), "serializer_sha256": "fixture",
                "artifacts": [{"path": "code.rs", "sha256": full.file_digest(artifact)}]}
            artifact.write_text("changed")
            with patch.object(full, "serializer_signature", return_value="fixture"):
                gate = full.export_checkpoint(base, {"order": ["A"]}, {"entries": {"A": record}}, {"A": scope})
            self.assertFalse(gate["passed"])
            self.assertIn("missing/changed export", [p["reason"] for p in gate["problems"]])

    def test_phase_save_commits_mutated_entry_before_other_reads(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(common, "PROJECT", Path(temporary)):
            base, store, scans, scopes, _ = self.store(Path(temporary))
            store["A"]["full_export"]["languages"]["Go"] = "passed"
            full.save(base, {"entries": store}, scopes, "A")
            self.assertEqual(EntryStore(base, scans, scopes)["A"]["full_export"]["languages"]["Go"], "passed")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Entry payloads preserve complete results across bounded-memory checkpoints."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import afp_common as common
import full
from result_store import EntryStore


class ResultStoreTests(unittest.TestCase):
    def store(self, root):
        base = root / "experiment"
        records = {e: {"scan": {"status": "passed", "theories": [e + ".thy"],
                               "semantic_identity": e},
                       "full_export": {"status": "complete", "candidates": {
                           e + ".f": {"Rust": {"status": "failed", "evidence": ["whole.xml"]}}},
                           "runs": [], "artifacts": [], "languages": {"Rust": "failed"}}}
                   for e in ("A", "B")}
        store = EntryStore(base, copy.deepcopy(records), {})
        for entry, record in records.items():
            store[entry] = copy.deepcopy(record)
            store.commit(entry, {})
        return base, store, records

    def test_all_result_fields_survive_lazy_load_and_working_set_eviction(self):
        # Paging to another entry must not reduce XML inventories, evidence,
        # failed candidates, or scanner context identity to the summary fields.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(common, "PROJECT", root):
                _, store, records = self.store(root)
                self.assertEqual(store["A"], records["A"])
                self.assertEqual(store["B"], records["B"])
                self.assertEqual(store["A"], records["A"])
                self.assertNotIn("candidates", store.summaries["A"]["full_export"])

    def test_uncommitted_new_payload_cannot_break_previous_atomic_index(self):
        # A host interruption after the entry write but before results.json is
        # replaced must leave the old payload and its old index fully usable.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(common, "PROJECT", root):
                base, store, records = self.store(root)
                previous = copy.deepcopy(store.serialize({"entries": store}))
                store["A"]["full_export"]["status"] = "blocked"
                store.commit("A", {})
                old = EntryStore(base, previous["entries"], previous["entry_files"])
                self.assertEqual(old["A"], records["A"])
                self.assertEqual(store["A"]["full_export"]["status"], "blocked")
                self.assertNotEqual(old.files["A"]["path"], store.files["A"]["path"])

    def test_legacy_migration_preserves_all_rows_and_keeps_old_checkpoint(self):
        # The full migration checks every payload and the discovery signature;
        # legacy and compact readers must return exactly the same entry data.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(common, "PROJECT", root), \
                    patch.object(full, "serializer_signature", return_value="test-serializer"):
                base, _, records = self.store(root)
                common.write_json(base / "manifest.json", {
                    "order": ["A", "B"], "entries": {"A": {}, "B": {}}})
                common.write_json(base / "exports.json", {
                    "A": {"A.thy": ["A.f"]}, "B": {"B.thy": ["B.f"]}})
                common.write_json(base / "results.json", {"entries": copy.deepcopy(records)})
                report = full.compact_results(base)
                self.assertEqual(report["entries_checked"], 2)
                _, result, _ = full.load(base)
                self.assertIsInstance(result["entries"], EntryStore)
                self.assertEqual(dict(result["entries"]), records)
                self.assertEqual(common.read_json(root / report["legacy"])["entries"], records)

    def test_changed_payload_bytes_are_rejected(self):
        # Existing evidence cannot be silently replaced by different valid JSON.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(common, "PROJECT", root):
                base, store, _ = self.store(root)
                path = root / store.files["A"]["path"]
                path.write_text('{"scan": {"status": "passed"}}')
                reader = EntryStore(base, store.summaries, store.files)
                with self.assertRaises(ValueError):
                    reader["A"]

    def test_phase_save_commits_mutated_entry_before_coverage_traversal(self):
        # Export/compile mutate one working record. Aggregating every other
        # entry must not evict that uncommitted result and lose completed work.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(common, "PROJECT", root):
                base, store, _ = self.store(root)
                result = {"entries": store}
                store["A"]["full_export"]["languages"]["Go"] = "passed"
                exports = {"A": {"A.thy": ["A.f"]}, "B": {"B.thy": ["B.f"]}}
                with patch.object(full, "serializer_signature", return_value="test-serializer"):
                    full.save(base, result, exports, "A")
                saved = common.read_json(base / "results.json")
                reader = EntryStore(base, saved["entries"], saved["entry_files"])
                self.assertEqual(reader["A"]["full_export"]["languages"]["Go"], "passed")
                self.assertEqual(saved["coverage"]["distinct_candidates"], 2)
                self.assertNotIn("candidates", saved["entries"]["A"]["full_export"])


if __name__ == "__main__":
    unittest.main()

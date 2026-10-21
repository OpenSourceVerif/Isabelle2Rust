#!/usr/bin/env python3
"""Regression tests for complete logs, report denominators and physical witnesses."""
import copy
import collections
from contextlib import closing
import csv
from datetime import datetime, timezone
import json
import os
import sqlite3
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import afp_common as common
import full
import full_audit
import full_report


class ReportingTests(unittest.TestCase):
    def test_full_certificate_message_survives_excerpted_result_record(self):
        # Scanner summaries are bounded, but the report must read the original
        # XML body rather than repeat a shortened certificate failure.
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            base = project / "full"
            base.mkdir()
            message = "long certificate failure " * 400
            (base / "scan.xml").write_text(
                '<scan><theory name="E.A"><error name="A.f">' + message + '</error></theory></scan>')
            data = {"order": ["E"]}
            result = {"entries": {"E": {"scan": {"status": "passed", "certificate_errors": [
                {"name": "A.f", "message": message[:2000], "truncated": True, "detail": "full/scan.xml"}]}}}}
            with patch.object(common, "PROJECT", project):
                events = list(full_report.failure_events(base, data, result))
            self.assertEqual(events[0]["error"], message)
            self.assertTrue(events[0]["full_message_available"])

    def test_performance_excludes_failed_paths_and_requires_equal_scopes(self):
        # A fast rejection is not successful serializer throughput. Six
        # successful samples must refer to exactly the same requested constants.
        attempts = [
            {"context": "merged", "batch": "all", "target": target, "status": "passed",
             "constants": ["A.f"], "seconds": "0.010"} for target in full.TARGETS]
        attempts.append({"context": "merged", "batch": "all", "target": "frontend",
                         "status": "passed", "constants": ["A.f"], "seconds": "0.020"})
        failed = [dict(a, batch="other", status="failed" if a["target"] == "Go" else a["status"])
                  for a in attempts]
        result = {"entries": {"E": {"full_export": {"runs": [{"attempts": attempts + failed}]}}}}
        timing = full_report.performance(result)
        self.assertEqual(timing["matched_successful_scopes"], 1)
        self.assertEqual(timing["languages"]["Go"]["all_failed_attempts"], 1)
        self.assertAlmostEqual(timing["shared_frontend_seconds"], 0.02)
        bad = copy.deepcopy(result)
        bad["entries"]["E"]["full_export"]["runs"][0]["attempts"][0]["constants"] = ["A.g"]
        with self.assertRaisesRegex(ValueError, "Mismatched"):
            full_report.performance(bad)

    def test_preview_keeps_all_entries_and_deduplicates_constant_references(self):
        # Empty and blocked entries still need rows. A candidate seen in two
        # theory scopes has one per-entry result, while global counts use full names.
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            base = project / "full"
            base.mkdir()
            data = {"order": ["E", "F"], "entries": {
                "E": {"theories": [{"path": "A.thy"}, {"path": "B.thy"}]},
                "F": {"theories": [{"path": "C.thy"}]}}}
            exports = {"E": {"A.thy": ["A.f"], "B.thy": ["A.f"]}, "F": {}}
            result = {"entries": {"E": {"scan": {"status": "passed", "theories": ["A.thy", "B.thy"]}},
                                  "F": {"scan": {"status": "blocked", "dependencies": ["E"]}}}}
            common.write_json(base / "exports.json", exports)
            common.write_json(base / "results.json", result)
            with patch.object(common, "PROJECT", project):
                summary = full_report.build_report(base, data, result, exports)
            self.assertEqual(summary["entry_count"], 2)
            self.assertEqual(summary["candidate_references"], 1)
            self.assertEqual(summary["distinct_candidates"], 1)
            self.assertFalse(summary["completion_verified"])
            with (base / "report/entries.csv").open() as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 2)
            with (base / "report/candidates.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["Go"], "pending")
            self.assertIn("本报告不是最终交付", (base / "report/README.md").read_text())

    def test_stage_coverage_is_independent_and_old_serializer_pass_does_not_count(self):
        # Stage-2 may compile a crate rejected by Stage-1. A later generator
        # change must invalidate that coverage until its actual outputs rebuild.
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            exports = {"E": {"A.thy": ["A.f", "A.g"]}}
            record = {"scan": {"status": "passed"}, "full_compile": {"crate/Cargo.toml": {
                "stage1_compile": {"status": "failed"}, "stage2_compile": {"status": "passed"}}}}
            record["full_export"] = {
                "status": "complete", "scope_sha256": full.scope_digest(exports["E"]),
                "scan_sha256": full.entry_scan_signature(record), "serializer_sha256": "new",
                "runs": [{"attempts": [{"target": "Rust", "status": "passed", "constants": ["A.f", "A.g"],
                                       "files": ["crate/Cargo.toml"]}]}]}
            result = {"entries": {"E": record}}
            with patch.object(full, "serializer_signature", return_value="new"):
                full.save(base, result, exports)
            self.assertEqual(result["coverage"]["distinct_stage1_compiled_candidates"], 0)
            self.assertEqual(result["coverage"]["distinct_stage2_compiled_candidates"], 2)
            with patch.object(full, "serializer_signature", return_value="changed"):
                full.save(base, result, exports)
            self.assertEqual(result["coverage"]["distinct_stage2_compiled_candidates"], 0)

    def test_physical_witness_must_match_language_and_failure_scope(self):
        # Matching counts and status strings are insufficient: Go cannot inherit
        # a Rust witness, and a failed multi-constant batch cannot condemn one member.
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            base = project / "full"
            work = base / "exports/E/S/attempt-0001"
            witness_dir = work / "attempts/merged/all"
            witness_dir.mkdir(parents=True)
            outcomes = {}
            for target in full.TARGETS:
                file = witness_dir / (target + ".xml")
                file.write_text('<attempt status="passed" target="' + target + '">'
                                '<constant name="A.f"/><library_only>true</library_only></attempt>')
                outcomes[target] = {"status": "passed", "evidence": [str(file.relative_to(project))]}
            scan = {"status": "passed", "theories": ["A.thy"]}
            record = {"scan": scan}
            exports = {"E": {"A.thy": ["A.f"]}}
            record["full_export"] = {
                "status": "complete", "scope_sha256": full.scope_digest(exports["E"]),
                "scan_sha256": full.entry_scan_signature(record), "serializer_sha256": "serializer",
                "candidates": {"A.f": outcomes}, "runs": []}
            result = {"entries": {"E": record}, "environment": {
                "proofs": "checked", "command_timeout_seconds": 0}}
            data = {"order": ["E"], "entries": {"E": {"theories": [{"path": "A.thy"}]}}}
            common.write_json(base / "exports.json", exports)
            common.write_json(base / "results.json", result)
            def audit():
                with patch.object(common, "PROJECT", project), \
                        patch.object(full, "serializer_signature", return_value="serializer"):
                    return full_audit.audit_data(base, data, result, exports)
            valid = audit()
            reason = "candidate has direct applicable witness"
            self.assertEqual(valid["issue_counts"].get(reason, 0), 0)
            original_go = outcomes["Go"]["evidence"]
            outcomes["Go"]["evidence"] = outcomes["Rust"]["evidence"]
            wrong_language = audit()
            self.assertEqual(wrong_language["issue_counts"][reason], 1)
            outcomes["Go"]["evidence"] = original_go
            (witness_dir / "Rust.xml").write_text(
                '<attempt status="failed" target="Rust" stage="target_preparation_or_serialization">'
                '<constant name="A.f"/><constant name="A.g"/><error>group failed</error></attempt>')
            outcomes["Rust"]["status"] = "failed"
            wrong_scope = audit()
            self.assertEqual(wrong_scope["issue_counts"][reason], 1)

    def test_failed_session_messages_are_bound_to_an_immutable_matching_database(self):
        # Session databases are mutable shared caches. A successful rebuild or a
        # database outside the failed command interval cannot witness that failure.
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            base = project / "full"
            heap = project / "global-heaps"
            database = heap / "ml/log/S.db"
            database.parent.mkdir(parents=True)
            with closing(sqlite3.connect(database)) as connection, connection:
                connection.execute(
                    "CREATE TABLE isabelle_session_info(session_name, return_code, uuid)")
                connection.execute("INSERT INTO isabelle_session_info VALUES ('S', 1, 'failed-build')")
            started = datetime.now(timezone.utc).isoformat()
            record = {"entries": {"E": {"scan": {"loading": [{
                "status": "failed", "failed_sessions": ["S"], "log": "load.log",
                "started": started, "seconds": 5}]}}}}
            args = SimpleNamespace(isabelle="isabelle")
            env = {"ISABELLE_HEAPS": str(heap), "ML_IDENTIFIER": "ml"}
            def capture(argv, log, arguments, snapshot_env):
                self.assertNotEqual(snapshot_env["ISABELLE_HEAPS"], str(heap))
                saved = Path(snapshot_env["ISABELLE_HEAPS"]) / "ml/log/S.db"
                self.assertEqual(full.file_digest(saved), full.file_digest(database))
                log.write_text("Full unfiltered error message")
                return {"status": "passed", "log": common.relative(log)}
            with patch.object(common, "PROJECT", project), patch.object(common, "command", side_effect=capture):
                index = full.archive_scan_messages(base, record, args, env)
                self.assertEqual(index["S"]["status"], "passed")
                original = project / index["S"]["database"]
                references = index["S"]["references"]
                checksum = full.file_digest(original)
                os.utime(database, (0, 0))
                self.assertFalse(full.session_database_origin(database, "S", references)["origin_verified"])
                with closing(sqlite3.connect(database)) as connection, connection:
                    connection.execute("UPDATE isabelle_session_info SET return_code = 0")
                index = full.archive_scan_messages(base, record, args, env)
                self.assertEqual(index["S"]["status"], "mismatched")
                self.assertEqual(full.file_digest(original), checksum)

    def test_prerequisite_outcome_blocks_checkpoint_and_has_failure_catalog_entry(self):
        # An auxiliary cache build is part of environment preparation. A pending
        # or failed process cannot be hidden behind successful candidate scans.
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            base = project / "full"
            auxiliary = base / "prerequisites/HOL-Analysis"
            auxiliary.mkdir(parents=True)
            common.write_json(auxiliary / "running.json", {"pid": -1})
            data = {"order": ["E"], "entries": {"E": {"theories": []}}}
            result = {"entries": {"E": {"scan": {"status": "passed", "theories": []}}}}
            exports = {"E": {}}
            common.write_json(base / "results.json", result)
            common.write_json(base / "exports.json", exports)
            with patch.object(common, "PROJECT", project):
                self.assertFalse(full.scan_checkpoint(base, data, result, exports)["passed"])
                (auxiliary / "build.log").write_text("out of memory")
                check = {"status": "memory_limit", "log": "full/prerequisites/HOL-Analysis/build.log"}
                common.write_json(auxiliary / "result.json", check)
                events = list(full_report.failure_events(base, data, result))
                self.assertEqual(events[0]["stage"], "prerequisite")
                self.assertEqual(collections.Counter(map(full_audit.failure_key, events)),
                                 full_audit.required_failure_inventory(base, data, result))
                # Repairing the current build must clear its gate without
                # dropping the complete earlier infrastructure failure.
                history = auxiliary / "history/attempt-0001"
                history.mkdir(parents=True)
                common.write_json(history / "result.json", check)
                common.write_json(auxiliary / "result.json", {"status": "passed"})
                self.assertTrue(full.scan_checkpoint(base, data, result, exports)["passed"])
                events = list(full_report.failure_events(base, data, result))
                self.assertEqual(len(events), 1)
                self.assertTrue(events[0]["historical"])
                self.assertEqual(collections.Counter(map(full_audit.failure_key, events)),
                                 full_audit.required_failure_inventory(base, data, result))
                self.assertEqual(full_report.category(
                    "java.lang.OutOfMemoryError: Java heap space")[0], "infrastructure")

    def test_report_audit_detects_wrong_compile_cell_and_omitted_failure(self):
        # Consistent totals do not prove catalog coverage: independently enumerate
        # raw failed commands, and compare every Rust crate cell to its record.
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            base = project / "full"
            base.mkdir()
            (base / "compile.log").write_text("error[E0308]: mismatched types")
            (base / "Go.xml").write_text(
                '<attempt status="failed"><error>No code equations for A.g</error></attempt>')
            (base / "process.log").write_text("finished")
            log = "full/compile.log"
            witness = "full/Go.xml"
            data = {"order": ["E"], "entries": {"E": {"theories": [{"path": "A.thy"}]}}}
            exports = {"E": {"A.thy": ["A.f"]}}
            outcomes = {t: {"status": "failed" if t == "Go" else "passed",
                            "evidence": [witness]} for t in full.TARGETS}
            manifest = "full/crate/Cargo.toml"
            record = {"scan": {"status": "passed", "theories": ["A.thy"]},
                      "full_export": {"languages": {t: v["status"] for t, v in outcomes.items()},
                                      "candidates": {"A.f": outcomes}, "runs": [{
                          "directory": "full/context", "command": {"status": "passed", "log": "full/process.log"},
                          "attempts": [
                              {"target": "Rust", "status": "passed", "constants": ["A.f"], "files": [manifest]},
                              {"target": "Go", "status": "failed", "stage": "target_preparation_or_serialization",
                               "constants": ["A.f"], "evidence": witness, "files": []}]}]},
                      "full_compile": {manifest: {
                          "stage2": "full/stage2-crate", "optimization": {"status": "passed", "log": log},
                          "stage1_compile": {"status": "passed", "checks": [{"status": "passed", "log": log}]},
                          "stage2_compile": {"status": "failed", "checks": [{"status": "failed", "log": log}]}}}}
            result = {"entries": {"E": record}}
            common.write_json(base / "results.json", result)
            common.write_json(base / "exports.json", exports)
            def audit():
                value = {"passed": True, "issues": [], "checks": {}, "issue_counts": {}}
                full_audit.audit_reports(base, data, result, exports, value)
                return value
            with patch.object(common, "PROJECT", project):
                full_report.build_report(base, data, result, exports, verified=True)
                self.assertTrue(audit()["passed"])
                path = base / "report/compilation.csv"
                with path.open() as stream:
                    rows = list(csv.DictReader(stream))
                rows[0]["stage2_compile"] = "passed"
                full_report.write_csv(path, list(rows[0]), rows)
                self.assertIn("compilation report matches crate evidence", audit()["issue_counts"])
                full_report.build_report(base, data, result, exports, verified=True)
                path = base / "report/failures.jsonl"
                events = [json.loads(line) for line in path.read_text().splitlines()]
                events = [value for value in events if value["phase"] != "export"]
                path.write_text("".join(json.dumps(value) + "\n" for value in events))
                summary = common.read_json(base / "report/summary.json")
                summary["failure_events"] = len(events)
                common.write_json(base / "report/summary.json", summary)
                failure = audit()
                self.assertIn("failure catalog covers every actual failed command and diagnostic",
                              failure["issue_counts"])

    def test_export_checkpoint_reads_infrastructure_error_beyond_excerpt(self):
        # A long serializer exception may mention an unavailable compiler after
        # the summary's 2000-character limit. The phase gate uses the full XML.
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            base = project / "full"
            base.mkdir()
            message = "diagnostic context " * 200 + "\ncommand not found: compiler"
            witness = base / "Go.xml"
            witness.write_text("<attempt><error>" + message + "</error></attempt>")
            exports = {"E": {"A.thy": ["A.f"]}}
            record = {"scan": {"status": "passed"}}
            record["full_export"] = {
                "status": "complete", "scope_sha256": full.scope_digest(exports["E"]),
                "scan_sha256": full.entry_scan_signature(record), "serializer_sha256": "current",
                "runs": [{"finished": True, "command": {"status": "passed"}, "attempts": [{
                    "status": "failed", "evidence": "full/Go.xml", "error": message[:2000]}]}]}
            with (patch.object(common, "PROJECT", project),
                  patch.object(full, "serializer_signature", return_value="current")):
                gate = full.export_checkpoint(base, {"order": ["E"]}, {"entries": {"E": record}}, exports)
            self.assertFalse(gate["passed"])
            self.assertEqual(gate["problems"][0]["reason"], "export infrastructure failure")


if __name__ == "__main__":
    unittest.main()

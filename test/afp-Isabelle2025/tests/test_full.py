#!/usr/bin/env python3
"""Coverage and checkpoint regressions for the exhaustive AFP experiment."""

import _paths  # Locate AFP tools independently of cwd and unittest discovery.
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import afp_common as common
import full


class ExhaustiveTests(unittest.TestCase):
    def test_aggregate_failure_requires_singleton_evidence(self):
        # Failure of a multi-constant export says nothing conclusive about an
        # individual member; all six cells remain unresolved until isolated.
        failure = {"constants": ["A.f", "A.g"], "target": "Rust", "status": "failed",
                   "stage": "target_preparation_or_serialization", "evidence": "group.xml",
                   "languages": [], "files": [], "error": "no equations"}
        outcomes = full.resolve_candidates(["A.f", "A.g"], [{"attempts": [failure]}])
        self.assertEqual(outcomes["A.f"]["Rust"]["status"], "blocked")
        self.assertEqual(outcomes["A.g"]["Rust"]["status"], "blocked")
        single = dict(failure, constants=["A.f"], evidence="singleton.xml")
        outcomes = full.resolve_candidates(["A.f", "A.g"], [{"attempts": [failure, single]}])
        self.assertEqual(outcomes["A.f"]["Rust"]["status"], "failed")
        self.assertEqual(outcomes["A.g"]["Rust"]["status"], "blocked")

    def test_frontend_failure_is_shared_and_success_in_another_context_wins(self):
        # A frontend failure applies to the languages actually requested for
        # that singleton. A successful branch is positive export evidence even
        # when another branch lacks the constant's executable dependencies.
        front = {"constants": ["A.f"], "target": "frontend", "status": "failed",
                 "stage": "frontend", "evidence": "front.xml", "languages": list(full.TARGETS),
                 "files": [], "error": "bad certificate"}
        passed = dict(front, target="Rust", status="passed", evidence="rust.xml")
        outcomes = full.resolve_candidates(["A.f"], [{"attempts": [front, passed, front]}])
        self.assertEqual(outcomes["A.f"]["Rust"]["status"], "passed")
        self.assertTrue(all(outcomes["A.f"][t]["status"] == "failed" for t in full.TARGETS if t != "Rust"))

    def test_partial_scan_can_export_loaded_core(self):
        # Failed example sessions must not erase a successfully loaded core.
        # A successful child already includes its parent heap and is sufficient.
        info = {"session_requirements": {"Core": [], "Child": ["Core"], "Example": ["Core"]}}
        scan = {"loading": [{"session": "Core", "status": "passed"},
                            {"session": "Child", "status": "passed"},
                            {"session": "Example", "status": "failed"}]}
        self.assertEqual(full.maximal_sessions(info, scan), ["Child"])

    def test_configured_unlimited_timeout_is_not_a_timeout_failure(self):
        # Every command line includes timeout=0. Only actual timeout diagnostics
        # may cause the infrastructure gate to reject a completed source failure.
        self.assertEqual(full.infrastructure("$ isabelle build -o timeout=0\n*** theorem failed"), [])
        self.assertIn("timeout", full.infrastructure("timeout\n$ isabelle build -o timeout=0"))
        self.assertIn("memory_or_stack", full.infrastructure("Warning - Unable to increase stack"))

    def test_attempt_directories_preserve_previous_partial_outputs(self):
        # Retries cannot overwrite full logs or already exported source files.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = full.next_attempt(root)
            (first / "keep.rs").write_text("source")
            second = full.next_attempt(root)
            self.assertNotEqual(first, second)
            self.assertEqual((first / "keep.rs").read_text(), "source")

    def test_stage2_is_attempted_after_stage1_compiler_error(self):
        # Ownership optimization can change compilability. Its result and the
        # Stage-2 compiler must therefore be recorded independently of Stage-1.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "source/Cargo.toml"
            manifest.parent.mkdir()
            manifest.write_text("[package]\n")
            record = {"full_export": {"runs": [{"attempts": [
                {"target": "Rust", "status": "passed", "files": ["source/Cargo.toml"]}]}]}}
            def optimize(argv, log, args, env):
                target = Path(argv[argv.index("--out-dir") + 1])
                target.mkdir(parents=True)
                (target / "Cargo.toml").write_text("[package]\n")
                return {"status": "passed", "log": "optimization.log"}
            with patch.object(common, "PROJECT", root), \
                    patch.object(full, "compile_crates", side_effect=[
                        {"status": "failed", "checks": [{"status": "failed", "returncode": 1}]},
                        {"status": "passed", "checks": [{"status": "passed", "returncode": 0}]}]) as compile_check, \
                    patch.object(common, "command", side_effect=optimize):
                full.compile_entry("E", record, root, SimpleNamespace(), {}, root / "cargo-opt")
            self.assertEqual(compile_check.call_count, 2)
            result = record["full_compile"]["source/Cargo.toml"]
            self.assertEqual(result["stage1_compile"]["status"], "failed")
            self.assertEqual(result["stage2_compile"]["status"], "passed")
            self.assertTrue(result["complete"])


if __name__ == "__main__":
    unittest.main()

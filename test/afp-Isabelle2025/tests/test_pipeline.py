#!/usr/bin/env python3
"""Regression checks for scope integrity, failure isolation and bounded execution.

These tests exercise the experiment tooling rather than Rust translation rules.
The native smoke command separately validates actual Isabelle/Cargo execution.
"""

import _paths  # Locate AFP tools independently of cwd and unittest discovery.

from contextlib import nullcontext, redirect_stdout
import io
import hashlib
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
import run
import scan
import full
import scan_frozen
import scan_store
from result_store import EntryStore


def compiled_record(names, status="passed"):
    """Current-format fixture: coverage must be derived from successful crate witnesses."""
    scope = {"A.thy": names}
    record = {"scan": {"status": "passed", "theories": ["A.thy"]}}
    record["full_export"] = {
        "scope_sha256": full.scope_digest(scope), "scan_sha256": full.entry_scan_signature(record),
        "serializer_sha256": "fixture", "status": "complete",
        "runs": [{"attempts": [{"target": "Rust", "status": "passed", "constants": names,
                                 "files": ["crate/Cargo.toml"]}]}]}
    record["full_compile"] = {"crate/Cargo.toml": {"stage1_compile": {"status": status}}}
    return record


class ScopeTests(unittest.TestCase):
    def test_symbolic_names_survive_outer_syntax_quoting(self):
        # Isabelle treats each \<...> as one symbol. Doubling its slash makes
        # export_code malformed; ordinary slash and quote characters escape.
        self.assertEqual(common.quote(r"Theory.f\<^sub>0"), r'"Theory.f\<^sub>0"')
        self.assertEqual(common.quote('a"b\\c'), '"a\\"b\\\\c"')

    def test_explicit_scope_is_deduplicated_and_empty_scope_is_safe(self):
        # A duplicate constant belongs to coverage once. An empty entry must
        # omit export_code rather than accidentally exporting every HOL constant.
        scope = {"A.thy": ["A.f", "A.f"], "B.thy": ["A.f", "B.g"]}
        self.assertEqual(common.candidates(scope), ["A.f", "B.g"])
        _, text = run.generated_theory("E", {"theories": []}, common.candidates(scope))
        self.assertEqual(text.count("export_code\n"), 1)
        self.assertEqual(text.count('"A.f"'), 1)
        _, empty = run.generated_theory("E", {"theories": []}, [])
        self.assertNotIn("export_code\n", empty)
        self.assertNotIn("export_code _", empty)

    def test_retry_includes_missing_requested_stage2(self):
        # A completed Stage-1 run still needs work when --stage2 is requested.
        args = SimpleNamespace(entries=None, retry_failed=True)
        data = {"order": ["A", "B", "C"], "entries": {"A": {}, "B": {}, "C": {}}}
        result = {"entries": {"A": {"status": "passed"},
                              "B": {"status": "passed", "stage2_compile": {"status": "passed"}},
                              "C": {"status": "no_candidates"}}}
        self.assertEqual(common.select(args, data, result, None, ["stage2_compile"]), ["A"])

    def test_root_generation_preserves_other_sessions_and_is_idempotent(self):
        # Regeneration must replace just its own block, preserve existing ROOT
        # content (including trailing sessions), and keep subdirectory imports.
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            here = project / "test/afp"
            here.mkdir(parents=True)
            root = project / "ROOT"
            root.write_text("session Existing = HOL +\n")
            data = {"entries": {"E": {"sessions": ["E"],
                                      "theories": [{"name": "E.Sub", "path": "sub/Sub.thy"}]}}}
            with patch.multiple(run, HERE=here, PROJECT=project), patch.object(common, "PROJECT", project):
                run.generate(data, {"E": {"sub/Sub.thy": ["Sub.f", "Sub.f"]}})
                root.write_text(root.read_text() + "session Trailing = HOL +\n")
                run.generate(data, {"E": {"sub/Sub.thy": ["Sub.f", "Sub.f"]}})
                first = root.read_text()
                run.generate(data, {"E": {"sub/Sub.thy": ["Sub.f", "Sub.f"]}})
                self.assertEqual(first, root.read_text())
                self.assertEqual(first.count('session "AFP-Rust-E"'), 1)
                self.assertIn("session Existing", first)
                self.assertIn("session Trailing", first)
                theory = (here / "E/E_Rust_Export.thy").read_text()
                self.assertIn('"E.Sub"', theory)
                self.assertEqual(theory.count('"Sub.f"'), 1)

    def test_export_imports_loaded_equation_contexts_and_explicit_candidates(self):
        # A conditional Haskell test which never loaded must not be imported
        # just because it appears in ROOT. A later equation-only theory must
        # remain imported even if it contributes no new constants of its own.
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            here = project / "test/afp"
            here.mkdir(parents=True)
            (project / "ROOT").write_text("session Existing = HOL +\n")
            info = {"sessions": ["E"], "theories": [
                {"name": "E.Origin", "path": "Origin.thy"},
                {"name": "E.Later", "path": "Later.thy"},
                {"name": "E.Haskell_Test", "path": "Haskell_Test.thy"}]}
            records = {"E": {"scan": {"theories": ["Origin.thy", "Later.thy"]}}}
            scope = {"E": {"Origin.thy": ["Origin.f"]}}
            with patch.multiple(run, HERE=here, PROJECT=project), patch.object(common, "PROJECT", project):
                run.generate({"entries": {"E": info}}, scope, records)
                text = (here / "E/E_Rust_Export.thy").read_text()
                self.assertIn('"E.Later"', text)
                self.assertNotIn('"E.Haskell_Test"', text)
                # An explicit new export scope may request a formerly skipped theory.
                scope["E"]["Haskell_Test.thy"] = ["Haskell_Test.f"]
                run.generate({"entries": {"E": info}}, scope, records)
                self.assertIn('"E.Haskell_Test"', (here / "E/E_Rust_Export.thy").read_text())

    def test_coverage_uses_full_names_and_counts_compilation_separately(self):
        # Shared full names count once; a failed crate contributes no compiled names.
        exports = {"A": {"A.thy": ["A.f", "A.f"]}, "B": {"A.thy": ["A.f", "B.f"]}}
        result = {"entries": {"A": compiled_record(["A.f", "A.f"]),
                              "B": compiled_record(["A.f", "B.f"], "failed")}}
        with patch.object(full, "serializer_signature", return_value="fixture"):
            coverage = full.coverage(result, exports)
        self.assertEqual(coverage["distinct_candidates"], 2)
        self.assertEqual(coverage["distinct_stage1_compiled_candidates"], 1)


class FailureTests(unittest.TestCase):
    def test_changed_scope_does_not_inherit_compiled_coverage(self):
        # New candidates cannot inherit a previous crate's successful coverage.
        result = {"entries": {"A": compiled_record(["A.f"]), "B": compiled_record(["B.f"])}}
        exports = {"A": {"A.thy": ["A.f", "A.g"]}, "B": {"A.thy": ["B.f"]}}
        with patch.object(full, "serializer_signature", return_value="fixture"):
            coverage = full.coverage(result, exports)
        self.assertEqual(coverage["distinct_candidates"], 3)
        self.assertEqual(coverage["distinct_stage1_compiled_candidates"], 1)

    def test_state_reload_derives_invalidated_compilation_coverage(self):
        # A saved success is never a saved coverage total. Reloading after a
        # scope change derives zero compiled coverage without another JSON report.
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            record = compiled_record(["A.f"])
            # An empty witness list avoids reading native XML in this store fixture.
            record["full_export"]["runs"] = []
            store = EntryStore(base, {"E": {"scan": record["scan"]}}, {"E": {"A.thy": ["A.f"]}})
            store["E"] = record; store.commit("E")
            scope = {"E": {"A.thy": ["A.f", "A.g"]}}
            loaded = EntryStore(base, {"E": {"scan": record["scan"]}}, scope)
            with patch.object(full, "serializer_signature", return_value="fixture"):
                coverage = full.coverage({"entries": loaded}, scope)
            self.assertEqual(coverage["distinct_candidates"], 2)
            self.assertEqual(coverage["distinct_stage1_compiled_candidates"], 0)
            self.assertFalse((base / "results.json").exists())
            self.assertFalse((base / "exports.json").exists())

    def test_loading_log_identifies_the_failed_parent(self):
        # A timeout during a shared HOL parent is not a failure of an AFP
        # theory that never started. Completed prerequisites stay usable.
        text = ("Building HOL-Analysis ...\n"
                "Finished HOL-Analysis (0:00:05 elapsed time)\n"
                "Building HOL-Probability ...\n")
        self.assertEqual(scan.failed_sessions_in_log(text, "timeout"), ["HOL-Probability"])
        self.assertEqual(scan.failed_sessions_in_log("HOL-Analysis FAILED (see log)", "failed"),
                         ["HOL-Analysis"])
        self.assertEqual(scan.failed_sessions_in_log(text, "passed"), [])

    def test_known_parent_failure_blocks_export_without_losing_scope(self):
        # Retained candidates from an incomplete scan must not cause every
        # dependent export to rebuild an already failing original AFP session.
        with tempfile.TemporaryDirectory() as temporary:
            here = Path(temporary)
            args = SimpleNamespace()
            record = {"scan": {"status": "failed", "theory_loading": {"status": "failed"}}}
            scope = {"A.thy": ["A.f"]}
            with patch.multiple(run, HERE=here, PROJECT=here), patch.object(common, "PROJECT", here), \
                    patch.object(run, "command") as execute:
                run.run_entry("E", {"theories": []}, scope, record, args, {})
            execute.assert_not_called()
            self.assertEqual(record["rust_export"]["status"], "blocked")
            self.assertEqual(scope["A.thy"], ["A.f"])

    def test_failed_import_preserves_command_diagnostics(self):
        # A joint import may fail before the generated export command runs.
        # Keep its command, exit status and error in the loading phase so the
        # committed report remains useful even without the local full log.
        with tempfile.TemporaryDirectory() as temporary:
            here = Path(temporary)
            args = SimpleNamespace(isabelle="isabelle", afp=here,
                                   timeout=180, skip_proofs=False)
            record = {"scan": {"status": "passed"}}
            failure = {"status": "failed", "returncode": 1, "seconds": 1.5,
                       "command": ["isabelle", "build"], "log": "export.log",
                       "error_excerpt": "Clash of specifications"}
            scope = {"A.thy": ["A.f"]}
            with patch.multiple(run, HERE=here, PROJECT=here), \
                    patch.object(common, "PROJECT", here), \
                    patch.object(run, "build_lock", nullcontext), \
                    patch.object(run, "command", return_value=failure):
                run.run_entry("E", {"theories": []}, scope, record, args, {})
            self.assertEqual(record["theory_loading"]["returncode"], 1)
            self.assertEqual(record["theory_loading"]["command"], failure["command"])
            self.assertEqual(record["theory_loading"]["error_excerpt"], failure["error_excerpt"])
            self.assertEqual(record["rust_export"]["status"], "blocked")
            self.assertEqual(record["stage1_compile"]["status"], "not_run")
            self.assertEqual(scope["A.thy"], ["A.f"])

    def test_dependent_session_is_not_rebuilt_after_parent_failure(self):
        # Multiple sessions in one entry can share a failed parent. Continue
        # other independent sessions, but do not retry that parent for its child.
        with tempfile.TemporaryDirectory() as temporary:
            here = Path(temporary)
            info = {"sessions": ["E", "E2"], "theories": [],
                    "session_requirements": {"E": [], "E2": ["E"]}}
            args = SimpleNamespace(isabelle="isabelle", afp=here, timeout=10, skip_proofs=False)
            def fail(argv, log, args, env):
                log.parent.mkdir(parents=True, exist_ok=True)
                log.write_text("Building E ...\nE FAILED (see log)\n")
                return {"status": "failed"}
            with patch.object(scan, "HERE", here), patch.object(scan, "build_lock", nullcontext), \
                    patch.object(scan, "command", side_effect=fail) as execute:
                result = scan.scan_entry("E", info, args, {}, {})
            self.assertEqual(execute.call_count, 1)
            self.assertEqual(result["loading"][1]["status"], "blocked")
            self.assertEqual(result["loading"][0]["failed_sessions"], ["E"])

    def test_failed_export_cannot_compile_stale_products(self):
        # A previous successful crate must be removed before an export attempt.
        # An export failure leaves compilation not_run and preserves the scope.
        with tempfile.TemporaryDirectory() as temporary:
            here = Path(temporary)
            old = here / "E/stage1/E_Rust_Export/export1"
            old.mkdir(parents=True)
            (old / "Cargo.toml").write_text("[package]\n")
            record = {"scan": {"status": "passed"}}
            args = SimpleNamespace(isabelle="isabelle", afp=here, timeout=10,
                                   skip_proofs=False, stage2=False, runtime_command=None)
            scope = {"A.thy": ["A.f"]}
            result = {"status": "failed", "log": "export.log"}
            with patch.multiple(run, HERE=here, PROJECT=here), patch.object(common, "PROJECT", here), \
                    patch.object(run, "build_lock", nullcontext), \
                    patch.object(run, "command", return_value=result) as execute:
                run.run_entry("E", {"theories": []}, scope, record, args, {})
                self.assertEqual(execute.call_count, 1)
                self.assertFalse(old.exists())
                self.assertEqual(record["stage1_compile"]["status"], "not_run")
                self.assertEqual(scope["A.thy"], ["A.f"])

    def test_cleanup_cannot_follow_a_stage_directory_symlink(self):
        # Even an in-workspace symlink must not redirect recursive artifact
        # cleanup into an unrelated source directory.
        with tempfile.TemporaryDirectory() as temporary:
            here = Path(temporary)
            source = here / "fixtures/E_Rust_Export"
            source.mkdir(parents=True)
            (source / "keep.thy").write_text("source")
            entry = here / "E"
            entry.mkdir()
            (entry / "stage1").symlink_to(here / "fixtures", target_is_directory=True)
            with patch.object(run, "HERE", here):
                with self.assertRaises(ValueError):
                    run.remove_generated(entry / "stage1/E_Rust_Export")
            self.assertTrue((source / "keep.thy").exists())

    def test_failed_scan_preserves_candidates(self):
        # A load error must never shrink a previously discovered export scope;
        # rerunning after an Isabelle/backend fix should retry those names.
        with tempfile.TemporaryDirectory() as temporary:
            here = Path(temporary)
            info = {"sessions": ["E"], "theories": [{"name": "E.A", "path": "A.thy",
                                                    "session": "E"}]}
            args = SimpleNamespace(isabelle="isabelle", afp=here, timeout=10, skip_proofs=False)
            exports = {"E": {"A.thy": ["A.f"]}}
            with patch.object(scan, "HERE", here), patch.object(scan, "build_lock", nullcontext), \
                    patch.object(scan, "command", return_value={"status": "failed"}):
                record = scan.scan_entry("E", info, args, {}, exports)
            self.assertEqual(record["status"], "failed")
            self.assertEqual(exports["E"]["A.thy"], ["A.f"])

    def test_multiple_sessions_contribute_equations_without_losing_candidates(self):
        # A later session can add equations for an earlier theory. Both scans
        # inspect every available entry theory and contribute a union; a retained
        # certificate error is diagnostic, not a missing theory or lost constant.
        with tempfile.TemporaryDirectory() as temporary:
            here = Path(temporary)
            info = {"sessions": ["E", "E2"],
                    "theories": [{"name": "E.A", "path": "A.thy", "session": "E"},
                                 {"name": "E2.B", "path": "B.thy", "session": "E2"}]}
            args = SimpleNamespace(isabelle="isabelle", afp=here, timeout=10, skip_proofs=False)
            exports = {"E": {"A.thy": ["A.stale"]}}
            def execute(argv, log, args, env):
                if argv[1] == "process":
                    names = Path(env["AFP_SCAN_THEORIES"]).read_text()
                    self.assertIn("E.A", names)
                    self.assertIn("E2.B", names)
                    later = argv[argv.index("-l") + 1] == "E2"
                    body = ('<theory name="E.A"><constant name="A.f"/>'
                            + ('<constant name="A.late"/><error name="A.late">certificate</error>'
                               if later else "") + '</theory>')
                    if later:
                        body += '<theory name="E2.B"><constant name="B.g"/></theory>'
                    Path(env["AFP_SCAN_OUTPUT"]).write_text("<scan>" + body + "</scan>")
                return {"status": "passed"}
            with patch.object(scan, "HERE", here), patch.object(common, "PROJECT", here), \
                    patch.object(scan, "build_lock", nullcontext), \
                    patch.object(scan, "command", side_effect=execute):
                record = scan.scan_entry("E", info, args, {}, exports)
            self.assertEqual(record["status"], "passed")
            self.assertEqual(exports["E"], {"A.thy": ["A.f", "A.late"], "B.thy": ["B.g"]})
            self.assertEqual(len(record["certificate_errors"]), 1)

    def test_failed_example_session_does_not_block_core_consumers(self):
        # A failed example session cannot erase the successfully loaded core
        # from the set of contexts available to downstream export requests.
        info = {"session_requirements": {"A": [], "A-Examples": ["A"], "B": ["A"]}}
        scanned = {"loading": [{"session": "A", "status": "passed"},
                              {"session": "A-Examples", "status": "failed"},
                              {"session": "B", "status": "passed"}]}
        self.assertEqual(full.maximal_sessions(info, scanned), ["B"])

    def test_changed_scan_invalidates_previous_compilation_coverage(self):
        # Current compilation evidence binds its scanned context. Changed theory
        # coverage must invalidate it even when constant names stay identical.
        record = compiled_record(["A.f"])
        record["scan"]["theories"].append("Later.thy")
        with patch.object(full, "serializer_signature", return_value="fixture"):
            coverage = full.coverage({"entries": {"E": record}}, {"E": {"A.thy": ["A.f"]}})
        self.assertEqual(coverage["distinct_stage1_compiled_candidates"], 0)

    def test_explicit_scan_retries_past_failed_prerequisites(self):
        # --retry-failed replaces a failed parent before scheduling its child.
        # The child's dependency decision must read the parent's current receipt.
        from test_scan_frozen import completed_fixture
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            info = {"sessions": ["A", "B"], "session_requirements": {"A": [], "B": ["A"]},
                    "theories": [{"name": "E.A", "path": "A.thy", "session": "A"}]}
            data = {"order": ["E"], "entries": {"E": info}}
            units = {s: scan_store.unit_input("E", s, info, {}) for s in info["sessions"]}
            store = scan_store.Store(base)
            store.commit(store.next_attempt(units["A"]), {"schema": 1, "unit": units["A"],
                "unit_id": scan_store.digest(units["A"]), "status": "unresolved_infrastructure",
                "build": {"status": "failed"}, "failed_sessions": ["A"], "evidence": {}})
            calls = []
            def execute(store, unit, *args):
                calls.append(unit["session"])
                store, attempt, receipt = completed_fixture(base, unit)
                return store.commit(attempt, receipt)
            with patch.object(sys, "argv", ["scan_frozen.py", "--output-dir", str(base), "--retry-failed"]), \
                 patch.object(common, "environment", return_value=({}, {})), \
                 patch.object(scan_frozen, "validate_contract", return_value=({}, data, units)), \
                 patch.object(scan_frozen, "run_unit", side_effect=execute), redirect_stdout(io.StringIO()):
                self.assertEqual(scan_frozen.main(), 0)
            self.assertEqual(calls, ["A", "B"])

    def test_one_entry_exception_does_not_stop_other_entries(self):
        # A filesystem/tool exception becomes the current failed unit receipt;
        # a later independent unit remains runnable and can commit successfully.
        from test_scan_frozen import fixture_unit, fixture_xml
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); store = scan_store.Store(base)
            args = SimpleNamespace(isabelle="isabelle", afp=base, timeout=0, skip_proofs=False)
            units = [fixture_unit("A"), fixture_unit("B")]
            def build(argv, log, args, env):
                if argv[-1] == "A":
                    raise OSError("controlled failure")
                log.write_text("finished")
                return {"status": "passed", "returncode": 0, "log": str(log)}
            def inspect(session, args, env, log, **kwargs):
                Path(env["AFP_SCAN_OUTPUT"]).write_text(fixture_xml(units[1]))
                log.write_text("finished")
                return {"status": "passed", "returncode": 0, "log": str(log)}
            with patch.object(common, "command", side_effect=build), \
                 patch.object(common, "build_lock", nullcontext), patch.object(scan, "inspect_session", side_effect=inspect):
                receipts = [scan_frozen.run_unit(store, unit, args, {}, {}, {}) for unit in units]
            self.assertEqual([r["status"] for r in receipts], ["unresolved_infrastructure", "complete"])
            self.assertEqual(len(store.state.keys("receipt/")), 2)


class ExecutionTests(unittest.TestCase):
    def test_zero_timeout_allows_process_and_isabelle_session_to_finish(self):
        # An unlimited scan must survive longer than zero seconds in both the
        # Python watchdog and the generated Isabelle build options.
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            args = SimpleNamespace(timeout=0, min_available_mb=0, skip_proofs=False)
            with patch.object(common, "PROJECT", project):
                result = common.command(
                    [sys.executable, "-c", "import time; time.sleep(0.7); print('finished')"],
                    project / "unlimited.log", args, os.environ.copy())
            self.assertEqual(result["status"], "passed")
            self.assertIn("finished", (project / "unlimited.log").read_text())
            self.assertIn("timeout=0", common.build_options(args))


    @unittest.skipUnless(Path("/proc/meminfo").exists(), "Linux process cleanup regression")
    def test_timeout_also_stops_detached_children(self):
        # Isabelle's bash_process can create a separate process session.
        # Killing only the Java group would leave Poly/ML consuming RAM. The
        # child ignores SIGTERM, so forced cleanup must follow reparenting too.
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            pidfile = project / "child.pid"
            code = ("import subprocess,sys,time; "
                    "p=subprocess.Popen([sys.executable,'-c',"
                    "'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'],"
                    "start_new_session=True); "
                    f"open({str(pidfile)!r},'w').write(str(p.pid)); time.sleep(60)")
            args = SimpleNamespace(timeout=0.2, min_available_mb=0)
            with patch.object(common, "PROJECT", project):
                result = common.command([sys.executable, "-c", code], project / "timeout.log",
                                        args, os.environ.copy())
            self.assertEqual(result["status"], "timeout")
            child = int(pidfile.read_text())
            state = Path(f"/proc/{child}/stat")
            deadline = time.monotonic() + 1
            while state.exists():
                status = state.read_text().rsplit(")", 1)[1].split()[0]
                if status == "Z":
                    break
                if time.monotonic() > deadline:
                    self.fail("Detached child survived forced timeout cleanup")
                time.sleep(0.01)


if __name__ == "__main__":
    unittest.main()

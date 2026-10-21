#!/usr/bin/env python3
"""Regression checks for scope integrity, failure isolation and bounded execution.

These tests exercise the experiment tooling rather than Rust translation rules.
Real Isabelle/Cargo smoke builds are documented separately in results.json.
"""

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
        # Imported/shared names do not inflate coverage. A failed crate may
        # retain candidates, but must not increase successful compilation counts.
        result = {"entries": {"A": {"stage1_compile": {"status": "passed"}},
                              "B": {"stage1_compile": {"status": "failed"}}}}
        exports = {"A": {"A.thy": ["A.f", "A.f"]}, "B": {"B.thy": ["A.f", "B.f"]}}
        with tempfile.TemporaryDirectory() as temporary, patch.object(common, "HERE", Path(temporary)):
            common.save_results(result, exports)
            self.assertEqual(result["coverage"]["distinct_candidates"], 2)
            self.assertEqual(result["coverage"]["distinct_stage1_compiled_candidates"], 1)


class FailureTests(unittest.TestCase):
    def test_changed_scope_does_not_inherit_compiled_coverage(self):
        # Editing exports.json for an entry outside the selected batch leaves
        # its old successful phase record intact. New names were never compiled
        # and must not count until a build of the updated scope succeeds.
        result = {"entries": {
            "A": {"stage1_compile": {"status": "passed"},
                  "scope_sha256": hashlib.sha256(b"A.f").hexdigest()},
            "B": {"stage1_compile": {"status": "passed"},
                  "scope_sha256": hashlib.sha256(b"B.f").hexdigest()}}}
        exports = {"A": {"A.thy": ["A.f", "A.g"]}, "B": {"B.thy": ["B.f"]}}
        with tempfile.TemporaryDirectory() as temporary, patch.object(common, "HERE", Path(temporary)):
            common.save_results(result, exports)
        self.assertEqual(result["coverage"]["distinct_candidates"], 3)
        self.assertEqual(result["coverage"]["distinct_stage1_compiled_candidates"], 1)

    def test_generate_only_persists_invalidated_compilation_coverage(self):
        # Regenerating theories after editing exports.json must also checkpoint
        # the stale build status. Otherwise results.json still presents the old
        # crate as a pass even though no build covers the expanded export scope.
        with tempfile.TemporaryDirectory() as temporary:
            here = Path(temporary)
            data = {"entries": {"E": {"theories": []}}, "order": ["E"]}
            exports = {"E": {"A.thy": ["A.f", "A.g"]}}
            result = {"entries": {"E": {
                "status": "passed", "stage1_compile": {"status": "passed"},
                "scope_sha256": hashlib.sha256(b"A.f").hexdigest()}}}
            with patch.object(sys, "argv", ["run.py", "--generate-only"]), \
                    patch.object(run, "environment", return_value=({}, {})), \
                    patch.object(run, "manifest", return_value=data), \
                    patch.object(run, "read_json", return_value=exports), \
                    patch.object(run, "load_results", return_value=result), \
                    patch.object(run, "generate"), patch.object(run, "build_lock", nullcontext), \
                    patch.object(common, "HERE", here), redirect_stdout(io.StringIO()):
                self.assertEqual(run.main(), 0)
            report = here / "results.json"
            self.assertTrue(report.is_file(), "Generation must checkpoint scope invalidation")
            saved = json.loads(report.read_text())
            self.assertEqual(saved["entries"]["E"]["status"], "stale")
            self.assertEqual(saved["coverage"]["distinct_candidates"], 2)
            self.assertEqual(saved["coverage"]["distinct_stage1_compiled_candidates"], 0)

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
        # Collections/Containers-style entries also contain example sessions.
        # Their examples can fail after the core heap succeeds. A downstream
        # entry which imports only that core must still be scanned normally.
        data = {"entries": {
            "A": {"dependencies": [], "source_errors": [], "theories": [],
                  "required_sessions": ["A", "A-Examples"]},
            "B": {"dependencies": ["A"], "source_errors": [], "theories": [],
                  "required_sessions": ["A", "B"]}}, "order": ["A", "B"]}
        result = {"entries": {"A": {}, "B": {}}}
        failed = {"status": "failed", "theory_loading": {"status": "failed"},
                  "loading": [{"session": "A", "status": "passed"},
                              {"session": "A-Examples", "status": "failed",
                               "failed_sessions": ["A-Examples"]}]}
        passed = {"status": "passed", "theory_loading": {"status": "passed"}}
        with patch.object(sys, "argv", ["scan.py"]), \
                patch.object(scan, "environment", return_value=({}, {})), \
                patch.object(scan, "manifest", return_value=data), \
                patch.object(scan, "read_json", return_value={}), \
                patch.object(scan, "load_results", return_value=result), \
                patch.object(scan, "scan_entry", side_effect=[failed, passed]) as execute, \
                patch.object(scan, "write_json"), patch.object(scan, "save_results"), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(scan.main(), 1)
        self.assertEqual(execute.call_count, 2)
        self.assertEqual(result["entries"]["B"]["scan"]["status"], "passed")

    def test_rescan_invalidates_previous_runtime_validation(self):
        # Runtime assertions describe a particular generated crate. Discovering
        # another executable constant changes that crate's scope, so its earlier
        # semantic check must remain diagnostic history rather than a current pass.
        data = {"entries": {"E": {"dependencies": [], "source_errors": [],
                                   "theories": []}}, "order": ["E"]}
        exports = {"E": {"A.thy": ["A.f"]}}
        result = {"entries": {"E": {
            "status": "passed", "stage1_compile": {"status": "passed"},
            "runtime_validation": {"status": "passed", "assertions": 4}}}}
        def discover(entry, info, args, env, scope):
            scope[entry]["A.thy"] = ["A.f", "A.g"]
            return {"status": "passed", "theory_loading": {"status": "passed"}}
        with patch.object(sys, "argv", ["scan.py"]), \
                patch.object(scan, "environment", return_value=({}, {})), \
                patch.object(scan, "manifest", return_value=data), \
                patch.object(scan, "read_json", return_value=exports), \
                patch.object(scan, "load_results", return_value=result), \
                patch.object(scan, "scan_entry", side_effect=discover), \
                patch.object(scan, "write_json"), patch.object(scan, "save_results"), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(scan.main(), 0)
        record = result["entries"]["E"]
        self.assertEqual(record["candidate_count"], 2)
        self.assertEqual(record["stage1_compile"]["status"], "stale")
        self.assertEqual(record["runtime_validation"], {"status": "stale", "assertions": 4})

    def test_explicit_scan_retries_past_failed_prerequisites(self):
        # Selecting a dependent entry after fixing its environment must let
        # Isabelle rebuild prerequisites. Only failures observed in this batch
        # may block it; an old report is not proof that the dependency still fails.
        data = {"entries": {"A": {}, "B": {"dependencies": ["A"], "source_errors": [],
                                         "theories": []}}, "order": ["A", "B"]}
        result = {"entries": {"A": {"scan": {"theory_loading": {"status": "failed"}}},
                              "B": {"status": "pending"}}}
        done = {"status": "passed", "theory_loading": {"status": "passed"}}
        with patch.object(sys, "argv", ["scan.py", "--entries", "B"]), \
                patch.object(scan, "environment", return_value=({}, {})), \
                patch.object(scan, "manifest", return_value=data), \
                patch.object(scan, "read_json", return_value={}), \
                patch.object(scan, "load_results", return_value=result), \
                patch.object(scan, "scan_entry", return_value=done) as execute, \
                patch.object(scan, "write_json"), patch.object(scan, "save_results"), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(scan.main(), 0)
        execute.assert_called_once()

    def test_one_entry_exception_does_not_stop_other_entries(self):
        # Independent entries must still run after one filesystem/tool failure;
        # checkpoint saving occurs after each attempt and the batch fails overall.
        data = {"entries": {"A": {}, "B": {}}, "order": ["A", "B"]}
        result = {"entries": {"A": {}, "B": {}}}
        visited = []
        def attempt(entry, *args):
            visited.append(entry)
            if entry == "A":
                raise OSError("controlled failure")
            args[2]["status"] = "passed"
        with patch.object(sys, "argv", ["run.py", "--entries", "A", "B"]), \
                patch.object(run, "environment", return_value=({}, {})), \
                patch.object(run, "manifest", return_value=data), \
                patch.object(run, "read_json", return_value={"A": {}, "B": {}}), \
                patch.object(run, "load_results", return_value=result), \
                patch.object(run, "generate"), patch.object(run, "build_lock", nullcontext), \
                patch.object(run, "run_entry", side_effect=attempt), \
                patch.object(run, "save_results") as save, redirect_stdout(io.StringIO()):
            self.assertEqual(run.main(), 1)
        self.assertEqual(visited, ["A", "B"])
        self.assertEqual(save.call_count, 2)


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

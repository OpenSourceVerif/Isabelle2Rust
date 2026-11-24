#!/usr/bin/env python3
"""Fresh setup, relocation and destructive-cleanup boundaries."""
import _paths
from contextlib import ExitStack
import fcntl
import json
import importlib.util
import io
import tarfile
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import afp_common as common
import clean
from state import State
import full
import scan_store as ss
from test_scan_frozen import completed_fixture, fixture_unit


class SetupTests(unittest.TestCase):
    def test_tools_launch_after_repository_relocation_from_an_unrelated_cwd(self):
        # Resource lookup must follow the copied tools, not the caller's cwd
        # or the former repository's fixed number of parent directories.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'another repository'
            (root / 'translate').mkdir(parents=True)
            (root / 'ROOT').write_text('session Dummy = HOL +\n')
            tools = root / 'test/afp-Isabelle2025/tools'
            shutil.copytree(common.HERE, tools, ignore=shutil.ignore_patterns('__pycache__'))
            result = subprocess.run([sys.executable, '-B', str(tools / 'afp.py'), '--help'],
                                    cwd=Path(temporary), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('export-checkpoint', result.stdout)

    def test_install_plan_accepts_spaces_and_has_no_filesystem_side_effects(self):
        # The complete installation preview must show checksummed downloads,
        # the pinned sibling and all build/setup stages without invoking sudo.
        with tempfile.TemporaryDirectory() as temporary:
            prefix = Path(temporary) / 'fresh install root'
            config = Path(temporary) / 'local config.json'
            command = [sys.executable, '-B', str(common.EXPERIMENT / 'setup/install.py'),
                       '--prefix', str(prefix), '--config', str(config), '--dry-run']
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(result.stdout)
            self.assertEqual(plan['prefix'], str(prefix))
            self.assertTrue(all(len(x['sha256']) == 64 for x in plan['downloads'].values()))
            self.assertEqual(plan['rust']['version'], '1.94.0')
            self.assertEqual(plan['config']['user_home'], str(prefix / 'user'))
            self.assertFalse(prefix.exists())
            self.assertFalse(config.exists())

    def test_installer_rejects_archive_traversal_through_an_earlier_link(self):
        # A lexical path inside staging can escape after an earlier symlink
        # is created. The installer must reject it before writing outside.
        spec = importlib.util.spec_from_file_location('afp_install_test', common.EXPERIMENT / 'setup/install.py')
        installer = importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); stage = root / 'stage'; stage.mkdir()
            archive = root / 'malicious.tar'
            with tarfile.open(archive, 'w') as stream:
                link = tarfile.TarInfo('a'); link.type = tarfile.SYMTYPE; link.linkname = '.'; stream.addfile(link)
                item = tarfile.TarInfo('a/../escaped'); item.size = 7; stream.addfile(item, io.BytesIO(b'outside'))
            with self.assertRaises(ValueError):
                installer.extract(archive, stage)
            self.assertFalse((root / 'escaped').exists())

    def test_paths_follow_current_repository_and_installations(self):
        # Fresh runs resolve their own paths without rewriting old-machine names.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(common, "PROJECT", root):
                self.assertEqual(common.resolve_path("translate/Rust.thy"), root / "translate/Rust.thy")
                self.assertEqual(common.resolve_path(root / "external/A.thy"), root / "external/A.thy")

    def test_fresh_configuration_has_one_file_and_no_scan_dependency(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); config = root / "config.json"
            run = subprocess.run([sys.executable, "-B", str(common.EXPERIMENT / "setup/install.py"),
                                  "--prefix", str(root / "deps"), "--configure-only", "--config", str(config)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            value = json.loads(config.read_text())
            self.assertIn("compilers", value)
            self.assertNotIn("compiler_settings", value)
            self.assertEqual(list(root.iterdir()), [config])

    def test_nonempty_initialization_preserves_existing_files(self):
        import scan_frozen
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root / "sentinel").write_text("keep")
            with self.assertRaisesRegex(ValueError, "empty"):
                scan_frozen.initialize(root, None, {}, {})
            self.assertEqual((root / "sentinel").read_text(), "keep")


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.experiment = self.root / "afp"
        self.work = self.experiment / "work"
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(common, "EXPERIMENT", self.experiment))
        self.stack.enter_context(patch.object(common, "PROJECT", self.root))
        self.state = State(self.work); self.state.put("run", {"schema": 1})
        for name in ("scan/proof", "report/case", "tools/code", "work/_build/cache", "work/logs/failure.log", "work/exports/E/receipt.xml"):
            path = self.experiment / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(name)

    def test_preview_and_cache_cleanup_preserve_current_evidence(self):
        self.assertTrue(clean.clean(self.work)["preview"])
        self.assertTrue((self.work / "_build/cache").exists())
        clean.clean(self.work, apply=True)
        self.assertFalse((self.work / "_build").exists())
        for name in ("scan/proof", "report/case", "work/logs/failure.log", "work/exports/E/receipt.xml"):
            self.assertTrue((self.experiment / name).exists())
        self.assertIsNotNone(self.state.get("run"))

    def test_protected_roots_ancestors_and_symlink_aliases_are_refused(self):
        for base in (self.root, self.experiment, self.experiment / "tools", self.experiment / "setup"):
            with self.subTest(base=base), self.assertRaises(ValueError):
                clean.targets(base, "export")
        shutil.rmtree(self.work / "_build")
        (self.work / "_build").symlink_to(self.experiment / "scan", target_is_directory=True)
        with self.assertRaises(ValueError):
            clean.clean(self.work, apply=True)
        self.assertTrue((self.experiment / "scan/proof").exists())

    def test_active_phase_lock_refuses_cleanup(self):
        directory = self.experiment / "setup"; directory.mkdir(exist_ok=True)
        with (directory / "batch.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, "running"):
                clean.clean(self.work, apply=True)
        self.assertTrue((self.work / "_build/cache").exists())

    def test_compile_and_export_resets_invalidate_only_selected_downstream_results(self):
        self.state.update({"entry/E": {"full_export": {"status": "complete"}, "full_compile": {"crate": {"complete": True}}},
                           "scan-checkpoint.json": {"passed": True}, "export-checkpoint.json": {"passed": True},
                           "audit.json": {"passed": True}})
        clean.clean(self.work, reset="compile", apply=True)
        self.assertNotIn("full_compile", self.state.get("entry/E"))
        self.assertEqual(self.state.get("entry/E")["full_export"]["status"], "complete")
        self.assertIsNone(self.state.get("audit.json"))
        self.assertIsNotNone(self.state.get("export-checkpoint.json"))
        clean.clean(self.work, reset="export", apply=True)
        self.assertEqual(self.state.get("entry/E"), {})
        self.assertIsNone(self.state.get("export-checkpoint.json"))
        self.assertTrue(self.state.get("scan-checkpoint.json")["passed"])



class WorkflowTests(unittest.TestCase):
    def test_run_stops_before_export_when_scan_fails(self):
        # The one-command workflow must stop at the failed boundary instead of
        # continuing to exports with a partially scanned catalogue.
        import afp
        with tempfile.TemporaryDirectory() as temporary, patch.object(afp, "call", side_effect=[0, 0, 1]) as call:
            self.assertEqual(afp.main(["--work", temporary, "run"]), 1)
            self.assertEqual([c.args[1][-1] for c in call.call_args_list], ["check", "init", "scan"])

    def test_run_resumes_existing_database_and_finishes_with_report_audit(self):
        # A second invocation never reinitializes the current database and its
        # retry request affects scanning only; final validation checks the report.
        import afp
        from state import State
        with tempfile.TemporaryDirectory() as temporary, patch.object(afp, "call", return_value=0) as call:
            State(temporary)
            self.assertEqual(afp.main(["--work", temporary, "run", "--retry-failed"]), 0)
            commands = [c.args[1] for c in call.call_args_list]
            self.assertFalse(any("init" in c for c in commands))
            self.assertTrue(any(c[-2:] == ["scan", "--retry-failed"] for c in commands))
            self.assertEqual(commands[-1][-2:], ["audit", "--with-report"])

if __name__ == "__main__":
    unittest.main()

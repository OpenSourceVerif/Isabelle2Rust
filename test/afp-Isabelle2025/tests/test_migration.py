#!/usr/bin/env python3
"""Portability, immutable frozen handoff and destructive-cleanup boundaries."""
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
import frozen
import full
import scan_store as ss
from test_scan_frozen import completed_fixture, fixture_unit
import test_current_candidates as candidates_fixture


class MigrationTests(unittest.TestCase):
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

    def test_different_installation_roots_resolve_historical_sources(self):
        # Frozen historical source paths remain byte-identical while runtime
        # resolution selects the explicitly configured AFP/Isabelle roots.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cfg = {'repository': str(root), 'afp': str(root / 'dependencies/AFP'),
                   'isabelle': str(root / 'dependencies/Isabelle2025/bin/isabelle')}
            with patch.object(common, 'PROJECT', root), patch.object(common, 'CONFIG', cfg):
                old = '/home/spring/Isabelle2Rust/Isabelle2Rust/temp/afp-Isabelle2025/thys/A/A.thy'
                self.assertEqual(common.resolve_path(old), root / 'dependencies/AFP/thys/A/A.thy')
                self.assertEqual(common.resolve_path('/home/spring/Isabelle/Isabelle2025/src/Pure/code.ML'),
                                 root / 'dependencies/Isabelle2025/src/Pure/code.ML')

    def test_moved_receipts_and_joint_snapshot_validate_and_handoff_without_rescan(self):
        # The fixture commits real catalogue XML and receipts under the old
        # prefix, then moves the whole scan. Validation and handoff must use
        # its original logs and preserve the false upstream scan checkpoint.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            experiment = root / 'test/afp-Isabelle2025'
            old = experiment / 'full/scan-frozen-2026-10-22'
            with patch.object(common, 'PROJECT', root), patch.object(common, 'EXPERIMENT', experiment):
                unit = fixture_unit()
                store, attempt, receipt = completed_fixture(old, unit)
                # Before the move, the historical scanner used direct project
                # paths. Restore that reader only while constructing old facts.
                legacy_reader = patch.object(common, 'resolve_path', side_effect=lambda p: (root / p).resolve())
                legacy_reader.start()
                self.addCleanup(legacy_reader.stop)
                store.commit(attempt, receipt)
                info = {'sessions': ['E'], 'theories': unit['theories'], 'dependencies': []}
                data = {'order': ['E'], 'entries': {'E': info}}
                units = {'E': unit}
                result, exports = ss.aggregate(store, data, units, {'afp_root': str(root / 'afp'), 'proofs': 'checked'})
                ss.publish(store, result, exports)
                for name, value in [('manifest.json', data), ('units.json', units),
                                    ('source-inputs.json', {'afp': {}}), ('scan-checkpoint.json', {'passed': False})]:
                    common.write_json(old / name, value)
                inventory = root / 'inventory.jsonl'
                inventory.write_text(''.join(json.dumps({'path': str(p.relative_to(old)),
                    'sha256': full.file_digest(p), 'bytes': p.stat().st_size}) + '\n'
                    for p in sorted(old.rglob('*')) if p.is_file()))
                moved = experiment / 'scan'
                old.rename(moved)
                legacy_reader.stop()
                before = {p.relative_to(moved): p.read_bytes() for p in moved.rglob('*') if p.is_file()}
                checked = frozen.verify(moved, inventory)
                self.assertTrue(checked['passed'])
                downstream = experiment / 'work'
                with patch('scan.scan_entry', side_effect=AssertionError('No rescan permitted')):
                    contract = full.initialize_candidates(downstream, moved)
                self.assertFalse(contract['scan_complete'])
                self.assertFalse((downstream / 'scan-checkpoint.json').exists())
                _, actual, scope = full.load(downstream)
                self.assertEqual(actual['entries'], result['entries'])
                self.assertEqual(scope, exports)
                full.require_scan_gate(downstream, actual, scope)
                self.assertEqual(before, {p.relative_to(moved): p.read_bytes() for p in moved.rglob('*') if p.is_file()})
                with self.assertRaises(ValueError):
                    full.initialize_candidates(downstream, moved)

    def test_nonempty_initialization_preserves_existing_files(self):
        # A stray old export or partial setup may never be adopted implicitly.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, base, _, _ = candidates_fixture.CurrentCandidateTests().fixture(root)
            base.mkdir(); (base / 'old-export.rs').write_text('retained sentinel')
            with self.assertRaisesRegex(ValueError, 'empty'):
                full.initialize_candidates(base, source)
            self.assertEqual((base / 'old-export.rs').read_text(), 'retained sentinel')
            self.assertFalse((base / 'results.json').exists())


class CleanupTests(unittest.TestCase):
    def setUp(self):
        # Shared retained roots are sentinels outside the owned work tree.
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.experiment = self.root / 'afp'
        self.work = self.experiment / 'work'
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(common, 'EXPERIMENT', self.experiment))
        self.stack.enter_context(patch.object(common, 'PROJECT', self.root))
        for name in ('scan/proof', 'report/case', 'tools/code', 'work/_build/cache',
                     'work/logs/failure.log', 'work/exports/E/receipt.xml'):
            p = self.experiment / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(name)
        common.write_json(self.work / 'afp-work.json', {'kind': 'afp-work-v1'})

    def test_preview_and_cache_cleanup_preserve_receipts_logs_scan_and_report(self):
        # Default cleanup removes only regenerable caches after an explicit
        # apply; durable failure logs and export receipts survive both passes.
        preview = clean.clean(self.work)
        self.assertTrue(preview['preview'])
        self.assertTrue((self.work / '_build/cache').is_file())
        clean.clean(self.work, apply=True)
        self.assertFalse((self.work / '_build').exists())
        for name in ('scan/proof', 'report/case', 'work/logs/failure.log', 'work/exports/E/receipt.xml'):
            self.assertTrue((self.experiment / name).is_file(), name)
        self.assertEqual(clean.clean(self.work)['paths'], [])

    def test_protected_roots_ancestors_and_symlink_aliases_are_refused(self):
        # Even an explicit reset cannot select scan/report, their ancestor, or
        # a cache symlink pointing into a retained tree.
        for root in (self.experiment, self.experiment / 'scan', self.experiment / 'report'):
            with self.subTest(root=root), self.assertRaises(ValueError):
                clean.targets(root, 'export')
        shutil.rmtree(self.work / '_build')
        (self.work / '_build').symlink_to(self.experiment / 'scan', target_is_directory=True)
        with self.assertRaises(ValueError):
            clean.clean(self.work, apply=True)
        self.assertTrue((self.experiment / 'scan/proof').is_file())
        shared = self.root.parent / 'RustLightAST'
        with self.assertRaises(ValueError):
            clean.validate_root(shared / 'accidental-work')

    def test_active_phase_lock_refuses_cleanup(self):
        # A real flock held by a writer must prevent even cache deletion.
        directory = self.experiment / 'setup'; directory.mkdir(exist_ok=True)
        with (directory / 'batch.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, 'running'):
                clean.clean(self.work, apply=True)
        self.assertTrue((self.work / '_build/cache').is_file())

    def test_explicit_compile_reset_does_not_reset_exports(self):
        # Compilation reset must invalidate stale phase results, retain export
        # witnesses, and leave the original scan boundary intact.
        fixture_root = self.root / 'fixture'
        source, base, _, _ = candidates_fixture.CurrentCandidateTests().fixture(fixture_root)
        full.initialize_candidates(base, source)
        common.write_json(base / 'afp-work.json', {'kind': 'afp-work-v1'})
        _, state, _ = full.load(base)
        state['entries']['A']['full_export'] = {'status': 'complete'}
        state['entries']['A']['full_compile'] = {'old': {'complete': True}}
        common.write_json(base / 'results.json', state)
        with patch.object(full, 'serializer_signature', return_value='fixture'):
            clean.clean(base, reset='compile', apply=True)
        _, changed, _ = full.load(base)
        self.assertNotIn('full_compile', changed['entries']['A'])
        self.assertEqual(changed['entries']['A']['full_export'], {'status': 'complete'})
        self.assertTrue((base / 'candidate-baseline.json').is_file())
        # An export reset also invalidates compilation, while keeping the
        # candidate scope and inherited scan boundary available for a new run.
        with patch.object(full, 'serializer_signature', return_value='fixture'):
            clean.clean(base, reset='export', apply=True)
        _, reset, scope = full.load(base)
        self.assertNotIn('full_export', reset['entries']['A'])
        self.assertEqual(scope['A'], {'A.thy': ['A.f']})
        self.assertTrue((base / 'baseline/snapshot.json').is_file())


if __name__ == '__main__':
    unittest.main()

"""Request recovery regressions using synthetic files; no native program runs.

A driver can disappear after a physical child exits and before its entry is
published. Recovery must consume that same request once, verify its original
bytes and exact candidate partition, and refuse an active or unrecorded exit.
"""

import _paths  # Locate AFP tools independently of cwd and unittest discovery.
from pathlib import Path
from types import SimpleNamespace
import copy
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import afp_common as common
import full


class LostDriver(BaseException):
    pass


class ExportProgressTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name)
        self.base = self.project / 'full'
        self.scope = {'A.thy': ['A.f', 'A.g']}
        self.info = {'theories': [{'path': 'A.thy', 'name': 'A'}]}
        self.record = {'scan': {'status': 'passed', 'theories': ['A.thy']}}
        self.args = SimpleNamespace(export_batch_size=1, source_fault_heap_mb=0,
                                    max_heap_mb=4500, timeout=0)
        self.env = {'ML_OPTIONS': '--minheap 256 --maxheap 4500 --stackspace 512'}
        self.calls = []
        for context in [patch.object(common, 'PROJECT', self.project),
                        patch.object(full, 'serializer_signature', return_value='serializer'),
                        patch.object(full, 'maximal_sessions', return_value=['S'])]:
            context.start()
            self.addCleanup(context.stop)

    @property
    def progress_path(self):
        return self.base / 'export-progress/E.json'

    def export(self, record=None):
        full.export_entry('E', self.info, record if record is not None else self.record,
                          self.scope, self.base, self.args, self.env)

    def native_files(self, session, work, args, env, resource=False):
        # These are test fixture receipts, never actual Isabelle outcomes.
        # Failed singleton frontend XML covers all six fixture language cells.
        names = (work / 'scope.txt').read_text().splitlines()
        self.calls.append((names, dict(env), work))
        log = work / 'process.log'
        log.write_text('Run out of store - interrupting threads\n' if resource else 'fixture normal return\n')
        check = {'status': 'failed' if resource else 'passed',
                 'returncode': 1 if resource else 0, 'log': common.relative(log)}
        common.write_json(work / 'process.log.json', check)
        if not resource:
            (work / 'finished.xml').write_text('<finished/>')
            node = ET.Element('attempt', status='failed', stage='frontend', target='frontend')
            for name in names:
                ET.SubElement(node, 'constant', name=name)
            for target in full.TARGETS:
                ET.SubElement(node, 'language').text = target
            ET.SubElement(node, 'error').text = 'fixture rejected source constant'
            path = work / 'attempts/merged/all/frontend.xml'
            path.parent.mkdir(parents=True)
            path.write_text(ET.tostring(node, encoding='unicode'))
        return check

    def crash_after_second_child_exit(self):
        initial = copy.deepcopy(self.record)
        def command(*args):
            check = self.native_files(*args)
            if len(self.calls) == 2:
                raise LostDriver()
            return check
        with patch.object(full, 'export_command', side_effect=command):
            with self.assertRaises(LostDriver):
                self.export()
        return initial

    def test_completed_active_child_is_consumed_without_relaunch(self):
        # The second child exited before the driver disappeared. Its raw exit
        # and XML must be recovered, not replaced by a third invocation.
        initial = self.crash_after_second_child_exit()
        before = [(path, path.read_bytes()) for path in self.base.glob('exports/**/*.xml')]
        with patch.object(full, 'export_command', side_effect=AssertionError('duplicate launch')):
            self.export(initial)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(initial['full_export']['status'], 'complete')
        self.assertTrue(all(value['status'] == 'failed'
                            for cells in initial['full_export']['candidates'].values()
                            for value in cells.values()))
        self.assertEqual(common.read_json(self.progress_path)['status'], 'complete')
        self.assertEqual(before, [(path, path.read_bytes()) for path, _ in before])

    def test_terminal_journal_survives_lost_entry_publication(self):
        # All requests completed, but the per-entry result was never committed.
        # The terminal journal must recover without re-exporting both names.
        initial = copy.deepcopy(self.record)
        with patch.object(full, 'export_command', side_effect=self.native_files):
            self.export()
        self.assertEqual(common.read_json(self.progress_path)['status'], 'complete')
        with patch.object(full, 'export_command', side_effect=AssertionError('duplicate launch')):
            self.export(initial)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(initial['full_export']['status'], 'complete')

    def test_changed_sealed_log_is_rejected(self):
        # A stored digest binds the accepted first request. Reusing a cached
        # verdict after changing its full native log must fail before launch.
        initial = self.crash_after_second_child_exit()
        self.calls[0][2].joinpath('process.log').write_text('changed')
        with patch.object(full, 'export_command', side_effect=AssertionError('new launch')):
            with self.assertRaisesRegex(ValueError, 'evidence changed'):
                self.export(initial)

    def test_missing_or_duplicate_pending_candidate_is_rejected(self):
        # Pending scopes and accepted requests must form exactly one disjoint
        # partition per original context, rather than merely having equal size.
        initial = self.crash_after_second_child_exit()
        original = common.read_json(self.progress_path)
        for pending in [[], [{'session': 'S', 'scope': ['A.f']}]]:
            progress = copy.deepcopy(original)
            progress.update(pending=pending, active=None)
            common.write_json(self.progress_path, progress)
            with self.subTest(pending=pending):
                with self.assertRaisesRegex(ValueError, 'partition'):
                    self.export(copy.deepcopy(initial))

    def test_changed_native_xml_is_rejected(self):
        # A changed target status cannot be silently adopted on recovery.
        initial = self.crash_after_second_child_exit()
        path = self.calls[0][2] / 'attempts/merged/all/frontend.xml'
        path.write_text(path.read_text().replace('status="failed"', 'status="passed"'))
        with self.assertRaisesRegex(ValueError, 'evidence changed'):
            self.export(initial)

    def test_unsealed_completed_receipt_is_rejected(self):
        initial = self.crash_after_second_child_exit()
        progress = common.read_json(self.progress_path)
        progress['runs'][0].pop('evidence_sha256')
        common.write_json(self.progress_path, progress)
        with self.assertRaisesRegex(ValueError, 'no evidence digests'):
            self.export(initial)

    def test_changed_discovery_or_serializer_identity_is_rejected(self):
        initial = self.crash_after_second_child_exit()
        with patch.object(full, 'serializer_signature', return_value='changed'):
            with self.assertRaisesRegex(ValueError, 'Stale export progress'):
                self.export(initial)

    def test_another_live_scheduler_cannot_be_replaced(self):
        initial = self.crash_after_second_child_exit()
        progress = common.read_json(self.progress_path)
        progress['owner'] = {'pid': -99, 'identity': ['fixture', -99, 'birth']}
        common.write_json(self.progress_path, progress)
        with patch.object(common, 'identity_matches', return_value=True):
            with self.assertRaisesRegex(ValueError, 'live scheduler'):
                self.export(initial)

    def test_live_child_is_not_launched_again(self):
        initial = self.crash_after_second_child_exit()
        active = common.read_json(self.progress_path)['active']
        def live(check):
            return check.get('log') == active['directory'] + '/process.log'
        with patch.object(common, 'identity_matches', side_effect=live):
            with self.assertRaisesRegex(ValueError, 'still live'):
                self.export(initial)
        self.assertEqual(len(self.calls), 2)

    def test_missing_exit_is_not_inferred_from_an_error_log(self):
        # Even plausible resource text cannot supply the missing return status.
        initial = self.crash_after_second_child_exit()
        active = self.calls[1][2]
        check = common.read_json(active / 'process.log.json')
        check.update(status='running')
        check.pop('returncode')
        common.write_json(active / 'process.log.json', check)
        active.joinpath('process.log').write_text('Run out of store - interrupting threads')
        with self.assertRaisesRegex(ValueError, 'no recorded process exit'):
            self.export(initial)

    def test_foreign_active_directory_is_rejected(self):
        initial = self.crash_after_second_child_exit()
        progress = common.read_json(self.progress_path)
        progress['active']['directory'] = 'unrelated/attempt-0001'
        common.write_json(self.progress_path, progress)
        with self.assertRaisesRegex(ValueError, 'foreign request directory'):
            self.export(initial)

    def test_retry_partition_preserves_all_members_and_native_failure(self):
        # Only the aggregate exhausts. Both independent singleton attempts
        # remain necessary; a registry entry only changes scheduling and heap.
        self.args.export_batch_size = 2
        self.args.source_fault_heap_mb = 1200
        def command(session, work, args, env):
            resource = len((work / 'scope.txt').read_text().splitlines()) > 1
            return self.native_files(session, work, args, env, resource)
        def registered(base, entry, scope, group):
            return {'family': 'fixture-observation'} if group == ['A.f'] else None
        with patch.object(full, 'export_command', side_effect=command), \
             patch.object(full, 'registered_source_fault', side_effect=registered):
            self.export()
        self.assertEqual([names for names, _, _ in self.calls], [['A.f', 'A.g'], ['A.f'], ['A.g']])
        self.assertEqual(self.calls[0][1], self.env)
        self.assertIn('--maxheap 1200', self.calls[1][1]['ML_OPTIONS'])
        self.assertEqual(self.calls[2][1], self.env)
        self.assertIn('--maxheap 4500', self.env['ML_OPTIONS'])
        self.assertEqual(self.record['full_export_history'][0]['runs'][0]['command']['status'], 'failed')
        self.assertFalse(self.record['full_export_history'][0]['runs'][0]['finished'])
        self.assertEqual(self.record['full_export']['status'], 'complete')
        self.assertEqual(len(common.read_json(self.progress_path)['retries']), 1)


if __name__ == '__main__':
    unittest.main()

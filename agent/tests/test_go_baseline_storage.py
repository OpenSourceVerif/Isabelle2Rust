import tempfile
import unittest
from pathlib import Path

from i2r_agent.baselines import language_artifacts, language_results
from i2r_agent.common import Failure, read, save
from i2r_agent.go_baseline import migrate_storage


class GoStorageTests(unittest.TestCase):
    def fixture(self, root, run, status):
        old = root / 'data/go-baselines' / run / 'case'
        save(root / 'data/baselines/case-version/baseline.json', {'id': 'case-version'})
        result = {'case': 'case', 'baseline_id': 'case-version', 'status': status,
                  'started_at': 'original timestamp', 'identity': {'runner': 'original hash'},
                  'reference': {'binary': str(old / 'reference')},
                  'performance': {'origin': str(old / 'performance.json'), 'samples': [10, 20]}}
        save(old / 'result.json', result)
        save(old.parent / 'summary.json', [result])
        save(old / 'logs/0001.json', {'stdout': str(old / 'logs/0001.stdout')})
        (old / 'logs/0001.stdout').write_text('historical command output')
        (old / 'reference').write_bytes(b'original binary')
        return old

    def test_preserves_attempts_evidence_and_measurement_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for run, status in [('run-1', 'failed'), ('run-2', 'passed')]:
                self.fixture(root, run, status)
            self.assertEqual(len(migrate_storage(root)), 2)
            self.assertFalse((root / 'data/go-baselines').exists())
            paths = language_results('go', root)
            self.assertEqual([read(p)['status'] for p in paths], ['failed', 'passed'])
            for path in paths:
                r = read(path)
                self.assertEqual(path.parent.parent, language_artifacts('case-version', 'go', root))
                self.assertEqual(r['measurement_id'], path.parent.name + '/case')
                self.assertEqual(r['started_at'], 'original timestamp')
                self.assertEqual(r['identity'], {'runner': 'original hash'})
                self.assertEqual(r['performance']['samples'], [10, 20])
                self.assertEqual(Path(r['reference']['binary']).read_bytes(), b'original binary')
                log = read(path.parent / 'logs/0001.json')
                self.assertEqual(Path(log['stdout']).read_text(), 'historical command output')
                summary = read(root / 'data/baselines/runs/go' / path.parent.name / 'summary.json')
                self.assertEqual(summary[0]['reference'], r['reference'])
            self.assertEqual(migrate_storage(root), {})

    def test_collision_rejected_before_any_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = self.fixture(root, 'run-1', 'passed')
            second = self.fixture(root, 'run-2', 'failed')
            language_artifacts('case-version', 'go', root).joinpath('run-2').mkdir(parents=True)
            with self.assertRaises(Failure):
                migrate_storage(root)
            self.assertTrue(first.is_dir())
            self.assertTrue(second.is_dir())

    def test_missing_parent_baseline_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = self.fixture(root, 'run-1', 'passed')
            (root / 'data/baselines/case-version/baseline.json').unlink()
            with self.assertRaises(Failure):
                migrate_storage(root)
            self.assertTrue(old.is_dir())

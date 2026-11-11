import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from i2r_agent import study


class ResumeStatusTest(unittest.TestCase):
    def test_resume_updates_status_before_build_preserving_history(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            case = root / 'catalog/cases/example'
            case.mkdir(parents=True)
            (case / 'source.txt').write_text('source')
            spec = root / 'study.json'
            spec.write_text(json.dumps({'id':'resume-test','cases':['example'],
                'variants':{'checked':{}}, 'base':{'generation':{'workflow':'knowledge-v5'}}}))
            directory = root / 'data/runs/resume-test'
            summary = directory / 'summary.json'
            def interrupted(*args, **kwargs):
                args[5]({'status':'running','phase':'support','model_calls':9})
                raise KeyboardInterrupt()
            def resumed(*args, **kwargs):
                record = json.loads(summary.read_text())
                self.assertEqual(record['status'], 'running')
                self.assertEqual(record['started_at'], started)
                self.assertEqual(record['results'], {'example--checked--01':'running'})
                self.assertIn('resumed_at', record)
                recovery = list((directory / 'trials/example--checked--01/recovery').glob('*.json'))
                self.assertEqual(len(recovery), 1)
                self.assertEqual(json.loads(recovery[0].read_text())['model_calls'], 9)
                result = {'status':'passed','phase':'finished','model_calls':10}
                args[5](result)
                return result
            with patch.object(study, 'ROOT', root), patch.object(study, 'config', return_value={}), \
                 patch.object(study.tool_sources, 'manifest', return_value={}), \
                 patch.object(study.tool_sources, 'verify'), \
                 patch('i2r_agent.context_evaluation.summarize'):
                with patch.object(study, 'build', side_effect=interrupted):
                    with self.assertRaises(KeyboardInterrupt):study.run(spec, 'resume-test')
                before = json.loads(summary.read_text())
                self.assertEqual(before['status'], 'interrupted')
                started = before['started_at']
                with patch.object(study, 'build', side_effect=resumed):
                    result = study.run(spec, 'resume-test', resume=True)
                self.assertEqual(result['status'], 'finished')
                self.assertEqual(result['results'], {'example--checked--01':'passed'})

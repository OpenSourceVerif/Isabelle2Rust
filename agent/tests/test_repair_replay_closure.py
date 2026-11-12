import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

from i2r_agent import translation_workflow as runner, repair_controller as repair
from i2r_agent.common import Executor, save
from test_segmented_workflow import source, mapping
from test_translation_workflow import cfg, accept


class ReplayClosureTests(unittest.TestCase):
    def test_only_exact_failure_occurrence_closes_after_successful_replay(self):
        failure = {'kind': 'contract', 'status': 'open', 'evidence': 'original'}
        unrelated = {'kind': 'contract', 'status': 'open', 'evidence': 'unrelated'}
        state = {'failures': [failure, unrelated]}
        issue = repair.register(state, 'compile', {'status': 'plan_contract_failed'},
                                {'roots': ['f']}, 'refine', failure)
        # Even another occurrence with the same reproducer id is not this replay.
        unrelated['repair_issue'] = issue['id']
        repair.replay_result(state, {'status': 'compile_failed'}, cfg())
        self.assertEqual(failure['status'], 'open')
        repair.replay_result(state, {'status': 'passed'}, cfg(),
                             verified_version='fixed', evidence='replay.json')
        self.assertEqual(failure['status'], 'closed')
        self.assertEqual(failure['verified_version'], 'fixed')
        self.assertEqual(failure['replay_evidence'], 'replay.json')
        self.assertEqual(unrelated['status'], 'open')

    def test_generic_mapping_repair_replays_once_and_review_receives_no_stale_failure(self):
        c = cfg()
        c['segmented']['support_tests'] = False
        c['segmented']['development_performance'] = False
        b = source()
        b['workflow'] = 'source-translation'
        b['source_model']['entities']['constant:A.f']['source_type'] = {
            'kind': 'free', 'name': "'a", 'sort': ['HOL.type']}
        b['original_source_model'] = deepcopy(b['source_model'])
        provider = Mock(calls=0, usage={})
        repaired = []
        post_repair_reviews = []

        def ask(pv, conf, path, payload, analysis=False):
            phase = payload['controller_state']['phase']
            if phase == 'generate':
                name = payload['unit']['members'][0].rsplit('.', 1)[-1]
                code = 'pub fn h()->u128{1}' if name == 'h' else 'pub fn f<T>(_: &T)->u128{h()+1}'
                return {'files': {'src/lib.rs': payload['current_files']['src/lib.rs'] + '\n' + code},
                        'mapping': [mapping(name)]}
            if phase == 'repair':
                self.assertEqual(len(payload['open_failures']), 1)
                repaired.append(True)
                self.assertEqual(len(repaired), 1, 'repair must not recur after successful replay')
                return {'mapping': [{**mapping('f'), 'type_parameters': {"'a": 'T'}}],
                        'repair_hypothesis': {'cause': 'missing HOL type-variable mapping',
                            'evidence': 'plan_contract_failed missing key',
                            'change': 'map HOL a to Rust T', 'prediction': 'original contract and build pass'}}
            if repaired:
                self.assertEqual(payload['open_failures'], [])
                self.assertIsNone(payload['repair_issue'])
                post_repair_reviews.append(phase)
            return accept(payload, c)

        with tempfile.TemporaryDirectory() as directory:
            w = Path(directory)
            save(w / 'regressions.json', [])
            with patch('i2r_agent.translation_workflow.ask', side_effect=ask):
                attempts, done = runner.search(b, None, c, provider, w, Executor(w / 'commands'),
                    None, [], [], w / 'regressions.json', lambda _: None)
        self.assertEqual(done[0]['status'], 'passed')
        self.assertEqual(len(repaired), 1)
        self.assertIn('refine', post_repair_reviews)
        self.assertEqual(sum(a['action_phase'] == 'repair_replay' for a in attempts), 1)
        self.assertEqual(done[0]['failures'][0]['status'], 'closed')
        self.assertEqual(done[0]['failures'][0]['failure']['status'], 'plan_contract_failed')


if __name__ == '__main__':
    unittest.main()

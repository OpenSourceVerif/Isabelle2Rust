import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from i2r_agent import segmented_support as support
from i2r_agent.common import ROOT, config, merge, read, Failure
from i2r_agent.segmented_config import configure, rust_config


class SupportProtocolTest(unittest.TestCase):
    def test_invalid_composite_source_has_actionable_retry_without_oracle_changes(self):
        cfg = configure(merge(config(), read(Path(__file__).parent/'fixtures/segmented-source.json')['base']))
        source_id = 'constant:A.f'
        state = {'bundle':{'source_model':{'entities':{source_id:{'id':source_id,'name':'A.f','kind':'constant',
                 'execution_equations':[]}},'entries':[source_id]},'numeric_policy':{'mode':'checked'}},
                 'files':{'src/lib.rs':'pub fn f()->u128 {2}'},'mapping':[], 'rust_config':rust_config({},cfg)}
        code = 'use i2r_candidate::f; #[test] fn source_value(){assert_eq!(f(),2);}'
        basis = 'Independent source equation f = 2'
        def review(payload, *args, **kwargs):
            self.assertEqual(payload['available_source_ids'], [source_id])
            if payload['task'].startswith('Review'):
                return {'action':'accept','review':'Expected value independently checked against source.'}
            prior = payload['prior_authoring_failure']
            if prior:
                self.assertEqual(prior['evidence']['valid_source_ids'], [source_id])
                self.assertIn('EXACTLY ONE', prior['message'])
            return {'test_source':code,'obligations':[{'source':source_id if prior else invalid_source,
                    'case':'f()','expected_basis':basis,'test_name':'source_value'}]}
        for invalid_source in [source_id+' equations 0 and 1', 'crate::f']:
            state.pop('feedback',None)
            with self.subTest(invalid_source=invalid_source), tempfile.TemporaryDirectory() as d, patch.object(support,'source_review',side_effect=review):
                with self.assertRaises(Failure) as error:support.prepare(state,cfg,Mock(),d)
                self.assertEqual(error.exception.code,'missing_support_verification')
                self.assertFalse(list(Path(d).glob('*.json')))
                state['feedback']={'status':error.exception.code,'message':str(error.exception),'evidence':error.exception.evidence}
                frozen = support.prepare(state,cfg,Mock(),d)
                self.assertEqual(frozen['tests'],[code])
                self.assertEqual(frozen['obligations'][0]['expected_basis'],basis)
                self.assertEqual(len(list(Path(d).glob('*-generation-*'))),2)

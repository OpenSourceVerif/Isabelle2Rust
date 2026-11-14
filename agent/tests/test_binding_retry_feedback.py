import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from i2r_agent import segmented_test_audit as audit
from i2r_agent.common import ROOT,config,merge,read,Failure
from i2r_agent.segmented_config import configure,rust_config


class BindingRetryFeedbackTest(unittest.TestCase):
    def test_failed_assertion_edit_is_explained_before_unchanged_assertion_adapter(self):
        cfg=configure(merge(config(),read(Path(__file__).parent/'fixtures/shared-workflow-config.json')['base']))
        ident='constant:A.f';code='use i2r_candidate::f; #[test] fn empty(){assert_eq!(f(vec![]),vec![]);}'
        obligation={'source':ident,'case':'empty list','expected_basis':'source equation f [] = []','test_name':'empty'}
        frozen={'identity':'original','tests':[code],'unit_tests':[],'obligations':[obligation]}
        state={'bundle':{'source_model':{'entities':{ident:{'id':ident,'name':'A.f','kind':'constant','execution_equations':[]}},'entries':[ident]},'numeric_policy':{'mode':'checked'}},
               'mapping':[],'files':{'src/lib.rs':'pub fn f<T>(xs: Vec<T>)->Vec<T>{xs}'},'rust_config':rust_config({},cfg),'feedback':None}
        def respond(payload,*args,**kwargs):
            if payload['task'].startswith('Independently review'):
                return {'action':'accept','review':'Only test-local type inference changed; assertion and source case remain exact.'}
            prior=payload['prior_binding_rejection']
            if prior:
                self.assertEqual(prior['status'],'support_oracle_change')
                self.assertIn('protected source-test invariants',prior['message'])
                old='fn empty(){';new='fn empty(){ let f=i2r_candidate::f::<i32>;'
            else:old='f(vec![])';new='f::<i32>(vec![])'
            return {'action':'binding_fix','reason':'Instantiate the empty-list test locally, retaining source behavior.',
                    'edits':[{'kind':'integration','index':0,'old':old,'new':new}]}
        with tempfile.TemporaryDirectory() as d,patch.object(audit,'source_review',side_effect=respond):
            with self.assertRaises(Failure) as error:audit.adjudicate(frozen,{'status':'support_test_compile_failed'},state,cfg,Mock(),Path(d)/'first')
            self.assertEqual(error.exception.code,'support_oracle_change')
            state['feedback']={'status':error.exception.code,'message':str(error.exception)}
            result=audit.adjudicate(frozen,{'status':'support_test_compile_failed'},state,cfg,Mock(),Path(d)/'second')
            updated=result['frozen']
            self.assertEqual(audit.invariants(updated['tests'][0]),audit.invariants(code))
            self.assertEqual(updated['oracle_identity'],'original')
            self.assertEqual(updated['obligations'],frozen['obligations'])
            self.assertEqual(frozen['tests'],[code])

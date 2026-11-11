import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock,patch
from i2r_agent.common import Executor
from i2r_agent.segmented_config import materialize,rust_config
from i2r_agent.segmented_support import prepare,execute
from i2r_agent.segmented_v8 import connector_identity
from i2r_agent.v8_identity import interfaces_for_cache
from test_segmented_workflow import source,mapping
from test_v8_workflow import cfg


class V8CacheTests(unittest.TestCase):
    def test_only_inline_function_attributes_are_nonbinding(self):
        plain={'src/lib.rs':'pub fn h()->u128{1}'}
        a=interfaces_for_cache(plain)
        for attr in ['#[inline]','#[inline(always)]','#[inline(never)]']:
            self.assertEqual(a,interfaces_for_cache({'src/lib.rs':attr+plain['src/lib.rs']}))
        for attr in ['#[cfg(feature="x")]','#[target_feature(enable="sse2")]','#[cfg_attr(feature="x", inline)]']:
            self.assertNotEqual(a,interfaces_for_cache({'src/lib.rs':attr+plain['src/lib.rs']}))
        state={'files':plain,'mapping':[],'rust_config':{}}
        before=connector_identity(state)
        state['files']={'src/lib.rs':'#[inline] pub fn h()->u128{2}'}
        self.assertEqual(before,connector_identity(state))
        state['files']={'src/lib.rs':'#[inline] pub fn h()->i128{2}'}
        self.assertNotEqual(before,connector_identity(state))

    def test_whole_support_interface_identity_ignores_body_but_tracks_scope(self):
        def identity(code):return interfaces_for_cache({'src/lib.rs':code})
        a=identity('pub fn h()->u128{1}')
        self.assertEqual(a,identity('\n// preceding comment\npub fn h()->u128{1}'))
        self.assertEqual(a,identity('pub fn h()->u128{2}'))
        self.assertNotEqual(a,identity('mod nested { pub fn h()->u128{1} }'))

    def test_frozen_tests_reused_and_executed_on_changed_body(self):
        c=cfg();rc=rust_config({},c)
        s={'bundle':source(),'files':{'src/lib.rs':'pub fn h()->u128{1}'},'mapping':[mapping('h')],'rust_config':rc}
        s['bundle']['numeric_policy']={'mode':'checked'}
        proposal={'test_source':'#[test] fn original(){assert_eq!(i2r_candidate::h(),1);}',
                  'obligations':[{'source':'constant:A.h','case':'h()','test_name':'original','expected_basis':'source h = 1'}]}
        with tempfile.TemporaryDirectory() as d:
            work=Path(d);ex=Executor(work/'commands');provider=Mock()
            with patch('i2r_agent.segmented_support.source_review',side_effect=[proposal,{'action':'accept','review':'Source h = 1 verified'}]) as author:
                frozen=prepare(s,c,provider,work/'tests')
                self.assertEqual(author.call_count,2)
                for body,expected in [('1','passed'),('2','support_contract_failed')]:
                    s['files']['src/lib.rs']='#[inline] pub fn h()->u128{'+body+'}'
                    reused=prepare(s,c,provider,work/'tests')
                    self.assertEqual(reused,frozen);self.assertEqual(author.call_count,2)
                    crate=materialize(work/'candidate',s['files'],rc)
                    self.assertEqual(execute(reused,crate,rc,c,ex)['status'],expected)


    def test_rollback_restores_parent_evidence_and_immutable_harness(self):
        from i2r_agent.v8_performance import snapshot
        from i2r_agent.segmented_v8 import revert_optimization,version
        from test_v8_workflow import CONNECTOR
        c=cfg();rc=rust_config({},c)
        with tempfile.TemporaryDirectory() as d:
            work=Path(d);binary=work/'original-binary';binary.write_bytes(b'original executable identity')
            s={'files':{'src/lib.rs':'pub fn f()->u128{2}'},'mapping':[],
               'rust_config':rc,'partition':source()['segmentation'],'completed':[],
               'reviews':{},'connector':{'src/lib.rs':CONNECTOR},'transport':'native-u128',
               'binary':str(binary),'whole_review_version':'original-review-version',
               'support_evidence':{'status':'passed','frozen_identity':'original-tests'},
               'connector_notes':{'version':'original-connector'},
               'static_feedback':{'version':'original'},'decisions':['original decision'],
               'numeric_representation':'u128'}
            parent=snapshot(s,work/'parent');parent['development_performance']={'version':version(s)}
            self.assertEqual(Path(parent['binary']).read_bytes(),b'original executable identity')
            binary.write_bytes(b'changed executable identity')
            s.update(optimization_parent=parent,optimization_attempts=[{'status':'validating'}],
                     optimization_no_gain=0,repair_issues=[],failures=[],harness='candidate-harness',
                     support_evidence={'status':'support_contract_failed','frozen_identity':'candidate-tests'},
                     connector_notes={'version':'candidate'},
                     static_feedback={'version':'candidate'},decisions=['candidate decision'],
                     numeric_representation='candidate')
            s.pop('whole_review_version')
            revert_optimization(s,{'reason':'candidate failed'})
            self.assertEqual(s['harness'],parent['harness'])
            self.assertEqual(Path(s['binary']).read_bytes(),b'original executable identity')
            self.assertEqual(s['support_evidence'],{'status':'passed','frozen_identity':'original-tests'})
            self.assertEqual(s['connector_notes'],{'version':'original-connector'})
            self.assertEqual(s['whole_review_version'],'original-review-version')
            self.assertEqual(s['decisions'],['original decision'])
            self.assertEqual(s['numeric_representation'],'u128')


    def test_library_guidance_is_bound_to_exact_dependency_and_actual_failure(self):
        from i2r_agent import v8_repair
        s={'rust_config':{'dependencies':{'dashu-int':'=0.6.2'}}}
        v8_repair.register(s,'compile',{'diagnostic':'E0599: no method on IBig'}, {'roots':[]},'refine')
        s['repair_issues'][0]['latest']={'diagnostic':'E0599: no method magnitude on &IBig'}
        def selected():return {r['id'] for r in v8_repair.targeted_material(s).get('entries',[])}
        self.assertIn('dashu-062-magnitude',selected())
        s['rust_config']['dependencies']['dashu-int']={'version':'=0.6.2'}
        self.assertIn('dashu-062-magnitude',selected())
        for value in ['=0.6.1','0.6.2',None]:
            s['rust_config']['dependencies']['dashu-int']=value
            self.assertNotIn('dashu-062-magnitude',selected())
        s['rust_config']['dependencies']['dashu-int']='=0.6.2'
        s['repair_issues'][0]['latest']={'diagnostic':'E0502 borrow conflict'}
        self.assertNotIn('dashu-062-magnitude',selected())


    def test_independent_reviewer_receives_same_complete_obligation_protocol(self):
        import json
        c=cfg();rc=rust_config({},c)
        s={'bundle':source(),'files':{'src/lib.rs':'pub fn f()->u128{2}'},'mapping':[mapping('f')],'rust_config':rc}
        s['bundle']['numeric_policy']={'mode':'checked'}
        seen=[];provider=Mock()
        def response(system,prompt,**kwargs):
            p=json.loads(prompt);seen.append((system,p['obligation_protocol']))
            row=p['coverage_requirements'][0]
            values={'source':row['source'],'category':row['category'],'test_name':'original',
                    'case':'f()','expected_basis':'source f = 2'}
            obligation={k:values[k] for k in p['obligation_protocol']['executed_case_fields']}
            return {'test_source':'#[test] fn original(){assert_eq!(i2r_candidate::f(),2);}',
                    'obligations':[obligation], 'notes':'Complete corrected proposal, including original category.'}
        provider.call.side_effect=response
        with tempfile.TemporaryDirectory() as d:
            frozen=prepare(s,c,provider,d)
            self.assertEqual(len(seen),2)
            self.assertEqual(seen[0],seen[1])
            self.assertEqual(frozen['obligations'][0]['category'],'public_behavior')
            self.assertEqual(frozen['obligations'][0]['expected_basis'],'source f = 2')


    def test_successful_whole_program_test_clears_authoring_error_not_history(self):
        from i2r_agent.common import Failure
        from i2r_agent.segmented_v8 import search
        from test_v8_workflow import accept
        c=cfg();c['segmented']['support_tests']=True
        b=source();b['workflow']='segmented-v8';b['case']='list-index'
        provider=Mock();provider.calls=0;provider.usage={};generation_feedback=[]
        def model(pv,conf,path,p,analysis=False):
            phase=p['controller_state']['phase']
            if phase=='generate':
                generation_feedback.append(p.get('feedback'))
                n='h' if 'h' not in p['current_files']['src/lib.rs'] else 'f'
                return {'files':{'src/lib.rs':p['current_files']['src/lib.rs']+'\npub fn '+n+'()->u128{'+('1' if n=='h' else 'h()+1')+'}'},'mapping':[mapping(n)]}
            return accept(p,c)
        with tempfile.TemporaryDirectory() as d:
            work=Path(d)
            with patch('i2r_agent.segmented_v8.ask',side_effect=model),patch('i2r_agent.segmented_support.prepare',side_effect=[Failure('missing_support_verification','category missing'),{'identity':'frozen'}]),patch('i2r_agent.segmented_support.execute',return_value={'status':'passed','tests_passed':1}):
                attempts,done=search(b,None,c,provider,work,Executor(work/'commands'),None,[],[],work/'regressions.json',lambda _:None)
            self.assertTrue(done)
            self.assertIsNone(done[0]['feedback'])
            phases=[a['action_phase'] for a in attempts]
            self.assertEqual(phases.count('support'),2)
            self.assertLess(phases.index('whole_review'),phases.index('support'))
            self.assertEqual(generation_feedback,[None,None])
            self.assertTrue(any(a.get('development',{}).get('status')=='missing_support_verification' for a in attempts))


if __name__=='__main__':unittest.main()

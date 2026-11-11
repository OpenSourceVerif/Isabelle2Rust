import tempfile
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path
from i2r_agent import implementation_strategy as st, segmented_v8 as runner
from i2r_agent import v8_review_scope as scope
from i2r_agent.common import Failure, save, read
from i2r_agent.task_context import fingerprint
import test_shared_invalidation as fixtures


class StrategyTests(unittest.TestCase):
    def state(self):
        s,c=fixtures.SharedInvalidationTest().make_state()
        analysis={'semantic_obligations':[{'source':'constant:A.f','rust_representation':'old owned value','conditions':['source range'],'boundary_cases':['zero']} ]}
        s['bundle'].update(semantic_analysis=analysis,numeric_policy='checked',programs=[])
        s['implementation_strategy']=st.initialize(analysis)
        s.update(phase='repair',unit=s['partition']['owner']['constant:A.f'],failures=[{'status':'open','input':[0]}],extra={},seen_pages=[],seen_code_pages=[])
        return s,c

    def change(self,s,c,updates=None,**kw):
        reply={**kw}
        if updates is not None:reply.update(strategy_version=fingerprint(st.current(s)),strategy_updates=updates)
        with tempfile.TemporaryDirectory() as d:return runner.apply_transaction(s,reply,c,Path(d))

    def patch(self,s,**kw):
        r=st.current(s)['decisions'][0]
        return {'id':r['id'],'expected_revision':r['revision'],'reason':'source equation and current API',**kw}

    def test_initial_suggestions_do_not_mutate_analysis(self):
        s,c=self.state();initial=deepcopy(s['bundle']['semantic_analysis'])
        self.assertEqual(st.project(s)[0]['status'],'proposed')
        out=self.change(s,c,[self.patch(s,status='adopted',choice='current owned value')])
        self.assertEqual(s['bundle']['semantic_analysis'],initial)
        self.assertEqual(out['bundle']['semantic_analysis'],initial)
        self.assertEqual(st.project(out)[0]['status'],'adopted')

    def test_interface_revision_reaches_repair_payload_and_executes(self):
        s,c=self.state();code=s['files']['src/lib.rs'].replace('pub fn f()->u128 {shared()}','pub fn f()->i128 {shared() as i128}')
        out=self.change(s,c,[self.patch(s,status='adopted',choice='signed return')],files={'src/lib.rs':code})
        with tempfile.TemporaryDirectory() as d:
            request,_=runner.payload(out,c,Path(d))
            choices=str(request['program']['current_strategy'])
            self.assertIn('signed return',choices);self.assertNotIn('old owned value',choices)
            self.assertNotIn('global_analysis',request['program'])
            source=Path(d)/'main.rs';source.write_text(code+'\nfn main(){let value:i128=f();assert_eq!(value,1);}')
            subprocess.run(['rustc',str(source),'-o',str(Path(d)/'check')],check=True,capture_output=True)
            subprocess.run([str(Path(d)/'check')],check=True,capture_output=True)

    def test_mapping_and_config_changes_mark_stale_choices(self):
        for field in ('mapping','rust_config'):
            s,c=self.state()
            kwargs={'mapping':[{**s['mapping'][0],'rust':'updated explanation'}]} if field=='mapping' else {'rust_config':{'edition':'2021'}}
            out=self.change(s,c,**kwargs)
            self.assertEqual(st.project(out)[0]['status'],'needs_review')

    def test_failed_or_stale_transaction_is_atomic(self):
        s,c=self.state();original=deepcopy(s)
        with self.assertRaises(Failure):self.change(s,c,[self.patch(s,status='verified')],files={'src/lib.rs':s['files']['src/lib.rs']+' fn extra(){}'})
        self.assertEqual(s,original)
        with self.assertRaises(Failure):self.change(s,c,[self.patch(s,expected_revision=999,choice='stale')])
        self.assertEqual(s,original)

    def test_local_binding_change_invalidates_only_related_review(self):
        s,c=self.state();out=self.change(s,c,[self.patch(s,conditions=['new representation condition'])])
        self.assertNotIn(s['partition']['owner']['constant:A.f'],out['completed'])
        self.assertIn(s['partition']['owner']['constant:A.g'],out['completed'])
        self.assertNotEqual(scope.review_identity(s,{'constant:A.f'},s['files']),scope.review_identity(out,{'constant:A.f'},out['files']))
        self.assertEqual(scope.review_identity(s,{'constant:A.g'},s['files']),scope.review_identity(out,{'constant:A.g'},out['files']))

    def test_reason_only_preserves_reviews_and_evidence(self):
        s,c=self.state();out=self.change(s,c,[self.patch(s,reason='More detailed rationale')])
        self.assertEqual(out['completed'],s['completed']);self.assertEqual(out['reviews'],s['reviews'])
        self.assertEqual(out['whole_review_version'],s['whole_review_version'])
        self.assertEqual(scope.review_identity(s,{'constant:A.f'},s['files']),scope.review_identity(out,{'constant:A.f'},out['files']))
        self.assertNotEqual(runner.version(s),runner.version(out))

    def test_superseded_choice_stays_out_after_checkpoint_roundtrip(self):
        s,c=self.state();r=st.project(s)[0]
        patch={**r,'id':'new-interface','expected_revision':0,'choice':'borrowed','reason':'current source API','supersedes':[r['id']]}
        patch.pop('revision')
        out=self.change(s,c,[patch]);out['strategy_digest']=fingerprint(st.current(out))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'checkpoint.json';save(p,out);restored=read(p);st.restore_check(restored)
        self.assertEqual([r['choice'] for r in st.project(restored)],['borrowed'])
        self.assertTrue(st.current(restored)['history'])
        with self.assertRaises(Failure):st.restore_check(s|{'implementation_strategy':None})
        restored['implementation_strategy']['decisions'][0]['choice']='tampered'
        with self.assertRaises(Failure):st.restore_check(restored)

    def test_test_projection_has_conditions_without_algorithm_or_expectations(self):
        s,c=self.state();out=self.change(s,c,[self.patch(s,choice='secret candidate algorithm',conditions=['representation boundary'])])
        focus=st.project(out,{'constant:A.f'},testing=True)
        self.assertNotIn('secret candidate algorithm',str(focus));self.assertIn('representation boundary',str(focus))
        self.assertEqual(out['failures'],s['failures'])
        self.assertEqual(st.project(out,{'constant:A.g'},testing=True),[])

    def test_optimization_revert_restores_strategy_and_archives_trial(self):
        s,c=self.state();s.update(connector={},binary='parent-binary',harness='parent-harness',repair_issues=[],development_performance={'parent':True})
        parent={k:deepcopy(s[k]) for k in ['files','mapping','rust_config','partition','connector','completed','reviews','implementation_strategy','binary','harness','development_performance']}
        parent['verification_state']={'whole_review_version':'verified-parent'}
        trial=self.change(s,c,[self.patch(s,choice='trial',status='adopted')])
        trial.update(optimization_parent=parent,optimization_attempts=[{'status':'validating'}])
        runner.revert_optimization(trial,'no gain')
        self.assertEqual(st.current(trial),st.current(s));self.assertEqual(trial['files'],s['files'])
        self.assertEqual(trial['whole_review_version'],'verified-parent')
        self.assertEqual(trial['strategy_archives'][0]['decisions'][0]['choice'],'trial')
        self.assertEqual(trial['optimization_attempts'][0]['status'],'reverted')

    def test_independent_new_function_preserves_existing_strategy_evidence(self):
        s,c=self.state();st.current(s)['decisions'][0]['status']='adopted'
        old=deepcopy(st.current(s));code=s['files']['src/lib.rs']+'\n/// New independent consumer.\npub fn future()->u128 { f()+1 }\n'
        out=self.change(s,c,files={'src/lib.rs':code})
        self.assertEqual(st.current(out),old)
        self.assertEqual(out['completed'],s['completed'])
        self.assertEqual(out['reviews'],s['reviews'])

    def test_existing_interface_change_still_invalidates_strategy(self):
        s,c=self.state();st.current(s)['decisions'][0]['status']='adopted'
        code=s['files']['src/lib.rs'].replace('pub fn f()->u128 {shared()}','pub fn f()->i128 {shared() as i128}')
        out=self.change(s,c,files={'src/lib.rs':code})
        self.assertEqual(st.project(out)[0]['status'],'needs_review')
        self.assertNotIn(s['partition']['owner']['constant:A.f'],out['completed'])

    def test_new_impl_dispatch_context_remains_conservative(self):
        s,c=self.state();st.current(s)['decisions'][0]['status']='adopted'
        code=s['files']['src/lib.rs']+'\nimpl std::fmt::Display for Local { fn fmt(&self,f:&mut std::fmt::Formatter)->std::fmt::Result {write!(f,"local")} }\n'
        out=self.change(s,c,files={'src/lib.rs':code})
        self.assertEqual(st.project(out)[0]['status'],'needs_review')

    def test_fresh_inline_module_has_no_old_scope_effect(self):
        s,c=self.state();st.current(s)['decisions'][0]['status']='adopted'
        code=s['files']['src/lib.rs']+'\n/// Module-local consumer.\npub mod fresh { use crate::f; pub fn consumer()->u128 {f()} }\n'
        out=self.change(s,c,files={'src/lib.rs':code})
        self.assertEqual(st.project(out)[0]['status'],'adopted')
        self.assertEqual(out['completed'],s['completed'])

    def test_new_module_with_impl_or_macro_remains_conservative(self):
        for body in ['impl Local { pub fn method(&self){} }','#[macro_export] macro_rules! x {()=>{1}}','mod external;']:
            s,c=self.state();st.current(s)['decisions'][0]['status']='adopted'
            code=s['files']['src/lib.rs']+'\npub mod fresh {'+body+'}\n'
            out=self.change(s,c,files={'src/lib.rs':code})
            self.assertNotEqual(out['completed'],s['completed'])

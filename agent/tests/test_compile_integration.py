from workflow_fixture import compile_until_source
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from copy import deepcopy

from i2r_agent.common import Executor,Failure,read,save
from i2r_agent.segmented_config import configure,materialize,rust_config
from i2r_agent.segmented_support import prepare,execute
from i2r_agent.segmented_test_audit import revise
from i2r_agent.translation_workflow import search,quality_reviews_enabled
from i2r_agent import task_context
from test_segmented_workflow import source,mapping
from test_translation_workflow import cfg,accept


class CompileIntegration(unittest.TestCase):
    def test_quality_stage_requires_explicit_optimization_switch(self):
        self.assertFalse(quality_reviews_enabled({}))
        c=cfg();self.assertTrue(quality_reviews_enabled(c))
        c['translation']['performance_refinement']=False
        c['segmented']['review_categories'].append('cost')
        self.assertFalse(quality_reviews_enabled(c))
        c['translation'].update(performance_refinement=True,correctness_only=True)
        self.assertFalse(quality_reviews_enabled(c))

    def test_correctness_compiler_failure_replays_without_review_evidence(self):
        c=cfg();c['translation']['correctness_only']=True;c=configure(c)
        # This fixture isolates compilation; behavioral/source execution has its
        # own end-to-end stage-order test with full support enabled.
        c['segmented']['support_tests']=False
        b=source();b['workflow']='source-translation';pv=Mock();pv.calls=0;pv.usage={}
        calls=[]
        def reply(provider,conf,path,p,analysis=False):
            phase=p['controller_state']['phase'];calls.append(phase)
            self.assertNotIn(phase,{'refine','whole_review'})
            if phase=='generate':
                n=p['unit']['members'][0].rsplit('.',1)[-1]
                body='missing_name' if n=='h' else 'h()+1'
                return {'files':{'src/lib.rs':p['current_files']['src/lib.rs']+'\npub fn '+n+'()->u128{'+body+'}'},'mapping':[mapping(n)]}
            self.assertEqual(phase,'repair')
            return {'edits':[{'file':'src/lib.rs','old':'missing_name','new':'1'}],
                    'repair_hypothesis':{'cause':'unbound identifier','evidence':'compiler unresolved name','change':'source constant 1','prediction':'original compilation succeeds'}}
        with tempfile.TemporaryDirectory() as tmp,patch('i2r_agent.translation_workflow.ask',side_effect=reply):
            w=Path(tmp);attempts,done=compile_until_source(b,None,c,pv,w,Executor(w/'commands'),None,[],[],w/'regressions.json',lambda _:None)
            self.assertEqual(calls,['generate','repair','generate'])
            self.assertEqual(done[0]['status'],'active');self.assertFalse(quality_reviews_enabled(c))
            self.assertEqual(done[0]['reviews'],{});self.assertNotIn('source_reviews',done[0])
            replay=next(a for a in attempts if a['action_phase']=='repair_replay')
            self.assertEqual(replay['original_replay']['status'],'passed')
            self.assertEqual([a['action_phase'] for a in attempts][-1:],['compile'])
            original=read(w/'segmented-checkpoint.json')
            # Same new identity must not make a removed stage executable.
            legacy=deepcopy(original);legacy.update(phase='post_review',status='active')
            save(w/'segmented-checkpoint.json',legacy)
            with self.assertRaises(Failure) as caught:
                search(b,None,c,pv,w,Executor(w/'refused'),None,[],[],w/'regressions.json',lambda _:None)
            self.assertEqual(caught.exception.code,'removed_checkpoint_stage')
            self.assertEqual(read(w/'segmented-checkpoint.json'),legacy)
            # Older workflow identity is rejected even if it names a live phase.
            legacy.update(phase='whole_review',identity=task_context.fingerprint({'source':b['source_model'],'config':c,'analysis':b['semantic_analysis']}))
            save(w/'segmented-checkpoint.json',legacy)
            with self.assertRaises(Failure) as caught:
                search(b,None,c,pv,w,Executor(w/'refused2'),None,[],[],w/'regressions.json',lambda _:None)
            self.assertEqual(caught.exception.code,'stale_snapshot')

    def test_single_source_author_fixed_oracle_and_distinct_cache_policy(self):
        c=cfg();c['translation']['correctness_only']=True;c=configure(c);rc=rust_config({},c)
        s={'bundle':source(),'files':{'src/lib.rs':'pub fn h()->u128{1} pub fn f()->u128{999}'},
           'mapping':[mapping('h'),mapping('f')],'rust_config':rc}
        proposal={'test_source':'#[test] fn source_value(){assert_eq!(i2r_candidate::f(),2);}',
                  'obligations':[{'source':'constant:A.f','category':'public_behavior','test_name':'source_value','case':'f()','expected_basis':'source equation f=h+1, h=1'}]}
        requests=[]
        def author(p,*args,**kwargs):
            requests.append(deepcopy(p));self.assertNotIn('pub fn f()->u128{999}',str(p));self.assertEqual(p['rust_signatures']['crate::f'],['pub fn f()->u128'])
            if p.get('authoring_policy')=='source-author-only-v1':
                self.assertNotIn('reviewer',kwargs['system'].lower())
                self.assertNotIn('independent review',str(p).lower())
                self.assertNotIn('action:accept',p['obligation_protocol']['correction'])
                self.assertIn('source/API',p['task'])
                self.assertIn('Never change an expectation to match candidate output',kwargs['system'])
            return {'action':'accept','review':'Source expectation independently checked'} if p['task'].startswith('Review') else deepcopy(proposal)
        with tempfile.TemporaryDirectory() as tmp,patch('i2r_agent.segmented_support.source_review',side_effect=author):
            w=Path(tmp);frozen=prepare(s,c,Mock(),w/'tests')
            self.assertEqual(len(requests),1);self.assertEqual(frozen['authoring_policy'],'source-author-only-v1')
            self.assertEqual(prepare(s,c,Mock(),w/'tests'),frozen);self.assertEqual(len(requests),1)
            crate=materialize(w/'crate',s['files'],rc)
            failure=execute(frozen,crate,rc,c,Executor(w/'bad'))
            self.assertEqual(failure['status'],'support_contract_failed')
            # A test challenge cannot replace the mathematical expectation with
            # the observed wrong candidate result, even under single authorship.
            with self.assertRaises(Failure) as caught:
                revise(frozen,{'reason':'candidate returned 999','edits':[{'kind':'integration','index':0,'old':'(),2','new':'(),999'}]},s)
            self.assertEqual(caught.exception.code,'support_oracle_change')
            s['files']['src/lib.rs']=s['files']['src/lib.rs'].replace('999','2')
            self.assertEqual(prepare(s,c,Mock(),w/'tests'),frozen);self.assertEqual(len(requests),1)
            crate=materialize(w/'crate',s['files'],rc)
            self.assertEqual(execute(frozen,crate,rc,c,Executor(w/'fixed'))['status'],'passed')
            d=cfg();reviewed=prepare(s,d,Mock(),w/'tests')
            self.assertNotEqual(reviewed['identity'],frozen['identity'])
            self.assertEqual(len(requests),3)


if __name__=='__main__':unittest.main()

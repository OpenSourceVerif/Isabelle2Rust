"""Actual Cargo calls for the direct complete-unit transition and recovery paths."""
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock,patch
from i2r_agent import segmented_v8 as runner
from i2r_agent.common import Executor,Failure,read,save
from i2r_agent.segmented_config import configure
from test_segmented_workflow import source,mapping
from test_v8_workflow import cfg


class FinalUnitCompilation(unittest.TestCase):
    def setup_run(self):
        c=cfg();c['v8']['correctness_only']=True;c=configure(c)
        c['segmented']['support_tests']=False # Isolate candidate compile count.
        b=source();b['workflow']='segmented-v8'
        pv=Mock();pv.calls=0;pv.usage={}
        return b,c,pv

    def reply(self,fail_last=False,stop_repair=False):
        def answer(pv,c,path,p,analysis=False):
            phase=p['controller_state']['phase']
            if phase=='generate':
                n=p['unit']['members'][0].rsplit('.',1)[-1]
                body='1' if n=='h' else 'missing_name' if fail_last else 'h()+1'
                return {'files':{'src/lib.rs':p['current_files']['src/lib.rs']+'\npub fn '+n+'()->u128{'+body+'}'},'mapping':[mapping(n)]}
            if phase=='repair' and not stop_repair:
                return {'edits':[{'file':'src/lib.rs','old':'missing_name','new':'h()+1'}],
                    'repair_hypothesis':{'cause':'undefined identifier','evidence':'actual compiler diagnostic','change':'source f=h+1','prediction':'original cumulative compile passes'}}
            raise Failure('needs_user','Stop the deliberately malformed fixture after observing coverage refusal')
        return answer

    def test_last_cumulative_compile_is_complete_without_duplicate_build(self):
        b,c,pv=self.setup_run()
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'ask',side_effect=self.reply()),patch.object(runner,'compile_crate',wraps=runner.compile_crate) as compile_call:
            w=Path(d);a,done=runner.search(b,None,c,pv,w,Executor(w/'cmd'),None,[],[],w/'regressions.json',lambda _:None)
            self.assertEqual(done[0]['status'],'passed');self.assertEqual(compile_call.call_count,2)
            builds=[x for x in a if 'compilation' in x]
            self.assertEqual([x['compilation_scope'] for x in builds],['cumulative_units','complete_program'])
            self.assertEqual(builds[-1]['coverage']['exports'],['constant:A.f'])
            self.assertEqual(builds[-1]['compilation']['status'],'passed')
            self.assertNotIn('final_compile',[x['action_phase'] for x in a])

    def test_last_unit_requires_final_export_coverage_before_cargo(self):
        b,c,pv=self.setup_run()
        b['source_model']['entities']['constant:A.extra']={**b['source_model']['entities']['constant:A.h'],'id':'constant:A.extra','name':'A.extra'}
        b['source_model']['entries'].append('constant:A.extra')
        b['original_source_model']=deepcopy(b['source_model'])
        replies=0;base=self.reply(stop_repair=True)
        def answer(pv,c,path,p,analysis=False):
            nonlocal replies
            if p['controller_state']['phase']=='repair' and replies==0:
                replies+=1
                return {'edits':[{'file':'src/lib.rs','old':'h()+1','new':'1+h()'}],
                    'repair_hypothesis':{'cause':'deliberately wrong mapping repair','evidence':'missing export','change':'irrelevant body rewrite','prediction':'must still fail the exact original final coverage'}}
            return base(pv,c,path,p,analysis)
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'ask',side_effect=answer),patch.object(runner,'compile_crate',wraps=runner.compile_crate) as compile_call:
            w=Path(d)
            with self.assertRaises(Failure) as caught:
                runner.search(b,None,c,pv,w,Executor(w/'cmd'),None,[],[],w/'regressions.json',lambda _:None)
            self.assertEqual(caught.exception.code,'needs_user')
            state=read(w/'segmented-checkpoint.json');a=state['attempts']
            failures=[x for x in a if x.get('development',{}).get('status')=='missing_exports']
            self.assertEqual(len(failures),1)
            self.assertTrue(state['repair_issues'][0]['reproducer']['final_coverage'])
            replay=next(x for x in a if x['action_phase']=='repair_replay')
            self.assertEqual(replay['original_replay']['status'],'missing_exports')
            self.assertEqual(compile_call.call_count,1)
            self.assertNotEqual(state['status'],'passed')
            self.assertNotIn('support',[x['action_phase'] for x in a])

    def test_last_unit_failure_replay_still_recompiles_complete_program(self):
        b,c,pv=self.setup_run()
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'ask',side_effect=self.reply(fail_last=True)),patch.object(runner,'compile_crate',wraps=runner.compile_crate) as compile_call:
            w=Path(d);a,done=runner.search(b,None,c,pv,w,Executor(w/'cmd'),None,[],[],w/'regressions.json',lambda _:None)
            self.assertEqual(done[0]['status'],'passed')
            self.assertEqual(compile_call.call_count,4) # first, failed last, replay, full affected compile
            replay=next(x for x in a if x['action_phase']=='repair_replay')
            self.assertEqual(replay['original_replay']['status'],'passed')
            final=[x for x in a if x['action_phase']=='compile'][-1]
            self.assertGreater(final['attempt'],replay['attempt'])
            self.assertEqual(final['compilation_scope'],'complete_program')
            self.assertEqual(final['coverage']['exports'],['constant:A.f'])
            self.assertEqual(final['compilation']['status'],'passed')
            self.assertNotIn('final_compile',[x['action_phase'] for x in a])

    def test_restored_final_compile_does_not_infer_missing_evidence(self):
        b,c,pv=self.setup_run()
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'ask',side_effect=self.reply()),patch.object(runner,'compile_crate',wraps=runner.compile_crate) as compile_call:
            w=Path(d);runner.search(b,None,c,pv,w,Executor(w/'cmd'),None,[],[],w/'regressions.json',lambda _:None)
            state=read(w/'segmented-checkpoint.json');state.update(phase='final_compile',status='active')
            save(w/'segmented-checkpoint.json',state);before=compile_call.call_count
            a,done=runner.search(b,None,c,pv,w,Executor(w/'resume'),None,[],[],w/'regressions.json',lambda _:None)
            self.assertEqual(compile_call.call_count,before+1)
            self.assertEqual(done[0]['status'],'passed')
            self.assertEqual(a[-2]['action_phase'],'final_compile')

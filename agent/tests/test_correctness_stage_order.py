"""Paper stage order with legacy early-testing settings and executed repair."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from i2r_agent.common import Executor, read, save
from i2r_agent.segmented_config import configure, origins
from i2r_agent.segmented_v8 import search
from i2r_agent import segmented_context, task_context
from test_segmented_workflow import source, mapping
from test_v8_workflow import cfg, accept, CONNECTOR


class CorrectnessStageOrder(unittest.TestCase):
    def legacy(self):
        c=cfg();c['v8'].update(correctness_only=True,early_support_tests=True)
        c['segmented']['support_tests']=False
        return c

    def test_mode_forces_stage_order_and_records_actual_origin(self):
        for existing_provenance in (False,True):
            with self.subTest(existing_provenance=existing_provenance):
                original=self.legacy()
                if existing_provenance:
                    original['_configuration_sources']=origins(original,[('legacy fixture',original)])
                else:original.pop('_configuration_sources',None)
                c=configure(original)
                self.assertTrue(original['v8']['early_support_tests'])
                self.assertNotIn('early_support_tests',c['v8'])
                self.assertTrue(c['_configuration_sources']['removed_legacy_settings']['v8.early_support_tests']['value'])
                self.assertNotIn('v8.early_support_tests',c['_configuration_sources']['origins'])
                self.assertTrue(c['segmented']['support_tests'])
                for key in ['segmented.support_tests']:
                    self.assertEqual(c['_configuration_sources']['origins'][key],'derived from v8.correctness_only')
                self.assertEqual(c['_configuration_sources']['effective_fingerprint'],task_context.fingerprint({k:v for k,v in c.items() if k!='_configuration_sources'}))

    def test_legacy_true_never_enters_early_support_but_full_tests_and_replay_execute(self):
        c=configure(self.legacy());b=source();b.update(case='list-index',workflow='segmented-v8')
        provider=Mock();provider.calls=0;provider.usage={}
        frozen={'identity':'paper-stage-order','tests':['#[test] fn source_equations(){assert_eq!(i2r_candidate::h(),1);assert_eq!(i2r_candidate::f(),2);}'],
                'unit_tests':[],'obligations':[{'source':'constant:A.f','test_name':'source_equations'}]}
        def ask(pv,conf,path,p,analysis=False):
            phase=p['controller_state']['phase']
            if phase=='generate':
                n=p['unit']['members'][0].rsplit('.',1)[-1]
                return {'files':{'src/lib.rs':p['current_files']['src/lib.rs']+'\npub fn '+n+'()->u128{'+('1' if n=='h' else 'h()+0')+'}'},'mapping':[mapping(n)]}
            if phase=='repair':
                self.assertEqual(p['repair_issue']['kind'],'support')
                return {'edits':[{'file':'src/lib.rs','old':'h()+0','new':'h()+1'}],
                        'repair_hypothesis':{'cause':'incorrect source offset','evidence':'fixed source f=2 test fails','change':'add source offset','prediction':'same frozen test passes'}}
            return accept(p,c)
        def prepare(state,conf,pv,directory):
            self.assertEqual(set(state['completed']),set(state['partition']['units']))
            save(Path(directory)/(frozen['identity']+'.json'),frozen)
            return frozen
        with tempfile.TemporaryDirectory() as tmp:
            w=Path(tmp);project=w/'testing';project.mkdir()
            (project/'Model.thy').write_text('fixture');(project/'Kernel.thy').write_text('fixture')
            refs={}
            for name in ('ocaml','stage2'):
                path=w/name;path.write_text('#!/bin/sh\nwhile read x; do echo "2 2 2"; done\n');path.chmod(0o755)
                refs[name]={'binary':str(path)}
            save(w/'regressions.json',[])
            with patch('i2r_agent.segmented_v8.ask',side_effect=ask),patch('i2r_agent.segmented_support.prepare',side_effect=prepare) as author,patch('i2r_agent.test_connector.connect',return_value=({'src/lib.rs':CONNECTOR},'fixture')):
                attempts,done=search(b,project,c,provider,w,Executor(w/'commands'),refs,[[9,1,2]],[],w/'regressions.json',lambda _:None)
            phases=[a['action_phase'] for a in attempts]
            self.assertEqual(done[0]['status'],'passed')
            self.assertNotIn('early_support',phases)
            first=phases.index('support')
            self.assertEqual(phases[first-1],'compile')
            self.assertNotIn('refine',phases)
            self.assertNotIn('whole_review',phases)
            self.assertEqual(phases[-1],'finish')
            self.assertEqual(phases[:first].count('generate'),2)
            self.assertEqual(attempts[first]['support']['status'],'support_contract_failed')
            self.assertGreaterEqual(author.call_count,1)
            replay=next(a for a in attempts if a['action_phase']=='repair_replay')
            self.assertEqual(replay['original_replay']['status'],'passed')
            self.assertEqual(read(w/'support-tests/paper-stage-order.json'),frozen)
            tests=next(a['development']['suites'] for a in attempts if a['action_phase']=='test')
            self.assertEqual([r['kind'] for r in tests],['fixed','kernel_fixed'])
            self.assertTrue(all(r['status']=='passed' and set(r['references'])=={'ocaml','stage2'} for r in tests))
            self.assertEqual(tests[1]['candidate']['command'][-1],'--i2r-kernel-check')

    def test_removed_setting_migrates_in_performance_mode_too(self):
        for enabled in (True,False):
            c=cfg();c['v8']['early_support_tests']=enabled
            c=configure(c)
            self.assertNotIn('early_support_tests',c['v8'])
            self.assertEqual(c['_configuration_sources']['removed_legacy_settings']['v8.early_support_tests']['value'],enabled)
            self.assertEqual(configure(c),c)

    def test_old_early_checkpoint_is_explicitly_rejected(self):
        from i2r_agent.common import Failure
        c=configure(self.legacy());provider=Mock()
        with tempfile.TemporaryDirectory() as tmp:
            w=Path(tmp);save(w/'segmented-checkpoint.json',{'phase':'early_support'})
            with self.assertRaises(Failure) as raised:
                search(source(),None,c,provider,w,Executor(w/'commands'),None,[],[],w/'regressions.json',lambda _:None)
            self.assertEqual(raised.exception.code,'removed_checkpoint_stage')
            provider.call.assert_not_called()
            self.assertEqual(read(w/'segmented-checkpoint.json'),{'phase':'early_support'})

    def test_current_phase_prompts_exclude_early_test_authorship(self):
        c=configure(self.legacy());provider=Mock()
        with tempfile.TemporaryDirectory() as tmp,patch('i2r_agent.task_context.Conversation.call',return_value={}) as call:
            for phase in ('generate','repair'):
                segmented_context.ask(provider,c,Path(tmp)/phase,{'controller_state':{'phase':phase,'unit':'u'}})
                system=call.call_args.args[1]
                self.assertIn('do not author or execute early semantic/support tests',system)
                self.assertIn('source-only test authorship',system)
                self.assertIn('original-failure repair replay',system)


if __name__=='__main__':unittest.main()

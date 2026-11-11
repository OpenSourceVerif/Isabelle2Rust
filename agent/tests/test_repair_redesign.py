import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from i2r_agent.common import config,Failure,Executor
from i2r_agent import task_context as tc,repair_state as repair
from i2r_agent.validation import check_suite
from i2r_agent.pipeline import feedback_for
from i2r_agent.knowledge_run import verify_support_issue,search,write_library
from test_task_context import bundle,managed_config

class RepairRedesignTests(unittest.TestCase):
    def test_range_failure_isolated_input_reaches_feedback_without_becoming_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'out';out.write_text('0\n')
            err=Path(d)/'err';err.write_text('I2R_NUMERIC_OVERFLOW')
            rec={'status':'failed','stdout':str(out),'stderr':str(err)}
            failed={'status':'numeric_range_exceeded','outputs':None,'record':rec}
            expected={k:{'record':{},'outputs':[[0],[0]]} for k in ['ocaml','stage2']}
            with patch('i2r_agent.validation.reference_outputs',return_value=expected),patch('i2r_agent.validation.execute',return_value=failed) as execute:
                result=check_suite('fixture',[[0],[2**128-1]],'binary',{},None,15,'fixed')
            self.assertEqual(execute.call_args_list[1].args[1],[[2**128-1]])
            f=repair.compact_feedback(feedback_for({'suites':[result]}))
            self.assertEqual(f['suites'][0]['range_event']['reproductions'][0]['input_bits'],[128])
            self.assertEqual(result['counterexamples'],[])
            self.assertEqual(result['status'],'numeric_range_exceeded')

    def test_format_failure_preserves_behavior_issue_and_compile_does_not_close_it(self):
        b={'files':{'src/lib.rs':'bad'},'mode':'generate','feedback':{'behavior_failure':{'counterexamples':[{'input':[3]}]}}}
        repair.capture(b);identity=b['repair_issue']['id']
        b['feedback']={'status':'missing_patch_version'};repair.capture(b)
        self.assertEqual(b['repair_issue']['id'],identity)
        self.assertEqual(repair.feedback(b)['behavior_failure']['counterexamples'][0]['input'],[3])
        repair.verified(b,'compile','new-version')
        with self.assertRaises(Failure):repair.ensure_acceptible(b)
        repair.verified(b,'behavior','new-version');repair.ensure_acceptible(b)

    def test_adapter_patch_atomic_and_stale_declaration_rejected(self):
        b={'plan':{'adapter':{'declarations':'wrong type','rust_files':{},'rust_root':''}}}
        version='code-'+tc.fingerprint(repair.adapter_snapshot(b))
        reply={'action':'adapt','base_adapter_version':version,'adapter_edits':[{'file':'declarations.thy','old':'wrong','new':'right'}]}
        fixed=repair.adapter_reply(b,reply)
        self.assertEqual(fixed['adapter']['declarations'],'right type')
        self.assertEqual(b['plan']['adapter']['declarations'],'wrong type')
        reply['adapter_edits'].append({'file':'declarations.thy','old':'absent','new':'X'})
        with self.assertRaises(Failure):repair.adapter_reply(b,reply)
        reply['base_adapter_version']='obsolete'
        with self.assertRaises(Failure):repair.adapter_reply(b,reply)

    def test_large_initial_graph_not_repeated_and_exact_turn_remains_readable(self):
        with tempfile.TemporaryDirectory() as d:
            cfg=managed_config();cfg['context_management']['history_characters']=1000
            p=Mock();p.call.return_value={'action':'generate','diagnosis':'One local error','files':{'src/lib.rs':'x'*20000}}
            session=tc.Conversation(Path(d)/'conversation.json',cfg);session.enter('generate')
            session.call(p,'rules',{'program':{'thingol':'graph'*30000}},d)
            for _ in range(7):
                session.enter('generate');session.call(p,'rules',{'feedback':{'status':'one-error'}},d)
            self.assertTrue(session.has_graph())
            self.assertLess(sum(len(x['content']) for x in p.call.call_args.kwargs['messages']),5000)
            exact=[session.archive.get(x.stem) for x in session.archive.directory.glob('turn-*.json')]
            self.assertTrue(any(x['request'].get('program',{}).get('thingol')=='graph'*30000 for x in exact))

    def test_support_issue_not_closed_by_business_or_compile_pass(self):
        b={'files':{'src/lib.rs':'bad'},'mode':'generate','feedback':{'status':'support_contract_failed','test_source':'independent original test'}}
        repair.capture(b);repair.verified(b,'behavior','v2');repair.verified(b,'compile','v2')
        with self.assertRaises(Failure):repair.ensure_acceptible(b)
        repair.verified(b,'support','v2');repair.ensure_acceptible(b)

    def test_identical_failed_adapter_build_is_cached_and_original_error_remains(self):
        cfg=managed_config();cfg['repair']['max_attempts']=3
        p=Mock();p.calls=0;p.phase_calls={'generation':0};p.usage={};requests=[]
        def respond(*args):
            requests.append(args[-1]);p.calls+=1;p.phase_calls['generation']+=1
            return {'action':'adapt','adapter':{'declarations':'BROKEN'}}
        with tempfile.TemporaryDirectory() as d,patch('i2r_agent.knowledge_run.call',side_effect=respond),patch('i2r_agent.knowledge_run.load_adapter',side_effect=Failure('adapter_isabelle_failed','Actual type mismatch')) as loader:
            attempts,survivors=search(bundle(),None,cfg,p,d,Mock(),None,[],[],Path(d)/'r.json',lambda x:None)
            self.assertEqual(loader.call_count,1);self.assertFalse(survivors)
            self.assertEqual(attempts[-1]['development']['status'],'repeated_adapter')
            self.assertIn('Actual type mismatch',json.dumps(requests[-1]['feedback']))
            self.assertIn('BROKEN',(Path(d)/'candidate-01/adapter-changes.diff').read_text())

    def test_original_reproducer_survives_new_failure_and_real_closure_is_logged(self):
        b={'files':{},'mode':'generate','feedback':{'behavior_failure':{'suites':[{'range_event':{'reproductions':[{'input':[2**128-1]}]}}]}}}
        repair.capture(b);identity=b['repair_issue']['id']
        b['feedback']={'behavior_failure':{'suites':[{'counterexamples':[{'input':[5]}]}]}};repair.capture(b)
        self.assertEqual(repair.reproducer_inputs(b),[[2**128-1],[5]])
        with tempfile.TemporaryDirectory() as d:
            attempt={'attempt':1,'action_phase':'connect','development':{'status':'passed','behavior_checked':True}}
            tc.record_attempt(b,attempt,{},None,d,before_issue=identity)
            self.assertNotIn('issue_closed',attempt['repair_event'])
            repair.verified(b,'behavior','v2')
            tc.record_attempt(b,attempt,{},None,d,before_issue=identity)
            self.assertEqual(attempt['repair_event']['issue_closed'],identity)

    def test_support_gate_executes_immutable_test_and_rejects_zero_tests(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cfg=managed_config();executor=Executor(root/'commands')
            b={'files':{'src/lib.rs':'pub fn answer()->i32 { 0 }'},'plan':{'dependencies':{}},'mode':'generate',
               'feedback':{'status':'support_contract_failed','test_source':'#[test] fn source_case(){assert_eq!(i2r_candidate::answer(),42);}'}}
            repair.capture(b);crate=root/'algorithm';write_library(crate,b['files'],b['plan'],{})
            self.assertEqual(verify_support_issue(b,crate,cfg,executor,root/'bad')['status'],'support_contract_failed')
            b['files']['src/lib.rs']='pub fn answer()->i32 { 42 }';write_library(crate,b['files'],b['plan'],{})
            self.assertEqual(verify_support_issue(b,crate,cfg,executor,root/'fixed')['status'],'passed')
            b['repair_issue']['evidence']['test_source']='// no tests'
            self.assertEqual(verify_support_issue(b,crate,cfg,executor,root/'empty')['status'],'support_contract_failed')

    def test_review_requires_actual_change_and_source_resolution(self):
        b={'files':{'src/lib.rs':'bad'},'mode':'generate','feedback':{'diagnosis':'Needless copy'},'connector':{}}
        repair.capture(b);issue=b['repair_issue']['id']
        with self.assertRaises(Failure):repair.review_resolution(b,{'issue_resolution':{'issue_id':issue,'source_basis':'checked'}})
        b['files']['src/lib.rs']='fixed'
        repair.review_resolution(b,{'issue_resolution':{'issue_id':issue,'source_basis':'original value no longer used'}})
        repair.ensure_acceptible(b)

    def test_generic_review_does_not_close_unaddressed_structural_lead(self):
        from i2r_agent.code_quality import findings,validate_review
        files={'src/lib.rs':'fn f(){ let tail:Vec<_> = it.collect(); }'}
        with self.assertRaises(Failure):validate_review(files,{'quality_review':'Everything looks correct'})
        lead=findings(files)[0]
        validate_review(files,{'quality_resolutions':[{'id':lead['id'],'source_operation':'returning owned list','source_cost':'linear result construction','rust_cost':'linear one-time collection','resolution':'retain','reason':'This is the result boundary, not a loop tail rebuild'}]})

if __name__=='__main__':unittest.main()

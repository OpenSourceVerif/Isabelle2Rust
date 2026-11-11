import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from i2r_agent.common import Executor,Failure
from i2r_agent.reference_policy import POLICY,collect
from i2r_agent.validation import check_suite
from i2r_agent import available_references as ar
from i2r_agent.experiment_metrics import aggregate

class AvailableReferenceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.executor=Executor(self.root/'commands');self.inputs=[[1],[2],[3]]
 def binary(self,name,code):
  import sys
  p=self.root/name;p.write_text('#!'+sys.executable+'\nimport sys\nfor line in sys.stdin:\n x=list(map(int,line.split()))\n '+code+'\n');p.chmod(0o755)
  return {'status':'passed','binary':str(p),'availability_policy':POLICY,'timing_protocol':'kernel-v1','kernel_behavior_argument':'--i2r-kernel-check'}
 def bad(self):return {'status':'reference_failed','phase':'export','failure':{'code':'tool_failed','evidence':'retained'},'availability_policy':POLICY}
 def run_suite(self,refs,args=()):
  candidate=self.binary('candidate','print(*x)')
  with patch('i2r_agent.reference_policy.domain',return_value=True),patch('i2r_agent.reference_policy.property_error',return_value=None),patch('i2r_agent.validation.property_error',return_value=None):
   return check_suite('fixture',self.inputs,candidate['binary'],refs,self.executor,3,'fixed',args)
 def test_one_good_one_bad_all_inputs_compared(self):
  result=self.run_suite({'ocaml':self.binary('good','print(*x)'),'stage1':self.bad(),'stage2':self.bad()})
  self.assertEqual(result['status'],'passed');self.assertEqual(result['reference_coverage']['covered'],3)
  self.assertTrue(all(r['available']==['ocaml'] and r['references']['stage2']['failure'] for r in result['reference_coverage']['matrix']))
 def test_all_failed_executes_candidate_without_claiming_diff(self):
  result=self.run_suite({n:self.bad() for n in ['ocaml','stage1','stage2']})
  self.assertEqual(result['status'],'differential_unavailable');self.assertTrue(result['candidate_execution_passed']);self.assertFalse(result['differential_passed']);self.assertEqual(result['reference_coverage']['covered'],0)
  self.assertEqual(Path(result['candidate']['stdout']).read_text().splitlines(),['1','2','3'])
 def test_available_conflict_remains_failure(self):
  with self.assertRaises(Failure) as caught:self.run_suite({'ocaml':self.binary('good','print(*x)'),'stage2':self.binary('wrong','print(x[0]+1)')})
  self.assertEqual(caught.exception.code,'oracle_conflict');self.assertEqual(caught.exception.evidence['input'],[1])
 def test_single_failed_input_is_not_dropped(self):
  result=self.run_suite({'ocaml':self.binary('partial','sys.exit(1) if x==[2] else print(*x)'),'stage2':self.bad()})
  self.assertEqual(result['status'],'differential_unavailable');matrix=result['reference_coverage']['matrix'];self.assertEqual([r['input'] for r in matrix],self.inputs);self.assertEqual([r['available'] for r in matrix],[['ocaml'],[],['ocaml']]);self.assertEqual(result['reference_coverage']['covered'],2)
  self.assertTrue(result['references']['ocaml']['isolated_after_failure']);self.assertTrue(matrix[1]['references']['ocaml']['record'])
 def test_other_reference_covers_failed_input(self):
  result=self.run_suite({'ocaml':self.binary('partial','sys.exit(1) if x==[2] else print(*x)'),'stage2':self.binary('good','print(*x)')})
  self.assertEqual(result['status'],'passed');self.assertEqual(result['reference_coverage']['matrix'][1]['available'],['stage2'])
 def test_kernel_is_actually_executed_and_mode_can_be_unavailable(self):
  ref=self.binary('good','sys.exit(1) if "--i2r-kernel-check" not in sys.argv else print(*x)')
  result=self.run_suite({'ocaml':ref},('--i2r-kernel-check',));self.assertEqual(result['status'],'passed')
  ref.pop('kernel_behavior_argument');result=self.run_suite({'ocaml':ref},('--i2r-kernel-check',));self.assertEqual(result['status'],'differential_unavailable')
 def test_reference_export_failure_does_not_skip_ocaml(self):
  calls=[];export=self.root/'export';export.mkdir();(export/'x.ocaml').write_text('source')
  def export_target(project,cfg,work,executor,target):
   calls.append(target)
   if target=='Rust':raise Failure('tool_failed','Rust backend error',{'stderr':'retained'})
   return export
  with patch.object(ar,'export_target',side_effect=export_target),patch.object(ar,'compile_ocaml_reference',return_value={'status':'passed','binary':'executed-test-fixture'}):
   r=ar.prepare(self.root,{},self.root/'prepare',self.executor)
  self.assertEqual(calls,['Rust','OCaml']);self.assertEqual(r['ocaml']['status'],'passed');self.assertEqual(r['stage2']['status'],'blocked_dependency')
 def test_stage1_compile_failure_does_not_skip_optimizer(self):
  export=self.root/'exports';export.mkdir();(export/'Cargo.toml').write_text('');(export/'x.ocaml').write_text('')
  with patch.object(ar,'export_target',return_value=export),patch.object(ar,'setup_rust',return_value=self.root/'stage1'),patch.object(ar,'compile_rust_reference',side_effect=[{'status':'compile_failed','checks':{'build':{'status':'failed'}}},{'status':'passed','binary':'stage2'}]),patch.object(ar,'compile_ocaml_reference',return_value={'status':'passed','binary':'ocaml'}),patch.object(ar.tool_sources,'repository',return_value=self.root),patch.object(ar,'cargo',return_value=['cargo']),patch.object(self.executor,'run',return_value={'status':'passed'}) as run:
   r=ar.prepare(self.root,{'tools':{},'budgets':{'build_seconds':30}},self.root/'prepare',self.executor)
  self.assertEqual(r['stage1']['status'],'compile_failed');self.assertEqual(r['stage2']['status'],'passed');self.assertEqual(run.call_count,2)
 def test_real_source_tests_and_generation_finish_with_no_reference(self):
  from unittest.mock import Mock
  from test_segmented_workflow import source,mapping
  from test_v8_workflow import cfg,accept,CONNECTOR
  from i2r_agent.segmented_config import configure
  from i2r_agent.segmented_v8 import search
  from i2r_agent.common import save
  c=cfg();c['v8']['correctness_only']=True;c['testing']['reference_policy']=POLICY;c=configure(c)
  bundle=source();bundle.update(case='list-index',workflow='segmented-v8');provider=Mock();provider.calls=0;provider.usage={}
  frozen={'identity':'no-ref-real-source-tests','tests':['#[test] fn source_equations(){assert_eq!(i2r_candidate::h(),1);assert_eq!(i2r_candidate::f(),2);}'],'unit_tests':[],'obligations':[{'source':'constant:A.f','test_name':'source_equations'}]}
  def ask(pv,conf,path,p,analysis=False):
   if p['controller_state']['phase']=='generate':
    n=p['unit']['members'][0].rsplit('.',1)[-1]
    return {'files':{'src/lib.rs':p['current_files']['src/lib.rs']+'\npub fn '+n+'()->u128{'+('1' if n=='h' else 'h()+1')+'}'},'mapping':[mapping(n)]}
   return accept(p,c)
  def prepare(state,conf,pv,directory):save(Path(directory)/(frozen['identity']+'.json'),frozen);return frozen
  w=self.root/'workflow';w.mkdir();project=w/'testing';project.mkdir();(project/'Model.thy').write_text('fixture');(project/'Kernel.thy').write_text('fixture');save(w/'regressions.json',[])
  with patch('i2r_agent.segmented_v8.ask',side_effect=ask),patch('i2r_agent.segmented_support.prepare',side_effect=prepare),patch('i2r_agent.test_connector.connect',return_value=({'src/lib.rs':CONNECTOR},'fixture')):
   attempts,done=search(bundle,project,c,provider,w,Executor(w/'commands'),{n:self.bad() for n in ['ocaml','stage1','stage2']},[[9,1,2]],[],w/'regressions.json',lambda _:None)
  self.assertEqual(done[0]['status'],'passed');self.assertEqual(done[0]['support_evidence']['status'],'passed')
  self.assertEqual([s['status'] for s in done[0]['differential_suites']],['differential_unavailable']*2)
  self.assertFalse(any(a['action_phase']=='repair' for a in attempts));provider.call.assert_not_called()
 def test_unavailable_is_generation_success_not_agent_failure(self):
  rows=[{'frozen_identity':'v8','status':'generated_reference_unavailable','seconds':1,'generation_success':True,'verified_end_to_end':False}]
  result=aggregate(rows);self.assertEqual((result['passed'],result['generation_success'],result['agent_generation_failed'],result['reference_unavailable']),(0,1,0,1))

if __name__=='__main__':unittest.main()

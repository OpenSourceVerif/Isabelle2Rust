import tempfile,unittest
from pathlib import Path
from copy import deepcopy
from unittest.mock import Mock,patch
from i2r_agent.common import Executor,Failure,save,read
from i2r_agent.segmented_config import configure,rust_config
from i2r_agent.source_stage_outcomes import collect,facts,after_source_failure
from i2r_agent.reference_policy import POLICY
from test_translation_workflow import cfg,CONNECTOR
from test_segmented_workflow import source,mapping

class SourceStageOutcomeTests(unittest.TestCase):
 def setUp(self):
  c=cfg();c['translation']['correctness_only']=True;c['testing']['reference_policy']=POLICY;self.cfg=configure(c);self.rc=rust_config({},c)
  b=source();b['case']='list-index';self.state={'files':{'src/lib.rs':'pub fn h()->u128{1} pub fn f()->u128{h()+1}'},'mapping':[mapping('h'),mapping('f')],'rust_config':self.rc,'bundle':b,'partition':{'units':{'u':{}}},'completed':['u'],'phase':'support','connector':{},'repair_issues':[],'support_evidence':{}}
 def refs(self,w):
  p=w/'reference';p.write_text('#!/bin/sh\nwhile read x; do echo "2 2 2"; done\n');p.chmod(0o755)
  return {n:{'status':'passed','binary':str(p),'availability_policy':POLICY,'timing_protocol':'kernel-v1','kernel_behavior_argument':'--i2r-kernel-check'} for n in ['ocaml','stage1','stage2']}
 def test_author_failure_reuses_recorded_differentials_without_new_calls(self):
  with tempfile.TemporaryDirectory() as tmp:
   self.state['differential_suites']=[{'status':'passed','kind':kind} for kind in ['fixed','kernel_fixed','generated_differential','kernel_generated_differential']]
   w=Path(tmp);project=w/'testing';project.mkdir();save(w/'segmented-checkpoint.json',self.state);save(w/'development-inputs.json',{'fixed':[[9,1,2]],'generated':[[9,1,2]]});save(w/'regressions.json',[]);before=(w/'segmented-checkpoint.json').read_bytes();provider=Mock()
   with patch('i2r_agent.test_connector.connect',return_value=({'src/lib.rs':CONNECTOR},'fixture')) as connector,patch('i2r_agent.segmented_support.prepare',side_effect=AssertionError('Must not restart authoring')):
    result=after_source_failure(w,self.cfg,provider,Executor(w/'commands'),self.refs(w),project,Failure('support_output_budget_exhausted','Preserved two raw author length failures'))
   connector.assert_not_called();provider.call.assert_not_called();self.assertTrue(result['generation_success']);self.assertEqual(result['source_test_production']['status'],'failed_or_partial');self.assertEqual(result['source_test_validation']['status'],'not_executed');self.assertEqual(result['differential_status'],'passed');self.assertEqual(len(result['differential']['suites']),4);self.assertFalse(result['verified_end_to_end']);self.assertEqual((w/'segmented-checkpoint.json').read_bytes(),before)
 def test_export_match_does_not_clear_source_counterexample_or_generic_interface(self):
  for status in ['support_contract_failed','support_test_compile_failed','support_coverage_missing']:
   state=deepcopy(self.state);state['support_evidence']={'status':status,'frozen_identity':'original','counterexample':{'expected':99,'actual':2},'obligations':[{'source':'constant:A.f'}]}
   result=facts(state,'passed',{'status':'passed','suites':[]},{'code':status})
   self.assertFalse(result['verified_end_to_end']);self.assertFalse(result['source_test_success']);self.assertTrue(result['source_test_validation']['conflicting']);self.assertEqual(result['source_test_validation']['evidence'],state['support_evidence']);self.assertEqual(result['candidate_defect_status'],'source_conflict_unresolved')
 def test_real_differential_counterexample_remains_candidate_defect(self):
  with tempfile.TemporaryDirectory() as tmp:
   w=Path(tmp);state=deepcopy(self.state);state['files']['src/lib.rs']='pub fn h()->u128{1} pub fn f()->u128{0}';provider=Mock();save(w/'regressions.json',[])
   with patch('i2r_agent.test_connector.connect',return_value=({'src/lib.rs':CONNECTOR},'fixture')):
    d=collect(state,w,self.cfg,provider,Executor(w/'commands'),self.refs(w),{'fixed':[[9,1,2]],'generated':[]},w/'regressions.json',w/'supplement')
   self.assertEqual(d['status'],'mismatch');self.assertTrue(any(s['counterexamples'] for s in d['suites']));self.assertEqual(facts(state,'passed',d,{'code':'support_test_compile_failed'})['candidate_defect_status'],'observed_differential_or_compile_failure')
 def test_no_connector_budget_reports_unavailable_without_retry_or_fake_pass(self):
  with tempfile.TemporaryDirectory() as tmp:
   w=Path(tmp);save(w/'regressions.json',[])
   with patch('i2r_agent.test_connector.connect',side_effect=Failure('budget_exhausted','No remaining request allocation')) as connector:
    d=collect(self.state,w,self.cfg,Mock(),Executor(w/'commands'),self.refs(w),{'fixed':[[9,1,2]],'generated':[]},w/'regressions.json',w/'supplement')
   self.assertEqual(connector.call_count,1);self.assertEqual(d['status'],'not_run_budget');self.assertEqual(d['suites'],[]);self.assertFalse(facts(self.state,'passed',d,{'code':'support_output_budget_exhausted'})['verified_end_to_end'])
if __name__=='__main__':unittest.main()

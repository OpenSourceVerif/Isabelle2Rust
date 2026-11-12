import tempfile,unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock,patch
from i2r_agent.common import Executor,Failure,read,save
from i2r_agent.segmented_config import configure,rust_config,materialize
from i2r_agent.segmented_support import execute
from i2r_agent.segmented_test_audit import adjudicate,invariants
from i2r_agent.support_binding_context import prepare,restrict
from i2r_agent.task_context import fingerprint
from test_translation_workflow import cfg
from test_segmented_workflow import source

class FocusedBindingTests(unittest.TestCase):
 def setUp(self):
  c=cfg();c['translation']['correctness_only']=True;self.cfg=configure(c);self.rc=rust_config({},self.cfg)
  self.code='pub enum Tree<A>{Leaf,Node(Box<Tree<A>>,A,Box<Tree<A>>)} pub fn tree_case<A,R,F:FnOnce(Tree<A>,A,Tree<A>)->R>(f:F,t:Tree<A>)->R{match t{Tree::Node(l,x,r)=>f(*l,x,*r),Tree::Leaf=>panic!()}}'
  self.bad='use i2r_candidate::{Tree,tree_case}; #[test] fn owned(){let t=Tree::Node(Box::new(Tree::Leaf),33u128,Box::new(Tree::Leaf));let out=tree_case(|l,x,r|{match *l{Tree::Leaf=>(),_=>panic!()};match *r{Tree::Leaf=>(),_=>panic!()};x},t);assert_eq!(out,33);}'
  self.other='#[test] fn sibling(){assert_eq!(1+1,2);}'
  self.frozen={'identity':'binding-interface-fixture','tests':[self.bad,self.other],'unit_tests':[],'obligations':[{'source':'constant:A.f','test_name':'__i2r_source_contract_0::owned','expected_basis':'source constructor payload33'},{'source':'constant:A.h','test_name':'__i2r_source_contract_1::sibling','expected_basis':'source arithmetic'}]}
  self.state={'files':{'src/lib.rs':self.code},'mapping':[{'source':'constant:A.f','rust_item':'tree_case'},{'source':'constant:A.h','rust_item':'Tree'}],'bundle':source(),'rust_config':self.rc}
  self.proposal={'action':'binding_fix','reason':'The closure signature passes Tree values; only the test incorrectly dereferences them. Preserve every assertion and literal.','edits':[{'kind':'integration','index':0,'old':'match *l','new':'match l'},{'kind':'integration','index':0,'old':'match *r','new':'match r'}]}
 def test_real_e0614_one_diagnosis_full_suite_execution_and_negative(self):
  with tempfile.TemporaryDirectory() as tmp:
   w=Path(tmp);ex=Executor(w/'commands');crate=materialize(w/'candidate',self.state['files'],self.rc);original=(crate/'src/lib.rs').read_bytes()
   failed=execute(self.frozen,crate,self.rc,self.cfg,ex);self.assertEqual(failed['status'],'support_test_compile_failed');self.assertIn('E0614',failed['diagnostic'])
   with patch('i2r_agent.segmented_test_audit.source_review',return_value=self.proposal) as classify:
    r=adjudicate(self.frozen,failed,self.state,self.cfg,Mock(),w/'audit')
   self.assertEqual(classify.call_count,1);fixed=r['frozen'];self.assertFalse(fixed['binding_audit']['second_model_review']);self.assertEqual(fixed['obligations'],self.frozen['obligations']);self.assertEqual(fixed['tests'][1],self.other);self.assertEqual(invariants(fixed['tests'][0]),invariants(self.bad))
   executed=execute(fixed,crate,self.rc,self.cfg,ex);self.assertEqual((executed['status'],executed['tests_passed']),('passed',2));self.assertEqual((crate/'src/lib.rs').read_bytes(),original)
   materialize(crate,{'src/lib.rs':self.code.replace('f(*l,x,*r)','{let _=f(*l,x,*r);panic!()}')},self.rc)
   self.assertEqual(execute(fixed,crate,self.rc,self.cfg,ex)['status'],'support_contract_failed')
   before=deepcopy(self.frozen)
   wrong={**self.proposal,'edits':[{'kind':'integration','index':0,'old':'assert_eq!(out,33)','new':'assert_eq!(out,34)'}]}
   with patch('i2r_agent.segmented_test_audit.source_review',return_value=wrong),self.assertRaises(Failure) as raised:adjudicate(self.frozen,failed,self.state,self.cfg,Mock(),w/'wrong')
   self.assertEqual(raised.exception.code,'support_oracle_change');self.assertEqual(before,self.frozen)
 def test_unknown_location_fallback_and_exact_optional_pages(self):
  failure={'status':'support_test_compile_failed','diagnostic':'error[E0614]: value\n --> tests/source_contract_0.rs:3:1','frozen_identity':self.frozen['identity'],'immutable_test_sources':self.frozen['tests'],'obligations':self.frozen['obligations']}
  with tempfile.TemporaryDirectory() as tmp:
   payload,pages=prepare(self.frozen,failure,self.state,self.cfg,tmp);scope=payload['focused_binding_scope']
   self.assertEqual(scope['integration_indices'],[0]);self.assertEqual(payload['frozen']['integration_tests'],[{'index':0,'source':self.bad}]);self.assertNotIn('immutable_test_sources',payload['failure']);self.assertNotIn('obligations',payload['failure'])
   archive=read(scope['archive']);self.assertEqual(archive,{'frozen':self.frozen,'failure':failure})
   self.assertEqual(''.join(p['text'] for p in pages if p.get('artifact')=='integration:1'),self.other)
   self.assertEqual({p['source'] for p in pages if p.get('required_for_group')},{'constant:A.f'})
   with self.assertRaises(Failure):restrict({'edits':[{'kind':'integration','index':1}]},scope)
   unknown={**failure,'diagnostic':'unlocated type inference failure'};fallback,_=prepare(self.frozen,unknown,self.state,self.cfg,tmp);self.assertEqual(fallback['focused_binding_scope']['integration_indices'],[0,1])
 def test_optimization_mode_retains_its_existing_second_review(self):
  c=deepcopy(self.cfg);c['translation']['correctness_only']=False
  with tempfile.TemporaryDirectory() as tmp,patch('i2r_agent.segmented_test_audit.source_review',side_effect=[self.proposal,{'action':'accept','review':'original assertions and bindings preserved'}]) as call:
   r=adjudicate(self.frozen,{'status':'support_test_compile_failed','diagnostic':'E0614'},self.state,c,Mock(),tmp)
  self.assertEqual(call.call_count,2);self.assertEqual(r['action'],'binding_fix')
if __name__=='__main__':unittest.main()

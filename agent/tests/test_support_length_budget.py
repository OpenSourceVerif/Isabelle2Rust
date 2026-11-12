import tempfile,unittest
from pathlib import Path
from i2r_agent.common import Failure
from i2r_agent.segmented_support import source_review,author_group_scope
from test_translation_workflow import cfg

class SourceLengthBudget(unittest.TestCase):
 def test_two_length_failures_persist_across_attempts_and_feedback(self):
  class Provider:
   calls=0
   def call(self,*args,**kwargs):
    self.calls+=1
    raise Failure('incomplete_response','length',{'finish_reason':'length','response':str(self.calls),'partial_characters':0})
  provider=Provider();settings=cfg()
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)
   for i,expected in enumerate(['incomplete_response','support_output_budget_exhausted','support_output_budget_exhausted']):
    with self.assertRaises(Failure) as caught:
     source_review({'task':'same source obligations','prior_authoring_failure':{'transport_path':str(i)}},[],settings,provider,root/str(i),failure_ledger=root/'ledger.json')
    self.assertEqual(caught.exception.code,expected)
   self.assertEqual(provider.calls,2)
   # A genuinely different obligation scope must not inherit another group's failures.
   with self.assertRaises(Failure) as caught:source_review({'task':'different obligations'},[],settings,provider,root/'other',failure_ledger=root/'ledger.json')
   self.assertEqual(caught.exception.code,'incomplete_response');self.assertEqual(provider.calls,3)
 def test_group_cache_scope_includes_candidate_prompt_and_obligations(self):
  state={'files':{'src/lib.rs':'fn f(){}'},'mapping':[],'rust_config':{}}
  payload={'coverage_requirements':[{'source':'f','category':'public_behavior'}],'test_framework':{'kind':'x'}}
  original=author_group_scope(state,payload,[],'prompt')
  self.assertNotEqual(original,author_group_scope({**state,'files':{'src/lib.rs':'fn g(){}'}},payload,[],'prompt'))
  self.assertNotEqual(original,author_group_scope(state,{**payload,'coverage_requirements':[]},[],'prompt'))
  self.assertNotEqual(original,author_group_scope(state,payload,[],'other prompt'))
if __name__=='__main__':unittest.main()

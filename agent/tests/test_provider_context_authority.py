"""Large legal requests reach the provider; real HTTP limits are retained once."""
import io,json,tempfile,urllib.error,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from i2r_agent.common import Failure,read
from i2r_agent.segmented_config import configure
from i2r_agent.task_context import Conversation
from i2r_agent.segmented_context import ask
from i2r_agent.segmented_support import source_review
from i2r_agent.provider import Provider
from i2r_agent.semantic_components import from_analysis
from test_v8_workflow import cfg
from test_segmented_workflow import source

class ProviderContextAuthority(unittest.TestCase):
 def settings(self):
  c=cfg();c['v8']['correctness_only']=True;c=configure(c);c['budgets']['max_model_calls']=40
  c['segmented']['max_request_characters']=180000;c['preprocessing']['max_context_chars']=180000
  return c
 def test_large_analysis_and_repair_reach_provider_mock(self):
  c=self.settings();pv=Mock();pv.call.return_value={'action':'algorithm_issue','reason':'fixture'}
  with tempfile.TemporaryDirectory() as tmp:
   for name,analysis in [('analysis',True),('repair',False)]:
    p={'controller_state':{'phase':name,'unit':None},'exact_material':'z'*200000}
    ask(pv,c,Path(tmp)/name,p,analysis=analysis)
    self.assertGreater(sum(len(m['content']) for m in pv.call.call_args.kwargs['messages']),180000)
  self.assertEqual(pv.call.call_count,2)
 def test_large_author_and_binding_payload_reach_provider(self):
  c=self.settings();pv=Mock();pv.call.return_value={'action':'algorithm_issue','reason':'fixture'}
  with tempfile.TemporaryDirectory() as tmp:
   for kind in ['author','binding']:
    payload={'task':kind,'exact_tests':'t'*200000}
    if kind=='binding':payload['focused_binding_scope']={'policy':'compiler-group-binding-context-v1'}
    source_review(payload,[],c,pv,Path(tmp)/kind)
    self.assertGreater(len(pv.call.call_args.args[1]),180000)
  self.assertEqual(pv.call.call_count,2)
 def test_resumed_conversation_does_not_reject_current_exact_request(self):
  c=self.settings();pv=Mock();pv.call.return_value={}
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'conversation.json';session=Conversation(path,c);session.enter('repair');session.call(pv,'system',{'first':'read context'},Path(tmp)/'first')
   resumed=Conversation(path,c);resumed.enter('repair');resumed.call(pv,'system',{'exact':'r'*200000},Path(tmp)/'resumed')
   self.assertGreater(len(pv.call.call_args.args[1]),180000);self.assertEqual(resumed.state['compactions'],2)
 def test_http_context_rejection_is_archived_once_without_retry_or_false_pass(self):
  c=self.settings();body=json.dumps({'error':{'message':'maximum context length exceeded','type':'invalid_request_error'}}).encode()
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);provider=Provider(c,root/'model')
   with patch('i2r_agent.provider.credential',return_value='fake-key'),patch('i2r_agent.provider.urllib.request.urlopen',side_effect=lambda *a,**kw:(_ for _ in ()).throw(urllib.error.HTTPError('https://fixture',400,'Bad Request',{},io.BytesIO(body)))) as http,self.assertRaises(Failure) as raised:
    source_review({'exact_material':'x'*200000},[],c,provider,root/'author')
   self.assertEqual(raised.exception.code,'provider_error');self.assertEqual(http.call_count,1);self.assertEqual(provider.calls,1)
   error=read(root/'model/001/error.json');self.assertEqual(error['http_status'],400);self.assertIn('maximum context length',error['detail']);self.assertFalse(raised.exception.evidence['automatic_retry']);self.assertFalse((root/'model/002').exists());self.assertFalse((root/'model/001/response.json').exists())
 def test_source_characters_alone_do_not_invalidate_legal_joint_group(self):
  c=self.settings();model=source()['source_model'];model['entities']['constant:A.f']['long_evidence']='x'*200000
  result=from_analysis(model,[],None,c)
  self.assertEqual(result['grouping_decision']['method'],'program_single_group')
  self.assertGreater(result['grouping_decision']['measured']['source_characters'],16000)
if __name__=='__main__':unittest.main()

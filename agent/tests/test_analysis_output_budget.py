import io,json,tempfile,unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock,patch
from i2r_agent.common import Failure,config,read
from i2r_agent.provider import Provider
from i2r_agent import segmented_context as ctx,prepared_identity
from test_segmented_workflow import source
from test_v8_workflow import cfg

class AnalysisOutputBudget(unittest.TestCase):
    def test_analysis_effort_is_explicit_and_does_not_leak_into_generation(self):
        c=cfg();c['model']['name']='deepseek-flash';c['generation']['thinking']='enabled'
        c['preprocessing']['model']={**c['preprocessing'].get('model',{}),'thinking':'enabled','reasoning_effort':'low','max_output_tokens':32768}
        raw={'choices':[{'finish_reason':'stop','message':{'content':'{}'}}],'usage':{}}
        with tempfile.TemporaryDirectory() as tmp,patch('i2r_agent.provider.credential',return_value='test'),patch('urllib.request.urlopen',side_effect=lambda *a,**k:io.BytesIO(json.dumps(raw).encode())):
            p=Provider(c,tmp);p.call('s','p',options=c['preprocessing']['model'],phase='preprocessing');p.call('s','p',phase='generation')
            analysis=read(Path(tmp)/'001/request.json');generation=read(Path(tmp)/'002/request.json')
            self.assertEqual(analysis['reasoning_effort'],'low');self.assertEqual(analysis['thinking'],{'type':'enabled'});self.assertEqual(analysis['max_tokens'],32768)
            self.assertNotIn('reasoning_effort',generation);self.assertEqual(generation['thinking'],{'type':'enabled'})
            with self.assertRaises(Failure):p.call('s','p',options={'reasoning_effort':'medium'})
            self.assertEqual(p.calls,2)

    def test_even_complete_looking_length_json_is_unvalidated_and_archived(self):
        c=cfg();content='{"boundaries":[],"analysis_coverage":[]}'
        raw={'choices':[{'finish_reason':'length','message':{'content':content}}],'usage':{'completion_tokens':32768,'completion_tokens_details':{'reasoning_tokens':32700}}}
        with tempfile.TemporaryDirectory() as tmp,patch('i2r_agent.provider.credential',return_value='test'),patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(raw).encode())):
            p=Provider(c,tmp)
            with self.assertRaises(Failure) as caught:p.call('s','p',phase='preprocessing')
            self.assertEqual(caught.exception.code,'incomplete_response');self.assertEqual(caught.exception.evidence['finish_reason'],'length')
            self.assertEqual((Path(tmp)/'001/partial-content.txt').read_text(),content)
            self.assertEqual(p.usage['completion_tokens'],32768)

    def test_two_same_material_length_failures_stop_without_committing_plan(self):
        c=cfg();c['v8']['correctness_only']=True;b=source();b['workflow']='segmented-v8';calls=[]
        def length(provider,conf,path,payload,analysis=False):
            calls.append(deepcopy(payload))
            raise Failure('incomplete_response','Completion ended with length',{'finish_reason':'length'})
        with tempfile.TemporaryDirectory() as tmp,patch.object(ctx,'ask',side_effect=length):
            with self.assertRaises(Failure) as caught:ctx.analyze(b,c,Mock(),Path(tmp))
            self.assertEqual(caught.exception.code,'analysis_output_budget_exhausted');self.assertEqual(len(calls),2)
            self.assertEqual(calls[0]['source_pages'],calls[1]['source_pages']);self.assertFalse((Path(tmp)/'analysis.json').exists())
            self.assertTrue((Path(tmp)/'analysis-0002/failure.json').exists())

    def test_new_source_material_has_its_own_bounded_length_counter(self):
        c=cfg();b=source();b['workflow']='segmented-v8';calls=[]
        def reply(provider,conf,path,payload,analysis=False):
            calls.append(deepcopy(payload))
            if len(calls)==2:
                return {'request_pages':[payload['page_catalog'][0]['id']],
                        'reading_notes':{p['id']:'Source equation retained for this page.' for p in payload['source_pages']}}
            raise Failure('incomplete_response','Completion ended with length',{'finish_reason':'length'})
        with tempfile.TemporaryDirectory() as tmp,patch.object(ctx,'ask',side_effect=reply):
            with self.assertRaises(Failure) as caught:ctx.analyze(b,c,Mock(),Path(tmp))
            self.assertEqual(caught.exception.code,'analysis_output_budget_exhausted');self.assertEqual(len(calls),4)
            states=read(Path(tmp)/'length-failures.json')['states']
            self.assertEqual(sorted(map(len,states.values())),[1,2])

    def test_effort_setting_changes_prepared_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=cfg();before=prepared_identity.identity(tmp,c);d=deepcopy(c);d['preprocessing'].setdefault('model',{})['reasoning_effort']='low'
            self.assertNotEqual(before,prepared_identity.identity(tmp,d))

import io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from i2r_agent.common import Failure,config
from i2r_agent.provider import Provider
from i2r_agent.v8_response import normalize

class ResponseEnvelope(unittest.TestCase):
    def test_optional_null_is_omission_without_nested_changes(self):
        original={'rust_config':{'target':None},'edits':None,'test_source':None,'unit_tests':[{'file':'src/lib.rs','source':'#[test] fn check() {}'}], 'obligations':[{'source':'constant:a','case':None}]}
        result,log=normalize(original)
        self.assertEqual(log['omitted_optional_null_fields'],['edits','test_source'])
        self.assertEqual(result['rust_config'],original['rust_config'])
        self.assertEqual(result['obligations'],original['obligations'])
        self.assertEqual(result['unit_tests'],original['unit_tests'])
        self.assertIn('edits',original)
        self.assertNotIn('edits',result)

    def test_malformed_envelopes_are_controlled_failures(self):
        for response in [[],{'rust_config':[]},{'edits':[None]},{'edits':[{'file':'x','old':None,'new':'x'}]}, {'mapping':[{'source':[], 'rust':'x'}]}, {'request_entities':[None]}, {'unit_complete':'true'}, {'test_source':[]}, {'obligations':[{'source':[]}]}, {'performance_analysis':{'classification':[]}}]:
            with self.subTest(response=response),self.assertRaises(Failure) as error:normalize(response)
            self.assertEqual(error.exception.code,'invalid_model_response')

    def test_provider_preserves_raw_and_limits_normalization_to_v8(self):
        reply={'action':'generate','rust_config':None,'edits':[{'file':'src/lib.rs','old':'','new':'// null stays literal'}]}
        raw={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(reply)}}]}
        for workflow in ['segmented-v8','segmented-v7']:
            with tempfile.TemporaryDirectory() as tmp,patch('i2r_agent.provider.credential',return_value='test'),patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(raw).encode())):
                cfg=config();cfg['generation']['workflow']=workflow
                result=Provider(cfg,tmp).call('system','prompt')
                self.assertEqual(json.loads((Path(tmp)/'001/response.json').read_text()),raw)
                self.assertEqual(result['edits'],reply['edits'])
                if workflow=='segmented-v8':
                    self.assertNotIn('rust_config',result)
                    self.assertEqual(json.loads((Path(tmp)/'001/response-normalizations.json').read_text())['omitted_optional_null_fields'],['rust_config'])
                else:self.assertEqual(result,reply)

    def test_normalization_does_not_waive_test_coverage(self):
        from i2r_agent.v8_support import validate_records
        result,_=normalize({'test_source':None,'unit_tests':None,'obligations':[{'source':'constant:a'}]})
        with self.assertRaises(Failure):validate_records(result,{'constant:a':{}})

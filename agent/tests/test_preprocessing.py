import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,Mock
from i2r_agent.common import config, Executor, Failure
from i2r_agent.preprocessing import preprocess
from i2r_agent.generation import intern_program
from i2r_agent.validation import execute,check_suite
from i2r_agent.provider import Provider

class PreprocessingEvidenceTests(unittest.TestCase):


    def test_shared_graph_codec_roundtrips_repeated_terms(self):
        term={'kind':'application','children':[{'symbol':'constant:M.observe'}]*100}
        programs=[{'nodes':[{'id':'constant:M.observe','term':term} for _ in range(200)]}]
        packed=intern_program(programs)
        def expand(value):
            if isinstance(value,dict) and set(value)=={'$ref'}:return expand(packed['table'][value['$ref']])
            if isinstance(value,dict):return {k:expand(v) for k,v in value.items()}
            if isinstance(value,list):return [expand(v) for v in value]
            return value
        self.assertEqual(expand(packed['root']),programs)
        self.assertLess(len(json.dumps(packed)),len(json.dumps(programs))//4)

    def test_range_exceeded_is_not_success_or_behavioral_counterexample(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bad=root/'bad';good=root/'good'
            bad.write_text('#!/usr/bin/env python3\nimport sys\nprint("I2R_NUMERIC_OVERFLOW",file=sys.stderr)\nsys.exit(1)\n')
            good.write_text('#!/usr/bin/env python3\nimport sys\nfor x in sys.stdin:print(1)\n')
            bad.chmod(0o755);good.chmod(0o755)
            refs={k:{'binary':str(good)} for k in ['ocaml','stage2']}
            result=check_suite('ackermann',[[0,0]],str(bad),refs,Executor(root/'logs'),5,'range')
            self.assertEqual(result['status'],'numeric_range_exceeded')
            self.assertEqual(result['counterexamples'],[])
            self.assertIsNone(result['failures'])

    def test_provider_preserves_raw_response_for_narrow_json_recovery(self):
        import io
        raw={'choices':[{'finish_reason':'stop','message':{'content':'{"a": 1}}'}}]}
        with tempfile.TemporaryDirectory() as tmp, patch('i2r_agent.provider.credential',return_value='test'), patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(raw).encode())):
            provider=Provider(config(),tmp)
            self.assertEqual(provider.call('s','p'),{'a':1})
            self.assertEqual(json.loads((Path(tmp)/'001/response.json').read_text()),raw)
            self.assertTrue((Path(tmp)/'001/format-normalizations.json').exists())

if __name__=='__main__':unittest.main()

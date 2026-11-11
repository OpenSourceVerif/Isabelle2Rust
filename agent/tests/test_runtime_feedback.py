import http.client
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from i2r_agent.common import Failure,config
from i2r_agent.pipeline import feedback_for
from i2r_agent.provider import Provider

class RuntimeFeedbackTests(unittest.TestCase):
    def test_incomplete_http_response_is_recorded_without_retry(self):
        with tempfile.TemporaryDirectory() as tmp,patch('i2r_agent.provider.credential',return_value='test'),patch('urllib.request.urlopen',side_effect=http.client.IncompleteRead(b'')) as transport:
            provider=Provider(config(),tmp)
            with self.assertRaises(Failure) as error:provider.call('system','JSON')
            self.assertEqual(error.exception.code,'provider_error')
            self.assertEqual(transport.call_count,1)
            self.assertEqual(provider.calls,1)
            self.assertEqual(json.loads((Path(tmp)/'001/error.json').read_text())['type'],'IncompleteRead')
    def test_model_gets_runtime_panic_text_and_log_keeps_timer_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'stderr';p.write_text('I2R_KERNEL_NS 100\nthread main panicked: subtraction underflow\n')
            feedback=feedback_for({'suites':[{'kind':'fixed','counterexamples':[],
                'candidate':{'status':'failed','returncode':101,'stderr':str(p)}}]})
            self.assertIn('subtraction underflow',feedback['runtime_diagnostics'][0]['stderr'])
            self.assertNotIn('I2R_KERNEL_NS',feedback['runtime_diagnostics'][0]['stderr'])
            self.assertIn('I2R_KERNEL_NS',p.read_text())

if __name__=='__main__':unittest.main()

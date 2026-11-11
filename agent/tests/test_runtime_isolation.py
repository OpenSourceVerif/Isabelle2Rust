import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from i2r_agent.validation import check_suite

class RuntimeIsolationTests(unittest.TestCase):
    def test_timeout_after_34_outputs_starts_at_input_35(self):
        inputs=[[n] for n in range(100)]
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'stdout';output.write_text('0\n'*34)
            record={'status':'timeout','stdout':str(output),'stderr':str(Path(tmp)/'stderr')}
            batch={'status':'runtime_failed','record':record,'outputs':None}
            expected={k:{'record':{},'outputs':[[0] for _ in inputs]} for k in ('ocaml','stage2')}
            with patch('i2r_agent.validation.reference_outputs',return_value=expected),patch('i2r_agent.validation.execute',return_value=batch) as execute:
                result=check_suite('fixture',inputs,'binary',{},None,15,'generated_differential')
            self.assertEqual(execute.call_args_list[1].args[1],[[34]])
            self.assertEqual(result['counterexamples'][0]['input'],[34])
            self.assertEqual(result['diagnostic_start_input'],34)

if __name__=='__main__':unittest.main()

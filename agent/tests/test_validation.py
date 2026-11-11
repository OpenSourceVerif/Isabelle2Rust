import json
import tempfile
import unittest
from pathlib import Path

from i2r_agent.common import Executor,Failure,merge
from i2r_agent.suites import fixed,generate,domain,property_error
from i2r_agent.validation import add_regressions,check_suite,reference_outputs
from i2r_agent.generation import intern_program


class ValidationTests(unittest.TestCase):
    def test_explicit_finite_domain_keeps_original_tests_and_matching_workload(self):
        from i2r_agent.suites import scoped_fixed,scoped_inputs,scoped_performance_input,in_numeric_domain
        original=fixed('karatsuba-sqrt')
        self.assertTrue(any(not in_numeric_domain(x,128) for x in original))
        bounded=scoped_fixed('karatsuba-sqrt',128)
        self.assertIn([2**128-2,2**128-1],bounded)
        generated=scoped_inputs('karatsuba-sqrt',200,23,128)
        self.assertEqual(len(generated),200)
        self.assertTrue(all(in_numeric_domain(x,128) and domain('karatsuba-sqrt',x) for x in bounded+generated))
        self.assertEqual(scoped_performance_input('karatsuba-sqrt',128),[2**128-1])
        self.assertEqual(fixed('karatsuba-sqrt'),original)
        self.assertEqual(scoped_inputs('karatsuba-sqrt',200,23,0),generate('karatsuba-sqrt',200,23))

    def test_program_compression_is_lossless(self):
        original=[{'id':'foo','body':{'x':[1,2,3]},'primitive':{'x':[1,2,3]}}]
        packed=intern_program(original)
        def expand(x):
            if isinstance(x,dict) and set(x)=={'$ref'}:return expand(packed['table'][x['$ref']])
            if isinstance(x,dict):return {k:expand(v) for k,v in x.items()}
            if isinstance(x,list):return list(map(expand,x))
            return x
        self.assertEqual(expand(packed['root']),original)

    def test_generated_inputs_respect_domain(self):
        for case in ['list-index','skew-heap','splay-tree','karatsuba-sqrt','shear-sort','list-interleaving','ackermann','transitive-closure','native-word-u64','collections-hashcode']:
            self.assertTrue(all(domain(case,x) for x in fixed(case)+generate(case,100,92)),case)
            self.assertEqual(generate(case,20,1),generate(case,20,1))

    def test_property_detects_wrong_sqrt(self):
        self.assertIsNone(property_error('karatsuba-sqrt',[17],[4,1]))
        self.assertIsNotNone(property_error('karatsuba-sqrt',[17],[4,0]))

    def test_regression_deduplicates_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'regressions.json'
            add_regressions(path,[{'input':[1,2],'expected':[0]}])
            add_regressions(path,[{'input':[1,2],'actual':[9]},{'input':[2]}])
            self.assertEqual(len(json.loads(path.read_text())),2)

    def test_disabled_repair_is_an_explicit_override(self):
        base={'repair':{'enabled':True,'max_attempts':3}}
        self.assertFalse(merge(base,{'repair':{'enabled':False}})['repair']['enabled'])
        self.assertTrue(merge(base,{})['repair']['enabled'])

    def test_reference_conflict_is_not_candidate_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            binaries=[]
            for i,value in enumerate([1,2]):
                p=directory/f'ref{i}'
                p.write_text('#!/usr/bin/env python3\nimport sys\nfor line in sys.stdin:print('+str(value)+')\n');p.chmod(0o755);binaries.append(str(p))
            refs={'ocaml':{'binary':binaries[0]},'stage2':{'binary':binaries[1]}}
            with self.assertRaises(Failure) as error:
                reference_outputs('ackermann',[[0,0]],refs,Executor(directory/'logs'),5)
            self.assertEqual(error.exception.code,'oracle_conflict')

    def test_wrong_candidate_is_captured_as_counterexample(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            good=directory/'good';bad=directory/'bad'
            for p,value in [(good,1),(bad,0)]:
                p.write_text('#!/usr/bin/env python3\nimport sys\nfor line in sys.stdin:print('+str(value)+')\n');p.chmod(0o755)
            refs={'ocaml':{'binary':str(good)},'stage2':{'binary':str(good)}}
            result=check_suite('ackermann',[[0,0]],str(bad),refs,Executor(directory/'logs'),5,'negative_control')
            self.assertEqual(result['status'],'mismatch')
            self.assertEqual(result['counterexamples'][0]['input'],[0,0])


if __name__=='__main__':unittest.main()

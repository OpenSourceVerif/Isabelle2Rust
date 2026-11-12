import tempfile,unittest,re
from pathlib import Path
from i2r_agent.common import ROOT,Executor
from i2r_agent.segmented_config import configure,rust_config,materialize
from i2r_agent.segmented_support import execute,passed_test_names
from test_translation_workflow import cfg

class SupportShouldPanic(unittest.TestCase):
    def test_original_stdout_and_exact_success_status(self):
        output=(ROOT/'tests/fixtures/bubblesort-should-panic-stdout.txt').read_text()
        name='__i2r_source_contract_0::hol_undefined_panics_instead_of_returning_value'
        self.assertEqual(len(re.findall(r'^test ([\w:]+) \.\.\. ok$',output,re.M)),14)
        self.assertEqual(len(passed_test_names(output)),15);self.assertIn(name,passed_test_names(output))
        for tail in [' - should panic ... FAILED',' - should panic ... ignored',' ... FAILED',' ... ignored',' - should panic ... ok trailing',' - should panic extra ... ok']:
            self.assertNotIn(name,passed_test_names('test '+name+tail))
        self.assertEqual(passed_test_names('test wrong_module::same - should panic ... ok'),{'wrong_module::same'})

    def test_real_cargo_expected_panic_failure_ignore_and_disabled_coverage(self):
        c=cfg();c['translation']['correctness_only']=True;c=configure(c);rc=rust_config({},c)
        test='#[test] #[should_panic(expected="source undefined")] fn required(){let _=i2r_candidate::f();}\n#[test] fn incidental(){}'
        cases=[('expected','pub fn f()->u128{panic!("source undefined")}',test,'passed',True),
               ('no_panic','pub fn f()->u128{1}',test,'support_contract_failed',False),
               ('wrong_panic','pub fn f()->u128{panic!("wrong reason")}',test,'support_contract_failed',False),
               ('ignored','pub fn f()->u128{panic!("source undefined")}',test.replace('#[test] #[should_panic','#[test] #[ignore] #[should_panic'),'support_coverage_missing',False),
               ('disabled','pub fn f()->u128{panic!("source undefined")}',test.replace('#[test] #[should_panic','#[cfg(any())] #[test] #[should_panic'),'support_coverage_missing',False)]
        with tempfile.TemporaryDirectory() as tmp:
            w=Path(tmp)
            for name,code,tests,status,covered in cases:
                with self.subTest(name=name):
                    frozen={'identity':name,'tests':[tests],'unit_tests':[],'obligations':[{'test_name':'required'}]}
                    crate=materialize(w/name,{'src/lib.rs':code},rc)
                    result=execute(frozen,crate,rc,c,Executor(w/(name+'-commands')))
                    self.assertEqual(result['compilation']['status'],'passed');self.assertEqual(result['status'],status)
                    full='__i2r_source_contract_0::required'
                    self.assertEqual(full in result['executed_tests'],covered)
                    self.assertEqual('required' not in result['missing_required_tests'],covered)
                    if covered:self.assertEqual(result['record']['returncode'],0)

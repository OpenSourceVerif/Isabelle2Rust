import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock
from i2r_agent.common import Executor,Failure,save
from i2r_agent.segmented_config import configure,materialize,rust_config
from i2r_agent.translation_workflow import connection,compile_crate,connector_identity
from i2r_agent.test_connector import connect
from i2r_agent.connector_templates import KERNEL,generate,identity
from i2r_agent.validation import execute
from test_translation_workflow import cfg

MODEL=r'''theory Model imports Recursion_Test begin
 definition observe :: "nat list \<Rightarrow> nat list" where
 "observe input = [Recursion_Test.add (input!0) (input!1)]" end'''
MAPPING=[{'source':'constant:Recursion_Test.add','rust_item':'crate::add','kind':'direct'}]
CODE='pub type Nat=u128; pub enum Overflow { I2R_NUMERIC_OVERFLOW } pub fn add(x:Nat,y:Nat)->Result<Nat,Overflow>{x.checked_add(y).ok_or(Overflow::I2R_NUMERIC_OVERFLOW)}'

class ConnectorTemplates(unittest.TestCase):
    def config(self):
        c=cfg();c['translation']['correctness_only']=True
        return configure(c)

    def test_strict_source_interface_and_error_rejection(self):
        c=self.config()
        good=generate('fpp-add',MODEL,KERNEL,{'src/lib.rs':CODE},MAPPING,c)
        self.assertEqual(good['status'],'generated')
        for model,kernel,code,mapping in [
            (MODEL.replace('input!1','input!0'),KERNEL,CODE,MAPPING),
            (MODEL,KERNEL.replace('kernel_prepare x = x','kernel_prepare x = rev x'),CODE,MAPPING),
            (MODEL,KERNEL,CODE.replace('u128','u64'),MAPPING),
            (MODEL,KERNEL,CODE.replace('I2R_NUMERIC_OVERFLOW }','I2R_NUMERIC_OVERFLOW, Other }'),MAPPING),
            (MODEL,KERNEL,CODE,[{**MAPPING[0],'rust_item':'crate::absent'}]),
        ]:
            with self.subTest(code=code):self.assertEqual(generate('fpp-add',model,kernel,{'src/lib.rs':code},mapping,c)['status'],'fallback_required')
        self.assertEqual(generate('fpp-unverified-tree',MODEL,KERNEL,{'src/lib.rs':CODE},MAPPING,c)['status'],'fallback_required')

    def test_single_unit_error_with_exact_public_overflow_constant(self):
        c=self.config()
        code='pub struct NumericOverflow; pub const I2R_NUMERIC_OVERFLOW: NumericOverflow = NumericOverflow; pub fn add(x:u128,y:u128)->Result<u128,NumericOverflow>{x.checked_add(y).ok_or(I2R_NUMERIC_OVERFLOW)}'
        generated=generate('fpp-add',MODEL,KERNEL,{'src/lib.rs':code},MAPPING,c)
        self.assertEqual(generated['status'],'generated')
        self.assertEqual(generated['result_error'],'i2r_candidate::NumericOverflow')
        for bad in [
            code.replace('pub const','const'),
            code.replace('= NumericOverflow;','= OTHER;'),
            code.replace(': NumericOverflow =',': OtherError ='),
            code.replace('pub struct NumericOverflow;','pub struct NumericOverflow(pub u128);'),
            code.replace('pub struct NumericOverflow;','pub enum NumericOverflow { I2R_NUMERIC_OVERFLOW, Other }'),
            code.replace('I2R_NUMERIC_OVERFLOW:','UNRELATED_ERROR:'),
        ]:
            with self.subTest(code=bad):self.assertEqual(generate('fpp-add',MODEL,KERNEL,{'src/lib.rs':bad},MAPPING,c)['status'],'fallback_required')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'Model.thy').write_text(MODEL);(p/'Kernel.thy').write_text(KERNEL)
            rc=rust_config({},c)
            self.assertNotEqual(identity(p,{'src/lib.rs':code},MAPPING,rc,c),identity(p,{'src/lib.rs':code.replace('= NumericOverflow;','= OTHER;')},MAPPING,rc,c))
            state={'files':{'src/lib.rs':code},'mapping':MAPPING,'rust_config':rc}
            before=connector_identity(state);state['files']['src/lib.rs']=code.replace('= NumericOverflow;','= OTHER;')
            self.assertNotEqual(before,connector_identity(state))

    def test_cache_identity_binds_scenarios_mapping_interfaces_numeric_and_config(self):
        c=self.config();files={'src/lib.rs':CODE};rc=rust_config({},c)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'Model.thy').write_text(MODEL);(p/'Kernel.thy').write_text(KERNEL)
            base=identity(p,files,MAPPING,rc,c)
            # Bodies do not change the required call binding; execution is still repeated.
            self.assertEqual(base,identity(p,{'src/lib.rs':CODE.replace('x.checked_add(y)','y.checked_add(x)')},MAPPING,rc,c))
            (p/'Model.thy').write_text(MODEL+'\n')
            self.assertNotEqual(base,identity(p,files,MAPPING,rc,c));(p/'Model.thy').write_text(MODEL)
            (p/'Kernel.thy').write_text(KERNEL+'\n')
            self.assertNotEqual(base,identity(p,files,MAPPING,rc,c));(p/'Kernel.thy').write_text(KERNEL)
            self.assertNotEqual(base,identity(p,files,[{**MAPPING[0],'rust_item':'crate::different'}],rc,c))
            self.assertNotEqual(base,identity(p,{'src/lib.rs':CODE.replace('x:Nat','x:u64')},MAPPING,rc,c))
            self.assertNotEqual(base,identity(p,files,MAPPING,{**rc,'cfg':['extra']},c))
            d=deepcopy(c);d['preprocessing']['numeric_mode']='arbitrary'
            self.assertNotEqual(base,identity(p,files,MAPPING,rc,d))

    def test_real_result_overflow_is_preserved_and_invalid_candidate_cannot_compile(self):
        c=self.config();rc=rust_config({},c)
        with tempfile.TemporaryDirectory() as tmp:
            w=Path(tmp);files={'src/lib.rs':CODE};binding=generate('fpp-add',MODEL,KERNEL,files,MAPPING,c)['files']
            crate=materialize(w/'candidate',files,rc);harness=connection(crate,binding,rc,c)
            ex=Executor(w/'commands');built=compile_crate(harness,rc,c,ex,False)
            self.assertEqual(built['status'],'passed')
            self.assertEqual(execute(built['binary'],[[4,5]],ex,10)['outputs'],[[9]])
            for args in [(),('--i2r-kernel-check',)]:
                self.assertEqual(execute(built['binary'],[[2**128-1,1]],ex,10,arguments=args)['status'],'numeric_range_exceeded')
            invalid={'src/lib.rs':CODE.replace('x.checked_add(y)','unbound_call(x,y)')}
            crate=materialize(w/'invalid',invalid,rc)
            self.assertEqual(compile_crate(connection(crate,binding,rc,c),rc,c,ex,False)['status'],'compile_failed')

    def test_unknown_shape_fallback_requests_only_binding_and_never_swallows_issue(self):
        c=self.config();provider=Mock();provider.call.return_value={'algorithm_issue':'unsupported source API'}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'Model.thy').write_text(MODEL);(p/'Kernel.thy').write_text(KERNEL)
            save(p/'case.json',{'id':'fpp-unknown','contract':'source-only observation'})
            with self.assertRaises(Failure) as caught:
                connect(p,None,{'src/lib.rs':CODE},MAPPING,{'rust_config':rust_config({},c)},c,provider,p/'call')
            self.assertEqual(caught.exception.code,'connector_algorithm_defect')
            provider.call.assert_called_once()
            system,payload=provider.call.call_args.args
            request=json.loads(payload)
            self.assertEqual(request['algorithm_files'],{})
            self.assertIn('algorithm_interfaces',request)
            self.assertNotIn('x.checked_add(y)',payload)
            self.assertIn('small Rust observation binding',system)
            self.assertEqual(request['candidate_call_paths']['constant:Recursion_Test.add'],'i2r_candidate::add')
            self.assertEqual(request['driver_signatures']['benchmark_run'],'fn(Prepared) -> KernelResult')
            self.assertIn('pub fn benchmark_run(prepared:Prepared)->KernelResult',system)
            self.assertIn('i2r_candidate::',system)
            self.assertIn('not &Prepared',system)
            self.assertIn('No long notes, boundary_review',system)

if __name__=='__main__':unittest.main()

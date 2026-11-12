import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from i2r_agent.common import ROOT,Failure,config,Executor
from i2r_agent.knowledge import material, requested, correspondence, apply_files, adapter_plan
from i2r_agent.provider import decode_model_json
from i2r_agent.knowledge_run import reference_bundle
from i2r_agent.planning import manifest
from i2r_agent import test_connector
from i2r_agent.references import compile_rust


def bundle():
    return {'programs':[{'entries':['constant:A.main'],'nodes':[
        {'id':'constant:A.main','dependencies':['constant:A.helper'],'statement':{'kind':'function','signature':{'variables':[]},'equations':['call helper']}},
        {'id':'constant:A.helper','dependencies':[],'statement':{'kind':'function','signature':{'variables':[]},'equations':['hidden body']}}]}],
        'sources':{},'numeric_policy':{'mode':'checked'},'observation_binding':'WIRE_SECRET',
        'workload':{'example':'BENCHMARK_SECRET'},'kernel':'KERNEL_SECRET'}


class KnowledgeFlowTests(unittest.TestCase):
    def test_default_test_domain_follows_numeric_mode(self):
        from i2r_agent.suites import input_bits
        cfg=config();self.assertEqual(input_bits(cfg),128)
        cfg['preprocessing']['numeric_mode']='arbitrary';self.assertEqual(input_bits(cfg),0)

    def test_single_json_delimiter_repair_preserves_rust_strings(self):
        original={'action':'adapt','adapter':{'declarations':'x \\<Rightarrow> y','rust_files':{'src/n.rs':'pub fn f(){ let s = "}"; }'}}}
        encoded=json.dumps(original)
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(decode_model_json(encoded[:-1],d),original)
            self.assertEqual(decode_model_json(encoded+'}',d),original)
            self.assertTrue((Path(d)/'format-normalizations.json').exists())
            with self.assertRaises(Failure):decode_model_json(encoded[:-2],d)

    def test_nested_adapter_metadata_is_normalized_and_recorded(self):
        plan=adapter_plan({'adapter':{'declarations':'','dependencies':{'example':'=1.2.3'},'numeric_representation':'selected'}},bundle())
        self.assertEqual(plan['dependencies'],{'example':'=1.2.3'})
        self.assertNotIn('dependencies',plan['adapter'])
        self.assertIn('moved adapter.dependencies to dependencies',plan['protocol_normalizations'])


    def test_large_take_drop_counts_are_in_fixed_regressions(self):
        from i2r_agent.suites import scoped_fixed,domain
        x=[2**64+1,3,1,2,4]
        self.assertTrue(domain('skew-heap',x));self.assertIn(x,scoped_fixed('skew-heap',128))

    def test_catalog_complete_and_nodes_requestable_without_test_metadata(self):
        b=bundle();m=material(b)
        self.assertEqual({n['id'] for n in m['symbols']},{'constant:A.main','constant:A.helper'})
        self.assertIn('hidden body',json.dumps(m['thingol']))
        self.assertEqual(requested({'request_nodes':['constant:A.helper']},b)['nodes'][0]['statement']['equations'],['hidden body'])
        self.assertNotIn('SECRET',json.dumps(m))
        with self.assertRaises(Failure):requested({'request_nodes':['missing']},b)

    def test_missing_helper_cannot_pass_coverage(self):
        with self.assertRaises(Failure) as e:
            correspondence(bundle(),{'src/lib.rs':'pub fn main(){}'},[{'source':'constant:A.main','rust':'main'}])
        self.assertEqual(e.exception.evidence['missing'],['constant:A.helper'])


    def test_representation_edits_are_not_ownership_only(self):
        out=apply_files({'src/lib.rs':'type N = u128;'}, {'edits':[{'file':'src/lib.rs','old':'u128','new':'CustomNat'}]})
        self.assertIn('CustomNat',out['src/lib.rs'])
        self.assertNotIn('dashu',manifest({},transport='none'))


    def test_adaptation_cannot_remove_original_export_obligation(self):
        b=bundle();b['original_programs']=b['programs'];b['programs']=[{'entries':[],'nodes':[]}]
        with self.assertRaises(Failure) as caught:correspondence(b,{},[])
        self.assertIn('constant:A.main',caught.exception.evidence['missing'])
        self.assertEqual(requested({'request_nodes':['constant:A.helper']},b)['nodes'][0]['statement']['equations'],['hidden body'])


    @unittest.skip("Historical non-FPP catalog remains in the original Agent repository; not an artifact regression")
    def test_algorithm_and_reference_projects_are_separate_and_preserved(self):
        before=json.loads((ROOT/'tests/fixtures/reference-source-hashes.json').read_text())
        for name in before:
            self.assertTrue((ROOT/'catalog/cases'/name).is_dir())
        for case in (ROOT/'catalog/cases').iterdir():
            export=(case/'program/Export.thy').read_text()
            self.assertNotIn('Model.observe',export);self.assertNotIn('Kernel.kernel_',export)
            for name in ['Model.thy','Kernel.thy','Export.thy']:
                self.assertTrue((case/'testing'/name).is_file())
                if case.name in before:
                    self.assertEqual(hashlib.sha256((case/'testing'/name).read_bytes()).hexdigest(),before[case.name][name])
        self.assertIn('splay_code',(ROOT/'catalog/cases/splay-tree/program/Algorithm.thy').read_text())

    def test_native_test_drivers_support_full_unsigned_and_signed_ranges(self):
        cfg=config()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);executor=Executor(root/'logs')
            for transport,typ,values in [('native-u128','u128',[0,2**128-1]),('native-i128','i128',[-2**127,2**127-1])]:
                crate=root/transport;(crate/'src').mkdir(parents=True)
                (crate/'Cargo.toml').write_text(manifest({},transport='none'))
                (crate/'src/lib.rs').write_text('pub fn marker(){}')
                source=f'''pub type WireInt={typ}; pub type Prepared=Vec<WireInt>; pub type KernelResult=Vec<WireInt>;
pub fn observe(x:&[WireInt])->Vec<WireInt>{{x.to_vec()}}
pub fn benchmark_prepare(x:&[WireInt])->Prepared{{x.to_vec()}}
pub fn benchmark_run(x:Prepared)->KernelResult{{x}}
pub fn benchmark_encode(x:KernelResult)->Vec<WireInt>{{x}}'''
                cc={**cfg,'testing':{**cfg['testing'],'transport':transport}}
                target=test_connector.materialize(crate,{'src/lib.rs':source},{'dependencies':{}},cc)
                build=compile_rust(target,cc,executor)
                self.assertEqual(build['status'],'passed')
                out=executor.run([build['binary'],'--i2r-benchmark'],stdin=' '.join(map(str,values))+'\n')
                self.assertEqual(Path(out['stdout']).read_text().strip(),' '.join(map(str,values)))
                self.assertIn('I2R_KERNEL_NS',Path(out['stderr']).read_text())


if __name__=='__main__':unittest.main()

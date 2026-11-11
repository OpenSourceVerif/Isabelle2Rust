import unittest
from copy import deepcopy
from i2r_agent.common import Failure
from i2r_agent.derived_candidate import resolve_config
from test_v8_workflow import cfg

class DerivedConfig(unittest.TestCase):
    def test_original_auto_config_resolves_like_build_without_mutation(self):
        for mode,wire in [('checked','native-u128'),('arbitrary','dashu-ubig')]:
            c=cfg();c['v8']['correctness_only']=True;c['preprocessing']['numeric_mode']=mode;c['testing']['transport']='auto';original=deepcopy(c)
            resolved,evidence=resolve_config(c,{'transport':wire})
            self.assertEqual(c,original);self.assertEqual(resolved['testing']['transport'],wire)
            self.assertEqual(evidence['configured_transport'],'auto');self.assertFalse(resolved['performance']['enabled'])
    def test_explicit_wire_cannot_change_derived_original_task(self):
        c=cfg();c['v8']['correctness_only']=True;c['testing']['transport']='native-i128'
        with self.assertRaises(Failure) as caught:resolve_config(c,{'transport':'native-u128'})
        self.assertEqual(caught.exception.code,'derived_transport_mismatch')

    @unittest.skip("Historical derived-worker scripts are not part of the FPP artifact")
    def test_worker_cli_reads_frozen_auto_config_and_runs_source_then_connector(self):
        import tempfile,runpy,sys
        from pathlib import Path
        from unittest.mock import patch
        from i2r_agent.common import ROOT,read,save
        from i2r_agent.segmented_config import configure,rust_config
        f=read(ROOT/'tests/fixtures/map_support_e0004.json');c=cfg();c['v8']['correctness_only']=True;c['testing']['transport']='auto'
        code='pub type WireInt=u128; pub type Prepared=Vec<u128>; pub type KernelResult=Vec<u128>; pub fn observe(x:&[u128])->Vec<u128>{x.to_vec()} pub fn benchmark_prepare(x:&[u128])->Prepared{x.to_vec()} pub fn benchmark_run(x:Prepared)->KernelResult{x} pub fn benchmark_encode(x:KernelResult)->Vec<u128>{x}'
        seen=[]
        def connector(*args,**kwargs):
            seen.append(args[5]['testing']['transport']);self.assertEqual(seen[-1],'native-u128')
            return {'src/lib.rs':code},'test-only driver binding'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);implementation=root/'implementation';implementation.mkdir();work=root/'run';work.mkdir()
            save(root/'identity.json',{'files':{},'tool_sources':{},'derived_case':'fpp-map'});save(root/'lineage.json',{'original_files':{}});save(root/'derived/lineage.json',{'original_files':{}})
            save(root/'effective-config.json',c);save(root/'admissions.json',{'fpp-map':{'reference_id':'fixture'}})
            save(implementation/'cache/fpp-baselines/fixture/baseline.json',{})
            save(root/'derived/segmented-checkpoint.json',{'files':f['files'],'mapping':f['mapping'],'transport':'native-u128','rust_config':rust_config({},configure(c)),'partition':{'units':{}},'bundle':{}})
            save(root/'derived/frozen-tests.json',f['frozen']);save(root/'derived/references.json',{'ocaml':{},'stage2':{}})
            save(root/'evaluation-inputs.json',{'fpp-map':{'fixed':[],'generated':[]}})
            with patch('i2r_agent.common.ROOT',implementation),patch('i2r_agent.tool_sources.verify'),patch('i2r_agent.baselines.valid_record',return_value=True),patch('i2r_agent.derived_candidate.coverage',return_value={'status':'passed'}),patch('i2r_agent.derived_candidate.test_connector.connect',side_effect=connector),patch.object(sys,'argv',['run-derived-map.py','--run',str(work),'--worker']):
                with self.assertRaises(SystemExit) as ended:runpy.run_path(str(ROOT/'bin/run-derived-map.py'),run_name='__main__')
            self.assertEqual(ended.exception.code,0);self.assertEqual(seen,['native-u128'])
            result=read(work/'result.json');self.assertEqual(result['status'],'passed')
            self.assertEqual(next(x['result']['tests_passed'] for x in result['steps'] if x['phase']=='support'),5)
            self.assertEqual(result['configuration_resolution']['configured_transport'],'auto')
            # Same real worker path with explicit-case authorization; no new
            # candidate-generation or checkpoint-migration mechanism.
            generic_work=root/'generic-run';generic_work.mkdir();seen.clear()
            with patch('i2r_agent.common.ROOT',implementation),patch('i2r_agent.tool_sources.verify'),patch('i2r_agent.baselines.valid_record',return_value=True),patch('i2r_agent.derived_candidate.coverage',return_value={'status':'passed'}),patch('i2r_agent.derived_candidate.test_connector.connect',side_effect=connector),patch.object(sys,'argv',['run-derived-candidate.py','--case','fpp-map','--run',str(generic_work),'--worker']):
                with self.assertRaises(SystemExit) as generic_exit:runpy.run_path(str(ROOT/'bin/run-derived-candidate.py'),run_name='__main__')
            self.assertEqual(generic_exit.exception.code,0);self.assertEqual(seen,['native-u128'])
            self.assertEqual(read(generic_work/'result.json')['status'],'passed')
            with patch('i2r_agent.common.ROOT',implementation),patch.object(sys,'argv',['run-derived-candidate.py','--case','fpp-other','--run',str(root/'wrong'),'--worker']):
                with self.assertRaises(SystemExit) as rejected:runpy.run_path(str(ROOT/'bin/run-derived-candidate.py'),run_name='__main__')
            self.assertIn('does not authorize',str(rejected.exception));self.assertFalse((root/'wrong').exists())


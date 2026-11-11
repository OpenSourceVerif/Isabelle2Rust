import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from i2r_agent.common import Executor, config
from i2r_agent.storage import attach_adapter, artifact_files
from i2r_agent.references import compile_rust


class StorageTests(unittest.TestCase):
    def test_adapter_versions_share_files_and_export_survives_relocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);trial=root/'run/trial';trial.mkdir(parents=True)
            a=trial/'candidate-01';b=trial/'candidate-02';a.mkdir();b.mkdir()
            loaded={'bindings':{'x':1},'before_target':{},'after_target':{}}
            attach_adapter(a,loaded,[]);attach_adapter(b,loaded,[])
            self.assertEqual((a/'adapter').resolve(),(b/'adapter').resolve())
            self.assertEqual((a/'loaded-adapter.json').resolve(),(b/'loaded-adapter.json').resolve())
            c=trial/'candidate-03';c.mkdir();attach_adapter(c,{**loaded,'bindings':{'x':2}},[])
            self.assertNotEqual((a/'adapter').resolve(),(c/'adapter').resolve())
            self.assertEqual(json.loads((a/'adapter/bindings.json').read_text()),{'x':1})
            self.assertIn(a/'adapter/bindings.json',list(artifact_files(a)))
            # Standalone delivery dereferences diagnostic links before temporary work is removed.
            shutil.copytree(a,root/'standalone')
            archive=shutil.make_archive(str(root/'export'),'gztar',root,'run')
            shutil.rmtree(root/'run')
            shutil.unpack_archive(archive,root/'relocated',filter='data')
            self.assertEqual(json.loads((root/'standalone/adapter/bindings.json').read_text()),{'x':1})
            self.assertEqual(json.loads((root/'relocated/run/trial/candidate-02/adapter/bindings.json').read_text()),{'x':1})

    def test_same_named_crates_share_cache_but_keep_distinct_executables(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);executor=Executor(root/'commands');cfg=config();results=[]
            for number in [1,2]:
                crate=root/str(number);(crate/'src').mkdir(parents=True)
                (crate/'Cargo.toml').write_text('[package]\nname="same_name"\nversion="0.1.0"\nedition="2021"\n')
                (crate/'src/main.rs').write_text(f'fn main() {{ println!("{number}"); }}')
                result=compile_rust(crate,cfg,executor,candidate=True)
                self.assertEqual(result['status'],'passed');results.append(result)
            self.assertEqual(results[0]['build_cache'],results[1]['build_cache'])
            shutil.rmtree(results[0]['build_cache'])
            for number,result in enumerate(results,1):
                self.assertEqual(subprocess.check_output([result['binary']],text=True).strip(),str(number))

    def test_copied_timestamps_do_not_reuse_another_crates_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);executor=Executor(root/'commands');cfg=config();results=[]
            for number in [1,2]:
                crate=root/str(number);(crate/'src').mkdir(parents=True)
                (crate/'Cargo.toml').write_text('[package]\nname="same_library"\nversion="0.1.0"\nedition="2021"\n')
                source=crate/'src/lib.rs'
                source.write_text(f'pub fn value() -> u32 {{ {number} }}')
                os.utime(source,(1_600_000_000,1_600_000_000))
                (crate/'src/main.rs').write_text('fn main() { println!("{}",same_library::value()); }')
                result=compile_rust(crate,cfg,executor)
                self.assertEqual(result['status'],'passed');results.append(result)
            for number,result in enumerate(results,1):
                self.assertEqual(subprocess.check_output([result['binary']],text=True).strip(),str(number))

if __name__=='__main__':unittest.main()

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from i2r_agent import tool_sources
from i2r_agent.baselines import identity
from i2r_agent.common import Failure, save


class WorkspaceToolTests(unittest.TestCase):
    def fixture(self, root):
        for path, content in {'Isabelle2Rust/ROOT':'session Rust = Main +',
                              'Isabelle2Rust/translate/code_rust.ML':'original',
                              'Isabelle2Rust/optimize/Cargo.toml':'[package]',
                              'RustLightAST/Cargo.toml':'[package]',
                              'RustLightAST/src/lib.rs':'original'}.items():
            file=root/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(content)
        return root/'Isabelle2Rust/agent'

    def test_uncommitted_changes_in_either_repository_invalidate_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);agent=self.fixture(root)
            with patch.object(tool_sources,'ROOT',agent):
                initial=identity('case',{'source_hashes':{}},{'tools':{}})
                for rel in ['Isabelle2Rust/translate/code_rust.ML','RustLightAST/src/lib.rs']:
                    p=root/rel;p.write_text('uncommitted edit')
                    self.assertNotEqual(initial,identity('case',{'source_hashes':{}},{'tools':{}}))
                    with self.assertRaises(Failure):tool_sources.verify(initial['tool_sources'])
                    p.write_text('original')
                self.assertEqual(initial,identity('case',{'source_hashes':{}},{'tools':{}}))
                generated=root/'RustLightAST/target/build.rs';generated.parent.mkdir();generated.write_text('cache')
                self.assertEqual(initial,identity('case',{'source_hashes':{}},{'tools':{}}))
                (root/'RustLightAST/src/added.rs').write_text('new module')
                self.assertNotEqual(initial,identity('case',{'source_hashes':{}},{'tools':{}}))

    def test_missing_workspace_repository_does_not_fall_back_to_copy(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(tool_sources,'ROOT',Path(tmp)/'agent'):
            with self.assertRaises(Failure) as cm:tool_sources.manifest()
            self.assertEqual(cm.exception.code,'missing_tool_repository')


if __name__=='__main__':unittest.main()

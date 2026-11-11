import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from i2r_agent import study

class SnapshotRootsTests(unittest.TestCase):
    def test_frozen_study_includes_isabelle_session_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'isabelle').mkdir();source='session Agent = HOL + theories Main\n'
            (root/'isabelle/ROOT').write_text(source)
            case=root/'catalog/cases/sample';case.mkdir(parents=True);(case/'case.json').write_text('{"id":"sample"}')
            spec=root/'spec.json';spec.write_text(json.dumps({'id':'snapshot','cases':['sample'],'variants':{'test':{}}}))
            with patch.object(study,'ROOT',root),patch.object(study,'config',return_value={}),patch.object(study.tool_sources,'manifest',return_value={}),patch.object(study.tool_sources,'verify'),patch.object(study,'build',return_value={'status':'passed','phase':'finished'}):
                study.run(spec,'snapshot-check')
            self.assertEqual((root/'data/runs/snapshot-check/implementation/isabelle/ROOT').read_text(),source)
            self.assertIn('isabelle/ROOT',json.loads((root/'data/runs/snapshot-check/study.json').read_text())['code'])

if __name__=='__main__':unittest.main()

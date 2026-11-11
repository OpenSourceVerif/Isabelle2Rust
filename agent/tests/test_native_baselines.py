import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from i2r_agent.common import digest, save, read
from i2r_agent.workbench import add_language_baselines


class NativeWorkbenchTests(unittest.TestCase):
    def fixture(self, root, language, status='passed'):
        work=root/'data/baselines/case-version/artifacts'/language/'run-1'
        work.mkdir(parents=True)
        source=work/'source';source.write_text('generated source')
        binary=work/'reference';binary.write_text('binary')
        sample={'median_ns':10,'min_ns':9,'max_ns':11,'samples':[9,10,11]}
        reference={'id':'original-measurement','summary':{'ocaml':sample,'stage2':sample},
                   'measured_at':'original timestamp','origin':'original record'}
        save(root/'measurement.json',reference)
        perf={'summary':{language:sample},'measured_at':'new timestamp','origin':'new record',
              'workload':[1,2],'protocol':{'options':{'samples':3}}}
        record={'case':'case','baseline_id':'case-version','status':status,'started_at':'new timestamp',
                'identity':{'sources':{'Model.thy':'hash'}},'checks':[],
                'reference':{'source':str(source),'sha256':digest(source),'binary':str(binary),'binary_sha256':digest(binary)},
                'performance':perf,'reference_measurement':str(root/'measurement.json'),
                'measurement_id':'run-1/case/'+language,'error':'recorded failure'}
        save(work/'result.json',record)
        key=hashlib.sha256(json.dumps([1,2],separators=(',',':')).encode()).hexdigest()[:10]
        row={'implementation':'other-version:ocaml','values':'2 位以内 · 输入 '+key,'scope':'kernel'}
        cases={'case':{'implementations':[],'performance_views':[
            {'protocol':{'options':{'samples':3}},'rows':[dict(row)]},
            {'protocol':{'options':{'samples':7}},'rows':[dict(row)]}]}}
        registry=[{'id':'other-version','identity':record['identity']}]
        return cases,registry,binary

    def test_new_backends_share_card_contract_and_match_measurement_conditions(self):
        for language in ['haskell','scala','sml']:
            with self.subTest(language=language),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);cases,registry,_=self.fixture(root,language)
                with patch('i2r_agent.workbench.ROOT',root):
                    add_language_baselines(cases,registry,language)
                case=cases['case'];card=case['implementations'][0]
                self.assertEqual(card['kind'],'baseline')
                self.assertEqual(card['status'],'passed')
                self.assertEqual(card['measurement']['median_ns'],10)
                self.assertEqual(len(case['performance_views'][0]['rows']),2)
                self.assertEqual(len(case['performance_views'][1]['rows']),1)
                self.assertEqual(case['performance_views'][-1]['rows'][0]['measured_at'],'original timestamp')
                self.assertEqual(case['performance_views'][-1]['rows'][-1]['measurement_id'],'run-1/case/'+language)

    def test_failure_visible_without_timing_and_changed_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cases,registry,_=self.fixture(root,'sml','failed')
            with patch('i2r_agent.workbench.ROOT',root):add_language_baselines(cases,registry,'sml')
            self.assertTrue(cases['case']['implementations'][0]['measurement_missing'])
            self.assertEqual(len(cases['case']['performance_views']),2)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cases,registry,binary=self.fixture(root,'scala')
            binary.write_text('changed')
            with patch('i2r_agent.workbench.ROOT',root):add_language_baselines(cases,registry,'scala')
            self.assertEqual(cases['case']['implementations'],[])

    def test_supplementary_workload_keeps_history_and_one_latest_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cases,registry,_=self.fixture(root,'haskell')
            work=root/'data/baselines/case-version/artifacts/haskell/run-1'
            old=read(work/'result.json');old['started_at']='2026-01-01';save(work/'result.json',old)
            new=read(work/'result.json')
            new.update(started_at='2026-01-02',measurement_id='small-workload')
            new['performance']['workload']=[3]
            save(work/'measurements/small/result.json',new)
            key=hashlib.sha256(b'[3]').hexdigest()[:10]
            cases['case']['performance_views'].append({'protocol':{'options':{'samples':3}},
                'rows':[{'implementation':'other-version:ocaml','values':'2 位以内 · 输入 '+key,'scope':'kernel'}]})
            with patch('i2r_agent.workbench.ROOT',root):add_language_baselines(cases,registry,'haskell')
            case=cases['case']
            self.assertEqual(len(case['implementations']),1)
            self.assertIn('/measurements/small/',case['implementations'][0]['record_path'])
            self.assertEqual(case['performance_views'][0]['rows'][-1]['measurement_id'],'run-1/case/haskell')
            self.assertEqual(case['performance_views'][2]['rows'][-1]['measurement_id'],'small-workload')
            self.assertEqual(len(case['performance_views'][0]['rows']),2)
            self.assertEqual(len(case['performance_views'][2]['rows']),2)

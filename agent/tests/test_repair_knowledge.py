import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock,patch
from i2r_agent import repair_knowledge as k,prepared_identity,segmented_v8,implementation_strategy
from i2r_agent.common import ROOT,Failure,save
from i2r_agent.knowledge_candidates import collect


class RepairKnowledgeTests(unittest.TestCase):
    def test_error_codes_are_exact_and_material_is_bounded(self):
        self.assertEqual(k.compiler({'error':'not a compiler diagnostic'},{}),{})
        self.assertEqual(k.compiler({'error':'XE0382 E03820'},{}),{})
        for code in ['E0382','E0277','E0308','E0499','E0502','E0597','E0599']:
            r=k.compiler({'code':code},{})
            self.assertEqual(r['entries'][0]['codes'],[code])
            self.assertEqual(r['entries'][0]['provenance'],'official_reference')
        actual={'diagnostics':[{'level':'error','code':{'code':'E0382','explanation':'See also E0277'}}]}
        self.assertEqual([x['codes'] for x in k.compiler(actual,{})['entries']],[['E0382']])
        r=k.compiler('E0382 E0277 E0308 E0499 E0502 E0597 E0599',{})
        self.assertLessEqual(len(r['entries']),3)
        self.assertLessEqual(len(json.dumps(r,ensure_ascii=False)),5000)
        self.assertEqual(k.compiler('E0382',{},characters=20),{})
        r=k.compiler('E0382 E0277',{},characters=1500)
        self.assertLessEqual(len(json.dumps(r,ensure_ascii=False)),1500)
        self.assertTrue(all('forbidden_shortcuts' in x for x in r['entries']))

    def test_historical_api_requires_receiver_operation_and_locked_dependency(self):
        def ids(text,dep):return [x['id'] for x in k.compiler(text,{'dependencies':{'dashu-int':dep}}).get('entries',[])]
        self.assertIn('dashu-062-magnitude',ids('E0599 magnitude &IBig','=0.6.2'))
        for text,dep in [('E0599 other &IBig','=0.6.2'),('E0599 magnitude Other','=0.6.2'),('E0599 magnitude IBig','^0.6.2'),('E0308 magnitude IBig','=0.6.2')]:
            self.assertNotIn('dashu-062-magnitude',ids(text,dep))

    def test_semantic_selection_uses_extracted_type_fact_identity_and_mode(self):
        key='constant:Bit_Operations.semiring_bit_operations_class.drop_bit'
        entity={'source_type':{'kind':'type','name':'Nat.nat','args':[]},
                'specifications':[{'name':'Bit_Operations.drop_bit_nat_def','equational':True,'rules':[{'proposition':'source equation'}]}]}
        model={'entities':{key:entity}}
        result=k.semantic(model,{'mode':'arbitrary'})
        self.assertEqual(result['entries'][0]['matched_source_entities'],[key])
        for change in ['name','type','facts','mode']:
            m=deepcopy(model);mode='arbitrary'
            if change=='name':m['entities']['constant:User.drop_bit']=m['entities'].pop(key)
            if change=='type':m['entities'][key]['source_type']['name']='User.word'
            if change=='facts':m['entities'][key]['specifications']=[]
            if change=='mode':mode='unknown'
            self.assertEqual(k.semantic(m,{'mode':mode}),{},change)

    @unittest.skip("Historical evidence archives stay in the original Agent repository; bounded advisory content is tested separately")
    def test_evidence_files_match_recorded_hashes(self):
        from i2r_agent.common import digest
        for row in k.catalog()['entries']:
            for e in row['evidence']:self.assertEqual(digest(ROOT/e['path']),e['sha256'])

    def test_knowledge_changes_invalidate_prepared_and_checkpoint_identity(self):
        from test_segmented_workflow import source
        with tempfile.TemporaryDirectory() as d:
            project=Path(d);(project/'A.thy').write_text('theory A imports Main begin end')
            with patch('i2r_agent.repair_knowledge.manifest',return_value={'catalog':'old'}):
                old=prepared_identity.identity(project,{})
                bundle=source();checkpoint=segmented_v8.checkpoint_identity(bundle,{}, {})
            with patch('i2r_agent.repair_knowledge.manifest',return_value={'catalog':'new'}):
                new=prepared_identity.identity(project,{})
                self.assertNotEqual(old,new)
                with self.assertRaises(Failure) as e:prepared_identity.validate({'prepared_identity':old},new)
                self.assertEqual(e.exception.code,'stale_preprocessing_cache')
                save(project/'segmented-checkpoint.json',{'identity':checkpoint,'implementation_strategy':implementation_strategy.initialize(bundle['semantic_analysis'])})
                with self.assertRaises(Failure) as e:
                    segmented_v8.search(bundle,None,{},Mock(),project,Mock(),None,[],[],project/'regressions.json',Mock())
                self.assertEqual(e.exception.code,'stale_snapshot')

    def test_real_catalog_edit_changes_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/k.CATALOG;p.parent.mkdir(parents=True);p.write_text('{}')
            with patch.object(k,'ROOT',root),patch.object(k,'REFERENCE_PATHS',(k.CATALOG,)):
                before=k.manifest();p.write_text('{"version":2}')
                self.assertNotEqual(before,k.manifest())

    def test_miner_requires_executed_same_condition_replay_and_never_promotes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for n in range(1,4):(root/f'segment-step-{n:04d}').mkdir()
            a=root/'segment-step-0001';b=root/'segment-step-0002';c=root/'segment-step-0003'
            build={'command':['cargo','build'],'status':'failed','returncode':101}
            save(a/'attempt.json',{'action_phase':'compile','unit':'u','state_version':'a','after_version':'a',
                'compilation':{'status':'compile_failed','diagnostics':[{'level':'error','message':'E0382 moved'}],'checks':{'build':build}}})
            save(b/'attempt.json',{'action_phase':'repair','unit':'u','state_version':'a','after_version':'b'})
            save(c/'attempt.json',{'action_phase':'repair_replay','unit':'u','state_version':'b'})
            (b/'changes.diff').write_text('- consume(xs)\n+ borrow(&xs)')
            self.assertFalse(collect(root)['candidates'])
            proof={'status':'passed','checks':{'build':{**build,'status':'passed','returncode':0}}}
            save(c/'original-replay.json',proof)
            rows=collect(root)['candidates'];self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['status'],'unreviewed_candidate')
            proof['checks']['build']['command']=['cargo','check'];save(c/'original-replay.json',proof)
            self.assertFalse(collect(root)['candidates'])

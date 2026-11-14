from workflow_fixture import compile_until_source
import tempfile,unittest
from pathlib import Path
from copy import deepcopy
from i2r_agent import generation_context as gc,task_context as tc
from i2r_agent.common import Failure
from i2r_agent.translation_workflow import apply_transaction,version
from test_segmented_workflow import source
from test_translation_workflow import cfg

class GenerationContextCompact(unittest.TestCase):
    def test_source_preserved_interfaces_and_exact_body_catalog_remain_available(self):
        b=source();files={'src/lib.rs':'pub trait Op{fn apply<T:Clone>(x:T)->T{x}}\nmacro_rules! choose{($x:expr)=>{$x}}\npub fn dependency()->u128{1}\n'+'// padding\n'*500}
        with tempfile.TemporaryDirectory() as d:
            versions=tc.register(b,Path(d)/'materials',files)
            s={'bundle':b,'files':files,'completed':['old'],'unit':'new','mapping':[],
               'partition':{'version':'p','order':['old','new'],'owner':{},'boundaries':[],
                 'units':{'old':{'members':['dependency'],'dependencies':[]},'new':{'members':['f'],'dependencies':['old']}},'source_edges':{'f':['dependency']}}}
            p={'material_versions':versions,'program':{'source_pages':[{'text':'COMPLETE SOURCE EQUATIONS'}]},'current_files':files,'code_pages':[],'rust_items':{}}
            out=gc.compact(p,s)
            self.assertEqual(out['program'],p['program']);self.assertEqual(out['current_files'],{})
            self.assertIn('fn apply<T:Clone>(x:T)->T{x}',str(out['dependency_interfaces']))
            self.assertIn('macro_rules!',str(out['dependency_declarations']))
            self.assertNotIn('->u128{1}',str(out['dependency_interfaces']))
            full=tc.read_material({'request_files':[{'path':'src/lib.rs','code_version':versions['code_version']}]},b,files)
            self.assertEqual(full['files'][0]['text'],files['src/lib.rs'].rstrip('\n'))
            catalog=tc.Archive(b['_context_archive']).get(out['material_versions']['source_catalog'])
            self.assertEqual(catalog,versions['sources'])

    def test_append_keeps_dependencies_byte_exact_and_rejects_stale_or_mixed_edits(self):
        state={'phase':'generate','files':{'src/lib.rs':'pub fn dependency()->u128{1}'}}
        reply={'state_version':'exact','append_files':{'src/lib.rs':'pub fn f()->u128{dependency()+1}'}}
        expanded=gc.expand_append(state,reply,'exact')
        self.assertEqual(expanded['files']['src/lib.rs'],state['files']['src/lib.rs']+'\n'+reply['append_files']['src/lib.rs'])
        for bad in [{**reply,'state_version':'old'},{**reply,'files':{'src/lib.rs':'replacement'}},{**reply,'append_files':{'src/missing.rs':'new'}}]:
            with self.assertRaises(Failure):gc.expand_append(state,bad,'exact')
        with self.assertRaises(Failure):gc.expand_append({**state,'phase':'repair'},reply,'exact')

    def test_large_dependency_append_enters_normal_transaction_and_real_cumulative_build(self):
        from unittest.mock import Mock,patch
        from i2r_agent import translation_workflow as runner
        from i2r_agent.common import Executor
        from i2r_agent.segmented_config import configure
        from test_segmented_workflow import mapping
        c=cfg();c['translation']['correctness_only']=True;c=configure(c);c['segmented']['support_tests']=False
        b=source();b['workflow']='source-translation';pv=Mock();pv.calls=0;pv.usage={};seen=[]
        def answer(pv,c,path,p,analysis=False):
            name=p['unit']['members'][0].rsplit('.',1)[-1]
            if name=='h':return {'files':{'src/lib.rs':'pub fn h()->u128{'+('let _=0; '*600)+'1}'},'mapping':[mapping('h')]}
            seen.append(p)
            return {'state_version':p['controller_state']['state_version'],'append_files':{'src/lib.rs':'pub fn f()->u128{h()+1}'},'mapping':[mapping('f')]}
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'ask',side_effect=answer):
            p=Path(d);_,done=compile_until_source(b,None,c,pv,p,Executor(p/'commands'),None,[],[],p/'regressions.json',lambda _:None)
            self.assertEqual(done[0]['status'],'active');self.assertEqual(seen[0]['current_files'],{})
            self.assertIn('pub fn h()',str(seen[0]['dependency_interfaces']))
            self.assertNotIn('let _=0',str(seen[0]['dependency_declarations']))

    def test_prepared_generation_and_resume_sources_are_original_immutable_objects(self):
        from i2r_agent.common import save,read
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);external=p/'Original.thy';external.write_text('original full source equations')
            b=source();b['sources']={str(external):external.read_text()}
            first=tc.register(b,p/'analysis');save(p/'prepared.json',b)
            external.write_text('changed external source MUST NOT be read')
            prepared=read(p/'prepared.json');versions=tc.register(prepared,p/'generation',{'src/lib.rs':'pub fn h(){}'})
            self.assertEqual(first['sources'],versions['sources'])
            # Same archive on checkpoint restoration also validates existing contents.
            save(p/'checkpoint.json',{'bundle':prepared});restored=read(p/'checkpoint.json')['bundle']
            tc.register(restored,p/'generation',{'src/lib.rs':'pub fn h(){}'})
            catalog=tc.Archive(restored['_context_archive']).put('catalog',versions['sources'])
            listed=tc.read_material({'request_materials':[catalog]},restored)['materials'][catalog]
            result=tc.read_material({'request_sources':[{'path':str(external),'source_version':listed[str(external)]}]},restored)
            self.assertEqual(result['sources'][0]['text'],'original full source equations')
            version=listed[str(external)];captured=p/'generation'/(version+'.json')
            captured.write_text('"corrupted"')
            with self.assertRaises(Failure) as caught:tc.register(restored,p/'generation')
            self.assertEqual(caught.exception.code,'material_changed')
            captured.unlink()
            with self.assertRaises(Failure) as caught:tc.register(restored,p/'generation')
            self.assertEqual(caught.exception.code,'unknown_material')

    def test_repeated_catalog_requests_are_bounded_by_existing_read_guard(self):
        from unittest.mock import Mock,patch
        from i2r_agent import translation_workflow as runner
        from i2r_agent.common import Executor
        from i2r_agent.segmented_config import configure
        c=cfg();c['translation']['correctness_only']=True;c=configure(c);c['segmented']['support_tests']=False
        b=source();b['workflow']='source-translation';b['sources']={'Original.thy':'complete original source'}
        pv=Mock();pv.calls=0;pv.usage={};seen=[]
        def answer(pv,c,path,p,analysis=False):
            seen.append(p)
            return {'request_materials':[p['material_versions']['source_catalog']],
                'reading_notes':{row['id']:'Retained source equations before exact catalog read' for row in p['program']['source_pages']}}
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'ask',side_effect=answer):
            p=Path(d)
            with self.assertRaises(Failure) as caught:runner.search(b,None,c,pv,p,Executor(p/'commands'),None,[],[],p/'regressions.json',lambda _:None)
            self.assertEqual(caught.exception.code,'repair_stalled')
            self.assertEqual(len(seen),c['translation']['diagnostic_read_limit'])
            self.assertIn('materials',seen[1]['requested_material'])

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch
from i2r_agent.common import config, merge, read, ROOT, Failure, Executor
from i2r_agent.segmentation import graph, partition, consumers
from i2r_agent.segmented_config import configure, rust_config, materialize, origins
from i2r_agent.segmented_contract import items, resolve, coverage
from i2r_agent.segmented_run import apply_transaction


def cfg():
    return configure(merge(config(),read(Path(__file__).parent/'fixtures/shared-workflow-config.json')['base']))


def source():
    entities={}
    for n,deps in [('A.h',[]),('A.f',['constant:A.h'])]:
        entities['constant:'+n]={'id':'constant:'+n,'name':n,'kind':'constant','source_type':{},
            'dependencies':deps,'execution_equations':[],'callers':[]}
    model={'kind':'isabelle2rust-program','schema_version':1,'entries':['constant:A.f'],
        'entities':entities,'uses':[],'recursive_groups':[],'provenance':{}}
    b={'workflow':'source-translation','source_model':model,'original_source_model':deepcopy(model),
       'programs':[{'entries':model['entries'],'nodes':[],'sccs':[]}], 'sources':{},'source_catalog':[],
       'numeric_policy':{'mode':'checked'},'semantic_analysis':{'opportunities':[]},'rust_config':rust_config({},cfg())}
    b['segmentation']=partition(model)
    return b


def mapping(n):
    return {'source':'constant:A.'+n,'rust':n,'rust_item':'crate::'+n,'kind':'replacement',
            'basis':'original source equation','conditions':['all original inputs']}


def route_reviews(p):
    return [{'source':n,'source_route':'source call structure','rust_route':'same calls in Rust',
             'transformation':'representation only','classification':'implementation_only','reason':'same source work'}
            for n in p['required_algorithm_routes']]


class SegmentationTests(unittest.TestCase):
    def test_algorithm_route_change_cannot_be_accepted_as_equivalence(self):
        from i2r_agent.segmented_run import validate_routes
        b=source();s={'bundle':b,'partition':b['segmentation'],'phase':'whole_review','unit':None,
                    'mapping':[mapping('h'),mapping('f')]}
        with self.assertRaises(Failure) as missing:validate_routes(s,{},cfg())
        self.assertEqual(missing.exception.code,'incomplete_algorithm_review')
        rows=route_reviews({'required_algorithm_routes':['constant:A.h','constant:A.f']})
        rows[1].update(source_route='nested recursive equations',rust_route='closed-form branch table',
                       classification='changed',reason='mathematically equal and faster')
        with self.assertRaises(Failure) as changed:validate_routes(s,{'algorithm_routes':rows},cfg())
        self.assertEqual(changed.exception.code,'algorithm_route_changed')
        rows[1].update(rust_route='explicit stack executing the same recursive calls',
                       classification='implementation_only',reason='continuations preserve source evaluation work')
        validate_routes(s,{'algorithm_routes':rows},cfg())

    def test_dependency_order_and_mutual_group(self):
        b=source();p=b['segmentation']
        self.assertEqual([p['units'][u]['members'] for u in p['order']],[['constant:A.h'],['constant:A.f']])
        self.assertEqual(consumers(p,[p['order'][0]]),set(p['order']))
        b['source_model']['entities']['constant:A.h']['dependencies']=['constant:A.f']
        self.assertEqual(len(partition(b['source_model'])['units']),1)

    def test_specification_types_do_not_pollute_executable_graph(self):
        b=source();b['source_model']['entities']['constant:A.f']['specifications']=[{'kind':'type','name':'Unrelated.T','args':[]}]
        self.assertNotIn('type:Unrelated.T',graph(b['source_model'])['edges'])

    def test_unknown_requires_explicit_boundary_and_business_not_pruned(self):
        b=source();b['source_model']['entities']['constant:A.h']['dependencies']=['constant:Library.x']
        with self.assertRaises(Failure):partition(b['source_model'])
        p=partition(b['source_model'],[{'source':'constant:Library.x','kind':'native','basis':'external contract','conditions':['review required']}])
        self.assertEqual(len(p['units']),2)
        with self.assertRaises(Failure):partition(b['source_model'],[{'source':'constant:A.h','kind':'inlined','basis':'x','conditions':['x']}])

    def test_type_function_cycle_joint_unit(self):
        b=source();m=b['source_model'];m['entities']['constant:A.h']['source_type']={'kind':'type','name':'A.T','args':[]}
        m['entities']['type:A.T']={'id':'type:A.T','kind':'datatype','dependencies':['constant:A.h']}
        p=partition(m);self.assertEqual(p['owner']['type:A.T'],p['owner']['constant:A.h'])

    def test_exact_paths_and_impl_methods(self):
        index=items({'src/lib.rs':'mod a { pub fn same() {} } mod b { pub fn same() {} } struct X; impl X { fn m(){} }'})
        self.assertEqual(resolve(index,'crate::a::same')['scope'],['a'])
        resolve(index,'crate::X::m')
        with self.assertRaises(Failure):resolve(index,'same')

    def test_local_vs_final_coverage(self):
        b=source();files={'src/lib.rs':'fn h()->u128 {1}'}
        coverage(b,files,[mapping('h')],['constant:A.h'],b['segmentation'])
        with self.assertRaises(Failure):coverage(b,files,[mapping('h')],['constant:A.h'],b['segmentation'],True)

    def test_configuration_rejects_legacy_budget(self):
        c=cfg();c['repair']['max_attempts']=50
        with self.assertRaises(Failure):configure(c)
        self.assertEqual(origins({},[('base',{'a':{'b':1}}),('override',{'a':{'b':2}})])['origins']['a.b'],'override')

    def test_dependency_diagnostic_explains_exact_accepted_configuration(self):
        with self.assertRaises(Failure) as result:rust_config({'dependencies':{'dashu-int':'0.6.2'}},cfg())
        self.assertEqual(result.exception.code,'invalid_rust_config')
        self.assertIn('"=0.6.2"',str(result.exception))
        self.assertEqual(rust_config({'dependencies':{'dashu-int':'=0.6.2'}},cfg())['dependencies'],{'dashu-int':'=0.6.2'})

    def test_materialization_removes_stale_source_and_keeps_config(self):
        with tempfile.TemporaryDirectory() as d:
            rc=rust_config({'edition':'2021','features':{'fast':[]}},cfg())
            materialize(d,{'src/lib.rs':'mod old;','src/old.rs':'pub fn x(){}'},rc)
            materialize(d,{'src/lib.rs':'pub fn f(){}'},rc)
            self.assertFalse((Path(d)/'src/old.rs').exists())
            self.assertIn('2021',(Path(d)/'Cargo.toml').read_text())
            self.assertIn('forbid(unsafe_code)',(Path(d)/'src/lib.rs').read_text())

    def test_failed_transaction_preserves_all_state(self):
        b=source();p=b['segmentation'];s={'bundle':b,'partition':p,'files':{'src/lib.rs':'fn h(){}'},'mapping':[mapping('h')],
            'rust_config':b['rust_config'],'completed':[p['order'][0]],'reviews':{},'transactions':[]}
        original=deepcopy(s)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(Failure):apply_transaction(s,{'files':{'src/lib.rs':'fn changed(){}'}},cfg(),d)
        self.assertEqual(s,original)

    def test_upstream_edit_invalidates_consumers(self):
        b=source();p=b['segmentation'];s={'bundle':b,'partition':p,'files':{'src/lib.rs':'fn h()->u128{1}\nfn f()->u128{h()}'},
            'mapping':[mapping('h'),mapping('f')],'rust_config':b['rust_config'],'completed':p['order'], 'reviews':{},'transactions':[]}
        with tempfile.TemporaryDirectory() as d:
            updated=apply_transaction(s,{'edits':[{'file':'src/lib.rs','old':'{1}','new':'{2}'}]},cfg(),d)
        self.assertFalse(updated['completed']);self.assertEqual(s['completed'],p['order'])


    def test_paged_review_cannot_accept_unread_source(self):
        from i2r_agent.segmented_run import payload, validate_review
        b=source();b['source_model']['entities']['constant:A.h']['specifications']=[{'rules':[{'proposition':{'text':'x'*1000}}]}]
        c=cfg();c['segmented']['source_page_characters']=100;c['segmented']['initial_source_characters']=100
        s={'bundle':b,'partition':b['segmentation'],'unit':b['segmentation']['order'][0],
           'phase':'refine','files':{'src/lib.rs':'fn h(){}'},'mapping':[mapping('h')],
           'rust_config':b['rust_config'],'completed':[],'failures':[],'transactions':[]}
        with tempfile.TemporaryDirectory() as d:
            p,ps=payload(s,c,d)
            self.assertGreater(len(ps),1)
            reply={'reviewed_sources':['constant:A.h'],'reviewed_pages':list(ps),'reviewed_code_pages':[x['id'] for x in p['code_page_catalog']],'quality_review':'review',
                'algorithm_routes':route_reviews(p),'review_checks':{k:'checked' for k in c['segmented']['review_categories']}}
            with self.assertRaises(Failure):validate_review(s,reply,ps,c)
            s['seen_pages']=list(ps);validate_review(s,reply,ps,c)

    def test_disjoint_inputs_even_for_small_generator_domain(self):
        from i2r_agent.segmented_inputs import split
        from i2r_agent.suites import scoped_fixed
        fixed=scoped_fixed('ackermann',128)
        dev,final,record=split('ackermann',fixed,[],150,300,20261103,128)
        self.assertTrue(final);self.assertTrue(record['generator_unique_shortfall'])
        self.assertFalse({tuple(x) for x in final}&{tuple(x) for x in dev+fixed})

    def test_large_read_is_batched_without_claiming_unseen_pages(self):
        from i2r_agent.segmented_context import read_pages
        catalog={str(i):{'id':str(i),'text':'x'*10} for i in range(5)}
        material=read_pages(catalog,list(catalog),20)
        self.assertEqual([p['id'] for p in material['pages']],['0','1'])
        self.assertEqual(material['pending_pages'],['2','3','4'])
        with self.assertRaises(Failure):read_pages(catalog,['absent'],20)

    def test_global_paged_analysis_retains_facts_and_reads_beyond_retry_threshold(self):
        from i2r_agent.segmented_context import analyze
        b=source();b['source_model']['entities']['constant:A.h']['specifications']=[{'rules':[{'proposition':{'text':'source fact '*120}}]}]
        c=cfg();c['segmented'].update(source_page_characters=100,initial_source_characters=100,no_progress_limit=2)
        calls=[]
        def answer(provider,cfg,path,p,analysis=False):
            current=p['source_pages']+p['requested_material'].get('pages',[])
            observed=set(p['read_pages'])|{x['id'] for x in current};missing=[x['id'] for x in p['page_catalog'] if x['id'] not in observed]
            calls.append(p)
            if missing:return {'request_pages':missing,'reading_notes':{x['id']:'Exact source conditions and dependencies retained' for x in current}}
            return {'opportunities':[],'boundaries':[],'rust_config':{},'analysis_coverage':list(p['executable_graph']['edges']),
                    'semantic_obligations':[{'source':n,'operation':'retain the supplied source call','rust_representation':'same callable interface','conditions':['source preconditions'],'boundary_cases':['source-defined base case'],'verification':['independent source cases']} for n in p['executable_graph']['edges']]}
        with tempfile.TemporaryDirectory() as d,patch('i2r_agent.segmented_context.ask',side_effect=answer):
            analyzed,_=analyze(b,c,Mock(),d)
            evidence=read(Path(d)/'reading-evidence.json')
            self.assertGreater(len(calls),2);self.assertGreater(len(evidence['retained_source_notes']),2)
            self.assertEqual(len(evidence['read_pages']),len(calls[-1]['page_catalog']))
            self.assertTrue(calls[-1]['source_reading_notes']);self.assertEqual(len(analyzed['segmentation']['units']),2)

    def test_quality_review_requires_actual_complete_rust_body_reads(self):
        from i2r_agent.segmented_run import payload,validate_review
        from i2r_agent.segmented_context import code_pages
        b=source();c=cfg();c['segmented'].update(source_page_characters=100,initial_code_characters=100)
        s={'bundle':b,'partition':b['segmentation'],'unit':b['segmentation']['order'][0],'phase':'refine',
           'files':{'src/lib.rs':'pub fn h(){}\n/*'+('body text '*100)+'*/'},'mapping':[mapping('h')],
           'rust_config':b['rust_config'],'completed':[],'failures':[],'transactions':[]}
        with tempfile.TemporaryDirectory() as d:
            p,ps=payload(s,c,d)
            reply={'quality_review':'review','reviewed_sources':p['required_review_sources'],'reviewed_pages':list(ps),
                   'reviewed_code_pages':[x['id'] for x in p['code_page_catalog']],'algorithm_routes':route_reviews(p),'review_checks':{k:'checked' for k in c['segmented']['review_categories']}}
            self.assertFalse(p['current_files']);self.assertGreater(len(p['code_page_catalog']),len(p['code_pages']))
            with self.assertRaises(Failure):validate_review(s,reply,ps,c)
            s['extra']={'code_pages':[x for x in code_pages(s['files'],100) if x['id'] not in s['seen_code_pages']]}
            p,ps=payload(s,c,d);validate_review(s,reply,ps,c)

    def test_connector_receives_feature_configuration_and_compiles_active_api(self):
        import json
        from i2r_agent.test_connector import connect
        from i2r_agent.segmented_run import connection,compile_crate
        c=cfg();c['testing']['transport']='native-u128'
        rc=rust_config({'features':{'fast':[]},'enabled_features':['fast']},c)
        files={'src/lib.rs':'#[cfg(feature="fast")] pub fn fast()->u128{7}'}
        provider=Mock()
        def answer(system,prompt,**kwargs):
            p=json.loads(prompt);name='fast' if 'fast' in (p.get('algorithm_rust_config') or {}).get('enabled_features',[]) else 'inactive'
            return {'files':{'src/lib.rs':'pub type WireInt=u128; pub type Prepared=(); pub type KernelResult=u128; pub fn observe(_: &[u128])->Vec<u128>{vec![i2r_candidate::'+name+'()]} pub fn benchmark_prepare(_: &[u128]){} pub fn benchmark_run(_:())->u128{i2r_candidate::'+name+'()} pub fn benchmark_encode(x:u128)->Vec<u128>{vec![x]}'}}
        provider.call.side_effect=answer
        with tempfile.TemporaryDirectory() as d:
            w=Path(d);project=w/'scenario';project.mkdir();(project/'Model.thy').write_text('source model');(project/'Kernel.thy').write_text('source kernel')
            crate=materialize(w/'crate',files,rc);ex=Executor(w/'commands')
            connector,_=connect(project,crate,files,[],{'dependencies':{},'rust_config':rc},c,provider,w/'connector')
            built=compile_crate(connection(crate,connector,rc,c),rc,c,ex,False)
            self.assertEqual(built['status'],'passed')
            r=ex.run([built['binary']],stdin='0\n');self.assertEqual(Path(r['stdout']).read_text(),'7\n')

    def test_support_author_and_reviewer_read_all_oversized_source(self):
        from i2r_agent.segmented_support import source_review
        c=cfg();c['segmented']['initial_source_characters']=10;c['segmented']['no_progress_limit']=2
        ps=[{'id':str(i),'source':'constant:A.f','text':'x'*10,'part':i+1,'parts':5} for i in range(5)]
        provider=Mock();seen=[]
        def reply(system,prompt,**kwargs):
            import json
            p=json.loads(prompt);seen.extend(x['id'] for x in p['source_material']['pages'])
            # Premature completion must force remaining exact pages, even with
            # more page reads than the no-progress threshold.
            return {'reading_notes':{x['id']:'Exact source equation and expected result retained' for x in p['source_material']['pages']},'test_source':'#[test] fn test(){assert_eq!(1,1);}','obligations':[{'source':'constant:A.f','expected_basis':'source equation'}]}
        provider.call.side_effect=reply
        with tempfile.TemporaryDirectory() as d:
            result=source_review({'task':'Generate'},ps,c,provider,Path(d))
        self.assertEqual(seen,[str(i) for i in range(5)])
        self.assertIn('test_source',result)

    def test_private_numeric_contract_executes_and_restores_production_source(self):
        from i2r_agent.segmented_support import execute
        c=cfg();rc=rust_config({},c)
        files={'src/lib.rs':'fn minus(a:u128,b:u128)->u128{a.saturating_sub(b)}\nfn add(a:u128,b:u128)->u128{a.checked_add(b).expect("I2R_NUMERIC_OVERFLOW")}\npub fn run()->u128{minus(1,2)}'}
        frozen={'identity':'independent-test','tests':['use i2r_candidate::run; #[test] fn public(){assert_eq!(run(),0);}'],
            'unit_tests':[{'file':'src/lib.rs','source':'#[cfg(test)] mod nested { use super::*; #[test] fn nat_underflow(){assert_eq!(minus(0,1),0);} #[test] #[should_panic(expected="I2R_NUMERIC_OVERFLOW")] fn overflow(){add(u128::MAX,1);} }'}],
            'obligations':[{'source':'nat','expected_basis':'truncated subtraction and explicit checked overflow'}]}
        with tempfile.TemporaryDirectory() as d:
            crate=materialize(Path(d)/'crate',files,rc);before=(crate/'src/lib.rs').read_text()
            result=execute(frozen,crate,rc,c,Executor(Path(d)/'commands'))
            self.assertEqual(result['status'],'passed');self.assertEqual(result['tests_passed'],3)
            self.assertEqual((crate/'src/lib.rs').read_text(),before)
            broken=deepcopy(frozen);broken['unit_tests'][0]['source']='use super::*; #[test] fn wrong(){assert_eq!(minus(0,1),9);}'
            result=execute(broken,crate,rc,c,Executor(Path(d)/'failed-commands'))
            self.assertEqual(result['status'],'support_contract_failed')
            self.assertEqual((crate/'src/lib.rs').read_text(),before)

    def test_support_binding_revision_preserves_original_oracle(self):
        from i2r_agent.segmented_test_audit import revise
        s={'files':{'src/lib.rs':'pub fn f()->u128{2}'}}
        frozen={'identity':'original','tests':['use missing::f; #[test] fn value(){assert_eq!(f(),2);}'],
                'unit_tests':[],'obligations':[{'source':'constant:A.f','case':'value','expected_basis':'two'}]}
        good={'reason':'wrong import','edits':[{'kind':'integration','index':0,'old':'missing::f','new':'i2r_candidate::f'}]}
        updated=revise(frozen,good,s)
        self.assertEqual(updated['oracle_identity'],'original');self.assertEqual(updated['obligations'],frozen['obligations'])
        for old,new in [('f(),2','f(),9'),('#[test]','#[test] #[ignore]'),('use missing::f;','use missing::f; #[derive(Clone)] struct NoClone;')]:
            with self.assertRaises(Failure):revise(frozen,{'reason':'invalid weakening','edits':[{'kind':'integration','index':0,'old':old,'new':new}]},s)

    def test_interfaces_expose_actual_data_layout_and_cfg_but_not_function_bodies(self):
        import json
        from i2r_agent.segmented_contract import interfaces
        files={'src/lib.rs':'mod internal { pub struct Shape { pub x:u128 } pub enum Kind { Empty, Full(Shape) } #[cfg(feature="fast")] pub fn f(x:Shape)->u128 { x.x+987654321 } }'}
        api=interfaces(files)
        self.assertIn('pub x:u128',api['crate::internal::Shape'][0]['declaration'])
        self.assertIn('Full(Shape)',api['crate::internal::Kind'][0]['declaration'])
        self.assertEqual(api['crate::internal::f'][0]['module_scope'],['internal'])
        self.assertIn('#[cfg(feature="fast")]',api['crate::internal::f'][0]['attributes'])
        self.assertNotIn('987654321',json.dumps(api))

    def test_private_inline_module_test_rebinding_preserves_code_and_oracle(self):
        from i2r_agent.segmented_support import execute
        from i2r_agent.segmented_test_audit import revise
        c=cfg();rc=rust_config({},c);files={'src/lib.rs':'// 私有模块\nmod hidden { fn minus(a:u128,b:u128)->u128{a.saturating_sub(b)} } pub fn run()->u128{2}'}
        frozen={'identity':'module-test','tests':['use i2r_candidate::run; #[test] fn public(){assert_eq!(run(),2);}'],
                'unit_tests':[{'file':'src/lib.rs','module':['missing'],'source':'mod nested { use super::*; #[test] fn math(){assert_eq!(minus(1,2),0);} }'}],
                'obligations':[{'source':'nat','case':'underflow','expected_basis':'truncation'}]}
        fixed=revise(frozen,{'reason':'Correct private module scope','unit_locations':[{'index':0,'file':'src/lib.rs','module':['hidden']}]},{'files':files})
        self.assertEqual(fixed['unit_tests'][0]['source'],frozen['unit_tests'][0]['source'])
        with tempfile.TemporaryDirectory() as d:
            crate=materialize(Path(d)/'crate',files,rc);before=(crate/'src/lib.rs').read_text();ex=Executor(Path(d)/'commands')
            self.assertEqual(execute(frozen,crate,rc,c,ex)['status'],'support_test_binding_failed')
            result=execute(fixed,crate,rc,c,ex)
            self.assertEqual(result['status'],'passed');self.assertEqual(result['tests_passed'],2)
            self.assertEqual((crate/'src/lib.rs').read_text(),before)


    def test_intrinsic_boundary_is_recorded_without_spurious_unit(self):
        b=source();p=partition(b['source_model'],[{'source':'class:HOL.type','kind':'native','basis':'logical sort','conditions':['no runtime dictionary']}])
        self.assertEqual(len(p['units']),2);self.assertEqual(len(p['intrinsic_contracts']),1)

    def test_future_function_cannot_be_generated_with_current_unit(self):
        b=source();p=b['segmentation'];s={'bundle':b,'partition':p,'phase':'generate','unit':p['order'][0],
            'files':{'src/lib.rs':''},'mapping':[],'rust_config':b['rust_config'],'completed':[], 'reviews':{},'transactions':[]}
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(Failure) as e:
                apply_transaction(s,{'files':{'src/lib.rs':'fn f(){}'},'mapping':[mapping('f')]},cfg(),d)
            self.assertEqual(e.exception.code,'future_unit_generation')


    def test_rust_cfg_and_feature_are_used_by_actual_compiler(self):
        from i2r_agent.segmented_run import compile_crate
        c=cfg();c['testing']['clippy']='off'
        rc=rust_config({'features':{'fast':[]},'enabled_features':['fast'],'cfg':['i2r_custom']},c)
        code='#[cfg(not(all(feature="fast", i2r_custom)))] compile_error!("configuration not applied"); pub fn f(){}'
        with tempfile.TemporaryDirectory() as d:
            materialize(d,{'src/lib.rs':code},rc)
            checked=compile_crate(Path(d),rc,c,Executor(Path(d)/'logs'))
            self.assertEqual(checked['status'],'passed',checked)

    def test_external_type_mapping_is_verified_by_rust_import_probe(self):
        from i2r_agent.segmented_contract import probes
        from i2r_agent.segmented_run import compile_crate
        c=cfg();c['testing']['clippy']='off';rc=rust_config({},c)
        rows=[{'source':'type:Nat.nat','rust_item':'u128','kind':'native'},
              {'source':'type:List.list','rust_item':'std::vec::Vec','kind':'native'}]
        with tempfile.TemporaryDirectory() as d:
            materialize(d,{'src/lib.rs':'pub fn f(){}'+probes(rows)},rc)
            self.assertEqual(compile_crate(Path(d),rc,c,Executor(Path(d)/'logs'))['status'],'passed')
            rows[1]['rust_item']='std::vec::Nonexistent'
            materialize(d,{'src/lib.rs':'pub fn f(){}'+probes(rows)},rc)
            self.assertEqual(compile_crate(Path(d),rc,c,Executor(Path(d)/'logs'))['status'],'compile_failed')

    def test_generated_unsafe_cannot_pass_compilation(self):
        from i2r_agent.segmented_run import compile_crate
        c=cfg();c['testing']['clippy']='off';rc=rust_config({},c)
        with tempfile.TemporaryDirectory() as d:
            materialize(d,{'src/lib.rs':'pub fn f(){unsafe {core::ptr::read(&1);}}'},rc)
            r=compile_crate(Path(d),rc,c,Executor(Path(d)/'logs'))
            self.assertEqual(r['status'],'compile_failed');self.assertTrue(r['diagnostics'])


if __name__=='__main__':unittest.main()

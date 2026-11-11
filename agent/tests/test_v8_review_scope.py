import tempfile,unittest
from pathlib import Path
from copy import deepcopy
from i2r_agent import segmented_v8 as runner
from i2r_agent import v8_review_scope as scope
from i2r_agent.common import Failure
import test_shared_invalidation as fixtures

class ReviewScopeTests(unittest.TestCase):
    def state(self):
        s,c=fixtures.SharedInvalidationTest().make_state();s['phase']='refine';s['unit']=s['partition']['owner']['constant:A.f'];return s,c
    def change(self,s,c,text):
        with tempfile.TemporaryDirectory() as d:return runner.apply_transaction(s,{'files':{'src/lib.rs':text}},c,Path(d))
    def test_independent_declaration_sequence_preserves_completed_reviews(self):
        s,c=self.state();original=deepcopy(s['reviews']);code=s['files']['src/lib.rs']
        for i in range(30):
            code+=f'pub type Added{i} = u128;\n'
            s=self.change(s,c,code)
            self.assertEqual(s['reviews'],original)
            self.assertEqual(s['transactions'][-1]['invalidated_completed'],[])
        for codepart in ['pub trait NewTrait {fn fresh(&self);}\n','pub enum NewEnum {One,More(Box<NewEnum>)}\n','pub struct NewStruct {pub value:u128}\n']:
            code+=codepart;s=self.change(s,c,code);self.assertEqual(s['reviews'],original)
    def test_shared_edits_and_shadowing_remain_invalidated(self):
        s,c=self.state();code=s['files']['src/lib.rs']
        self.assertFalse(self.change(s,c,code.replace('{1}','{2}'))['completed'])
        s['files']['src/lib.rs']='use helpers::*; pub fn f()->u128{shared()} pub fn g()->u128{shared()}'
        self.assertFalse(self.change(s,c,s['files']['src/lib.rs']+' fn shared()->u128{2}')['completed'])
    def test_documented_independent_additions_preserve_macro_view_reviews(self):
        s,c=self.state();s['partition']['policy']='semantic-components'
        s['partition']['source_edges']={n:[] for n in s['partition']['owner']}
        s['source_reviews']={n:{'evidence':'retained'} for n in s['partition']['owner']}
        old=s['files']['src/lib.rs']+'\nmacro_rules! existing {()=>{1}}\n// existing trailing comment\n'
        s['files']['src/lib.rs']=old
        for docs in ['/// fresh documentation\n/// second line\n',
                     '/** outer block documentation */\n',
                     '/// Unicode 文档\n#[allow(dead_code)]\n/// after attribute\n']:
            with self.subTest(docs=docs):
                extra=docs+'pub fn fresh()->u128{2}\n'
                out=self.change(s,c,old+extra)
                self.assertEqual(out['completed'],s['completed'])
                self.assertEqual(out['source_reviews'],s['source_reviews'])
                # Removing docs must not hide actual shared/macro/import changes.
                for changed in [old.replace('{1}','{2}'),old.replace('()=>{1}','()=>{2}'),old+'use other::*;\n']:
                    self.assertFalse(self.change(s,c,changed+extra)['completed'])

    def test_documentation_does_not_exempt_semantic_attributes_or_module_docs(self):
        old={'src/lib.rs':'pub fn existing(){}\n'}
        for attr in ['#[cfg(feature="x")]','#[custom]','#[repr(C)]']:
            text=old['src/lib.rs']+'/// doc\n'+attr+'\n/** doc */\npub struct Fresh;'
            trimmed,exempt=scope.independent_additions_removed(old,{'src/lib.rs':text})
            self.assertFalse(exempt);self.assertEqual(trimmed['src/lib.rs'],text)
        text='//! module documentation\n'+old['src/lib.rs']+'/// outer\npub fn fresh(){}'
        trimmed,_=scope.independent_additions_removed(old,{'src/lib.rs':text})
        self.assertIn('//! module documentation',trimmed['src/lib.rs'])

    def test_documented_fresh_trait_impl_removes_only_attached_outer_docs(self):
        old={'src/lib.rs':'fn existing(){}\n// keep trailing comment\n'}
        extra='/// trait docs\ntrait Fresh {fn new_method(&self);}\n/** impl docs */\nimpl Fresh for u128 {fn new_method(&self){}}'
        trimmed,exempt=scope.independent_additions_removed(old,{'src/lib.rs':old['src/lib.rs']+extra})
        self.assertEqual(scope.review_tokens(old),scope.review_tokens(trimmed))
        self.assertEqual({r['kind'] for r in exempt},{'trait_item','impl_item'})
    def test_custom_derive_impl_and_import_changes_do_not_get_addition_exemption(self):
        s,c=self.state();code=s['files']['src/lib.rs']
        for extra in ['#[derive(Custom)] pub struct Thing;','impl Thing {fn get()->u128{2}}','use other::Thing;','fn fresh(){impl Thing {fn get()->u128{2}}}']:
            with self.subTest(extra=extra):self.assertFalse(self.change(s,c,code+extra)['completed'])
    def test_fresh_standard_derive_preserves_reviews_but_shadowing_does_not(self):
        s,c=self.state();code=s['files']['src/lib.rs']
        extra='\n#[derive(Debug, Clone, Copy, PartialEq, Eq)]\npub enum NumericError {#[allow(non_camel_case_types)] OVERFLOW}\n'
        self.assertEqual(self.change(s,c,code+extra)['completed'],s['completed'])
        for prefix in ['use custom::Clone;\n','use custom::*;\n','macro_rules! make {()=>{}}\n','#[custom]\nstruct Something;\n','#[derive(Custom)] struct Something;\n']:
            old=prefix+code
            trimmed,exempt=scope.independent_additions_removed({'src/lib.rs':old},{'src/lib.rs':old+extra})
            self.assertNotIn('NumericError',[r['name'] for r in exempt])
        s['files']['src/lib.rs']=code+'\n#[derive(Clone)] pub struct Thing;'
        changed=self.change(s,c,s['files']['src/lib.rs'].replace('derive(Clone)','derive(Clone, Copy)'))
        self.assertFalse(changed['completed'])
    def test_unit_view_includes_helper_and_excludes_unrelated_body_and_finding(self):
        s,c=self.state();s['files']['src/lib.rs']+='\npub fn unrelated(mut v:Vec<u128>)->u128{v.remove(0)}\n'
        ids,_=runner.review_required(s,'refine',c);files,ps,ranges=scope.view(s,ids,c)
        text=''.join(files.values());self.assertIn('fn shared',text);self.assertIn('fn f',text)
        self.assertNotIn('fn g(',text);self.assertNotIn('unrelated',text)
        s['phase']='whole_review';whole,_,_=scope.view(s,ids,c);self.assertIn('unrelated',whole['src/lib.rs'])

    def test_fresh_trait_impl_preserves_old_evidence_in_both_policies(self):
        for policy in ['scc','semantic-components']:
            s,c=self.state();s['partition']['policy']=policy
            s['partition']['source_edges']={n:[] for n in s['partition']['owner']}
            s['source_reviews']={n:{'evidence':'retained'} for n in s['partition']['owner']}
            code=s['files']['src/lib.rs']
            extra='\ntrait FreshBits {fn fresh_bit(&self)->u128;}\nimpl FreshBits for u128 {fn fresh_bit(&self)->u128{*self}}\n'
            out=self.change(s,c,code+extra)
            self.assertEqual(out['completed'],s['completed'],policy)
            self.assertEqual(out['source_reviews'],s['source_reviews'])
            # Simultaneous real helper edits must still invalidate its users.
            self.assertFalse(self.change(s,c,code.replace('{1}','{2}')+extra)['completed'])

    def test_new_trait_impl_collision_and_opaque_context_remain_conservative(self):
        s,c=self.state();code=s['files']['src/lib.rs']
        extras=['trait Fresh {fn shared()->u128;} impl Fresh for u128 {fn shared()->u128{2}}',
                'trait Fresh {fn shared()->u128{2}} impl Fresh for u128 {}',
                'trait Fresh: Other {} impl Fresh for u128 {}',
                'impl std::fmt::Display for Local {fn fmt(&self,f:&mut std::fmt::Formatter)->std::fmt::Result {Ok(())}}',
                'trait Fresh {fn fresh(&self);} impl Fresh for u128 {fn fresh(&self){macro_rules! hidden {()=>{}}}}']
        for extra in extras:self.assertFalse(self.change(s,c,code+extra)['completed'])
        old=code+'\nmacro_rules! invoke {()=>{1}}\n'
        extra='trait Fresh {fn fresh(&self);} impl Fresh for u128 {fn fresh(&self){}}'
        _,exempt=scope.independent_additions_removed({'src/lib.rs':old},{'src/lib.rs':old+extra})
        self.assertFalse(any(r['kind']=='impl_item' for r in exempt))

    def test_trait_signature_has_exact_mapping_identity(self):
        from i2r_agent.segmented_contract import items,resolve
        index=items({'src/lib.rs':'pub trait Bits {fn drop_bit(&self,n:u128)->Self;} impl Bits for u128 {fn drop_bit(&self,n:u128)->Self{*self>>n}}'})
        self.assertEqual(resolve(index,'crate::Bits::drop_bit')['kind'],'function_signature_item')
        self.assertEqual(resolve(index,'crate::u128::drop_bit')['kind'],'function_item')
    def test_unit_view_includes_method_implementation_and_comments_do_not_expand_scope(self):
        s,c=self.state();s['files']['src/lib.rs']='struct Value; impl Value {fn get(&self)->u128{1}}\n// use a helper here\npub fn f()->u128{Value.get()}\npub fn g()->u128{7}\n'
        ids,_=runner.review_required(s,'refine',c);text=''.join(scope.view(s,ids,c)[0].values())
        self.assertIn('impl Value',text);self.assertNotIn('fn g(',text)
    def test_real_compile_pipeline_reviews_each_growing_unit_once(self):
        from unittest.mock import Mock,patch
        from test_segmented_workflow import source,mapping
        from test_v8_workflow import cfg,accept
        from i2r_agent.common import Executor,save
        c=cfg();c['segmented']['support_tests']=False
        c['segmented']['development_performance']=False
        bundle=source();bundle['workflow']='segmented-v8';provider=Mock();provider.calls=0;provider.usage={}
        reviewed=[]
        def ask(pv,conf,path,p,analysis=False):
            phase=p['controller_state']['phase']
            if phase=='generate':
                n=p['unit']['members'][0].rsplit('.',1)[-1]
                body='1' if n=='h' else 'h()+1'
                return {'files':{'src/lib.rs':p['current_files']['src/lib.rs']+f'\npub type Added_{n}=u128;\npub trait Fresh_{n} {{fn fresh_{n}(&self)->u128;}}\nimpl Fresh_{n} for u128 {{fn fresh_{n}(&self)->u128{{*self}}}}\npub fn {n}()->u128{{{body}}}\n'},'mapping':[mapping(n)]}
            if phase=='refine':reviewed.append(p['controller_state']['unit'])
            return accept(p,c)
        with tempfile.TemporaryDirectory() as d:
            w=Path(d);save(w/'regressions.json',[])
            with patch('i2r_agent.segmented_v8.ask',side_effect=ask):
                attempts,done=runner.search(bundle,None,c,provider,w,Executor(w/'commands'),None,[],[],w/'regressions.json',lambda _:None)
            self.assertEqual(done[0]['status'],'passed')
            self.assertEqual(len(reviewed),2);self.assertEqual(len(set(reviewed)),2)
            self.assertEqual(sum(a['action_phase']=='compile' for a in attempts),2)

    def test_repeated_identical_review_is_detected(self):
        s,c=self.state();ids,_=runner.review_required(s,'refine',c);files=scope.view(s,ids,c)[0]
        scope.record_review(s,ids,files)
        with self.assertRaises(Failure) as e:scope.record_review(s,ids,files)
        self.assertEqual(e.exception.code,'redundant_review_schedule')

    def test_transitive_mapping_change_is_new_evidence_but_unrelated_change_is_not(self):
        s,c=self.state();entities=s['bundle']['source_model']['entities']
        entities['constant:A.h']={**deepcopy(entities['constant:A.g']),'id':'constant:A.h','name':'A.h'}
        s['partition']['source_edges']={'constant:A.f':['constant:A.h'],'constant:A.h':['constant:A.g'],'constant:A.g':[]}
        ids={'constant:A.f'};files=scope.view(s,ids,c)[0]
        scope.record_review(s,ids,files)
        next(r for r in s['mapping'] if r['source']=='constant:A.g')['basis']='corrected dependency contract'
        scope.record_review(s,ids,files,check_only=True)
        scope.record_review(s,ids,files)
        s['mapping'].append({'source':'constant:Unrelated','basis':'unrelated update'})
        with self.assertRaises(Failure) as error:scope.record_review(s,ids,files,check_only=True)
        self.assertEqual(error.exception.code,'redundant_review_schedule')

    def test_shared_declaration_and_partition_changes_allow_new_review(self):
        for old,new in [('enum Error {Overflow}', 'enum Error {Overflow, Index}'),
                        ('type Number = u128;', 'type Number = u64;'),
                        ('const LIMIT:u128=1;', 'const LIMIT:u128=2;')]:
            s,c=self.state();s['files']['src/lib.rs']+='\n'+old
            ids={'constant:A.f'};files=scope.view(s,ids,c)[0]
            scope.record_review(s,ids,files)
            s=self.change(s,c,s['files']['src/lib.rs'].replace(old,new))
            self.assertFalse(s['completed'])
            # The bounded view can stay identical; shared declarations must count.
            scope.record_review(s,ids,scope.view(s,ids,c)[0])
            with self.assertRaises(Failure):scope.record_review(s,ids,scope.view(s,ids,c)[0])
        s,c=self.state();ids={'constant:A.f'};files=scope.view(s,ids,c)[0]
        scope.record_review(s,ids,files)
        s['partition']['version']='changed partition'
        scope.record_review(s,ids,files)

    def test_out_of_view_function_signature_change_is_new_review_context(self):
        for before,after in [('fn extra(x:u128)->u128{x}', 'fn extra(mut x:u128)->u128{x+=1;x}'),
                             ('fn extra(x:u128)->u128{x}', 'fn extra(x:u64)->u64{x}')]:
            s,c=self.state();s['files']['src/lib.rs']+='\n'+before
            ids={'constant:A.f'};files=scope.view(s,ids,c)[0]
            self.assertNotIn('fn extra',files['src/lib.rs'])
            old_three=scope.review_identity(s,ids,files,schema=3)
            scope.record_review(s,ids,files)
            changed=self.change(s,c,s['files']['src/lib.rs'].replace(before,after))
            self.assertFalse(changed['completed'])
            new_files=scope.view(changed,ids,c)[0]
            self.assertEqual(scope.review_identity(changed,ids,new_files,schema=3),old_three)
            scope.record_review(changed,ids,new_files)
            with self.assertRaises(Failure) as error:scope.record_review(changed,ids,new_files)
            self.assertEqual(error.exception.code,'redundant_review_schedule')

    def test_unrelated_body_edit_does_not_hide_duplicate_or_invalidate(self):
        s,c=self.state();s['files']['src/lib.rs']+='\nfn extra(x:u128)->u128{x}'
        ids={'constant:A.f'};files=scope.view(s,ids,c)[0]
        scope.record_review(s,ids,files)
        changed=self.change(s,c,s['files']['src/lib.rs'].replace('u128{x}', 'u128{x+1}'))
        self.assertEqual(changed['completed'],s['completed'])
        with self.assertRaises(Failure) as error:scope.record_review(changed,ids,scope.view(changed,ids,c)[0])
        self.assertEqual(error.exception.code,'redundant_review_schedule')

    def test_schema_three_ledger_requires_explicit_snapshot_migration(self):
        s,c=self.state();ids={'constant:A.f'};files=scope.view(s,ids,c)[0]
        s['review_work']=[{'identity_schema':3,'identity':scope.review_identity(s,ids,files,schema=3)}]
        with self.assertRaises(Failure) as error:scope.record_review(s,ids,files)
        self.assertEqual(error.exception.code,'review_evidence_upgrade_required')

    def test_schema_two_ledger_requires_explicit_snapshot_migration(self):
        s,c=self.state();ids={'constant:A.f'};files=scope.view(s,ids,c)[0]
        s['review_work']=[{'identity_schema':2,'identity':scope.review_identity(s,ids,files,schema=2)}]
        with self.assertRaises(Failure) as error:scope.record_review(s,ids,files)
        self.assertEqual(error.exception.code,'review_evidence_upgrade_required')

    def test_legacy_ledger_requires_audit_instead_of_silently_bypassing_guard(self):
        s,c=self.state();ids,_=runner.review_required(s,'refine',c);files=scope.view(s,ids,c)[0]
        s['review_work']=[{'identity':scope.review_identity(s,ids,files,legacy=True)}]
        with self.assertRaises(Failure) as error:scope.record_review(s,ids,files,check_only=True)
        self.assertEqual(error.exception.code,'review_evidence_upgrade_required')

    def test_shared_body_change_only_invalidates_actual_branch(self):
        s,c=self.state();s['files']['src/lib.rs']=s['files']['src/lib.rs'].replace('g()->u128 {shared()}','g()->u128 {7}')
        changed=self.change(s,c,s['files']['src/lib.rs'].replace('{1}','{2}'))
        self.assertEqual(changed['completed'],[s['partition']['owner']['constant:A.g']])

    def test_pending_function_repair_keeps_completed_dependencies(self):
        s,c=self.state();uid=s['partition']['owner']['constant:A.g']
        s['completed']=[u for u in s['completed'] if u!=uid];s['reviews'].pop(uid)
        s['files']['src/lib.rs']=s['files']['src/lib.rs'].replace('g()->u128 {shared()}','g()->u128 {missing()}')
        changed=self.change(s,c,s['files']['src/lib.rs'].replace('missing()','shared()'))
        self.assertEqual(changed['completed'],s['completed'])
        self.assertEqual(changed['transactions'][-1]['body_changes'],['crate::g'])

    def test_review_identity_ignores_padding_but_preserves_literal_whitespace(self):
        a={'src/lib.rs':'fn a()->&\'static str {r"one\n\ntwo"}'}
        b={'src/lib.rs':'\n\n'+a['src/lib.rs']}
        self.assertEqual(scope.review_tokens(a),scope.review_tokens(b))
        self.assertNotEqual(scope.review_tokens(a),scope.review_tokens({'src/lib.rs':a['src/lib.rs'].replace('\n\n','\n')}))
        s,c=self.state();ids,_=runner.review_required(s,'refine',c);files=scope.view(s,ids,c)[0]
        scope.record_review(s,ids,files,check_only=True);self.assertEqual(s['review_work'],[])
        scope.record_review(s,ids,files)
        with self.assertRaises(Failure):scope.record_review(s,ids,{p:'\n'+t for p,t in files.items()},check_only=True)
        self.assertEqual(len(s['review_work']),1)

    def test_real_compile_repair_replays_before_review_without_rechecking_dependency(self):
        from unittest.mock import Mock,patch
        from test_segmented_workflow import source,mapping
        from test_v8_workflow import cfg,accept
        from i2r_agent.common import Executor,save
        c=cfg();c['segmented']['support_tests']=False
        bundle=source();bundle['workflow']='segmented-v8';provider=Mock();provider.calls=0;provider.usage={}
        reviewed=[]
        def ask(pv,conf,path,p,analysis=False):
            phase=p['controller_state']['phase']
            if phase=='generate':
                n=p['unit']['members'][0].rsplit('.',1)[-1]
                body='1' if n=='h' else 'missing()+1'
                return {'files':{'src/lib.rs':p['current_files']['src/lib.rs']+f'\npub fn {n}()->u128{{{body}}}\n'},'mapping':[mapping(n)]}
            if phase=='repair':
                return {'files':{'src/lib.rs':p['current_files']['src/lib.rs'].replace('missing()','h()')},
                        'repair_hypothesis':{'cause':'wrong function name','evidence':'compiler unresolved missing','change':'call h','prediction':'original build passes'}}
            if phase=='refine':reviewed.append(p['unit']['members'][0])
            return accept(p,c)
        with tempfile.TemporaryDirectory() as d:
            w=Path(d);save(w/'regressions.json',[])
            with patch('i2r_agent.segmented_v8.ask',side_effect=ask):
                attempts,done=runner.search(bundle,None,c,provider,w,Executor(w/'commands'),None,[],[],w/'regressions.json',lambda _:None)
            self.assertEqual(done[0]['status'],'passed')
            self.assertEqual(reviewed.count('constant:A.h'),1)
            self.assertEqual(len(reviewed),3)
            replay=[a for a in attempts if a['action_phase']=='repair_replay']
            self.assertEqual(len(replay),1);self.assertEqual(replay[0]['original_replay']['status'],'passed')

"""Exact primitive adaptation, entry-focused responsibility, independent scopes."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock,patch
import pytest
from i2r_agent.common import read,Failure,Executor,save
from i2r_agent import native_numeric_contracts as native,default_adaptations as defaults
from i2r_agent import translation_workflow as generation,segmented_support as support,source_suite_review as full,source_failure_review as failure,support_scope,test_obligations
from i2r_agent.segmentation import partition
from i2r_agent.source_input import numeric_contract
from test_segmented_workflow import source
from test_translation_workflow import cfg

ROOT='constant:A.f'
NAT_SOURCES=['type:Nat.nat','constant:Nat.zero_nat_inst.zero_nat','constant:Nat.Suc',native.SOURCE]
NAMES=['Nat','nat_zero','nat_suc','nat_plus']

def fixture(mode='arbitrary'):
    c=cfg();c['translation']['correctness_only']=True;c['preprocessing']['numeric_mode']=mode
    if mode=='arbitrary':c['preprocessing']['numeric_library']='dashu-int'
    b=source();es=read(Path(__file__).parent/'fixtures/default-primitives.json')
    b['source_model']['entities']={n:deepcopy(es[n]) for n in NAT_SOURCES}
    b['source_model']['entities'][ROOT]={'id':ROOT,'name':'A.f','kind':'constant','dependencies':list(NAT_SOURCES),'execution_equations':[],'source_type':{}}
    b['source_model']['entries']=[ROOT];b['numeric_policy']=numeric_contract(c)
    b['original_source_model']=deepcopy(b['source_model']);b['workflow']='source-translation'
    b['segmentation']=partition(b['source_model'],defaults.proposals(b['source_model'],b['numeric_policy']))
    s={'bundle':b,'partition':b['segmentation'],'mapping':[{'source':n,'rust_item':'crate::'+name,'kind':'replacement','basis':'untrusted prose','conditions':['preserve source semantics']} for n,name in zip(NAT_SOURCES+[ROOT],NAMES+['f'])],
       'files':{'src/lib.rs':'pub type Nat=u128; pub fn nat_zero()->Nat{0} pub fn nat_suc(n:Nat)->Nat{n+1} pub fn nat_plus(m:Nat,n:Nat)->Nat{m+n} pub fn f(m:Nat,n:Nat)->Nat{if m==0{0}else{nat_plus(n,f(m-1,n))}}'},'rust_config':b['rust_config']}
    return c,b,s

@pytest.mark.parametrize('mode',['checked','arbitrary'])
def test_exact_native_contract_is_shared_and_contains_no_candidate_or_prose(mode):
    c,b,s=fixture(mode);first=native.context(s)
    assert len(first['contracts'])==1
    assert ('checked_add' if mode=='checked' else 'UBig') in first['contracts'][0]['implementation']
    s['partition']['boundaries'][0]['conditions']=['candidate says expected=999']
    s['files']['src/lib.rs']='private candidate secret'
    assert native.context(s)==first
    assert 'candidate says' not in str(first) and 'private candidate secret' not in str(first)

@pytest.mark.parametrize('change',['type','equation','same_name','entry','revoked','trait','backend'])
def test_nonregistered_or_revoked_boundary_never_grants_native_permission(change):
    _,_,s=fixture()
    if change=='type':s['bundle']['source_model']['entities'][native.SOURCE]['source_type']={}
    if change=='equation':s['bundle']['source_model']['entities'][native.SOURCE]['execution_equations']=[]
    if change=='same_name':
        e=s['bundle']['source_model']['entities'].pop(native.SOURCE);s['bundle']['source_model']['entities']['constant:Custom.plus_nat']=e
    if change=='entry':s['bundle']['source_model']['entries']=[native.SOURCE]
    if change=='revoked':s['partition']['boundaries']=[r for r in s['partition']['boundaries'] if r['source']!=native.SOURCE]
    if change=='trait':next(r for r in s['partition']['boundaries'] if r['source']==native.SOURCE)['kind']='trait'
    if change=='backend':s['bundle']['numeric_policy']['numeric_library']['name']='other'
    assert native.context(s)['contracts']==[]

@pytest.mark.parametrize('body',['let mut x=m;while x>0{x-=1;}n','nat_plus(m-1,n+1)'])
def test_exact_unary_helper_is_candidate_defect_but_business_recursion_is_retained(body):
    _,_,s=fixture();assert native.check_realization(s)['helpers']
    s['files']['src/lib.rs']=s['files']['src/lib.rs'].replace('{m+n}','{'+body+'}')
    with pytest.raises(Failure) as error:native.check_realization(s)
    assert error.value.code=='plan_contract_failed' and error.value.evidence['candidate_repair_only']
    assert error.value.evidence['test_expectations_unchanged']
    next(r for r in s['mapping'] if r['source']==native.SOURCE)['rust_item']='crate::f'
    assert native.check_realization(s)['helpers'][0]['status']=='inline_or_shared_owner'
    s['partition']['boundaries']=[]
    assert native.check_realization(s)['helpers']==[]


def test_delegated_helper_does_not_require_a_literal_operator():
    _,_,s=fixture();s['files']['src/lib.rs']=s['files']['src/lib.rs'].replace('{m+n}','{backend::add(m,n)}')
    assert native.check_realization(s)['helpers'][0]['status']=='no_local_unary_loop_or_self_recursion'


def test_only_exact_adopted_dependencies_leave_author_targets_and_rows():
    c,_,s=fixture();plan=support_scope.plan(s,c)
    assert plan['groups']==[[ROOT]]
    assert plan['context_dependencies']==sorted(NAT_SOURCES)
    assert plan['required_obligations']==[{'source':ROOT,'category':'public_behavior'}]
    assert set(NAT_SOURCES)<=set(support_scope.needed(s['bundle']['source_model'],[ROOT]))
    old=deepcopy(s);old['partition']['boundaries']=[]
    assert len(test_obligations.requirements(old,NAT_SOURCES+[ROOT]))==2
    assert set(n for g in support_scope.plan(old,c)['groups'] for n in g)==set(NAT_SOURCES+[ROOT])
    assert plan['identity']!=support_scope.plan(old,c)['identity']
    # Keep checked arithmetic range/overflow and Suc author responsibility.
    c,_,s=fixture('checked');plan=support_scope.plan(s,c)
    assert native.SOURCE in plan['source_owner'] and 'constant:Nat.Suc' in plan['source_owner']
    assert {'source':native.SOURCE,'category':'zero_and_range_boundaries'} in plan['required_obligations']
    # User functions and generic / boolean adapters are not globally pruned.
    model=s['bundle']['source_model'];model['entities']['constant:A.plus_nat']={'id':'constant:A.plus_nat','kind':'constant','execution_equations':[{}]}
    s['mapping'].append({'source':'constant:A.plus_nat','rust_item':'crate::user_plus'})
    assert 'constant:A.plus_nat' in support_scope.plan(s,c)['source_owner']

@pytest.mark.parametrize('mode',['checked','arbitrary'])
def test_actual_generation_repair_author_and_failure_payloads_share_contract(tmp_path,mode):
    c,b,s=fixture(mode)
    class Boundary(BaseException):pass
    seen=[]
    def stop(*args,**kwargs):seen.append(args[3]);raise Boundary()
    provider=Mock();provider.calls=0;provider.usage={};save(tmp_path/'regressions.json',[])
    with patch.object(generation,'ask',side_effect=stop),pytest.raises(Boundary):
        generation.search(b,None,c,provider,tmp_path/'generation',Executor(tmp_path/'commands'),{},[],[],tmp_path/'regressions.json',lambda _:None)
    state=read(tmp_path/'generation/segmented-checkpoint.json');state.update(files=s['files'],mapping=s['mapping'])
    expected=native.context(s)
    assert seen[-1]['program']['native_numeric_contracts']==expected
    state['phase']='repair'
    assert generation.payload(state,c,tmp_path/'repair')[0]['program']['native_numeric_contracts']==expected
    def author_stop(payload,*args,**kwargs):seen.append(payload);raise Boundary()
    with patch.object(support,'source_review',side_effect=author_stop),pytest.raises(Boundary):support.prepare(state,c,provider,tmp_path/'author')
    assert seen[-1]['native_numeric_contracts']==expected
    if mode=='arbitrary':
        assert seen[-1]['author_group']['owned_source_ids']==[ROOT]
        assert seen[-1]['coverage_requirements']==[{'source':ROOT,'category':'public_behavior'}]
    frozen={'identity':'fixture-suite','tests':['#[test] fn result(){assert_eq!(i2r_candidate::f(1,2),2);}'],'unit_tests':[],
        'obligations':[{'source':ROOT,'category':'public_behavior','test_name':'__i2r_source_contract_0::result','case':'1,2','expected_basis':'source'}]}
    material=failure.payload(frozen,state,c,['__i2r_source_contract_0::result'])
    assert material['native_numeric_contracts']==expected
    assert full.payload(frozen,state,c)['native_numeric_contracts']==expected
    key=failure.key_for(material,c);scope=full.scope(frozen,state,c)
    changed_type=deepcopy(state);changed_type['bundle']['source_model']['entities'][native.SOURCE]['source_type']={}
    assert full.scope(frozen,changed_type,c)!=scope
    assert failure.key_for(failure.payload(frozen,changed_type,c,['__i2r_source_contract_0::result']),c)!=key
    state['partition']['boundaries']=[]
    assert failure.key_for(failure.payload(frozen,state,c,['__i2r_source_contract_0::result']),c)!=key
    assert full.scope(frozen,state,c)!=scope
    with pytest.raises(Failure):failure.validation_scope(frozen,material,state)
    accepted={'revision':{'failed_test_ids':['__i2r_source_contract_0::result']},'source_check':{'status':'test_correct','scope':key}}
    with pytest.raises(Failure,match='scope changed'):failure.require_revision(frozen,state,c,accepted)
    provider.call.assert_not_called()


def test_explicit_unresolved_preserves_diagnostic_without_widening_permissions(tmp_path):
    from test_source_resources import fixture as resource_fixture
    from i2r_agent import source_resource_revision as revision
    frozen,result,material,verdict,_=resource_fixture(tmp_path);original=deepcopy(frozen)
    with pytest.raises(Failure) as error:revision.apply(frozen,verdict,{'action':'unresolved','reason':'no legal literal-only change','derivation':'source obligations conflict'},{},material,result)
    assert error.value.code=='source_check_unresolved'
    assert error.value.evidence['reason']=='no legal literal-only change'
    assert 'Invalid bounded resource proposal' not in str(error.value) and frozen==original


def test_missing_numeric_policy_or_unknown_backend_preserves_original_responsibilities():
    _,_,s=fixture();s['bundle'].pop('numeric_policy')
    assert native.context(s)['contracts']==[]
    assert test_obligations.responsibility_context(s)['context_dependencies']==[]
    _,_,s=fixture();s['bundle']['numeric_policy']['numeric_library']['name']='other'
    assert native.context(s)['contracts']==[]
    assert test_obligations.responsibility_context(s)['context_dependencies']==[]


def test_real_compile_controller_routes_unary_primitive_to_candidate_repair(tmp_path):
    c,b,s=fixture();provider=Mock();provider.calls=0;provider.usage={};save(tmp_path/'regressions.json',[])
    class Boundary(BaseException):pass
    seen=[]
    def stop(*args,**kwargs):seen.append(args[3]);raise Boundary()
    work=tmp_path/'run'
    with patch.object(generation,'ask',side_effect=stop),pytest.raises(Boundary):
        generation.search(b,None,c,provider,work,Executor(tmp_path/'commands'),{},[],[],tmp_path/'regressions.json',lambda _:None)
    state=read(work/'segmented-checkpoint.json');state.update(files=s['files'],mapping=s['mapping'],phase='final_compile',completed=list(s['partition']['units']))
    state['files']['src/lib.rs']=state['files']['src/lib.rs'].replace('{m+n}','{let mut x=m;while x>0{x-=1;}n}')
    save(work/'segmented-checkpoint.json',state)
    with patch.object(generation,'ask',side_effect=stop),pytest.raises(Boundary):
        generation.search(b,None,c,provider,work,Executor(tmp_path/'commands2'),{},[],[],tmp_path/'regressions.json',lambda _:None)
    after=read(work/'segmented-checkpoint.json')
    assert after['phase']=='repair' and after['files']==state['files']
    assert seen[-1]['feedback']['status']=='plan_contract_failed'
    assert seen[-1]['feedback']['evidence']['candidate_repair_only']
    assert not (work/'support-tests').exists()
    provider.call.assert_not_called()

"""Compiler-bound rejecting completion preserves all existing test evidence."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock,patch
import pytest
from i2r_agent.common import Failure,Executor,save,read
from i2r_agent.segmented_test_audit import (exhaustiveness_plan,exhaustiveness_revision,canonical_exhaustiveness,
    rejecting_match_sites,normalize_rejecting_proposal,adjudicate,revise,invariants)
from i2r_agent.segmented_support import execute
from i2r_agent.segmented_config import configure,materialize,rust_config
from i2r_agent.support_issue_lineage import migrate
from test_translation_workflow import cfg

SINGLE='#[test] fn singleton(){let x=i2r_candidate::value();match x{Some(7)=>(),None=>panic!(),}}'
NESTED='#[test] fn nested(){match Some(Some(7)){Some(x)=>match x{Some(7)=>(),None=>panic!(),},None=>panic!(),} match Some(1){Some(1)=>(),None=>panic!(),}}'
FILES={'src/lib.rs':'pub fn value()->Option<i32>{Some(7)}'}


def fixture(codes=(SINGLE,)):
    frozen={'identity':'frozen','tests':list(codes),'unit_tests':[],
            'obligations':[{'source':'A.f','test_name':f'__i2r_source_contract_{i}::'+('nested' if 'fn nested' in code else 'singleton')} for i,code in enumerate(codes)]}
    locations=[]
    for i,code in enumerate(codes):
        for site in rejecting_match_sites(code):
            # In NESTED, the outer Some(x)/None already is exhaustive. Bind only
            # the literal-payload child and the independent literal-payload match.
            if code==NESTED and site['match_start']==code.index('match'):continue
            locations.append((i,site['row']+2,site['column']))
    diagnostic='\n'.join(f'error[E0004]: non-exhaustive patterns\n  --> tests/source_contract_{i}.rs:{line}:{col}' for i,line,col in locations)
    result={'status':'support_test_compile_failed','frozen_identity':'frozen','immutable_test_sources':list(codes),'diagnostic':diagnostic}
    return frozen,result,{'files':FILES,'support_evidence':result,'failures':[],'repair_issues':[]}

@pytest.mark.parametrize('codes',[(SINGLE,), (NESTED,), (SINGLE,NESTED)])
def test_single_nested_and_cross_artifact_plan_preserves_original_invariants(codes):
    frozen,result,state=fixture(codes);plan=exhaustiveness_plan(frozen,result)
    fixed=exhaustiveness_revision(frozen,result,state)
    assert fixed['parent_identity']==frozen['identity'] and fixed['obligations']==frozen['obligations']
    assert sum(c.count('_ => ::core::panic!()') for c in fixed['tests'])==sum(len(v) for v in plan.values())
    for old,new in zip(frozen['tests'],fixed['tests']):assert invariants(old)==invariants(new)

@pytest.mark.parametrize('fault',['other_code','uncoded_error','production_file','stale_identity','stale_bytes','wrong_position','unknown_artifact','partial_binding','should_panic','catch_unwind'])
def test_incomplete_or_unsafe_compiler_evidence_never_authorizes_completion(fault):
    frozen,result,state=fixture((SINGLE,NESTED))
    if fault=='other_code':result['diagnostic']+='\nerror[E0308]: mismatched types'
    elif fault=='uncoded_error':result['diagnostic']+='\nerror: expected expression'
    elif fault=='production_file':result['diagnostic']=result['diagnostic'].replace('tests/source_contract_0.rs','src/lib.rs')
    elif fault=='stale_identity':result['frozen_identity']='old'
    elif fault=='stale_bytes':result['immutable_test_sources']=['different']
    elif fault=='wrong_position':result['diagnostic']=result['diagnostic'].replace('.rs:3:', '.rs:4:',1)
    elif fault=='unknown_artifact':result['diagnostic']=result['diagnostic'].replace('source_contract_0.rs','source_contract_99.rs')
    elif fault=='partial_binding':result['diagnostic']+='\nerror[E0004]: another error without a supported exact location'
    else:
        frozen['tests'][0]='// '+fault+'\n'+frozen['tests'][0];result['immutable_test_sources']=frozen['tests']
    assert exhaustiveness_revision(frozen,result,state) is None


def proposal_for(frozen,result,message='diagnostic payload 123'):
    canonical=canonical_exhaustiveness(frozen,exhaustiveness_plan(frozen,result))
    return {'action':'binding_fix','reason':'append failing branches',
       'edits':[{'kind':'integration','index':i,'old':frozen['tests'][i],
                 'new':text.replace('::core::panic!()',f'panic!("{message}")')} for i,text in canonical.items()]}


def test_model_added_diagnostic_strings_normalize_to_same_compiler_plan():
    frozen,result,state=fixture((SINGLE,NESTED));proposal=proposal_for(frozen,result)
    fixed=revise(frozen,proposal,state,compiler_failure=result)
    assert fixed==exhaustiveness_revision(frozen,result,state)
    assert 'diagnostic payload' not in ''.join(fixed['tests'])
    assert 'diagnostic payload' in proposal['edits'][0]['new']

@pytest.mark.parametrize('fault',['input','expected','assertion','success_fallback','return_fallback','guard','side_effect','format_args','non_target','remove_arm','obligations','partial_repair'])
def test_model_normalization_never_hides_non_rejecting_or_original_changes(fault):
    frozen,result,state=fixture((SINGLE,NESTED));proposal=proposal_for(frozen,result);new=proposal['edits'][0]['new']
    if fault=='input':new=new.replace('value()','value(1)')
    elif fault=='expected':new=new.replace('Some(7)','Some(8)')
    elif fault=='assertion':new=new.replace('Some(7)=>()','Some(7)=>assert!(true)')
    elif fault=='success_fallback':new=new.replace('panic!("diagnostic payload 123")','()')
    elif fault=='return_fallback':new=new.replace('panic!("diagnostic payload 123")','return')
    elif fault=='guard':new=new.replace('_ =>','_ if false =>')
    elif fault=='side_effect':new=new.replace('panic!("diagnostic payload 123")','{touch();panic!()}')
    elif fault=='format_args':new=new.replace('panic!("diagnostic payload 123")','panic!("{}", i2r_candidate::value().unwrap())')
    elif fault=='non_target':new+='\nfn extra(){}'
    elif fault=='remove_arm':new=new.replace('None=>panic!(),','')
    elif fault=='obligations':proposal['obligations']=[]
    else:proposal['edits'].pop()
    proposal['edits'][0]['new']=new
    with pytest.raises(Failure):revise(frozen,proposal,state,compiler_failure=result)


def test_real_multifile_compile_execution_lineage_and_wrong_candidate_rejection(tmp_path):
    frozen,_,_=fixture((SINGLE,NESTED));c=cfg();c['translation']['correctness_only']=True;c=configure(c);rc=rust_config({},c)
    crate=materialize(tmp_path/'candidate',FILES,rc);executor=Executor(tmp_path/'commands');provider=Mock()
    failed=execute(frozen,crate,rc,c,executor)
    assert failed['status']=='support_test_compile_failed' and failed['diagnostic'].count('error[E0004]')==3
    state={'files':FILES,'support_evidence':failed,'failures':[],'repair_issues':[]}
    fixed=adjudicate(frozen,failed,state,c,provider,tmp_path/'audit')['frozen'];provider.call.assert_not_called()
    assert fixed['binding_audit']['method']=='compiler-span-exhaustiveness-v2'
    migrate(state,frozen,fixed,tmp_path/'audit')
    assert execute(fixed,crate,rc,c,executor)['status']=='passed'
    materialize(crate,{'src/lib.rs':'pub fn value()->Option<i32>{Some(8)}'},rc)
    assert execute(fixed,crate,rc,c,executor)['status']=='support_contract_failed'
    tampered=deepcopy(fixed);tampered['tests'][0]=tampered['tests'][0].replace('Some(7)','Some(8)')
    with pytest.raises(Failure):migrate(state,frozen,tampered,tmp_path/'audit')


def test_actual_controller_replays_fix_then_requires_D_without_extra_audit_call(tmp_path):
    from i2r_agent.translation_workflow import search
    from test_segmented_workflow import source,mapping
    from i2r_agent import observation_source
    c=cfg();c['translation']['correctness_only']=True;c=configure(c);b=source();b['workflow']='source-translation'
    frozen={'identity':'controller-multi-e0004','tests':['#[test] fn first(){assert_eq!(i2r_candidate::h(),1);match i2r_candidate::f(){2=>(),}}',
            '#[test] fn second(){match i2r_candidate::h(){1=>(),}}'],'unit_tests':[],
            'obligations':[{'source':'constant:A.f','test_name':'__i2r_source_contract_0::first'}, {'source':'constant:A.h','test_name':'__i2r_source_contract_1::second'}]}
    save(tmp_path/'support-tests'/ (frozen['identity']+'.json'),frozen)
    provider=Mock();provider.calls=0;provider.usage={}
    def generate(pv,cfg,path,payload,analysis=False):
        assert payload['controller_state']['phase']=='generate'
        name=payload['unit']['members'][0].rsplit('.',1)[-1]
        return {'files':{'src/lib.rs':payload['current_files']['src/lib.rs']+'\npub fn '+name+'()->u128{'+('1' if name=='h' else 'h()+1')+'}'},'mapping':[mapping(name)]}
    testing=tmp_path/'testing';testing.mkdir();(testing/'Model.thy').write_text('fixture');(testing/'Kernel.thy').write_text('fixture')
    with patch('i2r_agent.translation_workflow.ask',side_effect=generate),patch('i2r_agent.segmented_support.prepare',return_value=frozen),patch.object(observation_source,'acquire',side_effect=Failure('needs_user','ZERO_API_D_CONNECTION_BOUNDARY')):
        with pytest.raises(Failure,match='ZERO_API_D_CONNECTION_BOUNDARY'):
            search(b,testing,c,provider,tmp_path,Executor(tmp_path/'commands'),{},[],[],tmp_path/'regressions.json',lambda _:None)
    state=read(tmp_path/'segmented-checkpoint.json');provider.call.assert_not_called()
    assert state['support_evidence']['status']=='passed' and state['phase']=='connect' and state.get('source_candidate_lock')
    assert not state.get('differential_suites') and state['status']=='active'
    assert len([a for a in state['attempts'] if a['action_phase']=='support_audit'])==1


def test_real_mixed_import_error_can_be_fixed_before_pure_exhaustiveness(tmp_path):
    original='use missing::value;\n'+SINGLE.replace('i2r_candidate::value()','value()')
    frozen,_,_=fixture((original,));c=cfg();c['translation']['correctness_only']=True;c=configure(c);rc=rust_config({},c)
    crate=materialize(tmp_path/'candidate',FILES,rc);executor=Executor(tmp_path/'commands')
    failed=execute(frozen,crate,rc,c,executor)
    # rustc may withhold downstream E0004 while the import is unresolved; retain
    # the actual binding diagnostic and add the independently known fixture span
    # to exercise the combined diagnostic policy deterministically.
    assert 'E0432' in failed['diagnostic']
    _,known,_=fixture((original,));mixed={**failed,'diagnostic':failed['diagnostic']+'\n'+known['diagnostic']}
    proposal={'action':'binding_fix','reason':'use the existing candidate API','edits':[{'kind':'integration','index':0,'old':'use missing::value;','new':'use i2r_candidate::value;'}]}
    fixed_import=revise(frozen,proposal,{'files':FILES},compiler_failure=mixed)
    assert fixed_import['tests'][0]==original.replace('missing::value','i2r_candidate::value')
    assert exhaustiveness_revision(frozen,mixed,{'files':FILES}) is None
    with pytest.raises(Failure):revise(frozen,proposal_for(frozen,known),{'files':FILES},compiler_failure=mixed)
    pure=execute(fixed_import,crate,rc,c,executor)
    assert 'E0004' in pure['diagnostic'] and 'E0432' not in pure['diagnostic']
    completed=exhaustiveness_revision(fixed_import,pure,{'files':FILES})
    assert execute(completed,crate,rc,c,executor)['status']=='passed'

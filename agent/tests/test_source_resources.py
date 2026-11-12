from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock,patch
import shutil,subprocess
import pytest
from i2r_agent.common import Failure,Executor,save,read
from i2r_agent import source_resources as resources,source_resource_revision as revision,source_failure_review as review,source_suite_review as full

NAME='__i2r_source_contract_0::large'
CODE='''fn n(s:&str)->u128{s.parse().unwrap()}
#[test] fn large(){assert_eq!(add(n("1000000000"), n("1000000000")),n("2000000000"));}
#[test] fn sibling(){assert_eq!(add(2u128, 3u128),5u128);}
'''

def fixture(tmp_path):
    frozen={'identity':'original','tests':[CODE],'unit_tests':[],'obligations':[{'source':'A.add','category':'large_data','disposition':'executed','test_name':NAME,'case':'large data','expected_basis':'source addition'}]}
    (tmp_path/'out').write_text('running 2 tests\ntest '+NAME+' ... ')
    (tmp_path/'err').write_text("\nthread '"+NAME+"' (123) has overflowed its stack\nfatal runtime error: stack overflow, aborting\n")
    record={'status':'failed','returncode':-6,'stdout':str(tmp_path/'out'),'stderr':str(tmp_path/'err'),'command':['test']}
    failure={'status':'support_contract_failed','compilation':{'status':'passed'},'record':record,'frozen_identity':'original','execution_artifacts':resources.snapshot(record)['artifacts']}
    material={'source':[{'id':'page','source':'A.add','part':1,'parts':1,'text':'{"equation":"add x 0 = x; add x (Suc y) = Suc (add x y)"}'}],'interfaces':{},'numeric_policy':{}}
    verdict={'action':'needs_revision','source_evidence':[{'id':'e1','kind':'source','source':'A.add','quote':'add x (Suc y) = Suc (add x y)'}],
       'tests':[{'id':r['id'],'verdict':'wrong' if r['id']==NAME else 'correct','basis':['e1'],'premise':'natural inputs','expectation':'source recursion','assertion':'exact equality','reason':'second argument controls recursive depth'} for r in full.inventory(frozen)],
       'obligations':[{'id':'o:0','verdict':'wrong','tests':[NAME],'basis':['e1'],'reason':'choose large first value and feasible second value'}],
       'resource_assessment':{'tests':[{'test_id':NAME,'control_parameters':['y'],'data_parameters':['x'],'growth':'depth y','feasible_plan':'retain first large data; small y','basis':['e1']}]}}
    slots=revision.slots(frozen,full.inventory(frozen)[0]);edits=[]
    for row,new in [(slots[1],'"7"'),(slots[2],'"1000000007"')]:edits.append({'slot_id':row['id'],'old':row['old'],'new':new})
    proposal={'action':'resample_resource_literals','derivation':'source recursion with y=7','literal_edits':edits}
    return frozen,failure,material,verdict,proposal


def test_exact_crash_name_is_bound_but_never_a_semantic_judgment(tmp_path):
    frozen,failure,_,_,_=fixture(tmp_path)
    assert review.failed_ids(frozen,failure)==[NAME]
    assert resources.bound(frozen,failure)['not_semantic_judgment']
    assert failure['status']=='support_contract_failed'

@pytest.mark.parametrize('fault',['unknown','missing','changed_log','compile','false_stack_message'])
def test_ambiguous_or_untrusted_crash_never_admits_checker(tmp_path,fault):
    frozen,failure,_,_,_=fixture(tmp_path)
    if fault in {'unknown','missing','false_stack_message'}:
        text=Path(failure['record']['stderr']).read_text()
        if fault=='unknown':text=text.replace(NAME,'unknown')
        elif fault=='missing':text='fatal runtime error: stack overflow, aborting\n'
        else:failure['record']['returncode']=101
        Path(failure['record']['stderr']).write_text(text);failure['execution_artifacts']=resources.snapshot(failure['record'])['artifacts']
    elif fault=='changed_log':Path(failure['record']['stderr']).write_text('tampered')
    else:failure['compilation']['status']='failed'
    with pytest.raises(Failure):review.failed_ids(frozen,failure)


def test_resource_resampling_only_changes_numeric_leaves_and_needs_new_judgment(tmp_path):
    frozen,failure,material,verdict,proposal=fixture(tmp_path)
    updated=revision.apply(frozen,verdict,proposal,{},material,failure)
    assert updated['tests'][0]==CODE.replace('n("1000000000"), n("1000000000")','n("1000000000"), n("7")').replace('n("2000000000")','n("1000000007")')
    assert updated['parent_identity']=='original' and updated['source_check']['requires_new_scope_acceptance']
    assert updated['resource_revision_origin']['execution_identity']==resources.bound(frozen,failure)['execution_identity']
    assert updated['obligations']==frozen['obligations'] and full.inventory(updated)==full.inventory(frozen)
    with pytest.raises(Failure):review.require_revision(updated,{}, {},None)
    with pytest.raises(Failure):revision.apply(updated,verdict,proposal,{},material,failure)

@pytest.mark.parametrize('fault',['expression','call','bool','unknown_slot','stale_literal','uncertain','no_source_assessment','wrong_scope','waive_obligation','sibling','new_category','type_suffix'])
def test_resource_route_cannot_rewrite_structure_or_waive_source_proof(tmp_path,fault):
    frozen,failure,material,verdict,proposal=fixture(tmp_path)
    edit=proposal['literal_edits'][0]
    if fault in {'expression','call','bool'}:edit['new']={'expression':'7 + 0','call':'candidate()','bool':'true'}[fault]
    elif fault=='unknown_slot':edit['slot_id']='invented'
    elif fault=='stale_literal':edit['old']='"2"'
    elif fault=='uncertain':verdict['tests'][0]['verdict']='uncertain'
    elif fault=='no_source_assessment':verdict.pop('resource_assessment')
    elif fault=='wrong_scope':verdict['resource_assessment']['tests'][0]['test_id']='unknown'
    elif fault=='waive_obligation':verdict['obligations'][0]['verdict']='not_applicable'
    elif fault=='sibling':
        slot=revision.slots(frozen,full.inventory(frozen)[1])[0];edit.update(slot_id=slot['id'],old=slot['old'],new='0u128')
    elif fault=='new_category':proposal['obligation_edits']=[{'id':'o:0','field':'category','old':'large_data','new':'small_data'}]
    else:
        frozen['tests'][0]=CODE.replace('n("1000000000"), n("1000000000")','n("1000000000"), 1000000000u128')
        slot=revision.slots(frozen,full.inventory(frozen)[0])[1];edit.update(slot_id=slot['id'],old=slot['old'],new='7u8')
    with pytest.raises(Failure):revision.apply(frozen,verdict,proposal,{},material,failure)


def test_real_libtest_exact_timeout_and_abort_receipts(tmp_path):
    rustc=shutil.which('rustc')
    if not rustc:pytest.skip('Rust toolchain required')
    src=tmp_path/'probe.rs';binary=tmp_path/'probe'
    src.write_text('mod __i2r_source_contract_0 { #[test] fn wait(){std::thread::sleep(std::time::Duration::from_secs(60));} #[test] fn abort(){std::process::abort();} #[test] fn fast(){} }')
    subprocess.run([rustc,'--test',str(src),'-o',str(binary)],check=True,capture_output=True)
    frozen={'identity':'suite','tests':['#[test] fn wait(){} #[test] fn abort(){} #[test] fn fast(){}']}
    ex=Executor(tmp_path/'commands')
    def command(name):return [str(binary),name,'--exact','--test-threads=1','--format=pretty']
    original=ex.run(command('__i2r_source_contract_0::wait'),timeout=2,check=False)
    diagnosis=resources.diagnose(frozen,original,{'testing':{'process_timeout':2}},ex,command)
    result={'status':'support_contract_failed','compilation':{'status':'passed'},'record':original,'frozen_identity':'suite','resource_diagnostic':diagnosis}
    bound=resources.bound(frozen,result)
    assert bound['failed_test_ids']==['__i2r_source_contract_0::abort','__i2r_source_contract_0::wait']
    assert len(diagnosis['isolations'])==3 and result['status']=='support_contract_failed'
    assert all(r['record']['timeout_seconds']==2 for r in diagnosis['isolations'])


def test_isolation_capped_and_no_test_start_is_unresolved(tmp_path):
    frozen,failure,_,_,_=fixture(tmp_path)
    frozen['tests']=['\n'.join('#[test] fn t'+str(i)+'(){}' for i in range(6))]
    record=failure['record'];record.update(status='timeout',returncode=-15)
    Path(record['stdout']).write_text('Compiling crate');Path(record['stderr']).write_text('')
    ex=Mock();ex.run.return_value=record
    diagnosis=resources.diagnose(frozen,record,{'testing':{'process_timeout':30}},ex,lambda name:['cargo','test',name,'--exact','--test-threads=1'])
    assert ex.run.call_count==4 and len(diagnosis['unisolated_test_ids'])==2 and diagnosis['failed_test_ids']==[]
    assert all(c.kwargs['timeout']==5 for c in ex.run.call_args_list)

@pytest.mark.parametrize('action',['accept','inconclusive'])
def test_independent_checker_can_keep_crash_as_candidate_or_unresolved(tmp_path,action):
    from test_translation_workflow import cfg
    from i2r_agent.common import digest
    frozen,failure,material,verdict,_=fixture(tmp_path)
    c=cfg();c['model']['name']='deepseek-flash'
    verdict.pop('resource_assessment');verdict['action']=action
    for row in verdict['tests']:row['verdict']='correct' if action=='accept' else 'uncertain'
    for row in verdict['obligations']:row['verdict']='covered' if action=='accept' else 'uncertain'
    material.update(inventory=full.inventory(frozen),obligations=[{'id':'o:0','claim':frozen['obligations'][0]}])
    def completed(provider,cfg,system,request,path,row,ledger,ledger_path):
        save(path/'verdict.json',verdict)
        row.update(status='completed',verdict_sha256=digest(path/'verdict.json'),provider_receipt={'mock':'offline'})
        return verdict
    original=deepcopy(frozen)
    with patch.object(review,'payload',return_value=material),patch.object(full,'call_record',side_effect=completed),patch.object(revision,'propose',side_effect=AssertionError('No resampling from crash alone')):
        if action=='accept':
            result=review.check(frozen,failure,{'mapping':[]},c,Mock(),tmp_path/'checker')
            assert result['action']=='candidate_repair'
        else:
            with pytest.raises(Failure):review.check(frozen,failure,{'mapping':[]},c,Mock(),tmp_path/'checker')
    assert frozen==original


def test_completed_source_execution_cannot_erase_pending_or_missing_recheck(tmp_path):
    frozen,failure,material,verdict,proposal=fixture(tmp_path)
    updated=revision.apply(frozen,verdict,proposal,{},material,failure)
    save(tmp_path/'support-tests'/(updated['identity']+'.json'),updated)
    state={'support_evidence':{'status':'passed','frozen_identity':updated['identity']},'source_oracle_revision_review':{'suite_identity':updated['identity']}}
    from i2r_agent.source_failure_check import lock
    state['support_pass_candidate']=lock(state)
    # Even an allegedly passed full suite does not discharge independent acceptance.
    with pytest.raises(Failure) as caught:review.require_state(state,{},tmp_path)
    assert 'complete current judgment' in str(caught.value)

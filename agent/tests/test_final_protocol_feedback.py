from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock,patch
import io,json
import pytest
from i2r_agent.common import Failure,save
from i2r_agent import source_suite_review as full,source_failure_review as failure
from i2r_agent.segmented_context import read_pages

@pytest.mark.parametrize('requests',['A.thy',['A.thy'],[{}],[{'path':''}]])
def test_provider_rejects_source_request_shape_with_usable_example(tmp_path,requests):
    from i2r_agent.provider import Provider
    from i2r_agent.common import read
    from test_v8_workflow import cfg
    reply={'request_sources':requests}
    raw={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(reply)}}],'usage':{}}
    with patch('i2r_agent.provider.credential',return_value='test'),patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(raw).encode())):
        provider=Provider(cfg(),tmp_path)
        with pytest.raises(Failure) as caught:provider.call('system','prompt',phase='generation')
    assert caught.value.code=='invalid_source_request'
    assert caught.value.evidence['reply_shape']['request_sources']==[{'path':'EXACT_SOURCE_CATALOG_PATH','start_line':1,'end_line':1}]
    assert provider.calls==1 and read(tmp_path/'001/response.json')==raw

@pytest.mark.parametrize('requests',[[{'path':'A.thy','start_line':1,'end_line':5,'source_version':'exact-version'}],None])
def test_provider_preserves_valid_source_requests_and_optional_null(tmp_path,requests):
    from i2r_agent.provider import Provider
    from test_v8_workflow import cfg
    reply={'request_sources':requests}
    raw={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(reply)}}],'usage':{}}
    with patch('i2r_agent.provider.credential',return_value='test'),patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(raw).encode())):
        provider=Provider(cfg(),tmp_path);result=provider.call('system','prompt',phase='generation')
    assert result==({} if requests is None else reply)
    assert provider.calls==1

MATERIAL={'inventory':[{'id':'a'},{'id':'b'}],'obligations':[{'id':'o:0'}]}
A={'id':'a','verdict':'correct','basis':['e1']};B={'id':'b','verdict':'correct','basis':['e1']};O={'id':'o:0','verdict':'covered','basis':['e1']}
ORIGINAL={'action':'accept','tests':[A,A,B],'obligations':[O],'source_evidence':[{'id':'e1','quote':'source'}]}
FIX={'action':'repair_inventory','tests':[A,B],'obligations':[O]}

def test_identical_duplicates_need_explicit_single_model_correction(tmp_path):
    row={};ledger={'attempts':[row]};provider=Mock()
    with patch.object(full,'call_record',return_value=FIX) as call:
        # Mock the receipt written by the real call_record only, not inventory validation.
        def answer(*args):
            args[5]['provider_receipt']={'test':'offline'};return deepcopy(FIX)
        call.side_effect=answer
        corrected,proof=full.resolve_inventory(deepcopy(ORIGINAL),MATERIAL,{},provider,tmp_path,row,ledger,tmp_path/'ledger.json')
    assert call.call_count==1 and corrected['tests']==[A,B]
    assert ORIGINAL['tests']==[A,A,B] and proof['diagnostic']['tests']['duplicate_ids']==['a']
    with patch.object(full,'call_record') as call,pytest.raises(Failure):full.resolve_inventory(ORIGINAL,MATERIAL,{},provider,tmp_path,row,ledger,tmp_path/'ledger.json')
    call.assert_not_called()

@pytest.mark.parametrize('change',['conflict','missing','extra','change_verdict','change_action','change_citations'])
def test_inventory_correction_cannot_erase_conflicts_or_responsibilities(change):
    original=deepcopy(ORIGINAL);fix=deepcopy(FIX)
    if change=='conflict':original['tests'][1]['verdict']='wrong'
    elif change=='missing':fix['tests'].pop()
    elif change=='extra':fix['tests'].append({'id':'invented'})
    elif change=='change_verdict':fix['tests'][0]['verdict']='wrong'
    elif change=='change_action':fix['action']='accept'
    else:fix['source_evidence']=[]
    with pytest.raises(Failure):full.preserve_inventory_judgments(original,fix,MATERIAL)

def test_missing_row_requires_explicit_completion_and_full_validator_still_runs():
    original={**ORIGINAL,'tests':[A]}
    assert full.inventory_protocol(original,MATERIAL)['tests']['missing_ids']==['b']
    corrected=full.preserve_inventory_judgments(original,FIX,MATERIAL)
    assert corrected['tests']==[A,B] and corrected['action']==original['action']

@pytest.mark.parametrize('shape',['page',{'page':'x'},[{'id':'x'}],[None],[1]])
def test_malformed_page_requests_are_not_normalized(shape):
    with pytest.raises(Failure) as caught:read_pages({'x':{'id':'x','text':'source'}},shape,100)
    assert caught.value.code=='invalid_page_request'
    assert caught.value.evidence['available_page_ids']==['x']


def refresh_fixture(tmp_path):
    frozen={'identity':'suite','tests':[]};origin=tmp_path/'source-failure-check/judgment-001';origin.mkdir(parents=True)
    save(origin/'verdict.json',{'action':'accept'});save(origin/'input.json',{'version':'old'});save(origin/'original-suite.json',frozen);save(origin/'validated-verdict.json',{'action':'accept'})
    from i2r_agent.common import digest
    record={'status':'test_correct','scope':'old','evidence':str(origin),'verdict_sha256':digest(origin/'validated-verdict.json'),'provider_receipt':{},'failed_test_ids':['t']}
    save(tmp_path/'source-failure-check/ledger.json',{'policy':failure.POLICY,'attempts':[{'status':'completed','action':'accept','scope':'old','resolved_verdict_sha256':record['verdict_sha256'],'directory':str(origin),'provider_receipt':{},'verdict_sha256':digest(origin/'verdict.json')}]})
    save(tmp_path/'support-tests/suite.json',frozen)
    save(tmp_path/'source-failure-check/failures/1.json',{'failure':{'status':'support_contract_failed','diagnostic':'original'}})
    state={'support_evidence':{'status':'passed','frozen_identity':'suite'},'support_pass_candidate':'locked','support_review_evidence':{'source_check':record},'phase':'finish','differential_suites':[{'status':'passed'}],'behavior_version':'old'}
    return state,origin

def refresh_patches():
    from contextlib import ExitStack
    stack=ExitStack()
    stack.enter_context(patch.object(failure,'lock',return_value='locked'))
    stack.enter_context(patch.object(failure,'payload',return_value={'version':'new'}))
    stack.enter_context(patch.object(failure,'key_for',side_effect=lambda material,cfg:material['version']))
    stack.enter_context(patch.object(failure,'failed_ids',return_value=['t']))
    stack.enter_context(patch.object(full,'verify_receipt'))
    return stack

def test_scope_refresh_requires_new_acceptance_and_reexecutes_source_and_D(tmp_path):
    state,origin=refresh_fixture(tmp_path);previous=deepcopy(state['support_review_evidence'])
    with refresh_patches(),patch.object(failure,'check',return_value={'action':'accept_revision','source_check':{'scope':'new','status':'test_correct'}}) as check:
        assert failure.refresh_changed_revision(state,{},Mock(),tmp_path)
        assert state['phase']=='support_execute' and state['differential_suites']==[] and 'behavior_version' not in state
        assert state['support_pass_candidate']=='locked' and state['source_scope_refreshes'][0]['previous_acceptance']==previous
        assert not failure.refresh_changed_revision(state,{},Mock(),tmp_path)
        assert check.call_count==1

@pytest.mark.parametrize('fault',['lock','tamper','repeat','not_accepted'])
def test_scope_refresh_fail_closed_controls(tmp_path,fault):
    state,origin=refresh_fixture(tmp_path)
    if fault=='lock':state['support_pass_candidate']='changed'
    elif fault=='tamper':save(origin/'validated-verdict.json',{'action':'test_wrong'})
    elif fault=='repeat':state['source_scope_refreshes']=[{'from':'older','to':'old'}]
    with refresh_patches(),patch.object(failure,'check',return_value={'action':'binding_fix'}) as check:
        if fault=='lock':assert not failure.refresh_changed_revision(state,{},Mock(),tmp_path)
        else:
            with pytest.raises(Failure):failure.refresh_changed_revision(state,{},Mock(),tmp_path)
        assert state['phase']=='finish' and state['differential_suites']==[{'status':'passed'}]
        assert check.call_count==(1 if fault=='not_accepted' else 0)

@pytest.mark.parametrize('action',['accept','needs_revision','inconclusive','unresolved'])
def test_complete_or_terminal_inventory_does_not_add_calls(tmp_path,action):
    proposal={**ORIGINAL,'action':action,'tests':[A,B]}
    with patch.object(full,'call_record') as call:
        actual,proof=full.resolve_inventory(proposal,MATERIAL,{},Mock(),tmp_path,{}, {},tmp_path/'ledger.json')
    assert actual==proposal and proof is None;call.assert_not_called()


def test_refresh_rejects_unbound_old_ledger(tmp_path):
    state,origin=refresh_fixture(tmp_path)
    save(tmp_path/'source-failure-check/ledger.json',{'policy':failure.POLICY,'attempts':[]})
    with refresh_patches(),patch.object(failure,'check') as check,pytest.raises(Failure):failure.refresh_changed_revision(state,{},Mock(),tmp_path)
    check.assert_not_called();assert state['phase']=='finish'


def test_scope_refresh_cannot_bypass_total_provider_budget(tmp_path):
    from test_v8_workflow import cfg
    from i2r_agent.provider import Provider
    state,origin=refresh_fixture(tmp_path);c=cfg();c['budgets']['max_model_calls']=48
    provider=Provider(c,tmp_path/'model');provider.calls=48
    def checked(*args,**kwargs):return provider.call('offline','offline',phase='source_test_check')
    with refresh_patches(),patch.object(failure,'check',side_effect=checked),patch('urllib.request.urlopen') as network,pytest.raises(Failure) as caught:
        failure.refresh_changed_revision(state,c,provider,tmp_path)
    assert caught.value.code=='budget_exhausted' and provider.calls==48
    network.assert_not_called();assert state['phase']=='finish' and state['differential_suites']==[{'status':'passed'}]

@pytest.mark.parametrize('requests', [['A.thy'],{'path':'A.thy'},[{'path':1}],[{}]])
def test_source_request_shape_feedback_is_explicit_and_non_normalizing(requests):
    from i2r_agent.task_context import validate_source_requests
    with pytest.raises(Failure) as caught:validate_source_requests({'request_sources':requests})
    assert caught.value.code=='invalid_source_request'
    assert caught.value.evidence['reply_shape']['request_sources'][0]=={'path':'EXACT_SOURCE_CATALOG_PATH','start_line':1,'end_line':1}
    validate_source_requests({'request_sources':[{'path':'A.thy','start_line':1,'end_line':5}]})


def test_conflicting_checklist_duplicate_does_not_spend_another_call(tmp_path):
    proposal=deepcopy(ORIGINAL);proposal['tests'][1]={**proposal['tests'][1],'reason':'different semantic justification'}
    with patch.object(full,'call_record') as call,pytest.raises(Failure):full.resolve_inventory(proposal,MATERIAL,{},Mock(),tmp_path,{}, {},tmp_path/'ledger.json')
    call.assert_not_called()

@pytest.mark.parametrize('fault',[None,'unaccepted','wrong_scope','wrong_suite','candidate_changed','audit_phase'])
def test_locked_source_reexecution_is_narrowly_authorized(fault):
    from i2r_agent import test_order_policy as policy
    from i2r_agent.source_failure_check import lock
    state={'files':{'src/lib.rs':'fn f(){}'},'test_order_policy':policy.A,'source_scope_refreshes':[{'status':'accepted','to':'new'}],
           'support_review_evidence':{'source_check':{'scope':'new'}},'support_pending_identity':'suite','support_evidence':{'frozen_identity':'suite'}}
    state['source_candidate_lock']=lock(state);phase='support_execute'
    if fault=='unaccepted':state['source_scope_refreshes'][0]['status']='reserved'
    elif fault=='wrong_scope':state['support_review_evidence']['source_check']['scope']='old'
    elif fault=='wrong_suite':state['support_pending_identity']='different'
    elif fault=='candidate_changed':state['files']['src/lib.rs']='fn changed(){}'
    elif fault=='audit_phase':phase='support_audit'
    if fault:
        with pytest.raises(Failure):policy.guard_phase(state,phase)
    else:policy.guard_phase(state,phase)

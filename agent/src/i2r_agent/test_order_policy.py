"""Explicit diagnostic/acceptance policies; the default is source-first after explicit v18 authorization."""
from .common import Failure
from .source_failure_check import lock,enforce_lock
A='source_repair_then_diff_accept'
B='diff_repair_then_source_accept'
def configure(state,cfg):
    policy=cfg.get('v8',{}).get('test_order_policy',A)
    if policy not in {A,B}:raise Failure('invalid_workflow_policy',policy)
    if state.get('test_order_policy',policy)!=policy:raise Failure('stale_snapshot','Test-order policy changed')
    state['test_order_policy']=policy
    return policy
def source_first(state):return state.get('test_order_policy')==A
def enter_source(state):
    if not source_first(state):state.setdefault('source_candidate_lock',lock(state))
    enforce_lock(state)
def transition(state,testing_project):
    if source_first(state):
        if state.get('support_evidence',{}).get('status')!='passed' or state.get('support_pass_candidate')!=lock(state):
            state['phase']='support';return
        if state.get('source_suite_review_required') and (state.get('support_review_evidence',{}).get('status')!='accepted' or state.get('support_evidence',{}).get('source_test_check',{}).get('scope')!=state.get('support_review_evidence',{}).get('scope')):
            raise Failure('source_suite_review_unresolved','A cannot lock a candidate without full-suite independent checking and execution')
        if not testing_project:raise Failure('source_check_unresolved','A requires differential acceptance')
        state.setdefault('source_candidate_lock',lock(state));enforce_lock(state)
        state['phase']='test' if state['connector'] and state.get('connector_identity')==__import__('i2r_agent.segmented_v8',fromlist=['connector_identity']).connector_identity(state) else 'connect'
    elif state.get('source_candidate_lock'):state['phase']='finish'
    elif not testing_project:state['phase']='support'
    else:state['phase']='test' if state['connector'] and state.get('connector_identity')==__import__('i2r_agent.segmented_v8',fromlist=['connector_identity']).connector_identity(state) else 'connect'
def guard_phase(state,phase):
    enforce_lock(state)
    allowed={'support','source_test_check','support_execute','support_audit','support_check','finish'}
    if source_first(state):allowed={'connect','test','repair','repair_replay','repair_diagnose','finish'}
    refresh=state.get('source_scope_refreshes',[])
    if (phase=='support_execute' and len(refresh)==1 and refresh[0].get('status')=='accepted' and
        state.get('support_review_evidence',{}).get('source_check',{}).get('scope')==refresh[0].get('to') and
        state.get('support_pending_identity')==state.get('support_evidence',{}).get('frozen_identity')):
        allowed.add('support_execute') # Reexecute the same suite on the still-locked candidate; no edits.
    if state.get('source_candidate_lock') and phase not in allowed:raise Failure('source_candidate_locked','Candidate repair/replay escape after acceptance lock',phase)
def guard_edit(state):
    enforce_lock(state)
    if state.get('source_candidate_lock'):raise Failure('source_candidate_locked','Acceptance candidate is immutable; only connector repair is allowed')

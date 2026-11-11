"""Issue-specific repair evidence. Protocol failures never replace the defect."""
from copy import deepcopy
import re
from .task_context import fingerprint

PROTOCOL_ERRORS={'invalid_candidate_path','invalid_adapter_path','invalid_adapter','invalid_mapping_field','backend_symbol_not_source','missing_patch_version','stale_patch','invalid_edit','invalid_candidate','invalid_decisions',
 'unknown_edit_file','edit_text_mismatch','read_only_edit','repair_protocol_stalled',
 'invalid_model_response','incomplete_response','unchanged_repair','unchanged_connector','repeated_adapter',
 'unresolved_issue','plan_contract_failed','adapter_not_installed','invalid_dependencies','missing_verification','adapter_already_loaded','invalid_adapter_patch','invalid_source_range','unknown_material','unknown_source_symbol',
 'invalid_material_type','unknown_code_file','unknown_source_path','unknown_reference','stale_source_version','invalid_connector','binding_sync_required','invalid_analysis','incomplete_quality_review'}


def compact_feedback(value):
    """Remove execution bookkeeping, not diagnostics, inputs or expected outputs."""
    if isinstance(value,list):return [compact_feedback(x) for x in value]
    if not isinstance(value,dict):return value
    omitted={'compilation','references','candidate','record','original_record','execution','attempted_adapter'}
    return {k:compact_feedback(v) for k,v in value.items() if k not in omitted}


def capture(branch):
    feedback=branch.get('connector_feedback') if branch.get('mode')=='connect' else branch.get('feedback')
    if not feedback:return
    status=feedback.get('status','')
    contract=status=='plan_contract_failed' and branch.get('bundle',{}).get('workflow')=='source-v6'
    if status in PROTOCOL_ERRORS and not contract:return
    kind=('contract' if contract else 'support' if status=='support_contract_failed' else 'declaration' if status.startswith('adapter') else
          'behavior' if feedback.get('behavior_failure') else 'compile' if status=='compile_failed' else 'review')
    # Routing a previously diagnosed issue is not a new independent defect.
    if feedback.get('algorithm_issue') or feedback.get('diagnosis') and branch.get('repair_issue'):return
    issue=branch.get('repair_issue')
    if issue and issue['kind']==kind:
        issue['latest_evidence']=deepcopy(feedback)
        return
    if issue:
        branch.setdefault('suspended_issues',[]).append(issue)
    branch['repair_issue']={'id':'issue-'+fingerprint(feedback)[:12],'kind':kind,'evidence':deepcopy(feedback),
        'opened_code':fingerprint(branch['files']),'opened_connector':fingerprint(branch.get('connector',{})),'status':'open'}


def feedback(branch):
    current=branch.get('feedback')
    issue=branch.get('repair_issue')
    if not issue:return compact_feedback(current)
    base=compact_feedback(issue.get('latest_evidence',issue['evidence']))
    if current and current!=issue.get('latest_evidence',issue['evidence']):base['last_action_error']=compact_feedback(current)
    base['issue_id']=issue['id']
    base['completion_requirement']={'declaration':'Changed declarations must load successfully.',
        'contract':'Current realizations must pass original source/export coverage, including generic interfaces.',
        'compile':'The modified library must compile; behavior checks still follow.',
        'behavior':'Reproduce the original failing input and pass development suites on the current version.',
        'support':'Source-grounded tests for the reported support operation must exist and pass on current files.',
        'review':'Resolve the reported source/code finding; unchanged unrelated tests do not resolve it.'}[issue['kind']]
    return base


def verified(branch,kind,version):
    issue=branch.get('repair_issue')
    if not issue or issue['kind']!=kind:return
    issue.update(status='verified',verified_version=version)
    branch.setdefault('closed_issues',[]).append(issue)
    branch['repair_issue']=branch.get('suspended_issues',[]).pop() if branch.get('suspended_issues') else None


def ensure_acceptible(branch):
    from .common import Failure
    if branch.get('repair_issue'):
        raise Failure('unresolved_issue','A successful unrelated check does not close the original issue.',feedback(branch))


def reproducer_inputs(branch):
    """Original failing inputs survive newer diagnostics and routing changes."""
    result=[]
    for issue in [branch.get('repair_issue'),*branch.get('suspended_issues',[])]:
        if not issue or issue['kind']!='behavior':continue
        for evidence in [issue['evidence'],issue.get('latest_evidence',{})]:
            for suite in evidence.get('behavior_failure',{}).get('suites',[]):
                examples=suite.get('counterexamples',[])+suite.get('range_event',{}).get('reproductions',[])
                for example in examples:
                    values=example.get('input')
                    if isinstance(values,list) and values not in result:result.append(values)
    return result


def executable_text(files):
    # Conservative comment-only/no-op signal, not a Rust parser or equivalence test.
    return fingerprint({n:re.sub(r'(?m)^\s*//[^\n]*','',s).strip() for n,s in files.items()})


def adapter_snapshot(branch):
    adapter=(branch.get('pending_adapter') or {}).get('adapter') or branch['plan']['adapter']
    return {'declarations.thy':adapter.get('declarations',''),'support-root.rs':adapter.get('rust_root',''),
            **adapter.get('rust_files',{})}


def adapter_reply(branch,reply):
    from .common import Failure
    if not reply.get('adapter_edits'):return reply
    files=adapter_snapshot(branch)
    if reply.get('base_adapter_version') not in {fingerprint(files),'code-'+fingerprint(files)}:
        raise Failure('stale_patch','Adapter edit must name the current base_adapter_version')
    new=deepcopy(files)
    for edit in reply['adapter_edits']:
        name,old,replacement=edit.get('file'),edit.get('old'),edit.get('new')
        if name not in new or not old or not isinstance(replacement,str) or new[name].count(old)!=1:
            raise Failure('invalid_adapter_patch','Use one exact current text match in an adapter file',edit)
        new[name]=new[name].replace(old,replacement,1)
    previous=deepcopy(branch.get('pending_adapter') or {'adapter':branch['plan']['adapter'],
        'dependencies':branch['plan'].get('dependencies',{}),'build_dependencies':branch['plan'].get('build_dependencies',{})})
    previous.update({k:v for k,v in reply.items() if k not in {'adapter_edits','base_adapter_version'}})
    previous['adapter'].update(declarations=new.pop('declarations.thy'),rust_root=new.pop('support-root.rs'),rust_files=new)
    return previous


def review_resolution(branch,reply):
    from .common import Failure
    issue=branch.get('repair_issue')
    if not issue or issue['kind']!='review':return
    changed=(fingerprint(branch['files'])!=issue['opened_code'] or
             fingerprint(branch.get('connector',{}))!=issue.get('opened_connector'))
    resolution=reply.get('issue_resolution',{})
    if not changed or resolution.get('issue_id')!=issue['id'] or not resolution.get('source_basis'):
        raise Failure('unresolved_issue','Resolve the original review finding with an actual change and issue_resolution {issue_id,source_basis}.',feedback(branch))
    verified(branch,'review',fingerprint({'files':branch['files'],'connector':branch.get('connector')}))

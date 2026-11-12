"""Migrate binding reproducers by accepted parentage; close only on bound execution."""
from copy import deepcopy
from pathlib import Path
import re
from .common import Failure,read,digest
from .task_context import fingerprint


def binding(state,frozen):
    from .segmented_v8 import version
    return {'candidate':version(state),
            'source':fingerprint({k:state['bundle'].get(k) for k in ['source_model','original_source_model','numeric_policy','source_hashes']}),
            'suite':fingerprint({k:frozen.get(k) for k in ['identity','tests','unit_tests','obligations','author_group_plan']})}


def migrate(state,frozen,updated,audit):
    """No closure here. Replay the already accepted binding edit, then move all matching occurrences."""
    from .segmented_test_audit import revise,exhaustiveness_revision,macro_separator_revision
    path=Path(audit);method=updated.get('binding_audit',{}).get('method')
    if method in {'source-pattern-check-v1','source-resource-check-v1'}:
        from .source_pattern_revision import apply as pattern_revision,verify_repair_receipt
        if method=='source-resource-check-v1':
            from .source_resource_revision import apply as pattern_revision
        diagnosis=read(path/'diagnosis.json');patch_path=Path(diagnosis.get('patch_path',''))
        verify_repair_receipt(diagnosis.get('patch_provider_receipt'))
        record=read(patch_path/'record.json')
        if record.get('status')!='completed' or read(patch_path/'proposal.json')!=diagnosis.get('model_patch') or digest(patch_path/'proposal.json')!=record.get('proposal_sha256'):
            raise Failure('support_lineage_invalid','Pattern repair lacks its exact completed model proposal')
        verified=pattern_revision(frozen,read(path/'validated-verdict.json'),diagnosis['model_patch'],state,read(path/'input.json'),state.get('support_evidence',{}))
    elif method=='source-expectation-check-v1':
        if (path/'validated-verdict.json').is_file() and (path/'input.json').is_file():
            # Modern checker: replay the complete canonical validated judgment,
            # including exact page citations and protected obligation metadata.
            from .source_suite_review import revise as revise_suite
            verified=revise_suite(frozen,read(path/'validated-verdict.json'),state,read(path/'input.json'))
        else:
            from .source_failure_check import revise as revise_expectation
            verified=revise_expectation(frozen,read(path/'diagnosis.json'),state)
    elif method in {'compiler-span-exhaustiveness-v1','compiler-span-exhaustiveness-v2'}:verified=exhaustiveness_revision(frozen,state.get('support_evidence',{}),state)
    elif method=='compiler-span-final-macro-separator-v1':verified=macro_separator_revision(frozen,state.get('support_evidence',{}),state)
    elif (path/'diagnosis.json').is_file():
        proposal=read(path/'diagnosis.json')
        if proposal.get('action')!='binding_fix':raise Failure('support_lineage_invalid','No accepted binding proposal')
        verified=revise(frozen,proposal,state,compiler_failure=state.get('support_evidence',{}))
    else:raise Failure('support_lineage_invalid','Missing accepted binding evidence')
    keys=['identity','parent_identity','oracle_identity','tests','unit_tests','obligations','author_group_plan']
    if verified is None or any(verified.get(k)!=updated.get(k) for k in keys) or updated.get('parent_identity')!=frozen['identity']:
        raise Failure('support_lineage_invalid','Binding child differs from mechanically replayed edit')
    associated=[f for f in state.get('failures',[]) if f.get('kind')=='support' and f.get('status')=='open' and f.get('frozen_identity')==frozen['identity']]
    for issue in state.get('repair_issues',[]):
        if issue.get('kind')!='support' or issue.get('status')!='open' or issue.get('reproducer',{}).get('frozen_identity')!=frozen['identity']:continue
        links=[f for f in associated if f.get('repair_issue')==issue['id'] and f.get('evidence') in issue.get('failure_evidence',[])]
        if not links:continue # Never migrate an unrelated/older occurrence merely by shared test name.
        issue.setdefault('original_reproducer',deepcopy(issue['reproducer']))
        issue.setdefault('binding_revisions',[]).append(updated['identity'])
        issue.setdefault('binding_lineage',[]).append({'from':frozen['identity'],'to':updated['identity'],'audit':str(path),'execution_binding_at_revision':binding(state,updated),'failure_evidence':[f['evidence'] for f in links]})
        issue['reproducer']['frozen_identity']=updated['identity']


def execution_proof(state,frozen,result):
    """Called directly after execute(), before any further model/candidate action."""
    result['execution_binding']=binding(state,frozen)
    record=result.get('record',{});compiled=result.get('compilation',{})
    result['execution_artifacts']={str(Path(record[k])):digest(record[k]) for k in ['stdout','stderr'] if record.get(k) and Path(record[k]).is_file()}
    return result


def close(state,frozen,result,evidence_path):
    from .segmented_support import required_test_bindings,passed_test_names
    from .segmented_contract import items
    if result.get('status')!='passed' or result.get('execution_binding')!=binding(state,frozen):return []
    if result.get('frozen_identity')!=frozen['identity'] or result.get('missing_required_tests')!=[] or result.get('obligations')!=frozen['obligations'] or result.get('immutable_test_sources')!=frozen['tests'] or result.get('immutable_unit_tests')!=frozen.get('unit_tests',[]):return []
    record=result.get('record',{});compiled=result.get('compilation',{})
    if any(r.get('status')!='passed' or r.get('returncode')!=0 for r in [record,compiled]) or '--format=pretty' not in record.get('command',[]):return []
    paths=[record.get('stdout'),record.get('stderr')]
    if any(not p or not Path(p).is_file() or result.get('execution_artifacts',{}).get(str(Path(p)))!=digest(p) for p in paths):return []
    executed=passed_test_names(''.join(Path(p).read_text() for p in paths));bindings=required_test_bindings(frozen)
    if not bindings or any(len(names)!=1 or names[0] not in executed for names in bindings.values()):return []
    inventory=set()
    groups=[(code,[f'__i2r_source_contract_{i}']) for i,code in enumerate(frozen['tests'])]
    groups += [(row['source'],row.get('module',[])+[f'__i2r_contract_{i}']) for i,row in enumerate(frozen.get('unit_tests',[]))]
    for code,prefix in groups:
        for rows in items({'src/lib.rs':code}).values():
            for row in rows:
                if row['kind']=='function_item' and any(re.fullmatch(r'#\s*\[\s*test\s*\]',a) for a in row.get('attributes',[])):inventory.add('::'.join(prefix+row['module_scope']+[row['name']]))
    if not inventory or not inventory<=executed or result.get('tests_passed',0)<len(inventory):return []
    closed=[]
    for issue in state.get('repair_issues',[]):
        if issue.get('kind')!='support' or issue.get('status')!='open' or issue.get('reproducer',{}).get('frozen_identity')!=frozen['identity']:continue
        links=[f for f in state.get('failures',[]) if f.get('kind')=='support' and f.get('frozen_identity')==frozen['identity'] and f.get('repair_issue')==issue['id'] and f.get('evidence') in issue.get('failure_evidence',[])]
        if not links:continue
        issue['status']='verified_passed';issue['latest']=deepcopy(result)
        issue['verified_execution']={'candidate_source_suite':result['execution_binding'],'artifacts':result['execution_artifacts'],'evidence':str(evidence_path),'executed_tests':sorted(inventory)}
        closed.append(issue['id'])
    return closed

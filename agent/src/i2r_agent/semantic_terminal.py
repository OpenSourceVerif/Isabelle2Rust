"""Evidence-bound terminal rejection of a locked candidate; never permission to edit it."""
from copy import deepcopy
from pathlib import Path
import re
from .common import Failure,read,digest
from .source_failure_check import lock,enforce_lock
from .test_order_policy import source_first
from .v8_repair import active
from .rust_index import build

STATUS='candidate_semantic_rejected'

def needs_user_failure(state,reply,current_version):
    fallback=Failure('needs_user',reply.get('reason','Implementation requires a changed boundary'))
    enforce_lock(state)
    diagnosis=reply.get('diagnosis')
    if not isinstance(diagnosis,dict):return fallback
    # The explicit kind is preferred. The original structured diagnostic shape
    # also supplies a typed candidate-vs-connector distinction, without reading
    # keywords from reason or from unstructured model prose.
    if diagnosis.get('kind','candidate_semantic')!='candidate_semantic':return fallback
    required=['active_issue','failed_path','executed_evidence']
    lists=['source_equations_used','candidate_locations','why_connector_is_not_at_fault']
    if any(not isinstance(diagnosis.get(k),str) or not diagnosis[k].strip() for k in required):return fallback
    if any(not isinstance(diagnosis.get(k),list) or not diagnosis[k] for k in lists):return fallback
    if any(not isinstance(v,str) or not v.strip() for k in ['source_equations_used','why_connector_is_not_at_fault'] for v in diagnosis[k]):return fallback
    if not source_first(state) or state.get('source_candidate_lock')!=lock(state):return fallback
    if state.get('support_pass_candidate')!=lock(state) or state.get('support_evidence',{}).get('status')!='passed':return fallback
    issue=active(state)
    if not issue or issue.get('kind')!='behavior' or diagnosis['active_issue']!=issue['id']:return fallback
    latest=issue.get('latest',{})
    if latest.get('status')!='mismatch' or latest not in state.get('differential_suites',[]):return fallback
    if latest.get('candidate',{}).get('status')!='passed' or latest.get('candidate',{}).get('returncode')!=0:return fallback
    if not latest.get('reference_coverage',{}).get('complete'):return fallback
    if not any(c.get('actual') is not None and c.get('expected') is not None and c['actual']!=c['expected'] and not c.get('property_error') for c in latest.get('counterexamples',[])):return fallback
    entries=state.get('bundle',{}).get('source_model',{}).get('entries',[])
    cited=set(re.findall(r'constant:[A-Za-z0-9_\.]+',diagnosis['failed_path']))
    if not cited.intersection(entries):return fallback
    index=build(state['files']);locations=[]
    if index['parse_error_files']:return fallback
    for location in diagnosis['candidate_locations']:
        if isinstance(location,dict):file,symbol=location.get('file'),location.get('symbol')
        elif isinstance(location,str):
            match=re.match(r'^(crate::[A-Za-z0-9_:]+) \(([^,()]+\.rs)(?:, [^)]*)?\)$',location)
            if not match:return fallback
            symbol,file=match.groups()
        else:return fallback
        found=[item for item in index['items'] if item['file']==file and item['path_addressable'] and 'crate::'+'::'.join(item['scope']+[item['name']])==symbol]
        if len(found)!=1:return fallback
        item=found[0];locations.append({k:item[k] for k in ['file','start_line','end_line','name','kind']})
    failure=next((f for f in reversed(state.get('failures',[])) if f.get('kind')=='behavior' and f.get('status')=='open' and f.get('repair_issue')==issue['id'] and f.get('version')==current_version and f.get('failure')==latest and f.get('evidence') in issue.get('failure_evidence',[])),None)
    if not failure:return fallback
    path=Path(failure['evidence'])
    if not path.is_file():return fallback
    try:attempt=read(path)
    except (ValueError,OSError):return fallback
    if attempt.get('action_phase')!='test' or attempt.get('state_version')!=current_version or attempt.get('after_version')!=current_version:return fallback
    if attempt.get('compilation',{}).get('status')!='passed' or attempt.get('development',{}).get('suites')!=state.get('differential_suites'):return fallback
    evidence={'kind':'locked_candidate_semantic_rejection_v1','candidate_lock':lock(state),'state_version':current_version,
              'active_issue':issue['id'],'diagnosis':deepcopy(diagnosis),'candidate_locations':locations,
              'source_entries':entries,'executed_attempt':str(path),'executed_attempt_sha256':digest(path),
              'differential_suites':deepcopy(state['differential_suites']),'repair_issue':deepcopy(issue),
              'source_test_status':state['support_evidence']['status'],'terminal_reply':deepcopy(reply),
              'candidate_edits_authorized':False,'retry_authorized':False}
    return Failure(STATUS,reply.get('reason','Executed differential rejected the locked candidate'),evidence)

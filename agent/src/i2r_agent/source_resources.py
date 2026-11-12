"""Bound resource-failure diagnostics to executed, inventoried tests; never an oracle."""
from pathlib import Path
import re
from .common import Failure,digest
from .task_context import fingerprint

MAX_ISOLATIONS=4
ISOLATION_SECONDS=5


def text(record):
    return ''.join(Path(record[k]).read_text() for k in ['stdout','stderr'])


def kind(record,output):
    if record.get('status') in {'timeout','timed_out'}:return 'timeout'
    aborted=record.get('returncode')==-6 or re.search(r'signal: 6, SIGABRT',output)
    if aborted and 'has overflowed its stack' in output and 'stack overflow, aborting' in output:return 'stack_overflow'
    if aborted:return 'abort'
    return None


def snapshot(record):
    return {'record':record,'artifacts':{record[k]:digest(record[k]) for k in ['stdout','stderr']}}


def verify(receipt):
    record=receipt.get('record',{})
    if any(not record.get(k) or not Path(record[k]).is_file() for k in ['stdout','stderr']):
        raise Failure('source_check_unresolved','Resource execution log is missing')
    if any(receipt.get('artifacts',{}).get(record.get(k))!=digest(record[k]) for k in ['stdout','stderr']):
        raise Failure('source_check_unresolved','Resource execution log changed')
    return record,text(record)


def thread_ids(output,known):
    names=re.findall(r"^thread '([^'\n]+)'(?: \(\d+\))? has overflowed its stack$",output,re.M)
    return names if names and len(names)==len(set(names)) and set(names)<=known else []


def diagnose(frozen,record,cfg,executor,command):
    """Run at most four short exact-test diagnostics, with the frozen crate intact.
    These runs consume the enclosing task's existing active-time budget. Passing
    isolation runs never replace the original failed full-suite execution.
    """
    from .source_suite_review import inventory
    from .segmented_support import passed_test_names
    output=text(record);cause=kind(record,output)
    if not cause:return None
    known={r['id'] for r in inventory(frozen)}
    result={'kind':cause,'original':snapshot(record),'isolations':[],'failed_test_ids':[],
            'suite_identity':frozen['identity'],'not_semantic_judgment':True}
    names=thread_ids(output,known) if cause=='stack_overflow' else []
    if names:result.update(method='runtime_thread',failed_test_ids=sorted(names));return result
    remaining=sorted(known-passed_test_names(output))
    for name in remaining[:MAX_ISOLATIONS]:
        isolated=executor.run(command(name),timeout=min(ISOLATION_SECONDS,cfg['testing']['process_timeout']),check=False)
        receipt={**snapshot(isolated),'test_id':name};result['isolations'].append(receipt)
        out=text(isolated)
        if kind(isolated,out) and re.search(r'^test '+re.escape(name)+r'(?: - should panic)? \.\.\.',out,re.M):
            result['failed_test_ids'].append(name)
    result.update(method='exact_isolation',isolation_limit=MAX_ISOLATIONS,isolation_seconds=ISOLATION_SECONDS,
                  unisolated_test_ids=remaining[MAX_ISOLATIONS:])
    return result


def bound(frozen,result):
    """Recheck stored receipts; old real stack-overflow archives need no rerun."""
    from .source_suite_review import inventory
    if result.get('status')!='support_contract_failed' or result.get('compilation',{}).get('status')!='passed':return None
    known={r['id'] for r in inventory(frozen)}
    diagnosis=result.get('resource_diagnostic')
    if diagnosis:
        record,output=verify(diagnosis['original'])
        if record!=result.get('record') or diagnosis.get('suite_identity')!=result.get('frozen_identity'):raise Failure('source_check_unresolved','Resource receipt/suite differs')
    else:
        record=result.get('record',{})
        if not all(record.get(k) for k in ['stdout','stderr']):return None
        artifacts=result.get('execution_artifacts',{})
        if not artifacts:return None
        record,output=verify({'record':record,'artifacts':artifacts})
    cause=kind(record,output)
    if not cause:return None
    names=thread_ids(output,known) if cause=='stack_overflow' else []
    if not names and diagnosis:
        isolations=diagnosis.get('isolations',[])
        if len(isolations)>MAX_ISOLATIONS:raise Failure('source_check_unresolved','Isolation budget exceeded')
        for receipt in isolations:
            rec,out=verify(receipt);name=receipt.get('test_id');cmd=rec.get('command',[])
            if name not in known or '--exact' not in cmd or name not in cmd or '--test-threads=1' not in cmd or rec.get('timeout_seconds',ISOLATION_SECONDS)>ISOLATION_SECONDS:
                raise Failure('source_check_unresolved','Isolation lacks exact inventory/command/time binding')
            if kind(rec,out) and re.search(r'^test '+re.escape(name)+r'(?: - should panic)? \.\.\.',out,re.M):names.append(name)
    if len(names)!=len(set(names)):raise Failure('source_check_unresolved','Ambiguous repeated resource test identity')
    return {'kind':cause,'failed_test_ids':sorted(names),'origin_suite':result.get('frozen_identity'),
            'execution_identity':fingerprint(diagnosis or {'record':record,'artifacts':result.get('execution_artifacts')}),
            'scope_bound':bool(names),'not_semantic_judgment':True}

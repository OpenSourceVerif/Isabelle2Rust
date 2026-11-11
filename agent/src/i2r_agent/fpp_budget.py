"""External cross-process reservation before every model request; immutable provider core."""
import fcntl,hashlib,json,os,time
from pathlib import Path


def atomic_save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+str(os.getpid())+'.tmp')
    with temporary.open('w') as stream:
        json.dump(value,stream,sort_keys=True,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)


def initialize(run,release):
    run=Path(run).resolve();run.mkdir(parents=True,exist_ok=True)
    with (run/'global-provider-budget.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        path=run/'global-provider-budget.json'
        expected={'release_identity':release['identity'],'prior_attempts':0,
                  'limit':release['global_limit'],'new_study_limit':release['global_limit'],
                  'per_case_limit':release['per_task_calls'],'allowed_cases':release['evaluation_order']}
        if path.exists():
            data=json.loads(path.read_text())
            if any(data.get(k)!=v for k,v in expected.items()):raise ValueError('Global provider budget identity mismatch')
        else:atomic_save(path,{**expected,'reservations':[]})


def install(provider_module,run,release):
    run=Path(run).resolve();initialize(run,release);original=provider_module.save
    def reserved_save(path,payload):
        path=Path(path).resolve()
        if path.name!='request.json':return original(path,payload)
        if payload.get('model')!='deepseek-flash':raise provider_module.Failure('model_policy_mismatch','All actual requests must use deepseek-flash')
        try:parts=path.relative_to(run/'tasks').parts
        except ValueError:raise provider_module.Failure('global_budget_identity_mismatch','Request lies outside this release task tree')
        if len(parts)!=5 or parts[1:3]!=('diagnostics','model') or not parts[3].isdigit():
            raise provider_module.Failure('global_budget_identity_mismatch','Unexpected provider archive path')
        case=parts[0]
        with (run/'global-provider-budget.lock').open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            ledger_path=run/'global-provider-budget.json';data=json.loads(ledger_path.read_text())
            if data['release_identity']!=release['identity'] or case not in data['allowed_cases']:
                raise provider_module.Failure('global_budget_identity_mismatch','Wrong release or case')
            records=data['reservations']
            if any(r['request']==str(path) for r in records) or path.exists():
                raise provider_module.Failure('global_budget_identity_mismatch','A request archive cannot be overwritten or reserved twice')
            if len(records)>=data['new_study_limit'] or data['prior_attempts']+len(records)>=data['limit']:
                raise provider_module.Failure('budget_exhausted','Global attempted-call budget exhausted before request/network')
            if sum(r['case']==case for r in records)>=data['per_case_limit']:
                raise provider_module.Failure('budget_exhausted','Fresh-task attempted-call budget exhausted before request/network')
            row={'external_execution_identity':release.get('execution_identity'),'case':case,'request':str(path),'local_call':int(parts[3]),'pid':os.getpid(),'reserved_at':time.time(),
                 'payload_sha256':hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                 'state':'reserved_before_request_write'}
            records.append(row);atomic_save(ledger_path,data)
            # A crash after reservation never releases the slot automatically.
            # This is conservative, and prevents unrecorded network retries.
            original(path,payload)
            row['state']='request_persisted';atomic_save(ledger_path,data)
    provider_module.save=reserved_save
    return original

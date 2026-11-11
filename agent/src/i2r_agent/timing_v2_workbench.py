"""Atomically published v2 measurements; never mix v1/v2 comparison rows."""
from pathlib import Path
import hashlib,json
from .common import ROOT,read,digest


def apply(cases,root=ROOT):
    active=Path(root)/'data/baselines/runs/timing-v2/active.json'
    if not active.exists():return None
    manifest=read(active)
    if manifest.get('status')!='complete' or manifest.get('protocol')!='kernel-v2':return None
    pending=[];memo={}
    def unchanged(path,expected):
        if path not in memo:memo[path]=digest(path) if Path(path).is_file() else None
        return memo[path]==expected
    # A partial or changed publication must not silently replace the default.
    for record in manifest['cases']:
        if not unchanged(record['path'],record['sha256']):return None
        measurement=read(record['path'])
        if measurement['status']!='passed' or measurement['protocol']['version']!='kernel-v2':return None
        for b in measurement['builds']:
            if not all(unchanged(p,h) for p,h in b['source_hashes'].items()):return None
            if not all(unchanged(p,h) for p,h in b['artifact_hashes'].items()):return None
            if not unchanged(b['binary'],measurement['identity']['binaries'][b['id']]):return None
        pending.append((record['path'],measurement))
    for path,m in pending:
        if m['case'] not in cases:continue
        case=cases[m['case']];by_id={i['implementation_id']:i for i in case['implementations']}
        workload=m['workload'];key=hashlib.sha256(json.dumps(workload,separators=(',',':')).encode()).hexdigest()[:10]
        label=str(max((abs(x).bit_length() for x in workload),default=0))+' 位以内 · 输入 '+key
        rows=[]
        for b in m['builds']:
            if b['id'] not in by_id:continue
            i=by_id[b['id']];s=m['summary'][b['id']]
            quality={'independent_processes':s['independent_processes'],'samples':len(s['samples']),
                     'unstable_processes':s['unstable_processes'],'process_min_ns':s['process_min_ns'],
                     'process_max_ns':s['process_max_ns'],'mad_ns':s['mad_ns'],
                     'warnings':sorted({w for p in m['processes'][b['id']] for w in p['warnings']})}
            i['timing_quality']=quality;i['timing_protocol']='kernel-v2';i['timing_record']=path
            if i['kind']=='baseline':
                i['legacy_measurement']=i.get('measurement');i['measurement']=s
                i['measured_at']=m['measured_at'];i['measurement_origin']=path
            rows.append({'implementation':b['id'],'kind':b['kind'],'median_ns':s['median_ns'],
                         'min_ns':s['process_min_ns'],'max_ns':s['process_max_ns'],'successful_rounds':len(s['samples']),
                         'scope':'kernel','length':len(workload),'query':'fixed_workload','values':label,
                         'measurement_id':manifest['id']+'/'+m['case'],'measurement_round':b['round_id'],
                         'numeric_profile':b['numeric_profile'],'reused':b['kind']=='baseline',
                         'measured_at':m['measured_at'],'origin':path,'timing_quality':quality})
        round_ids={b['round_id'] for b in m['builds'] if b['kind']=='llm'}
        for round_id in sorted(round_ids|{'baseline'}):
            selected=[r for r in rows if r['kind']=='baseline' or r['measurement_round']==round_id]
            case['performance_views'].append({'id':manifest['id']+'/'+m['case'],'round_id':round_id,'rows':selected,
                'measured_at':m['measured_at'],'sequence':len(case['performance_views'])+1,'source':path,'reference':path,
                'protocol':m['protocol']})
    return 'kernel-v2'

"""Per-input executed reference availability, without inventing oracle outputs."""
from .common import Failure
from .suites import domain,property_error
POLICY='available-per-input-v1'
LANES=('ocaml','stage1','stage2')

def enabled(cfg):return cfg.get('testing',{}).get('reference_policy')==POLICY

def selected(references):return any(r.get('availability_policy')==POLICY for r in references.values())

def collect(case,inputs,references,executor,timeout,arguments=()):
    from .validation import execute
    if not all(domain(case,x) for x in inputs):raise Failure('invalid_domain','Input does not meet declared precondition')
    lanes={};matrix=[{'input_index':i,'input':x,'references':{},'available':[],'expected':None} for i,x in enumerate(inputs)]
    for name in LANES:
        ref=references.get(name,{'status':'reference_missing','phase':'admission'})
        ready=ref.get('status')=='passed' and bool(ref.get('binary'))
        args=()
        if arguments and ready:
            ready=ref.get('timing_protocol')=='kernel-v1' and bool(ref.get('kernel_behavior_argument'))
            args=(ref.get('kernel_behavior_argument'),) if ready else ()
        if not ready:
            evidence={'status':ref.get('status') if ref.get('status')!='passed' else 'kernel_unavailable',
                      'phase':ref.get('phase','kernel_mode' if arguments else 'admission'),'failure':ref.get('failure'),
                      'checks':ref.get('checks'),'depends_on':ref.get('depends_on',[])}
            lanes[name]={'status':'reference_unavailable','outputs':[None]*len(inputs),'record':evidence}
            for row in matrix:row['references'][name]=evidence
            continue
        batch=execute(ref['binary'],inputs,executor,timeout,arguments=args)
        rows=[]
        if batch['status']=='passed':
            rows=[{'status':'passed','output':out,'record':batch['record'],'batch_output_index':i} for i,out in enumerate(batch['outputs'])]
        else:
            # Preserve the failed batch; isolate only after an actual batch failure.
            for x in inputs:
                single=execute(ref['binary'],[x],executor,timeout,arguments=args)
                rows.append({'status':single['status'],'output':single['outputs'][0] if single['outputs'] is not None else None,'record':single['record']})
        values=[r['output'] for r in rows]
        lanes[name]={'status':'passed' if all(r['status']=='passed' for r in rows) else 'partial_or_unavailable','outputs':values,
                     'record':{'status':batch['status'],'phase':'kernel_runtime' if arguments else 'runtime','batch':batch['record'],'isolated_after_failure':batch['status']!='passed'},'inputs':rows}
        for row,r in zip(matrix,rows):
            row['references'][name]=r
            if r['status']=='passed':row['available'].append(name)
    for row in matrix:
        available=row['available']
        if not available:continue
        expected=row['references'][available[0]]['output'];row['expected']=expected
        if any(row['references'][n]['output']!=expected for n in available[1:]):
            raise Failure('oracle_conflict','Available references disagree',{'input':row['input'],'input_index':row['input_index'],'matrix':matrix,'references':lanes})
        error=property_error(case,row['input'],expected)
        if error:raise Failure('oracle_property_conflict',error,{'input':row['input'],'output':expected,'matrix':matrix,'references':lanes})
    covered=sum(bool(row['available']) for row in matrix)
    lanes['selection']={'status':'passed' if covered==len(inputs) else 'differential_unavailable',
                        'outputs':[r['expected'] for r in matrix],'matrix':matrix,'covered':covered,'total':len(inputs),
                        'policy':POLICY,'complete':covered==len(inputs)}
    return lanes

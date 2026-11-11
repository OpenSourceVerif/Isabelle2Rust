from __future__ import annotations

import json
from pathlib import Path

from .common import Failure, save
from .suites import domain, property_error


def execute(binary,inputs,executor,timeout,arguments=()):
    wire=''.join(' '.join(map(str,x))+'\n' for x in inputs)
    record=executor.run([binary,*arguments],stdin=wire,timeout=timeout,check=False)
    if record['status']!='passed':
        explicit_range_error=record['status']=='failed' and 'I2R_NUMERIC_OVERFLOW' in Path(record['stderr']).read_text()
        return {'status':'numeric_range_exceeded' if explicit_range_error else 'runtime_failed','record':record,'outputs':None}
    lines=Path(record['stdout']).read_text().splitlines()
    try:
        values=[[int(v) for v in line.split()] for line in lines]
        if len(values)!=len(inputs):raise ValueError('Incorrect result count')
    except ValueError:
        return {'status':'protocol_failed','record':record,'outputs':None}
    return {'status':'passed','record':record,'outputs':values}


def reference_outputs(case,inputs,references,executor,timeout,arguments=()):
    from .reference_policy import selected,collect
    if selected(references):return collect(case,inputs,references,executor,timeout,arguments)
    if not all(domain(case,x) for x in inputs):raise Failure('invalid_domain','Input does not meet declared precondition')
    if references['ocaml'].get('outputs_path'):
        from .baselines import cached_outputs
        outputs=cached_outputs(case,inputs,references,executor,timeout)
    else:
        outputs={k:execute(references[k]['binary'],inputs,executor,timeout) for k in ['ocaml','stage2']}
    for k,v in outputs.items():
        if v['status']!='passed':raise Failure('reference_runtime_failed',k,v)
    for i,(a,b) in enumerate(zip(outputs['ocaml']['outputs'],outputs['stage2']['outputs'])):
        if a!=b:raise Failure('oracle_conflict','OCaml and Stage 2 disagree',{'input':inputs[i],'ocaml':a,'stage2':b})
        error=property_error(case,inputs[i],a)
        if error:raise Failure('oracle_property_conflict',error,{'input':inputs[i],'output':a})
    return outputs


def check_suite(case,inputs,binary,references,executor,timeout,kind,arguments=()):
    expected=reference_outputs(case,inputs,references,executor,timeout,arguments)
    actual=execute(binary,inputs,executor,timeout,arguments=arguments)
    result={'kind':kind,'status':actual['status'],'count':len(inputs),'failures':0,
            'references':{k:v['record'] for k,v in expected.items() if k!='selection'},'candidate':actual['record'],'counterexamples':[]}
    selection=expected.get('selection')
    if selection:result['reference_coverage']={k:v for k,v in selection.items() if k!='outputs'}
    if actual['outputs'] is None:
        result['failures']=None
        result['completed_output_lines']=len(Path(actual['record']['stdout']).read_text().splitlines())
        result['remaining_results_unknown']=max(0,len(inputs)-result['completed_output_lines'])
        if actual['status']=='numeric_range_exceeded':
            start=min(result['completed_output_lines'],max(0,len(inputs)-1))
            result['range_event']={'record':actual['record'],'suspected_input':inputs[start] if inputs else None,
                'input_index':start,'reproductions':[],
                'note':'Range failure is not a successful result. Isolated inputs below are execution evidence, not output mismatches. Other incomplete inputs remain unknown.'}
            for index in range(start,min(len(inputs),start+3)):
                single=execute(binary,[inputs[index]],executor,min(timeout,3),arguments=arguments)
                result['range_event']['reproductions'].append({'input':inputs[index],'input_index':index,
                    'input_bits':[abs(int(n)).bit_length() for n in inputs[index]],'status':single['status'],'record':single['record']})
                if single['status']=='numeric_range_exceeded':break
            return result
        # Prioritize the first input without a completed output. Starting again
        # at input zero can entirely miss failures after the first 20 inputs.
        start=min(result['completed_output_lines'],max(0,len(inputs)-1))
        result['diagnostic_start_input']=start
        diagnostic_inputs=inputs[start:]+inputs[:start]
        for x in diagnostic_inputs[:min(20,len(inputs))]:
            single=execute(binary,[x],executor,min(timeout,3),arguments=arguments)
            if single['status'] not in {'passed','numeric_range_exceeded'}:
                result['counterexamples'].append({'input':x,'kind':single['status'],'record':single['record']})
                break
        return result
    for x,ref,out in zip(inputs,selection['outputs'] if selection else expected['ocaml']['outputs'],actual['outputs']):
        error=property_error(case,x,out)
        if (ref is not None and out!=ref) or error:
            result['counterexamples'].append({'input':x,'expected':ref,'actual':out,'property_error':error})
    result['failures']=len(result['counterexamples'])
    result['status']='mismatch' if result['failures'] else 'differential_unavailable' if selection and not selection['complete'] else 'passed'
    result['candidate_execution_passed']=not result['failures']
    result['differential_passed']=result['status']=='passed'
    return result


def add_regressions(path,counterexamples):
    path=Path(path)
    existing=json.loads(path.read_text()) if path.exists() else []
    keys={json.dumps(x['input']) for x in existing}
    for item in counterexamples:
        key=json.dumps(item['input'])
        if key not in keys:
            existing.append(item);keys.add(key)
    save(path,existing)
    return existing

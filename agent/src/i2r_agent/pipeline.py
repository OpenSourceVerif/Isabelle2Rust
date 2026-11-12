"""Diagnostic feedback formatting."""
from pathlib import Path
import json

def feedback_for(result):
    response=dict(result)
    if 'compilation' in response:
        response['compiler_diagnostics']={k:(Path(v['stdout']).read_text()+Path(v['stderr']).read_text())
            for k,v in response['compilation']['checks'].items()}
        # Repeat the first error at the end of long generation contexts. Keep
        # every diagnostic above: this highlight does not truncate the evidence.
        import re
        response['first_compiler_errors']={}
        for check,diagnostic in response['compiler_diagnostics'].items():
            match=re.search(r'^error(?:\[[^\]]+\])?:[^\n]*(?:\n(?!\s*$|error(?:\[|:)).*)*',diagnostic,re.MULTILINE)
            if match:response['first_compiler_errors'][check]=match.group(0)
    response['suites']=[{**s,'counterexamples':sorted(s.get('counterexamples',[]),key=lambda c:len(c['input']))[:5]}
                       for s in response.get('suites',[])]
    # Runtime log paths alone are not useful to a model without filesystem tools.
    # Include actual failure diagnostics, excluding only timing marker lines;
    # the complete original log remains on disk.
    response['runtime_diagnostics']=[]
    for suite in response['suites']:
        records=[('batch',suite.get('candidate',{}))]+[
            ('isolated_input',example.get('record',{})) for example in suite['counterexamples']]
        records += [('isolated_range_input',example.get('record',{})) for example in suite.get('range_event',{}).get('reproductions',[])]
        for kind,record in records:
            if record.get('status') in {None,'passed'}:continue
            path=record.get('stderr');message=Path(path).read_text() if path and Path(path).is_file() else ''
            response['runtime_diagnostics'].append({'suite':suite['kind'],'kind':kind,
                'status':record.get('status'),'returncode':record.get('returncode'),
                'stderr':'\n'.join(line for line in message.splitlines() if not line.startswith('I2R_KERNEL_NS ')),
                'original_record':record})
    response['repair_instruction']='Trace the smallest failing input through each source equation and candidate call. Preserve entire matched subtrees and aliases. Diagnose the mismatch, read missing source evidence and return concrete edits to the responsible implementation or connection. Compare actual changes and results; do not merely repeat the previous code.'
    return response

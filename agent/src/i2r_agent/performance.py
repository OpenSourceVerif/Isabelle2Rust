from __future__ import annotations

import statistics
import re
from pathlib import Path

from .common import Failure, save
from .validation import execute


def benchmark(implementations, workload, expected, cfg,executor,directory):
    if cfg['performance'].get('protocol')=='kernel-v2':
        from .kernel_benchmark import benchmark as batch_benchmark
        return batch_benchmark(implementations,workload,expected,cfg,executor,directory)
    options=cfg['performance'];samples={k:[] for k in implementations};records=[]
    inputs=[workload]*options['iterations']
    for block in range(options['warmups']+options['samples']):
        names=list(implementations)
        shift=block%len(names);names=names[shift:]+names[:shift]
        for name in names:
            result=execute(implementations[name],inputs,executor,max(30,cfg['testing']['process_timeout']),arguments=('--i2r-benchmark',))
            if result['status']!='passed' or any(y!=expected for y in result['outputs']):
                raise Failure('benchmark_behavior_failure',name,result)
            stderr=Path(result['record']['stderr']).read_text()
            ticks=[int(n) for n in re.findall(r'^I2R_KERNEL_NS ([0-9]+)$',stderr,re.M)]
            if len(ticks)!=options['iterations']:
                raise Failure('kernel_timing_missing','Expected one in-process algorithm timing per invocation',result['record'])
            elapsed=sum(ticks);value=elapsed/options['iterations']
            records.append({'implementation':name,'block':block,'warmup':block<options['warmups'],
                'batch_ns':elapsed,'iterations':options['iterations'],'per_call_ns':value,'kernel_samples_ns':ticks,'execution':result['record']})
            if block>=options['warmups']:samples[name].append(value)
    result={'scope':'kernel','protocol':{'version':'kernel-v1','boundary':'in-process kernel_run only; input parsing, representation conversion, preparation and result encoding/checking excluded',
            'timer':'Rust Instant / OCaml CLOCK_MONOTONIC; ordinary timer-call overhead is not subtracted',
            'order':'rotating blocks','options':options},'workload':workload,'raw_samples':records,
            'summary':{k:{'median_ns':statistics.median(v),'min_ns':min(v),'max_ns':max(v),'samples':v} for k,v in samples.items()}}
    save(Path(directory)/'performance.json',result)
    return result

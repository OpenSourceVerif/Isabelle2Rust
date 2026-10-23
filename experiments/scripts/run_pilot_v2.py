#!/usr/bin/env python3
"""Two-task pilot: prepare, generate (3 independent runs/task), benchmark.

Keeps the original pilot runner and records unchanged. No automatic HTTP retries.
"""
import argparse
from collections import Counter
import itertools
import json
from pathlib import Path
import random
import re
import shutil
import statistics
import time
import urllib.error
import urllib.request

import run_list_index as common

EXP = common.EXP
REPO = common.REPO
BATCH_ID = '20261023-02-two-task-pilot'
BATCH = EXP/'runs'/BATCH_ID
CONFIG_PATH = EXP/'tasks/direct-two-task-v2.json'
OLD = EXP/'runs/20261023-01-list-index-smoke'
save, digest, command, require = common.save, common.digest, common.command, common.require


def fixture(task):
    return EXP/'harness'/('list-index-v2' if task == 'list-index' else 'skew-heap')


def encode(tree):
    if tree is None:
        return '#'
    l, x, r = tree
    return str(x)+' '+encode(l)+' '+encode(r)


def merge(a, b, strict=False):
    if a is None:
        return b
    if b is None:
        return a
    l1, x, r1 = a
    l2, y, r2 = b
    if x < y if strict else x <= y:
        return (merge(b, r1, strict), x, l1)
    return (merge(a, r2, strict), y, l2)


def values(t):
    return [] if t is None else values(t[0])+[t[1]]+values(t[2])


def heap(t):
    return t is None or (all(t[1] <= x for x in values(t[0])+values(t[2])) and heap(t[0]) and heap(t[2]))


def trees(n, alphabet):
    if n == 0:
        return [None]
    return [(l,x,r) for i in range(n) for l in trees(i,alphabet)
            for r in trees(n-1-i,alphabet) for x in alphabet]


def random_tree(rng, n, ordered=False):
    if n == 0:
        return None
    if ordered:
        t = None
        for _ in range(n):
            t = merge(t, (None,rng.randrange(-10,11),None))
        return t
    i = rng.randrange(n)
    x = rng.choice([-2**130, -2, 0, 1, 2, 2**130])
    return random_tree(rng,i), x, random_tree(rng,n-1-i)


def skew_cases(cfg):
    dev, final = [], []
    seen = set()
    def add(dest,a,b):
        text = encode(a)+' '+encode(b)
        if text in seen:
            return
        seen.add(text)
        result = merge(a,b)
        assert Counter(values(result)) == Counter(values(a)+values(b))
        if heap(a) and heap(b):
            assert heap(result)
        dest.append(dict(input=text,expected=encode(result),valid_heaps=heap(a) and heap(b),
                         nodes=len(values(a))+len(values(b))))
    small = sum([trees(n,[0,1]) for n in range(3)],[])
    for a,b in itertools.product(small,repeat=2):
        add(dev,a,b)
    rng = random.Random(cfg['development_seed'])
    for i in range(cfg['development_random_cases']):
        add(dev,random_tree(rng,rng.randrange(21),i%2==0),random_tree(rng,rng.randrange(21),i%2==0))
    rng = random.Random(cfg['final_seed'])
    larger = sum([trees(n,[-1,0,1]) for n in range(4)],[])
    for index in rng.sample(range(len(larger)**2),cfg['final_exhaustive_samples']):
        add(final,larger[index//len(larger)],larger[index%len(larger)])
    for i in range(cfg['final_random_cases']):
        add(final,random_tree(rng,rng.randrange(65),i%2==0),random_tree(rng,rng.randrange(65),i%2==0))
    for x in [-2**150,0,2**150]:
        for n in [16,32,64]:
            chain = None
            for _ in range(n):
                chain = (None,x,chain)
            add(final,chain,(None,x,None))
            add(final,(None,x,None),chain)
    return dev,final


def evaluate(binary,data,log):
    result = command([binary],log,stdin=''.join(c['input']+'\n' for c in data))
    out = result['stdout'].splitlines()
    if result['returncode'] != 0 or result['timed_out']:
        return dict(status='runtime_failed',timed_out=result['timed_out'],diagnostic=result['stderr'][-4000:])
    if len(out)!=len(data):
        return dict(status='protocol_failed',expected_lines=len(data),actual_lines=len(out))
    errors = [dict(index=i,input=c['input'],expected=c['expected'],actual=out[i])
              for i,c in enumerate(data) if out[i]!=c['expected']]
    return dict(status='mismatch' if errors else 'passed',count=len(data),failures=len(errors),
                counterexamples=errors[:3],seconds=result['seconds'])


def crate(task,path,baseline=None,code=None):
    (path/'src').mkdir(parents=True,exist_ok=True)
    manifest = ('[package]\nname = "pilot_runner"\nversion = "0.1.0"\nedition = "2024"\n'
                '[features]\ncandidate = []\nstage2 = []\n'
                '[dependencies]\nnum-bigint = "=0.4.6"\n')
    if baseline:
        manifest += 'exported = { package = "isabelle_exported", path = '+json.dumps(str(baseline))+' }\n'
    (path/'Cargo.toml').write_text(manifest)
    shutil.copyfile(fixture(task)/'rust_main.rs',path/'src/main.rs')
    if code is not None:
        (path/'src/candidate.rs').write_text(code)
    return path/'target/release/pilot_runner'


def prepare_task(task,config):
    root = BATCH/task
    base = root/'baselines'
    base.mkdir(parents=True,exist_ok=True)
    if task == 'list-index':
        old_ready = json.loads((OLD/'prepared.json').read_text())
        assert digest(common.AFP/'List-Index/List_Index.thy') == old_ready['environment']['source_sha256']
        shutil.copytree(OLD/'baselines/generated',base/'generated',dirs_exist_ok=True)
        shutil.copytree(OLD/'baselines/optimized',base/'optimized',dirs_exist_ok=True)
        for split in ['development','final']:
            data = json.loads((OLD/'data'/(split+'.json')).read_text())
            save(root/'data'/(split+'.json'),[dict(input=' '.join([c['x']]+c['xs']),expected=c['expected']) for c in data])
        shutil.copyfile(OLD/'prompt.txt',root/'prompt.txt')
        shutil.copytree(OLD/'source',root/'source',dirs_exist_ok=True)
    else:
        session = base/'session'
        session.mkdir(exist_ok=True)
        for name in ['ROOT','Direct_Skew_Heap.thy']:
            shutil.copyfile(fixture(task)/name,session/name)
        dirs = ['-d',REPO,'-d',common.AFP,'-d',session]
        require([common.ISABELLE,'build','-j','2','-o','threads=2']+dirs+['Direct_Skew_Heap'],base/'build.json',timeout=660)
        require([common.ISABELLE,'export','-n']+dirs+['-O',base/'generated','-p','2','-x',
                'Direct_Skew_Heap.Direct_Skew_Heap:code/**','Direct_Skew_Heap'],base/'export.json')
        require(common.CARGO+['build','--locked','--manifest-path',REPO/'optimize/Cargo.toml','--bin','cargo-opt'],base/'optimizer-build.json')
        require([REPO/'optimize/target/debug/cargo-opt',base/'generated/reference','--out-dir',base/'optimized'],base/'optimizer.json')
        dev,final = skew_cases(config['skew_heap_tests'])
        save(root/'data/development.json',dev)
        save(root/'data/final.json',final)
        source = (common.AFP/'Skew_Heap/Skew_Heap.thy').read_text()
        (root/'source').mkdir(exist_ok=True)
        (root/'source/Skew_Heap.thy').write_text(source)
        tree_source = Path('/Applications/Isabelle2025.app/src/HOL/Library/Tree.thy')
        shutil.copyfile(tree_source,root/'source/Tree.thy')
        excerpt = source[source.index('function merge ::'):source.index('text\\<open>An alternative')]
        prompt = '''Translate the Isabelle/HOL merge function below directly into safe Rust.
Return only the full content of candidate.rs, without Markdown fences or explanations.
Define exactly this public data type and function (additional helpers are allowed):
pub enum Tree<T> { Leaf, Node(Box<Tree<T>>, T, Box<Tree<T>>) }
pub fn merge<T: Ord>(a: Tree<T>, b: Tree<T>) -> Tree<T>
Node fields are LEFT SUBTREE, VALUE, RIGHT SUBTREE, in that order.
The input trees are owned. Do not require Clone or Copy bounds on T.
Preserve the exact output tree shape and values for all finite trees, not only heaps.
Equal keys use the <= branch, exactly as in the Isabelle definition.
Isabelle pattern aliases such as (Node l1 a1 r1 =: t1) bind t1 to that whole tree.
Use Rust edition 2024 and std; no unsafe, filesystem/network/process access, or main.
No reference implementation source is supplied. The following is the exact AFP source excerpt:
\n'''+excerpt
        (root/'prompt.txt').write_text(prompt)
    binaries = {}
    for stage,source in [('stage1',base/'generated/reference'),('stage2',base/'optimized')]:
        path = base/(stage+'-runner')
        binaries[stage] = str(crate(task,path,baseline=source))
        result = common.build_rust(path,'stage2' if stage=='stage2' else '',base/(stage+'-build.json'))
        if result['returncode']!=0:
            raise RuntimeError('Baseline compile failed: '+task+' '+stage)
    ocaml = base/'ocaml'
    ocaml.mkdir(exist_ok=True)
    shutil.copyfile(base/'generated/reference.ocaml',ocaml/'exported_reference.ml')
    shutil.copyfile(fixture(task)/'ocaml_main.ml',ocaml/'main.ml')
    require([common.OPAM/'bin/ocamlfind','ocamlopt','-package','zarith,unix','-linkpkg',
             'exported_reference.ml','main.ml','-o','reference'],base/'ocaml-build.json',cwd=ocaml)
    binaries['ocaml'] = str(ocaml/'reference')
    checks = {}
    for name,binary in binaries.items():
        checks[name] = {}
        for split in ['development','final']:
            data = json.loads((root/'data'/(split+'.json')).read_text())
            check = evaluate(binary,data,base/(name+'-'+split+'.json'))
            checks[name][split] = check
            if check['status']!='passed':
                save(root/'baseline-failure.json',checks)
                raise RuntimeError('Baseline validation failed: '+task+' '+name+' '+split)
    # Actual compiled negative controls, separate from all model samples.
    if task == 'list-index':
        wrong = 'pub fn last_index<T: Eq>(xs: &[T], x: &T) -> num_bigint::BigInt { num_bigint::BigInt::from(xs.iter().position(|v| v == x).unwrap_or(xs.len())) }'
    else:
        wrong = '''pub enum Tree<T> { Leaf, Node(Box<Tree<T>>, T, Box<Tree<T>>) }
pub fn merge<T: Ord>(a: Tree<T>, b: Tree<T>) -> Tree<T> {
    match (a,b) {
        (Tree::Leaf,t) | (t,Tree::Leaf) => t,
        (Tree::Node(l1,x,r1), Tree::Node(l2,y,r2)) => {
            if x < y { Tree::Node(Box::new(merge(Tree::Node(l2,y,r2),*r1)),x,l1) }
            else { Tree::Node(Box::new(merge(Tree::Node(l1,x,r1),*r2)),y,l2) }
        }
    }
}'''
    nc = root/'negative-control'
    binary = crate(task,nc,code=wrong)
    built = common.build_rust(nc,'candidate',nc/'build.json')
    assert built['returncode']==0
    negative = evaluate(binary,json.loads((root/'data/development.json').read_text()),nc/'execution.json')
    assert negative['status']=='mismatch'
    save(nc/'result.json',negative)
    info = dict(binaries=binaries,baseline_checks=checks,negative_control=negative)
    save(root/'prepared.json',info)
    print(task,'baselines passed; negative control rejected',flush=True)
    return info


def prepare():
    if (BATCH/'prepared.json').exists():
        raise RuntimeError('Already prepared; do not overwrite the frozen protocol.')
    config = json.loads(CONFIG_PATH.read_text())
    save(BATCH/'config.json',config)
    info = {task:prepare_task(task,config) for task in config['tasks']}
    environment = common.provenance(BATCH)
    protocol = [Path(__file__),Path(common.__file__),CONFIG_PATH,EXP/'plans/paper-01-v0.1.md']
    for task in config['tasks']:
        protocol += [p for p in fixture(task).iterdir() if p.is_file()]
    protocol_hashes = {}
    for path in protocol:
        target = BATCH/'protocol-snapshot'/path.relative_to(REPO)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)
        protocol_hashes[str(path.relative_to(REPO))] = digest(path)
    frozen = [BATCH/'config.json']
    for task in config['tasks']:
        root = BATCH/task
        frozen += [root/'prompt.txt',root/'data/development.json',root/'data/final.json',root/'prepared.json']
        frozen += [Path(x) for x in info[task]['binaries'].values()]
        frozen += list((root/'source').iterdir())
        for d in ['generated','optimized']:
            frozen += [p for p in (root/'baselines'/d).rglob('*') if p.is_file() and 'target' not in p.parts]
    save(BATCH/'prepared.json',dict(prepared_at=common.now(),environment=environment,tasks=info,
         protocol_sha256=protocol_hashes,frozen_sha256={str(p.relative_to(BATCH)):digest(p) for p in frozen}))


def verify():
    ready = json.loads((BATCH/'prepared.json').read_text())
    for name,sha in ready['protocol_sha256'].items():
        assert digest(REPO/name)==sha,'Protocol changed: '+name
    for name,sha in ready['frozen_sha256'].items():
        assert digest(BATCH/name)==sha,'Frozen data changed: '+name
    return ready


def model_run(task,index,config,key,ledger):
    root = BATCH/task
    run = root/('run-%03d'%index)
    run.mkdir()
    messages = [dict(role='system',content='You translate Isabelle/HOL definitions to safe Rust. Follow the supplied interface and semantics.'),
                dict(role='user',content=(root/'prompt.txt').read_text())]
    result = dict(task=task,run_id=run.name,status='running',started_at=common.now(),attempts=[],final_feedback=False)
    save(run/'result.json',result)
    for attempt in range(1,config['max_calls_per_run']+1):
        folder = run/('attempt-%02d'%attempt)
        folder.mkdir()
        payload = dict(model=config['model'],messages=messages,thinking=config['thinking'],temperature=config['temperature'],
                       max_tokens=config['max_tokens'],stream=False)
        body = json.dumps(payload,ensure_ascii=False).encode()
        estimate = (len(body)*0.30+config['max_tokens']*1.20)/1e6
        if ledger['calls']>=config['max_calls_batch'] or ledger['estimated_peak_cost_usd']+estimate>config['estimated_peak_cost_guard_usd']:
            result['status']='budget_exhausted'
            break
        save(folder/'request.json',payload)
        ledger['calls']+=1
        ledger['in_flight']=str(folder.relative_to(BATCH))
        save(BATCH/'ledger.json',ledger)
        request = urllib.request.Request('https://api.deepseek.com/chat/completions',data=body,
                  headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        try:
            start = time.monotonic()
            with urllib.request.urlopen(request,timeout=180) as response:
                raw = response.read()
            (folder/'response.json').write_bytes(raw)
            reply = json.loads(raw)
        except Exception as error:
            result['status']='api_error_unknown_billing'
            result['error_type']=type(error).__name__
            if isinstance(error,urllib.error.HTTPError):
                result['http_status']=error.code
            save(run/'result.json',result)
            raise RuntimeError('API call failed; stop batch without retries; inspect '+str(run)) from None
        usage = reply.get('usage',{})
        ledger['estimated_peak_cost_usd']+=(usage.get('prompt_tokens',0)*0.30+usage.get('completion_tokens',0)*1.20)/1e6
        ledger['in_flight']=None
        save(BATCH/'ledger.json',ledger)
        choice = reply['choices'][0]
        content = choice['message'].get('content') or ''
        code = content.strip()
        match = re.fullmatch(r'```(?:rust)?\s*\n(.*?)\n```',code,re.S)
        if match:
            code = match.group(1)
        (folder/'candidate.rs').write_text(code+'\n')
        record = dict(attempt=attempt,usage=usage,model=reply.get('model'),api_seconds=time.monotonic()-start,
                      finish_reason=choice.get('finish_reason'))
        binary = crate(task,folder/'crate',code=code)
        if choice.get('finish_reason')!='stop':
            feedback=dict(status='incomplete_response')
        else:
            built = common.build_rust(folder/'crate','candidate',folder/'build.json')
            if built['returncode']!=0:
                feedback=dict(status='compile_failed',diagnostic=built['stderr'][-8000:])
            else:
                feedback=evaluate(binary,json.loads((root/'data/development.json').read_text()),folder/'development.json')
        record['development']=feedback
        result['attempts'].append(record)
        save(folder/'feedback.json',feedback)
        save(run/'result.json',result)
        print(task,run.name,'attempt',attempt,feedback['status'],flush=True)
        if feedback['status']=='passed':
            result.update(status='candidate_frozen',selected_attempt=attempt,candidate_sha256=digest(folder/'candidate.rs'),binary=str(binary))
            save(run/'result.json',result)
            result['final']=evaluate(binary,json.loads((root/'data/final.json').read_text()),folder/'final.json')
            result['status']='passed' if result['final']['status']=='passed' else 'final_failed'
            break
        messages += [dict(role='assistant',content=content),dict(role='user',content='Fix the candidate using this development feedback; return complete candidate.rs only.\n'+json.dumps(feedback))]
    else:
        result['status']='attempt_budget_exhausted'
    result['finished_at']=common.now()
    save(run/'result.json',result)
    return result


def generate():
    verify()
    config=json.loads((BATCH/'config.json').read_text())
    key=common.read_key(Path.home()/'.config/isabelle2rust/deepseek.env')
    if (BATCH/'ledger.json').exists():
        raise RuntimeError('Batch already started; no implicit restart or overwrite.')
    ledger=dict(calls=0,estimated_peak_cost_usd=0.0,in_flight=None)
    save(BATCH/'ledger.json',ledger)
    results=[]
    for task in config['tasks']:
        for index in range(1,config['independent_runs_per_task']+1):
            results.append(model_run(task,index,config,key,ledger))
            save(BATCH/'generation-results.json',results)
    print(json.dumps(ledger),flush=True)


def benchmark():
    ready=verify()
    config=json.loads((BATCH/'config.json').read_text())['performance']
    runs=json.loads((BATCH/'generation-results.json').read_text())
    binaries=dict(ready['tasks']['list-index']['binaries'])
    for result in runs:
        if result['task']=='list-index' and result['status']=='passed':
            binaries[result['run_id']]=result['binary']
    output=BATCH/'performance'
    output.mkdir()  # prevent accidental repetition/overwriting
    names=list(binaries)
    samples=[]
    for length in config['lengths']:
        for mode in config['queries']:
            for round_index in range(config['rounds']):
                order=names[round_index%len(names):]+names[:round_index%len(names)]
                for name in order:
                    log=output/('%s-n%d-%s-r%d.json'%(name,length,mode,round_index))
                    measured=command([binaries[name],'--bench',str(length),mode,str(config['iterations'])],log)
                    sample=dict(implementation=name,length=length,query=mode,round=round_index,order=order,
                                returncode=measured['returncode'],timed_out=measured['timed_out'])
                    if measured['returncode']==0 and not measured['timed_out']:
                        fields=measured['stdout'].split()
                        nanos,iterations=int(fields[0]),int(fields[1])
                        expected=length if mode=='absent' else (0 if mode=='first' else length-1)
                        assert int(fields[2])==expected and iterations==config['iterations'] and nanos>0
                        sample.update(status='passed',ns_per_call=nanos/iterations,total_ns=nanos)
                    else:
                        sample['status']='failed'
                    samples.append(sample)
            print('benchmark',length,mode,'complete',flush=True)
    aggregates=[]
    for name,length,mode in itertools.product(names,config['lengths'],config['queries']):
        group=[s for s in samples if s['implementation']==name and s['length']==length and s['query']==mode]
        values=[s['ns_per_call'] for s in group if s['status']=='passed']
        aggregates.append(dict(implementation=name,length=length,query=mode,successful_rounds=len(values),
                               median_ns=statistics.median(values) if values else None,
                               min_ns=min(values) if values else None,max_ns=max(values) if values else None))
    save(BATCH/'performance.json',dict(protocol=config,samples=samples,aggregates=aggregates))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','generate','benchmark'])
    args=parser.parse_args()
    BATCH.mkdir(parents=True,exist_ok=True)
    globals()[args.action]()


if __name__=='__main__':
    main()

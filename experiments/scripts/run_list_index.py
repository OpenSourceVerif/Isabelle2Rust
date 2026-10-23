#!/usr/bin/env python3
"""One-task direct Isabelle-to-Rust pilot. prepare makes no API requests.

Usage: python3 experiments/scripts/run_list_index.py prepare|generate [--key-file PATH]
Raw artifacts stay in experiments/runs; no credentials are written to disk.
"""
import argparse
import datetime as dt
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import random
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO = Path(__file__).resolve().parents[2]
EXP = REPO / 'experiments'
FIXTURE = EXP / 'harness/list-index'
CONFIG = EXP / 'tasks/direct-list-index-smoke-v1.json'
ISABELLE = '/Applications/Isabelle2025.app/bin/isabelle'
AFP = Path.home() / 'Libraries/afp-Isabelle2025/thys'
OPAM = Path.home() / '.opam/isabelle2rust'
CARGO = ['cargo', '+1.94.0']


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def command(args, log, cwd=REPO, stdin=None, timeout=180):
    env = dict(os.environ)
    env.pop('DEEPSEEK_API_KEY', None)
    env.pop('RUSTC_BOOTSTRAP', None)
    env['PATH'] = str(OPAM / 'bin') + os.pathsep + env.get('PATH', '')
    env['CARGO_BUILD_JOBS'] = '2'
    started = time.monotonic()
    p = subprocess.Popen([str(a) for a in args], cwd=str(cwd), env=env,
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, start_new_session=True)
    timed_out = False
    try:
        out, err = p.communicate(stdin, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(p.pid, signal.SIGKILL)
        out, err = p.communicate()
    result = dict(argv=[str(a) for a in args], cwd=str(cwd), returncode=p.returncode,
                  timed_out=timed_out, seconds=time.monotonic()-started,
                  stdout=out, stderr=err)
    save(log, result)
    return result


def require(args, log, **kwargs):
    result = command(args, log, **kwargs)
    if result['returncode'] != 0 or result['timed_out']:
        raise RuntimeError('Command failed; inspect ' + str(log))
    return result


def cases(config):
    dev, final = [], []
    def add(dest, xs, x):
        expected = len(xs)
        for i, value in enumerate(xs):
            if value == x:
                expected = i
        dest.append(dict(xs=[str(v) for v in xs], x=str(x), expected=str(expected)))
    for n in range(config['development']['boolean_max_length'] + 1):
        for xs in itertools.product([0, 1], repeat=n):
            for x in [0, 1, 2]:
                add(dev, xs, x)
    for n in range(config['final']['ternary_min_length'], config['final']['ternary_max_length']+1):
        for xs in itertools.product([-1, 0, 1], repeat=n):
            if -1 in xs:  # exclude Boolean-only development cases
                for x in [-1, 0, 1, 2]:
                    add(final, xs, x)
    for name, dest in [('development', dev), ('final', final)]:
        cfg = config[name]
        rng = random.Random(cfg['seed'])
        for i in range(cfg['random_cases']):
            n = rng.randrange(1, cfg['max_random_length'] + 1)
            pool = [rng.randrange(-(2**130), 2**130) for _ in range(8)]
            xs = [rng.choice(pool) for _ in range(n)]
            x = pool[0] if i % 3 else 2**160 + i
            add(dest, xs, x)
    for n in [129, 255, 512]:
        for x in [-(2**150), 0, 2**150]:
            add(final, [-(2**150)] + [0]*(n-2) + [2**150], x)
    return dev, final


def evaluate(binary, data, log, timeout):
    stdin = ''.join(' '.join([c['x']] + c['xs']) + '\n' for c in data)
    result = command([binary], log, stdin=stdin, timeout=timeout)
    lines = result['stdout'].splitlines()
    if result['returncode'] != 0 or result['timed_out']:
        return dict(status='runtime_failed', count=len(data), diagnostic=result['stderr'][-4000:],
                    timed_out=result['timed_out'])
    if len(lines) != len(data):
        return dict(status='protocol_failed', expected_lines=len(data), actual_lines=len(lines))
    errors = [dict(index=i, input=c, actual=lines[i]) for i,c in enumerate(data)
              if lines[i] != c['expected']]
    return dict(status='passed' if not errors else 'mismatch', count=len(data),
                failures=len(errors), counterexamples=errors[:3], seconds=result['seconds'])


def rust_crate(path, baseline=None, candidate=None):
    (path/'src').mkdir(parents=True, exist_ok=True)
    name = 'list_index_runner'
    manifest = ('[package]\nname = "'+name+'"\nversion = "0.1.0"\nedition = "2024"\n'
                '[features]\ncandidate = []\nstage2 = []\n'
                '[dependencies]\nnum-bigint = "=0.4.6"\n')
    if baseline:
        manifest += 'exported = { package = "isabelle_exported", path = ' + json.dumps(str(baseline)) + ' }\n'
    (path/'Cargo.toml').write_text(manifest)
    shutil.copyfile(FIXTURE/'rust_main.rs', path/'src/main.rs')
    if candidate is not None:
        (path/'src/candidate.rs').write_text(candidate)
    return path/'target/release'/name


def build_rust(path, feature, log):
    lock = command(CARGO+['generate-lockfile', '--manifest-path', path/'Cargo.toml'],
                   log.with_name(log.stem+'-lock.json'))
    if lock['returncode'] != 0:
        return lock
    return command(CARGO+['build', '--release', '--locked', '--manifest-path', path/'Cargo.toml']
                   + (['--features', feature] if feature else []), log)


def provenance(batch):
    info = dict(recorded_at=now(), os=platform.platform(), machine=platform.machine(),
                python=sys.version, source_sha256=digest(AFP/'List-Index/List_Index.thy'))
    for label, args, cwd in [
        ('repo_head', ['git','rev-parse','HEAD'], REPO),
        ('rustlightast_head', ['git','rev-parse','HEAD'], REPO.parent/'RustLightAST'),
        ('repo_status', ['git','status','--porcelain'], REPO),
        ('rustlightast_status', ['git','status','--porcelain'], REPO.parent/'RustLightAST'),
        ('rustc', ['rustc','+1.94.0','--version'], REPO),
        ('ocaml', [OPAM/'bin/ocamlopt','-version'], REPO),
        ('isabelle', [ISABELLE,'version'], REPO),
        ('hardware', ['sysctl','hw.model','hw.memsize','hw.ncpu'], REPO)]:
        info[label] = require(args, batch/'environment'/(label+'.json'), cwd=cwd)['stdout'].strip()
    for name, repo in [('repo', REPO), ('rustlightast', REPO.parent/'RustLightAST')]:
        diff = require(['git','diff','HEAD','--binary'], batch/'environment'/(name+'-diff.json'), cwd=repo)
        (batch/'environment'/(name+'.patch')).write_text(diff['stdout'])
    return info


def prepare(batch, config):
    if (batch/'prepared.json').exists():
        raise RuntimeError('Already prepared; choose a new batch ID to avoid overwriting evidence.')
    base = batch/'baselines'
    session = base/'session'
    session.mkdir(parents=True, exist_ok=True)
    save(batch/'config.json', config)
    for filename in ['ROOT', 'Direct_List_Index.thy']:
        shutil.copyfile(FIXTURE/filename, session/filename)
    dirs = ['-d', REPO, '-d', AFP, '-d', session]
    require([ISABELLE, 'build', '-j','2','-o','threads=2']+dirs+['Direct_List_Index'],
            base/'build.json', timeout=660)
    generated = base/'generated'
    require([ISABELLE,'export','-n']+dirs+['-O',generated,'-p','2','-x',
            'Direct_List_Index.Direct_List_Index:code/**','Direct_List_Index'], base/'export.json')
    require(CARGO+['build','--locked','--manifest-path',REPO/'optimize/Cargo.toml','--bin','cargo-opt'],
            base/'optimizer-build.json')
    require([REPO/'optimize/target/debug/cargo-opt',generated/'reference','--out-dir',base/'optimized'],
            base/'optimizer.json')
    binaries = {}
    for stage, source in [('stage1',generated/'reference'),('stage2',base/'optimized')]:
        crate = base/(stage+'-runner')
        binaries[stage] = str(rust_crate(crate, baseline=source))
        build = build_rust(crate, 'stage2' if stage=='stage2' else '', base/(stage+'-build.json'))
        if build['returncode'] != 0:
            raise RuntimeError('Rust baseline build failed: '+stage)
    ocaml = base/'ocaml'
    ocaml.mkdir(exist_ok=True)
    shutil.copyfile(generated/'reference.ocaml', ocaml/'exported_reference.ml')
    shutil.copyfile(FIXTURE/'ocaml_main.ml', ocaml/'main.ml')
    require([OPAM/'bin/ocamlfind','ocamlopt','-package','zarith','-linkpkg',
             'exported_reference.ml','main.ml','-o','reference'], base/'ocaml-build.json',cwd=ocaml)
    binaries['ocaml'] = str(ocaml/'reference')
    dev, final = cases(config)
    # The final suite is frozen here, before any model call, and never sent to the model.
    save(batch/'data/development.json',dev)
    save(batch/'data/final.json',final)
    checks = {}
    for name, binary in binaries.items():
        checks[name] = {}
        for split, data in [('development',dev),('final',final)]:
            checks[name][split] = evaluate(binary, data, base/(name+'-'+split+'.json'),
                                          config['command_timeout_seconds'])
            if checks[name][split]['status'] != 'passed':
                save(batch/'baseline-failure.json', checks)
                raise RuntimeError('Baseline disagrees with independent Python oracle: '+name+' '+split)
    source = (AFP/'List-Index/List_Index.thy').read_text()
    (batch/'source').mkdir(exist_ok=True)
    (batch/'source/List_Index.thy').write_text(source)
    excerpt = source[:source.index('lemma find_index_append')]
    prompt = '''Translate the Isabelle/HOL last_index definition below directly into safe Rust.
Return only the full content of candidate.rs, without Markdown fences or explanations.
Required public signature:
pub fn last_index<T: Eq>(xs: &[T], x: &T) -> num_bigint::BigInt
Use Rust edition 2024 and num-bigint 0.4.6. You may choose the implementation and
use std, but no unsafe, filesystem/network/process access, other dependencies, or main.
Preserve the source behavior for every finite representable list: index is zero-based;
when absent return list length. Equality is ordinary element equality. Isabelle nat
is nonnegative and unbounded, subtraction saturates at zero. rev reverses a list,
size is its length. Return BigInt, not a machine-sized integer. Do not change the interface.
The source below is an exact excerpt from AFP List_Index.thy (definitions and commentary).
No generated OCaml or Rust reference implementation is supplied.
\n''' + excerpt
    (batch/'prompt.txt').write_text(prompt)
    env = provenance(batch)
    snapshot = batch/'protocol-snapshot'
    paths = [CONFIG, Path(__file__), EXP/'plans/paper-01-v0.1.md']+list(FIXTURE.iterdir())
    hashes = {}
    for path in paths:
        target = snapshot/path.relative_to(REPO)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)
        hashes[str(path.relative_to(REPO))] = digest(path)
    frozen = [batch/'config.json',batch/'prompt.txt',batch/'data/development.json',batch/'data/final.json']
    frozen += [Path(p) for p in binaries.values()]
    save(batch/'prepared.json', dict(status='ready_for_model',prepared_at=now(),environment=env,
         baseline_checks=checks,binaries=binaries,protocol_sha256=hashes,
         frozen_sha256={str(p.relative_to(batch)):digest(p) for p in frozen}))
    print(json.dumps(dict(status='ready_for_model',development=len(dev),final=len(final),
                          baselines=list(binaries)),ensure_ascii=False),flush=True)


def read_key(path):
    key = os.environ.get('DEEPSEEK_API_KEY','').strip()
    if key:
        return key
    if path and path.is_file():
        # Only parse a literal env assignment; never execute configuration as code.
        for line in path.read_text().splitlines():
            parts = shlex.split(line, comments=True)
            if parts and parts[0]=='export':
                parts=parts[1:]
            if len(parts)==1 and parts[0].startswith('DEEPSEEK_API_KEY='):
                return parts[0].split('=',1)[1].strip()
    raise RuntimeError('DEEPSEEK_API_KEY unavailable; use environment or --key-file. Do not paste it into chat.')


def generate(batch, keyfile):
    ready = json.loads((batch/'prepared.json').read_text())
    for name, expected in ready['protocol_sha256'].items():
        if digest(REPO/name) != expected:
            raise RuntimeError('Protocol changed after preparation: '+name)
    for name, expected in ready['frozen_sha256'].items():
        if digest(batch/name) != expected:
            raise RuntimeError('Frozen input changed: '+name)
    key = read_key(keyfile)
    run = batch/'run-001'
    run.mkdir()  # fail rather than overwrite a prior call or ambiguous API outcome
    config = json.loads((batch/'config.json').read_text())
    dev = json.loads((batch/'data/development.json').read_text())
    messages = [dict(role='system',content='You translate Isabelle/HOL definitions to safe Rust. Follow the supplied interface and semantics.'),
                dict(role='user',content=(batch/'prompt.txt').read_text())]
    result = dict(status='running',started_at=now(),attempts=[],estimated_peak_cost_usd=0.0,
                  final_test_feedback=False,performance='not_measured_smoke_only')
    save(run/'result.json',result)
    for attempt in range(1,config['max_calls']+1):
        folder = run/('attempt-%02d'%attempt)
        folder.mkdir()
        payload = dict(model=config['model'],messages=messages,thinking=config['thinking'],
                       temperature=config['temperature'],max_tokens=config['max_tokens'],stream=False)
        body = json.dumps(payload,ensure_ascii=False).encode()
        # Conservative byte-count input estimate, not a provider-side billing cap.
        estimated_next = (len(body)*0.30+config['max_tokens']*1.20)/1e6
        if result['estimated_peak_cost_usd']+estimated_next > config['estimated_cost_guard_usd']:
            result['status']='estimated_budget_exhausted'
            break
        save(folder/'request.json',payload)
        request = urllib.request.Request('https://api.deepseek.com/chat/completions',data=body,
                  headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request,timeout=config['api_timeout_seconds']) as response:
                raw=response.read()
            (folder/'response.json').write_bytes(raw)
            reply=json.loads(raw)
        except Exception as error:
            # An interrupted request may have been billed. No automatic HTTP retries.
            result['status']='api_error_unknown_billing'
            result['api_error_type']=type(error).__name__
            if isinstance(error,urllib.error.HTTPError):
                result['http_status']=error.code
            break
        usage=reply.get('usage',{})
        price=(usage.get('prompt_tokens',0)*0.30+usage.get('completion_tokens',0)*1.20)/1e6
        result['estimated_peak_cost_usd']+=price
        choice=reply['choices'][0]
        content=choice['message'].get('content') or ''
        code=content.strip()
        if code.startswith('```'):
            match=re.fullmatch(r'```(?:rust)?\s*\n(.*?)\n```',code,re.S)
            if match:
                code=match.group(1)
        (folder/'candidate.rs').write_text(code+'\n')
        record=dict(attempt=attempt,model=reply.get('model'),usage=usage,
                    finish_reason=choice.get('finish_reason'),api_seconds=time.monotonic()-started)
        crate=folder/'crate'
        binary=rust_crate(crate,candidate=code)
        if choice.get('finish_reason') != 'stop':
            feedback=dict(status='incomplete_response',reason=choice.get('finish_reason'))
        else:
            build=build_rust(crate,'candidate',folder/'build.json')
            if build['returncode'] != 0:
                feedback=dict(status='compile_failed',diagnostic=build['stderr'][-8000:])
            else:
                feedback=evaluate(binary,dev,folder/'development-execution.json',config['command_timeout_seconds'])
        record['development']=feedback
        result['attempts'].append(record)
        save(folder/'feedback.json',feedback)
        save(run/'result.json',result)
        print('attempt',attempt,feedback['status'],flush=True)
        if feedback['status']=='passed':
            result['selected_attempt']=attempt
            result['selected_candidate_sha256']=digest(folder/'candidate.rs')
            # Freeze selection before opening or executing the held-out suite.
            result['status']='candidate_frozen'
            save(run/'result.json',result)
            final=json.loads((batch/'data/final.json').read_text())
            result['final']=evaluate(binary,final,folder/'final-execution.json',config['command_timeout_seconds'])
            result['status']='passed' if result['final']['status']=='passed' else 'final_failed'
            break
        messages += [dict(role='assistant',content=content),dict(role='user',content=
                     'Fix your candidate using this development feedback. Return the complete candidate.rs only.\n'+
                     json.dumps(feedback,ensure_ascii=False))]
    else:
        result['status']='attempt_budget_exhausted'
    result['finished_at']=now()
    save(run/'result.json',result)
    save(EXP/'results'/(batch.name+'.json'),dict(batch_id=batch.name,task=config,run=result,
                                              baseline_checks=ready['baseline_checks']))
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','generate'])
    parser.add_argument('--batch-id',default='20261023-01-list-index-smoke')
    parser.add_argument('--key-file',type=Path,default=Path.home()/'.config/isabelle2rust/deepseek.env')
    args=parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',args.batch_id):
        parser.error('batch ID must be a simple directory name')
    batch=EXP/'runs'/args.batch_id
    batch.mkdir(parents=True,exist_ok=True)
    if args.action=='prepare':
        prepare(batch,json.loads(CONFIG.read_text()))
    else:
        generate(batch,args.key_file.expanduser())


if __name__=='__main__':
    main()

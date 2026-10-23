#!/usr/bin/env python3
"""Build one offline HTML dashboard from recorded experiment summaries.

Reads only experiment summaries, documented plans, prompts and saved candidates.
It does not read API credentials or issue model requests.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
UI = EXP/'dashboard'
REPO = EXP.parent


def text_at(relative, path_base='experiments'):
    base = REPO if path_base == 'repository' else EXP
    path = (base/relative).resolve()
    allowed = [EXP.resolve(), (REPO/'test/afp').resolve()]
    if not any(path.is_relative_to(root) for root in allowed):
        raise ValueError('Artifact outside experiment and AFP directories')
    return path.read_text() if path.is_file() else None


def latest_measurements(views):
    """Latest per exact implementation and workload, retaining rows not remeasured."""
    result = {}
    for view in sorted(views, key=lambda v:v['sequence']):
        for row in view['rows']:
            key = (row['implementation'], row['code_sha256'], row['scope'], row['length'], row['query'], row['values'])
            result[key] = dict(row)
    return list(result.values())


def build_cases(batches):
    """Project immutable run records into persistent cases and case-local rounds."""
    catalog = json.loads((EXP/'cases.json').read_text())
    by_batch = {b['id']: b for b in batches}
    cases = []
    for spec in catalog['cases']:
        case = dict(spec, rounds=[], implementations=[])
        for item in spec['rounds']:
            original = by_batch[item['batch_id']]
            runs = [dict(r, legacy_reference=r['reference'], round_id=item['id'],
                         reference=f"{spec['id']}/{item['id']}/{r['run_id']}")
                    for r in original['runs'] if r['task'] == spec['id']]
            for addition_path in item.get('additions', []):
                saved = json.loads(text_at(addition_path))
                result = saved['result']
                code = text_at(saved['code_path'], 'repository')
                usage = {k:sum(a.get('usage', {}).get(k, 0) for a in result.get('attempts', []))
                         for k in ['prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens']}
                runs.append(dict(result, task=spec['id'], run_id=saved['run_id'], round_id=item['id'],
                    reference=f"{spec['id']}/{item['id']}/{saved['run_id']}", code=code,
                    code_path=saved['code_path'], code_sha256=saved['code_sha256'],
                    code_verified=hashlib.sha256(code.encode()).hexdigest() == saved['code_sha256'],
                    usage=usage, cost_estimate=result.get('estimated_peak_cost_usd'),
                    implementation_kind=saved.get('kind', 'llm'), own_config=saved['config'],
                    implementation_name=saved.get('name'), record_source=addition_path))
            costs = [r['cost_estimate'] for r in runs]
            scoped = dict(original, round_id=item['id'], round_title=item['title'], runs=runs,
                          tasks=[spec['id']], baselines={spec['id']:original['baselines'].get(spec['id'], {})},
                          cost=sum(costs) if all(c is not None for c in costs) else None,
                          measurements=[dict(source=p, record=json.loads(text_at(p))) for p in item.get('measurements', [])])
            if (scoped.get('performance') or {}).get('protocol', {}).get('task') != spec['id']:
                scoped['performance'] = None
            case['rounds'].append(scoped)
            case['implementations'].extend(dict(r, implementation_id=r['reference'], kind=r.get('implementation_kind', 'llm'),
                                                name=r.get('implementation_name') or f"{item['id']} / {r['run_id']}") for r in runs)
        baseline_path = f"{spec['source_root']}/baseline.json"
        baseline = json.loads(text_at(baseline_path, 'repository'))
        shared = []
        for kind, name in [('stage1','Stage 1'), ('stage2','Stage 2'), ('ocaml','OCaml')]:
            files = []
            for f in baseline['files']:
                if f'/{kind}/' not in f['path']:
                    continue
                code = text_at(f['path'], 'repository')
                files.append(dict(path=f['path'], code=code, sha256=f['sha256'],
                                  verified=hashlib.sha256(code.encode()).hexdigest() == f['sha256']))
            primary = next((f for f in files if f['path'].endswith(('Reference.rs','reference.ml'))), files[0])
            shared.append(dict(implementation_id=kind, kind='baseline', name=name, files=files,
                               code=primary['code'], code_path=primary['path'], code_sha256=primary['sha256'],
                               code_verified=all(f['verified'] for f in files)))
        case['implementations'] = shared + case['implementations']
        views = []
        for registered in spec.get('performance_records', []):
            raw_record = text_at(registered['source'])
            if registered.get('sha256') and hashlib.sha256(raw_record.encode()).hexdigest() != registered['sha256']:
                raise ValueError('Recorded measurement file has changed')
            record = json.loads(raw_record)
            round_id = registered['round_id']
            if registered['kind'] == 'batch':
                measured = record['performance']
                rows = []
                for row in measured['aggregates']:
                    implementation = row['implementation']
                    if implementation.startswith('run-'):
                        implementation = f"{spec['id']}/{round_id}/{implementation}"
                    rows.append(dict(row, implementation=implementation, values='small',
                                     iterations=measured['protocol']['iterations']))
                protocol = measured['protocol']
                measured_at = None
            elif registered['kind'] == 'diagnostic':
                candidate = next(r for r in case['implementations']
                                 if r.get('round_id') == round_id and r.get('run_id') == registered['candidate_run_id'])
                expected = [sha for path,sha in record['source_sha256'].items() if '/llm/' in path]
                if candidate['code_sha256'] not in expected:
                    raise ValueError('Measurement candidate does not match recorded source hash')
                for kind, suffix in [('stage2','/stage2/src/Reference.rs'), ('ocaml','/ocaml/reference.ml')]:
                    impl = next(i for i in shared if i['implementation_id'] == kind)
                    if impl['code_sha256'] not in [sha for path,sha in record['source_sha256'].items() if path.endswith(suffix)]:
                        raise ValueError('Measurement baseline hash mismatch: '+kind)
                operations = {'candidate_e2e':candidate['implementation_id'], 'stage2_e2e':'stage2', 'ocaml_e2e':'ocaml'}
                rows = [dict(implementation=operations[r['operation']], length=r['n'], query=r['mode'], values=r['values'],
                             median_ns=r['median_ns'], min_ns=min(r['ns_per_call']), max_ns=max(r['ns_per_call']),
                             successful_rounds=len(r['ns_per_call']), iterations=r['iterations'])
                        for r in record['rows'] if r['operation'] in operations]
                protocol = record['protocol']
                measured_at = record['created']
            elif registered['kind'] == 'normalized':
                rows, protocol, measured_at = record['rows'], record['protocol'], record['measured_at']
            else:
                raise ValueError('Unknown measurement kind')
            view = dict(registered, reference=f"{spec['id']}/{round_id}/{registered['id']}",
                        rows=rows, protocol=protocol, measured_at=measured_at,
                        measured_ids=list(dict.fromkeys(r['implementation'] for r in rows)))
            known = {i['implementation_id']:i['code_sha256'] for i in case['implementations']}
            for row in rows:
                if row['implementation'] not in known:
                    raise ValueError('Measurement references an unknown implementation')
                if registered['kind'] == 'normalized' and row.get('code_sha256') != known[row['implementation']]:
                    raise ValueError('Measurement code hash mismatch')
                row.update(measurement_id=view['id'], measurement_ref=view['reference'],
                           measurement_round=round_id, sequence=view['sequence'], scope=view['scope'],
                           code_sha256=known[row['implementation']], measured_at=measured_at)
            views.append(view)
        if len({v['id'] for v in views}) != len(views) or len({v['sequence'] for v in views}) != len(views):
            raise ValueError('Measurement IDs and sequence numbers must be unique within a case')
        case['performance_views'] = sorted(views, key=lambda v:v['sequence'])
        case['performance_latest'] = latest_measurements(case['performance_views'])
        cases.append(case)
    return cases


def get_data():
    batches, notices = [], []
    registry_path = EXP/'registry.json'
    entries = json.loads(registry_path.read_text())['experiments'] if registry_path.exists() else []
    registered = {e['batch_id']:e for e in entries}
    for path in sorted((EXP/'results').glob('*.json')):
        try:
            raw = json.loads(path.read_text())
        except (ValueError, OSError) as error:
            notices.append(f'{path.name}: {type(error).__name__}')
            continue
        if not isinstance(raw, dict) or not raw.get('batch_id') or not ('run' in raw or 'runs' in raw):
            continue
        identity = registered.get(raw['batch_id'], {})
        config = raw.get('config', raw.get('task', {}))
        source_runs = raw.get('runs', [raw['run']] if 'run' in raw else [])
        default_task = ('list-index' if 'list-index' in config.get('task_id', '')
                        else config.get('target_constant', '未命名任务'))
        runs = []
        rates = config.get('peak_usd_per_million', {})
        for n, original in enumerate(source_runs, 1):
            run = {k:v for k,v in original.items() if k != 'binary'}
            run['task'] = original.get('task', default_task)
            run['run_id'] = original.get('run_id', f'run-{n:03d}')
            attempts = run.get('attempts', [])
            run['usage'] = {key:sum(a.get('usage', {}).get(key,0) for a in attempts)
                            for key in ['prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens']}
            run['cost_estimate'] = original.get('estimated_peak_cost_usd')
            if run['cost_estimate'] is None and 'input_cache_miss' in rates and 'output' in rates:
                run['cost_estimate'] = (run['usage']['prompt_tokens']*rates['input_cache_miss']+
                                        run['usage']['completion_tokens']*rates['output'])/1e6
            entry = next((c for c in raw.get('candidates', [])
                          if c.get('task')==run['task'] and c.get('run_id')==run['run_id']), None)
            code_path = entry.get('file') if entry else f'results/candidates/{raw["batch_id"]}.rs'
            run['code'] = text_at(code_path, entry.get('path_base', 'experiments') if entry else 'experiments')
            run['reference'] = f"{identity.get('experiment_id', raw['batch_id'])}/{run['task']}/{run['run_id']}"
            run['code_path'] = code_path if run['code'] is not None else None
            run['code_sha256'] = original.get('candidate_sha256', original.get('selected_candidate_sha256'))
            run['code_verified'] = (hashlib.sha256(run['code'].encode()).hexdigest()==run['code_sha256']) if run['code'] and run['code_sha256'] else None
            if run['code_verified'] is False:
                notices.append(f'{raw["batch_id"]}/{run["run_id"]}: 候选文件哈希与记录不一致')
            runs.append(run)
        tasks = list(dict.fromkeys(r['task'] for r in runs))
        baselines = {task:dict(checks=value.get('baseline_checks', {}),negative_control=value.get('negative_control'))
                     for task,value in raw.get('baselines', {}).items()}
        if not baselines and raw.get('baseline_checks'):
            baselines[default_task] = dict(checks=raw['baseline_checks'],negative_control=None)
        preflight = EXP/'results'/f'{raw["batch_id"]}-preflight.json'
        environment = raw.get('environment', {})
        if not environment and preflight.exists():
            previous = json.loads(preflight.read_text())
            environment = previous.get('environment', {})
            if default_task in baselines:
                control = previous.get('negative_control', {})
                baselines[default_task]['negative_control'] = control.get('result', control)
        # Keep portable environment facts, not host-local filesystem paths.
        environment = {k:environment[k] for k in ['os','machine','rustc','ocaml','isabelle','repo_head','rustlightast_head'] if k in environment}
        cost = raw.get('ledger', {}).get('estimated_peak_cost_usd')
        if cost is None:
            known = [r['cost_estimate'] for r in runs if r['cost_estimate'] is not None]
            cost = sum(known) if len(known)==len(runs) else None
        snapshot_path = EXP/'results'/'snapshots'/f'{raw["batch_id"]}.json'
        snapshot = json.loads(snapshot_path.read_text()) if snapshot_path.exists() else None
        if snapshot and snapshot['config'] != config:
            notices.append(f'{raw["batch_id"]}: 汇总配置与历史快照不一致')
        batches.append(dict(snapshot=snapshot, id=raw['batch_id'],experiment_id=identity.get('experiment_id'),
                            artifact_root=identity.get('artifact_root'), display_name=identity.get('title'),config=config,runs=runs,tasks=tasks,baselines=baselines,
                            performance=raw.get('performance'),environment=environment,cost=cost,
                            source='results/'+path.name,notes='batches/'+raw['batch_id']+'.md',
                            prompts={t:text_at('prompts/'+raw['batch_id']+'-'+t+'.txt') for t in tasks}))
    documents = {}
    paths = [EXP/'decisions.md']
    for folder in ['plans','batches','notes']:
        paths.extend(sorted((EXP/folder).glob('*.md')))
    for path in paths:
        if path.is_file():
            documents[str(path.relative_to(EXP))] = path.read_text()
    return dict(schema_version=1,generated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                batches=batches,cases=build_cases(batches),documents=documents,notices=notices,
                research=json.loads((UI/'research.json').read_text()))


def build():
    data = json.dumps(get_data(), ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&','\\u0026')
    html = (UI/'template.html').read_text()
    html = html.replace('/* DASHBOARD_STYLE */', (UI/'style.css').read_text())
    html = html.replace('/* DASHBOARD_DATA */', data)
    html = html.replace('/* DASHBOARD_APP */', (UI/'app.js').read_text())
    output = UI/'index.html'
    output.write_text(html)
    return output


if __name__ == '__main__':
    print(build())

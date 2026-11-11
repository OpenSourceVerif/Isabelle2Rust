"""Read new run records through the migrated workbench's existing data contract."""
from __future__ import annotations

import json
import hashlib
import re
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .common import ROOT,digest,now,read
from .baselines import language_results,fingerprint


def source_record(path):
    if not path or not Path(path).is_file():return {'code':'','code_path':path,'code_verified':None,'files':[]}
    p=Path(path)
    return {'code':p.read_text(),'code_path':str(p),'code_sha256':digest(p),'code_verified':True,
            'files':[{'path':str(p),'sha256':digest(p)}]}


def crate_record(crate):
    if not crate:return source_record(None)
    root=Path(crate)
    paths=sorted((root/'src').rglob('*.rs'))
    if not paths:return source_record(None)
    return {'code':'\n\n'.join('// FILE: '+str(p.relative_to(root))+'\n'+p.read_text() for p in paths),
            'code_path':str(root),'code_sha256':digest(root/'src/lib.rs') if (root/'src/lib.rs').exists() else None,
            'code_verified':True,'files':[{'path':str(p),'sha256':digest(p)} for p in paths]}


def adaptation_label(adaptation,kind):
    labels=[]
    for decision in adaptation.get('decisions',[]):
        scopes=' '.join(decision.get('scope',[]))
        matches=(re.search(r'Nat\.nat|Int\.int|integer|Uint\d*\.uint\d*|Word\.word',scopes)
                 if kind=='numeric' else 'List.list' in scopes)
        if matches and (decision.get('representation') or decision.get('rust_type')):
            value=(decision.get('representation') or decision['rust_type']).replace('num_bigint::','')
            if value not in labels:labels.append(value)
    label=' + '.join(labels) or 'LLM 自动选择'
    return label if len(label)<=96 else label[:93]+'…'


def outcome(result,trial):
    status=result['status'];attempts=result.get('attempts',[])
    if status=='not_run':return '尚未运行'
    if result.get('phase')=='recovery_pending':return '已保留中断记录；等待继续执行'
    if status=='passed':return ('通过最终差分测试；已完成算法计时' if result.get('performance',{}).get('scope')=='kernel' else '通过最终差分测试；历史端到端耗时不作为算法性能')
    if status=='planning_failed':
        failures=sorted((trial/'diagnostics/planning').glob('plan-*/failure.json'))
        if failures:
            evidence=read(failures[-1]).get('evidence')
            if isinstance(evidence,dict) and evidence.get('check',{}).get('status')=='passed' and (evidence.get('clippy') or {}).get('status')=='failed':
                return '尚未生成算法 Rust：adapter 探针通过，旧版 Clippy 严格门槛阻断'
        return '停在预处理规划；尚未生成算法 Rust'
    if status=='attempt_budget_exhausted':
        last=attempts[-1].get('development',{}).get('status') if attempts else None
        return '候选仍未通过编译/接口检查；未进入最终测试' if last in {'compile_failed','plan_contract_failed'} else '生成/修复预算结束；未进入最终测试'
    if status=='interrupted':return '接入运行已中断；不作为完成的实验结论'
    if status=='running':return '正在运行：'+result.get('phase','')
    return result.get('error') or status


def registry_baselines():
    result=[]
    for path in (ROOT/'data/baselines').glob('*/baseline.json'):
        record=read(path);record['measurements']=sorted([read(p) for p in (path.parent/'measurements').glob('*.json')],key=lambda x:x.get('measured_at',''))
        result.append(record)
    return sorted(result,key=lambda r:r['created_at'])



BACKENDS = {
    'go': ('Go', 'AFP Go · math/big', 'isabelle/exported/**/Candidate/exported.go'),
    'haskell': ('Haskell', 'GHC · Integer', 'Candidate.raw.hs'),
    'scala': ('Scala', 'Scala/JVM · BigInt', 'Candidate.scala'),
    'sml': ('SML', 'Poly/ML · IntInf', 'Candidate.ML'),
}


def add_language_baselines(cases, registry, language):
    """Present optional backends with the same baseline card/data contract."""
    title,container,source_glob=BACKENDS[language]
    sources={b['id']:b['identity']['sources'] for b in registry}
    latest={};cards={}
    paths=language_results(language,ROOT)
    paths += [p for path in list(paths) for p in (path.parent/'measurements').glob('*/result.json')]
    records=sorted(((path,read(path)) for path in paths),key=lambda item:item[1].get('started_at',''))
    for path,record in records:
        if record.get('status') not in {'passed','failed'}:continue
        key=(record['case'],record['baseline_id'])
        cards[key]=(path,record)
        perf=record.get('performance',{})
        measurement=fingerprint([perf.get('workload'),perf.get('protocol')])
        latest[(*key,measurement)]=(path,record)
    for (case_id,base_id,_),(path,r) in latest.items():
        if case_id not in cases:continue
        case=cases[case_id]
        current=cards[(case_id,base_id)]
        if current[1]['status']=='failed' and path!=current[0]:continue
        if r['status']=='failed':
            if path!=current[0]:continue
            source=r.get('reference',{}).get('source') or next(path.parent.glob(source_glob),None)
            case['implementations'].append({'implementation_id':base_id+':'+language,'kind':'baseline',
                'name':'Isabelle → '+title,'tags':['BASELINE','失败'],'baseline_id':base_id,
                'round_id':'baseline','numeric_profile':'shared','container':container,
                'status':'failed','created_at':r['started_at'],'origin':str(path),'measured_at':None,
                'measurement':None,'measurement_missing':True,'error':r.get('error'),
                'record_path':str(path),'final':{'status':'failed'},**source_record(source)})
            continue
        ref=r['reference'];perf=r['performance']
        if not Path(ref['binary']).is_file() or digest(ref['binary'])!=ref['binary_sha256']:continue
        if not Path(ref['source']).is_file() or digest(ref['source'])!=ref['sha256']:continue
        iid=base_id+':'+language;mid=r.get('measurement_id',path.parent.name+'/'+case_id)
        if path==current[0]:case['implementations'].append({'implementation_id':iid,'kind':'baseline',
            'name':'Isabelle → '+title,'tags':['BASELINE','固定基线','复用'],'baseline_id':base_id,
            'round_id':'baseline','numeric_profile':'shared','container':container,
            'status':'passed','created_at':r['started_at'],'origin':str(path),
            'measured_at':perf['measured_at'],'measurement_origin':perf['origin'],
            'measurement':perf['summary'][language],'record_path':str(path),'final':{'status':'passed','checks':r['checks']},
            **source_record(ref['source'])})
        workload=perf['workload'];key=hashlib.sha256(json.dumps(workload,separators=(',',':')).encode()).hexdigest()[:10]
        label=str(max((abs(x).bit_length() for x in workload),default=0))+' 位以内 · 输入 '+key
        def row(name,measurement):
            sample=measurement['summary'][name]
            return {'implementation':base_id+':'+name,'kind':'baseline',**{k:sample[k] for k in ['median_ns','min_ns','max_ns']},
                'successful_rounds':len(sample['samples']),'scope':'kernel','length':len(workload),'query':'fixed_workload','values':label,
                'measurement_id':mid if name==language else measurement['id'],'measurement_round':'baseline','numeric_profile':'shared',
                'reused':True,'measured_at':measurement['measured_at'],'origin':measurement['origin']}
        backend_row=row(language,perf)
        for view in case['performance_views']:
            if view['protocol'].get('options')!=perf['protocol']['options']:continue
            if any(x['implementation'].endswith(':ocaml')
                   and sources.get(x['implementation'].rsplit(':',1)[0])==r['identity']['sources']
                   and x['values']==label and x['scope']=='kernel' for x in view['rows']):
                view['rows'].append(dict(backend_row))
        previous=read(r['reference_measurement'])
        case['performance_views'].append({'id':mid,'round_id':'baseline','rows':[row(n,previous) for n in ['ocaml','stage2']]+[backend_row],
            'measured_at':perf['measured_at'],'sequence':len(case['performance_views'])+1,'source':perf['origin'],'reference':str(path),
            'protocol':{**perf['protocol'],'comparison':title+' measured separately; OCaml and Stage 2 reuse recorded measurements and timestamps.'}})


def overall_progress(studies, cases):
    """Overlay only explicitly related reruns; never select the best historical score."""
    if not studies:return None
    by_id={s['id']:s for s in studies};chain=[];current=studies[-1]
    while current and current['id'] not in {s['id'] for s in chain}:
        chain.append(current)
        current=by_id.get(current.get('parent_study'))
    chain.reverse();slots={};modes=[]
    for study in chain:
        for trial in study['trials']:
            key=(trial['case'],trial['variant'],trial['repeat'])
            previous=slots.get(key)
            slots[key]={**trial,'source_study':study['id']}
            if previous:slots[key]['previous']={k:previous[k] for k in ('status','source_study','implementation')}
            mode=(trial['variant'],trial['repeat'])
            if mode not in modes:modes.append(mode)
    rows=[]
    for case in cases.values():
        for variant,repeat in modes:
            rows.append(slots.get((case['id'],variant,repeat),{
                'case':case['id'],'variant':variant,'repeat':repeat,
                'title':case['title']+' · '+variant,'status':'not_run',
                'conclusion':'未纳入当前实验计划；未执行','source_study':None,'implementation':None}))
    return {'trials':rows,'planned':len(rows),'source_studies':[s['id'] for s in chain],
            'passed':sum(t['status']=='passed' for t in rows),
            'running':sum(t['status']=='running' for t in rows),
            'not_run':sum(t['status']=='not_run' for t in rows),
            'stopped':sum(t['status'] not in {'passed','running','not_run'} for t in rows)}


def dataset():
    cases={};studies=[];registry=registry_baselines()
    descriptions={'list-index':'首次/末次索引与谓词查找','skew-heap':'斜堆合并与树形输出',
                  'splay-tree':'伸展树插入、查找与删除','karatsuba-sqrt':'任意精度平方根与余数',
                  'shear-sort':'矩阵排序与蛇形遍历','list-interleaving':'带谓词的列表交错判断',
                  'ackermann':'Ackermann 递归计算','transitive-closure':'有限图可达性与工作列表顺序'}
    for path in sorted((ROOT/'catalog/cases').glob('*/case.json')):
        c=read(path)
        cases[c['id']]={'id':c['id'],'title':c['title'],'target':descriptions.get(c['id'],c['contract']),'source_root':str(path.parent),
                       'rounds':[],'implementations':[],'performance_views':[],'baseline_records':[]}
    for record in registry:
        if record['case'] not in cases:continue
        case=cases[record['case']];case['baseline_records'].append({k:v for k,v in record.items() if k not in {'references','identity'}})
        for name in ['ocaml','stage2']:
            ref=record['references'][name];kernel_measurements=[m for m in record['measurements'] if m.get('scope')=='kernel'];measured=kernel_measurements[-1] if kernel_measurements else None
            case['implementations'].append({'implementation_id':record['id']+':'+name,'kind':'baseline',
                'name':'OCaml' if name=='ocaml' else 'Rust Stage 2','tags':['BASELINE','固定基线','复用'],
                'baseline_id':record['id'],'round_id':'baseline','numeric_profile':'shared','container':'参考实现',
                'status':'passed','created_at':record['created_at'],'origin':record['origin'],'measured_at':measured.get('measured_at') if measured else None,
                'measurement_origin':measured.get('origin') if measured else None,
                'measurement':measured['summary'][name] if measured else None,'historical_timing_only':any(m.get('scope')=='end_to_end' for m in record['measurements']) and not bool(measured),'measurement_missing':not bool(measured),
                'record_path':ref['baseline_record'],'final':{'status':'not_run','note':'输入级参考结果见基线缓存'},
                **source_record(ref['source'])})
    for study in sorted((ROOT/'data/runs').glob('*/study.json'),key=lambda p:read(p.parent/'summary.json').get('started_at','')):
        directory=study.parent;spec=read(study);summary=read(directory/'summary.json');sid=directory.name
        review_path=directory/'review-findings.json'
        review_findings=read(review_path).get('findings',[]) if review_path.exists() else []
        study_view={'id':sid,'title':summary.get('display_title',spec['spec'].get('description',spec['spec']['id'])),'status':summary['status'],
                    'started_at':summary['started_at'],'finished_at':summary.get('finished_at'),'planned':len(spec['tasks']),'trials':[],
                    'review_findings':review_findings}
        # Older frozen recovery specs declare the parent in their description.
        parent=re.search(r'完整轮次见\s+([\w.-]+)',spec['spec'].get('description',''))
        study_view['parent_study']=spec['spec'].get('recovery_of') or (parent.group(1) if parent else None)
        for task in spec['tasks']:
            case=cases[task['case']];trial=directory/'trials'/task['id'];path=trial/'result.json'
            result_exists=path.exists()
            r=read(path) if result_exists else {'status':'not_run'}
            effective=trial/'diagnostics/effective-config.json'
            if not result_exists and summary['status']=='running' and effective.exists():
                r={'status':'running','phase':'preprocessing','config':read(effective)}
            cfg=r.get('config',{});attempts=r.get('attempts',[])
            workflow=r.get('workflow') or cfg.get('generation',{}).get('workflow') or spec['spec'].get('base',{}).get('generation',{}).get('workflow')
            round_=next((x for x in case['rounds'] if x['round_id']==sid),None)
            if round_ is None:
                round_={'round_id':sid,'round_title':study_view['title'],'id':sid,'experiment_id':sid,'status':summary['status'],
                    'runs':[],'tasks':[task['case']],'config':{'model':cfg.get('model',{}).get('name'),'study':spec['spec'],
                    'route':'G0 → 程序适配 → G1 → 所有权候选 → 测试修复 → 可选源优化' if cfg.get('generation',{}).get('max_ownership_candidates') else 'Thingol → 适配 → 生成与测试','candidate_selection':'开发测试通过后比较候选算法耗时，再作独立最终评测' if cfg.get('generation',{}).get('max_ownership_candidates') else '开发通过后最终评测'},
                    'baselines':{},'environment':cfg.get('tools',{}),'prompts':{},'cost':None,'snapshot':None}
                case['rounds'].append(round_)
            adaptation=r.get('adaptation') or r.get('preprocessing',{}).get('adaptation',{});auto=cfg.get('preprocessing',{}).get('mode')=='auto'
            numeric=(adaptation_label(adaptation,'numeric') if adaptation else '未完成适配') if auto else cfg.get('representation',{}).get('numeric','bigint')
            container=(adaptation_label(adaptation,'sequence') if adaptation else '未完成适配') if auto else 'Vec'
            if workflow in {'knowledge-v5','source-v6','segmented-v7','segmented-v8'}:
                mode=cfg.get('preprocessing',{}).get('numeric_mode','unknown')
                numeric=mode+' · '+str(r.get('numeric_representation','待生成确认'))
                round_['config']['route']='算法导出 → 语义分析 → 适配与 Rust 生成／代码反馈 → 独立测试连接 → 测试修复'
                round_['config']['candidate_selection']='主候选优先；有实际替代选择才追加；仅比较既有通过候选'
                if workflow=='source-v6':
                    round_['config']['route']='自有源图 → Rust 生成 → quality-refine → 编译修复 → 行为验证与修复 → 最终评测'
                    round_['config']['candidate_selection']='单主候选；独立打印器适配已移出生成路径'
                if workflow in {'segmented-v7','segmented-v8'}:
                    round_['config']['route']='自有源图与分割 → 全局语义适配及 Rust 配置 → 依赖优先逐单元翻译、精化与累计编译 → 整体审查 → 独立源契约与双参考测试 → 最终评测'
                    round_['config']['candidate_selection']='开发精化可使用性能反馈；保留集独立；修订后重验受影响单元'
                    container='按实际单元接口表示（见代码与源对应）'
            crate=r.get('output') or next((a.get('crate') for a in reversed(attempts) if a.get('crate')),None)
            if workflow in {'segmented-v7','segmented-v8'} and not crate and (trial/'diagnostics/cumulative/src/lib.rs').exists():
                crate=str(trial/'diagnostics/cumulative')
            conclusion=outcome(r,trial)
            view_status='not_run' if r.get('phase')=='recovery_pending' else r['status']
            matching_findings=[f for f in review_findings if f.get('case')==task['case'] and f.get('variant',task['variant'])==task['variant']]
            if any(f.get('invalidates_result') for f in matching_findings):
                view_status='review_failed';conclusion='补充审查未通过：'+'；'.join(f['summary'] for f in matching_findings if f.get('invalidates_result'))
            impl={'implementation_id':task['id']+'@'+sid,'run_id':task['id'],'name':task['variant']+' · '+str(task['repeat']),
                'kind':'llm','tags':['LLM 生成' if result_exists else '计划任务',task['variant']]+(['工程验证'] if summary.get('classification')=='engineering-validation' else []),'candidate_generated':bool(crate),'task':task['case'],'round_id':sid,'reference':str(path) if result_exists else str(study),'result_exists':result_exists,
                'status':view_status,'conclusion':conclusion,'numeric_profile':numeric,'container':container,
                'attempts':[{**{k:v for k,v in a.items() if k!='prompt'},
                             'replayed_checkpoint':bool(a.get('crate') and (Path(a['crate'])/'checkpoint-replay.json').exists())}
                            for a in attempts],'selected_attempt':r.get('selected_attempt'),
                'usage':r.get('usage',{'total_tokens':0}),'cost_estimate':None,'started_at':r.get('started_at'),
                'final':r.get('final',{'status':'not_run'}),'model_calls':r.get('model_calls'),
                'own_config':{**cfg,'phase':r.get('phase'),'unit_progress':{k:r.get(k) for k in ['units_completed','units_total','active_unit']} if workflow in {'segmented-v7','segmented-v8'} else None,'preprocessing':r.get('preprocessing'),'source_optimization':r.get('source_optimization'),
                              'experiment_input_domain':r.get('experiment_input_domain'),
                              'review_findings':[f for f in review_findings if f.get('case')==task['case']],
                              'ownership_candidates':r.get('ownership_candidates'),'ownership_selection':r.get('ownership_selection'),'recovery':r.get('recovery'),'baseline':r.get('baseline'),'error':r.get('error'),'error_evidence':r.get('error_evidence')},
                'prompt':attempts[0].get('prompt','')[:120000] if attempts else '',**crate_record(crate)}
            round_['runs'].append(impl);case['implementations'].append(impl)
            study_view['trials'].append({'case':task['case'],'title':case['title']+' · '+task['variant'],'status':view_status,'conclusion':conclusion,
                'variant':task['variant'],'repeat':task['repeat'],
                'candidate_generated':bool(crate),'stop_stage':'compile' if view_status not in {'passed','running','not_run'} and attempts and attempts[-1].get('development',{}).get('status') in {'compile_failed','plan_contract_failed'} else None,'final_count':r.get('final',{}).get('count'),
                'implementation':impl['implementation_id'],'clippy_policy':cfg.get('testing',{}).get('clippy'),
                'source_optimization':cfg.get('source_optimization',{}).get('enabled',False)})
            refs=r.get('references') or {};checks={}
            for name in ['ocaml','stage2']:
                checks[name]={'final':{'status':'passed','count':r['final']['count']} if name in r.get('final',{}).get('references',{}) else {'status':'not_run'}}
            round_['baselines'][task['case']]={'checks':checks}
            if not r.get('performance') or any(f.get('invalidates_result') or f.get('invalidates_performance') for f in matching_findings):continue
            perf=r['performance'];measurement=task['id']+'@'+sid+'-performance';rows=[]
            workload_key=hashlib.sha256(json.dumps(perf['workload'],separators=(',',':')).encode()).hexdigest()[:10]
            workload_label=str(max((abs(x).bit_length() for x in perf['workload']),default=0))+' 位以内 · 输入 '+workload_key
            if 'candidate' in perf['summary']:
                sample=perf['summary']['candidate']
                rows.append({'implementation':impl['implementation_id'],'kind':'llm','median_ns':sample['median_ns'],'min_ns':sample['min_ns'],
                    'max_ns':sample['max_ns'],'successful_rounds':len(sample['samples']),'scope':perf.get('scope','end_to_end'),'length':len(perf['workload']),
                    'query':'fixed_workload','values':workload_label,'measurement_id':measurement,'measurement_round':sid,
                    'numeric_profile':numeric,'measured_at':r.get('finished_at'),'reused':False,'code_sha256':impl.get('code_sha256')})
            matching=[b for b in registry if b['case']==task['case'] and (not r.get('baseline',{}).get('id') or b['id']==r['baseline']['id']) and all(b['references'][k]['sha256']==refs.get(k,{}).get('sha256') for k in ['ocaml','stage2'])]
            if matching:
                base=matching[-1]
                measurements=[m for m in base['measurements'] if m.get('scope')==perf.get('scope') and m['workload']==perf['workload'] and m['protocol']['options']==perf['protocol']['options']]
                if measurements:
                    m=measurements[-1]
                    for name in ['ocaml','stage2']:
                        s=m['summary'][name]
                        rows.append({'implementation':base['id']+':'+name,'kind':'baseline','median_ns':s['median_ns'],'min_ns':s['min_ns'],
                            'max_ns':s['max_ns'],'successful_rounds':len(s['samples']),'scope':m.get('scope','end_to_end'),'length':len(perf['workload']),
                            'query':'fixed_workload','values':workload_label,'measurement_id':m['id'],'measurement_round':'baseline',
                            'numeric_profile':'shared','reused':True,'measured_at':m['measured_at'],'origin':m['origin'],
                            'code_sha256':base['references'][name]['sha256']})
            case['performance_views'].append({'id':measurement,'round_id':sid,'rows':rows,'measured_at':r.get('finished_at'),
                'sequence':len(case['performance_views'])+1,'source':str(trial/'diagnostics/performance.json'),'reference':str(path),'protocol':perf['protocol']})
        if any(t['status']=='running' for t in study_view['trials']):study_view['status']='running'
        studies.append(study_view)
    progress=overall_progress(studies,cases)
    latest=studies[-1] if studies else None
    if latest:
        latest={**latest,'passed':sum(t['status']=='passed' for t in latest['trials']),
                'planning_stopped':sum(t['status']=='planning_failed' for t in latest['trials']),
                'compilation_stopped':sum(t.get('stop_stage')=='compile' for t in latest['trials']),
                'other_stopped':sum(t['status'] not in {'passed','planning_failed','running','not_run'} and t.get('stop_stage')!='compile' for t in latest['trials'])}
        for case in cases.values():
            case['latest_round']=latest['id']
            for impl in case['implementations']:
                if impl['kind']=='llm':impl['tags']+=['本轮新增' if impl['round_id']==latest['id'] else '历史记录']
    for case in cases.values():
        records=case['baseline_records']
        measured=[x for x in records if any(m.get('scope')=='kernel' for m in x['measurements'])]
        case['active_baseline_id']=(measured or records)[-1]['id'] if records else None
        if not case['rounds']:case['rounds']=[{'round_id':'not-run','round_title':'尚未运行','id':'not-run','runs':[],'tasks':[case['id']],'config':{},'baselines':{},'environment':{},'prompts':{},'cost':None,'snapshot':None}]
    for language in BACKENDS:add_language_baselines(cases,registry,language)
    for case in cases.values():
        # Optional backends retain independent build histories, including failures.
        active=[i['implementation_id'] for i in case['implementations']
                if i['kind']=='baseline' and i['baseline_id']==case['active_baseline_id']
                and i['implementation_id'].rsplit(':',1)[-1] not in BACKENDS]
        for language in BACKENDS:
            entries=[i for i in case['implementations'] if i['implementation_id'].endswith(':'+language)]
            if entries:active.append(max(entries,key=lambda i:i['created_at'])['implementation_id'])
        case['active_baseline_implementation_ids']=active
    from .timing_v2_workbench import apply as apply_timing_v2
    active_timing_protocol=apply_timing_v2(cases,ROOT)
    order=['list-index','skew-heap','splay-tree','karatsuba-sqrt','shear-sort','list-interleaving','ackermann','transitive-closure']
    return {'generated_at':now(),'active_timing_protocol':active_timing_protocol,'cases':[cases[k] for k in order+sorted(set(cases)-set(order)) if k in cases],
            'latest_study':latest,'overall_progress':progress,'studies':studies,'notices':[
            'LLM 生成与 BASELINE 分开记录；基线复用原计时，每条保留来源。',
            '编译与 Clippy 策略以每项实际配置为准；segmented-v7 本轮启用 Clippy 建议检查，历史配置独立保留。',
            ('v2 计时覆盖 kernel_run 与批次内结果留存；' if active_timing_protocol else '算法计时仅覆盖 kernel_run；')+
            '解析、转换、输入准备和结果编码不计时。旧端到端耗时保留为历史记录，不能作为算法性能。']+
            ['补充审查：'+f['summary'] for f in (latest or {}).get('review_findings',[])]+
            (['当前默认 kernel-v2：5 个独立进程，每进程 10 批；预热未稳定及批次时长限制见测量详情。旧 v1 计时按协议分开查看。'] if active_timing_protocol else
             ['kernel-v2 发布证据缺失或发生变化，当前仅显示历史 v1 计时。'] if (ROOT/'data/baselines/runs/timing-v2/active.json').exists() else [])}


def engineering_update():
    pointer=ROOT/'state/repair-redesign-active.json'
    if not pointer.exists():return None
    active=read(pointer);directory=Path(active['directory'])
    if not (directory/'final-verification.json').exists():return None
    verification=read(directory/'final-verification.json')
    labels={'splay-tree--arbitrary--01':('Splay arbitrary','仅声明加载；未重新验证整个算法'),
        'karatsuba-sqrt--checked--01':('Karatsuba checked','边界溢出修复；开发双参考差分通过'),
        'karatsuba-checked-support':('Karatsuba support','人工提供独立源语义测试；首个错误补丁被拦截'),
        'transitive-closure--arbitrary--01':('Transitive arbitrary','含无效审查调用；局部 VecDeque 修改通过开发差分')}
    checks=[]
    for name,(title,scope) in labels.items():
        path=directory/'targeted'/name/'result.json'
        if not path.exists():continue
        result=read(path);diffs=[]
        for patch in sorted(path.parent.glob('candidate-*/changes.diff')):
            if patch.read_text().strip():diffs.append(patch.parent.name+'\n'+patch.read_text())
        # The declaration-only diagnostic stores its actual reply separately.
        if not diffs and name.startswith('splay'):
            reply=path.parent/'adapter-01/reply.json'
            if reply.exists():diffs.append(reply.read_text())
        checks.append({'id':name,'title':title,'scope':scope,'calls':result['calls'],'usage':result['usage'],
            'passed':result.get('passed',any(x.get('status')=='adapter_loaded' for x in result.get('outcomes',[]))),
            'attempts':[{'attempt':x['attempt'],'phase':x['action_phase'],'status':x.get('development',{}).get('status'),
                'suites':[{'kind':t['kind'],'count':t['count'],'status':t['status']} for t in x.get('development',{}).get('suites',[])]} for x in result.get('attempts',[])],
            'diff':'\n'.join(diffs)})
    before=read(directory/'context-before.json')['rows'];after=read(directory/'context-final.json')['rows']
    return {'recorded_at':verification['recorded_at'],'tests':verification['tests'],'checks':checks,
        'calls':sum(x['calls'] for x in checks),'prompt_tokens':sum(x['usage']['prompt_tokens'] for x in checks),
        'completion_tokens':sum(x['usage']['completion_tokens'] for x in checks),
        'context':[{'case':a['case'],'before':a['total_characters'],'after':b['total_characters'],
            'reduction':100*(1-b['total_characters']/a['total_characters'])} for a,b in zip(before,after)],
        'report_url':'/reports/repair-redesign','default_enabled':verification['default_context_enabled']}


def html():
    template=(ROOT/'ui/template.html').read_text()
    return template.replace('/* DASHBOARD_STYLE */',(ROOT/'ui/style.css').read_text()).replace(
        '/* DASHBOARD_APP */',(ROOT/'ui/app.js').read_text()).replace('/* DASHBOARD_DATA */',
        json.dumps({**dataset(),'engineering_update':engineering_update()},ensure_ascii=False).replace('<','\\u003c')).encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path=urlsplit(self.path).path
        if path in {'/','/index.html'}:body=html();mime='text/html; charset=utf-8'
        elif path=='/api/results':body=json.dumps({**dataset(),'engineering_update':engineering_update()},ensure_ascii=False).encode();mime='application/json; charset=utf-8'
        elif path=='/reports/repair-redesign':body=(ROOT/'docs/experiment-system/22-repair-redesign.md').read_bytes();mime='text/plain; charset=utf-8'
        else:self.send_error(404);return
        self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)


def serve(port=8765):
    print(f'工作台 http://127.0.0.1:{port}/',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()

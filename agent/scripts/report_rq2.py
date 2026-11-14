"""Export an independently measured RQ2 matrix; never rewrite paper sources.

Usage: python agent/scripts/report_rq2.py --matrix RUN --output REPORT
Requires matplotlib for the two PNG/SVG figures; data exports use the stdlib.
"""
import argparse
import csv
import hashlib
import html
import json
import math
from pathlib import Path
import statistics


LABELS = {'hol-integer-gcd':'Integer GCD', 'fpp-map':'Map',
          'fpp-deq-list':'Queue drain', 'fpp-msort':'Merge sort',
          'fpp-avl-updates':'AVL updates', 'fpp-acomp':'Expr. compiler',
          'hol-eratosthenes':'Eratosthenes', 'hol-polynomial':'Polynomial',
          'hol-fibonacci':'Fibonacci', 'fpp-leftist-heap-merge':'Heap merge',
          'fpp-multip':'Multiplication', 'fpp-quicksort':'Quicksort',
          'fpp-next-listprog-endswith':'Suffix matching',
          'fpp-tree-inorder':'Tree inorder', 'fpp-next-recursion-exp':'Exponentiation'}
MODES = ['off', 'rust-only', 'full']
COLORS = {'off':'#aeb9c8', 'rust-only':'#477fbd', 'full':'#2b8b79'}
PLOT_LABELS = {'hol-integer-gcd':'GCD','fpp-map':'Map','fpp-deq-list':'Queue',
               'fpp-msort':'Merge sort','fpp-avl-updates':'AVL','fpp-acomp':'AComp',
               'hol-eratosthenes':'Sieve','hol-polynomial':'Polynomial',
               'hol-fibonacci':'Fibonacci','fpp-leftist-heap-merge':'Heap\nmerge',
               'fpp-multip':'Multip.','fpp-quicksort':'Quicksort',
               'fpp-next-listprog-endswith':'EndsWith',
               'fpp-tree-inorder':'Inorder', 'fpp-next-recursion-exp':'Power'}


def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def plot(primary, output, kind, audit_hold=False):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    fig, ax = plt.subplots(figsize=(13.5, 4.7), layout='constrained')
    modes = MODES if kind == 'numeric' else ['rust-only', 'full']
    width = .23 if len(modes) == 3 else .31
    for i, mode in enumerate(modes):
        key = mode + '-numeric' if kind == 'numeric' else mode + '-vs-off-arbitrary'
        ratios = [p['ratios'].get(key) for _, p in primary]
        values = [r['speedup'] if r else math.nan for r in ratios]
        locations = [j + (i - (len(modes)-1)/2)*width for j in range(len(primary))]
        ax.bar(locations, values, width=width*.94, color=COLORS[mode], label=mode.title(), zorder=3)
        # Draw interval endpoints directly: a percentile interval need not
        # contain the reported ratio of medians, so do not clip an errorbar.
        for x, r in zip(locations, ratios):
            if r is None:continue
            lo, hi = r['ci95']; ax.vlines(x, lo, hi, color='#26313d', linewidth=.8, zorder=4)
            ax.hlines([lo, hi], x-.035, x+.035, color='#26313d', linewidth=.8, zorder=4)
        for x, y in zip(locations, values):
            if not math.isfinite(y):
                ax.text(x,1,'N/A',ha='center',fontsize=7,rotation=90);continue
            ax.annotate(f'{y:.2f}', (x, y), xytext=(0, 4), textcoords='offset points',
                        ha='center', va='bottom', fontsize=7, rotation=0)
    ax.set_yscale('log'); ax.axhline(1, color='#303842', linewidth=1.1, zorder=2)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:g}×'))
    ax.set_xticks(range(len(primary)), [LABELS.get(c, c) for c,_ in primary], rotation=20, ha='right')
    ax.set_ylabel('Arbitrary / checked runtime' if kind == 'numeric' else 'Off / optimized runtime (arbitrary)')
    ax.grid(axis='y', which='major', color='#d9dfe5', linewidth=.6, zorder=0)
    ax.spines[['top','right']].set_visible(False)
    ax.legend(loc='upper left', ncols=len(modes), frameon=False)
    title='Numeric representation ablation' if kind == 'numeric' else 'Optimization ablation'
    ax.set_title(('AUDIT HOLD · ' if audit_hold else '')+title, loc='left', pad=16)
    lo, hi = ax.get_ylim(); ax.set_ylim(min(lo,.75), hi*1.55)
    fig.text(.99, -.015, '10 predeclared primary workloads · independent process rounds · 95% paired bootstrap intervals · higher is faster',
             ha='right', fontsize=8, color='#505a65')
    for suffix in ['png','svg']:
        fig.savefig(output / (kind + '-ablation.' + suffix), dpi=180, bbox_inches='tight')
    plt.close(fig)
    return matplotlib.__version__


def plot_matrix(primary, output, development=False, total_cases=None, audit_hold=False):
    """User's two-panel layout: one common Off+arbitrary denominator per case."""
    import matplotlib.pyplot as plt
    from i2r_agent.numeric_experiment import interval
    normalized=[]; warning_cases=set()
    for case, w in primary:
        record=json.loads(Path(w['record']).read_text());raw=record['summary']; base=raw['off-arbitrary']
        if any(set(p['warnings']) & {'batch_too_close_to_clock_resolution','warmup_not_stable'}
               for processes in record['processes'].values() for p in processes):
            warning_cases.add(case)
        for backend in ['arbitrary','checked']:
            for mode in MODES:
                key=mode+'-'+backend
                normalized.append({'case':case,'backend':backend,'mode':mode,
                                   'normalized_runtime':w['median_ns'][key]/w['median_ns']['off-arbitrary'] if key in raw else None,
                                   'ci95_low':interval(raw[key],base)[0] if key in raw else None,
                                   'ci95_high':interval(raw[key],base)[1] if key in raw else None})
    write_csv(output/'normalized-matrix.csv',normalized)
    plt.rcParams['svg.fonttype']='none';plt.rcParams['pdf.fonttype']=42
    fig,axes=plt.subplots(2,1,figsize=(7.5,4.2),sharex=True,sharey=True)
    fig.subplots_adjust(left=.075,right=.99,top=.79,bottom=.16,hspace=.34)
    maximum=max(1.04,max(r['ci95_high'] for r in normalized if r['ci95_high'] is not None)*1.13)
    names={'off':'Off','rust-only':'Rust-only','full':'Full'}
    for ax,backend,title in zip(axes,['arbitrary','checked'],['(a) Arbitrary','(b) Checked']):
        for i,mode in enumerate(MODES):
            rows=[next(r for r in normalized if r['case']==case and r['backend']==backend and r['mode']==mode) for case,_ in primary]
            x=[j+(i-1)*.24 for j in range(len(primary))]
            y=[r['normalized_runtime'] if r['normalized_runtime'] is not None else math.nan for r in rows]
            bars=ax.bar(x,y,width=.21,color=COLORS[mode],label=names[mode],zorder=3)
            for bar,(_,workload) in zip(bars,primary):
                if mode in workload.get('unchanged_modes',[]):
                    bar.set_hatch('///');bar.set_edgecolor('#53637b');bar.set_linewidth(.4)
            for at,value,row in zip(x,y,rows):
                if not math.isfinite(value):
                    ax.text(at,.012*maximum,'N/A',ha='center',va='bottom',fontsize=6,rotation=90,color='#6b7280');continue
                if mode!='off' or backend!='arbitrary':
                    ax.vlines(at,row['ci95_low'],row['ci95_high'],linewidth=.65,color='#35465d',zorder=4)
                    ax.hlines([row['ci95_low'],row['ci95_high']],at-.025,at+.025,linewidth=.65,color='#35465d',zorder=4)
                # Tiny genuine runtimes remain visible as values on a linear axis.
                if value<.04:
                    ax.text(at,.012*maximum,f'{value:.2g}',ha='center',va='bottom',fontsize=5.8,rotation=90,color='#24364e',zorder=5)
        ax.set_title(title,loc='left',fontsize=10,fontweight='bold',color='#24364e',pad=10)
        ax.axhline(1,color='#8c9bb0',linestyle=(0,(5,4)),linewidth=1.1,zorder=2)
        ax.set_ylim(0,maximum)
        step=.25 if maximum<1.6 else (.5 if maximum<3 else 1.0)
        ax.set_yticks([i*step for i in range(int(maximum/step)+1)])
        ax.grid(axis='y',color='#e1e7ee',linewidth=.8,zorder=0)
        ax.spines[['top','right','left']].set_visible(False);ax.spines['bottom'].set_color('#aeb9c8')
        ax.tick_params(axis='both',length=0,pad=6,labelsize=8.5,colors='#4d607c')
    axes[1].set_xticks(range(len(primary)),[PLOT_LABELS.get(c,c)+('†' if c in warning_cases else '') for c,_ in primary])
    count=(f'Interim: {len(primary)} / {total_cases} cases' if total_cases and total_cases!=len(primary)
           else f'{len(primary)} cases')
    fig.text(.075,.94,count+'  /  Three modes  /  Two numeric backends',fontsize=13,fontweight='bold',color='#24364e')
    prefix='Development run · ' if development else ''
    subtitle=('AUDIT HOLD · optimization comparisons require correction' if audit_hold else
              prefix+'Fresh final measurements · 95% paired process bootstrap intervals')
    fig.text(.075,.895,subtitle,fontsize=7.5,color='#ad431f' if audit_hold else '#5b6d86')
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='upper right',bbox_to_anchor=(.99,.872),ncol=3,frameon=False,fontsize=8.5)
    fig.text(.005,.48,'Normalized kernel runtime  (lower is better)',rotation=90,va='center',fontsize=9,color='#24364e')
    fig.text(.075,.065,"Within each case, all six runtimes are divided by that case's Off + arbitrary runtime.",fontsize=6.5,color='#526680')
    footer='Same linear scale. † Short-batch or warmup warnings; see raw observations and uncertainty in the report.'
    if any(w.get('unchanged_modes') for _,w in primary): footer+=' Hatched: original retained.'
    fig.text(.075,.033,footer,fontsize=6.5,color='#71829b')
    for suffix in ['png','svg','pdf']:fig.savefig(output/('rq2-matrix.'+suffix),dpi=300,bbox_inches='tight')
    plt.close(fig)


def report(matrix, output, source_increment=None, integrity_audit=None):
    data = json.loads((matrix / 'matrix.json').read_text())
    quality_path = matrix / 'baseline-quality-review.json'
    if data.get('baseline_quality_review_sha256') is not None:
        if (not quality_path.is_file() or hashlib.sha256(quality_path.read_bytes()).hexdigest() != data['baseline_quality_review_sha256']):
            raise ValueError('Sealed baseline quality review is missing or changed')
    baseline_quality = json.loads(quality_path.read_text()) if quality_path.exists() else None
    if data.get('publication_hold') or (baseline_quality and baseline_quality.get('publication_hold')):
        raise ValueError('Baseline publication hold applies uniformly to Off, Rust-only and Full; see baseline-quality-review.json')
    if not data.get('complete'): raise ValueError('Final matrix is incomplete')
    cases = data['results']; output.mkdir(parents=True, exist_ok=True)
    audit_path=Path(integrity_audit) if integrity_audit else matrix/'integrity-review.json'
    audit=json.loads(audit_path.read_text()) if audit_path.exists() else None
    if integrity_audit and audit is None:raise ValueError('Integrity audit does not exist')
    audit_hold=bool(audit and audit.get('publication_hold'))
    if audit:
        (output/'integrity-review.json').write_text(json.dumps(audit,indent=2)+'\n')
    primary = [(c['case'], {**next(w for w in c['rows'] if w['workload']==c['primary_workload']),
                           'unchanged_modes':[m for m,s in c['selections'].items() if not s['improved']]}) for c in cases]
    if len(set(c for c,_ in primary)) != len(cases): raise ValueError('Duplicate case')
    timing_rows = []; ratio_rows = []; budget_rows = []; exclusions = []; source_transforms=[];scope_reviews=[];quality=[]
    for case in cases:
        for w in case['rows']:
            raw=json.loads(Path(w['record']).read_text())
            for variant,processes in raw['processes'].items():
                for i,process in enumerate(processes):
                    quality.append({'case':case['case'],'workload':w['workload'],'variant':variant,'process_round':i+1,
                                    'measured_executable':raw.get('executable_aliases',{}).get(variant,variant),
                                    'shared_observations':raw.get('executable_aliases',{}).get(variant,variant)!=variant,
                                    'batch_size':process['batch_size'],'warmup_stable':process['warmup']['stable'],
                                    'sample_count':len(process['raw_samples']),
                                    'minimum_batch_ns':min(p['batch_ns'] for p in process['raw_samples']),
                                    'minimum_timer_probe_ns':process['clock']['minimum_positive_ns'],
                                    'empty_batch_fraction':process.get('empty_batch_fraction'),
                                    'warnings':'|'.join(process['warnings'])})
            for key, ns in w['median_ns'].items():
                mode, backend = key.rsplit('-',1)
                timing_rows.append({'case':case['case'], 'workload':w['workload'],
                                    'primary':w['workload']==case['primary_workload'],
                                    'mode':mode, 'numeric_backend':backend, 'median_ns':ns, 'raw_record':w['record']})
            for key, r in w['ratios'].items():
                ratio_rows.append({'case':case['case'], 'workload':w['workload'],
                                   'primary':w['workload']==case['primary_workload'], 'comparison':key,
                                   'speedup':r['speedup'], 'ci95_low':r['ci95'][0], 'ci95_high':r['ci95'][1]})
        for mode, s in case['selections'].items():
            source_policy=s['budget'].get('source_policy',{'calls':10,'seconds':1200,'reserve_rust_calls':12,'reserve_rust_seconds':1800}) if mode=='full' else {}
            review_path=Path(s['selected_state']).parent/'scope-review/review.json'
            scope_reviews.append({'case':case['case'],'mode':mode,'selected':s['scope_selection']['candidate'],
                                  'record':str(review_path),'review':json.loads(review_path.read_text())})
            active_attempts=[a for a in s['attempts'] if a.get('status')!='retired_full_stage_gate_defect']
            budget_rows.append({'case':case['case'], 'mode':mode, 'model_calls':s['model_calls'],
                                'charged_seconds':s['budget']['charged_seconds'],
                                'resource_wait_seconds':s['budget'].get('resource_wait_seconds',0),
                                'final_review_seconds':s['scope_selection']['seconds'],
                                'final_review_model_calls':s['scope_selection']['model_calls'],
                                'final_review_status':s['scope_selection']['status'],
                                'final_review_candidate':s['scope_selection']['candidate'],
                                'known_total_tokens':s['known_usage']['total_tokens'],
                                'unknown_usage_requests':len(s['unknown_usage_requests']),
                                'improved_during_search':s['improved'],
                                'selected_source_optimized':s['selected_source_optimized'],
                                'completed_stage':s.get('completed_stage','rust'),
                                'stage_schema':s.get('stage_schema',1),
                                'scope_review_phase':'before_acceptance' if s.get('stage_schema')==2 else 'final',
                                'source_phase_calls':s.get('source_stage',{}).get('model_calls',0),
                                'source_call_cap':source_policy.get('calls'),
                                'source_seconds_cap':source_policy.get('seconds'),
                                'rust_reserved_calls':source_policy.get('reserve_rust_calls'),
                                'rust_reserved_seconds':source_policy.get('reserve_rust_seconds'),
                                'source_phase_seconds':s.get('source_stage',{}).get('seconds',0),
                                'source_phase_stop':s.get('source_stage',{}).get('stop'),
                                'source_attempts':sum(a.get('action')=='source' for a in active_attempts),
                                'source_proofs_passed':sum(a.get('status')=='source_proved' for a in active_attempts),
                                'source_candidates_accepted':sum(a.get('status')=='accepted' and a.get('source_optimized',False) for a in active_attempts),
                                'retired_attempts':len(s['attempts'])-len(active_attempts), 'stop':s['stop']})
            if s['selected_source_optimized']:
                state=json.loads(Path(s['selected_state']).read_text())
                source_transforms.append({'case':case['case'],'mode':mode,
                                          'proof':state['bundle']['source_equivalence'],
                                          'selected_state':s['selected_state'],
                                          'selected_state_sha256':s['selected_state_sha256']})
        validated = json.loads((matrix / case['case'] / 'validation.json').read_text())
        for variant, lanes in validated['lanes'].items():
            for lane in lanes:
                if lane['range_exclusions']:
                    exclusions.append({'case':case['case'], 'variant':variant, 'lane':lane.get('lane'),
                                       'inputs':lane['range_exclusions']})
    write_csv(output / 'timings.csv', timing_rows)
    write_csv(output / 'speedups.csv', ratio_rows)
    write_csv(output / 'optimization-cost.csv', budget_rows)
    write_csv(output / 'timing-quality.csv', quality)
    (output/'source-transforms.json').write_text(json.dumps(source_transforms,indent=2)+'\n')
    (output/'scope-reviews.json').write_text(json.dumps(scope_reviews,indent=2)+'\n')
    keys = set.intersection(*(set(w['ratios']) for _,w in primary))
    aggregate = {k: math.exp(statistics.mean(math.log(w['ratios'][k]['speedup']) for _,w in primary)) for k in sorted(keys)}
    for k, value in aggregate.items():
        if not math.isclose(value, data['primary_geomean_speedups'][k], rel_tol=1e-12):
            raise ValueError('Aggregate disagrees with frozen matrix')
    wins = {k: {'gain_ci_above_one':sum(w['ratios'][k]['ci95'][0]>1 for _,w in primary),
                'regression_ci_below_one':sum(w['ratios'][k]['ci95'][1]<1 for _,w in primary)} for k in sorted(keys)}
    summary = {'cases':len(cases), 'workloads':sum(len(c['rows']) for c in cases),
               'matrix_cells':len(cases)*6, 'primary_geomean_speedups':aggregate,
               'primary_interval_classification':wins, 'range_exclusions':exclusions,
               'optimization_attempted_calls':sum(r['model_calls'] for r in budget_rows),
               'final_review_attempted_calls':sum(r['final_review_model_calls'] for r in budget_rows),
               'final_review_seconds':sum(r['final_review_seconds'] for r in budget_rows),
               'review_unavailable_cases':[{k:r[k] for k in ['case','mode','model_calls','final_review_status']}
                                           for r in budget_rows if r['final_review_status']=='review_unavailable'],
               'selected_source_optimized_cases':[r['case'] for r in budget_rows if r['selected_source_optimized']],
               'original_retained':[{'case':case,'mode':mode} for case,w in primary for mode in w['unchanged_modes']],
               'timing_quality':{'process_rounds':len(quality),'unstable_warmups':sum(not r['warmup_stable'] for r in quality),
                                 'rounds_with_warnings':sum(bool(r['warnings']) for r in quality),
                                 'clock_resolution_warnings':sum('batch_too_close_to_clock_resolution' in r['warnings'] for r in quality)},
               'matrix':str(matrix.resolve()), 'aggregation':'equal case weight, predeclared primary workloads only'}
    if baseline_quality:
        summary['baseline_quality'] = baseline_quality
        (output / 'baseline-quality-review.json').write_text(json.dumps(baseline_quality, indent=2) + '\n')
    summary['optimization_cost_by_mode']={mode:{
        'cases':len(rows),'model_calls':sum(r['model_calls'] for r in rows),
        'known_tokens':sum(r['known_total_tokens'] for r in rows),
        'median_charged_wall_seconds':statistics.median(r['charged_seconds'] for r in rows),
        'median_resource_wait_seconds':statistics.median(r['resource_wait_seconds'] for r in rows),
        'median_wall_excluding_resource_wait_seconds':statistics.median(r['charged_seconds']-r['resource_wait_seconds'] for r in rows),
        'source_phase_model_calls':sum(r['source_phase_calls'] for r in rows),
        'source_selected_cases':sum(r['selected_source_optimized'] for r in rows),
        'note':'Wall time excluding resource waits still includes network and tool execution; it is not CPU time.'}
        for mode in ['rust-only','full'] if (rows:=[r for r in budget_rows if r['mode']==mode])}
    without_queue=[w for case,w in primary if case!='fpp-deq-list']
    summary['sensitivity_without_queue']={
        'cases':len(without_queue),'excluded_case':'fpp-deq-list',
        'reason':'Supplementary sensitivity to the prepared-container identity workload; the ten-case primary analysis remains unchanged.',
        'primary_geomean_speedups':{k:math.exp(statistics.mean(math.log(w['ratios'][k]['speedup']) for w in without_queue))
            for k in set.intersection(*(set(w['ratios']) for w in without_queue))} if without_queue else None}
    runs={Path(s['selected_state']).parents[2] for c in cases for s in c['selections'].values()}
    releases=[{'run':str(r), 'identity':json.loads((r/'release.json').read_text())['identity'],
               'release_sha256':hashlib.sha256((r/'release.json').read_bytes()).hexdigest()}
              for r in sorted(runs) if (r/'release.json').exists()]
    mixed_releases=len({r['identity'] for r in releases})>1
    summary['controller_releases']=releases
    summary['mixed_controller_releases']=mixed_releases
    source_first=all(s.get('stage_schema')==2 for c in cases for s in c['selections'].values())
    summary['workflow']='bounded_source_then_fixed_source_rust' if source_first else 'legacy_development_workflow'
    summary['unique_measured_process_rounds']=sum(not r['shared_observations'] for r in quality)
    summary['executable_aliases']={c['case']:c.get('executable_aliases',{}) for c in cases}
    migrations=[str(p) for r in runs for p in r.glob('*migration.json')]
    development=bool(migrations)
    summary['controller_migrations']=sorted(migrations)
    summary['report_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    summary['study_status']=('controller_development_round; a clean frozen-controller rerun is needed for a publication ablation'
                             if development else 'mixed_frozen_controller_releases' if mixed_releases else 'frozen_controller_experiment')
    if audit:
        summary['integrity_audit']={'path':str(audit_path.resolve()),
                                    'sha256':hashlib.sha256(audit_path.read_bytes()).hexdigest(),
                                    'status':audit['status'],'publication_hold':audit_hold}
        if audit_hold:summary['study_status']='integrity_audit_hold; recorded measurements are exploratory and do not establish the intended optimization ablation'
        if audit.get('experiment_recovery'):
            summary['experiment_recovery']=audit['experiment_recovery']
    all_keys=set.intersection(*(set(w['ratios']) for c in cases for w in c['rows']))
    summary['all_workloads_case_balanced_geomean']={
        k:math.exp(statistics.mean(statistics.mean(math.log(w['ratios'][k]['speedup']) for w in c['rows']) for c in cases))
        for k in sorted(all_keys)}
    summary['matplotlib_version'] = plot(primary, output, 'optimization', audit_hold)
    plot(primary, output, 'numeric', audit_hold)
    plot_matrix(primary, output, development, audit_hold=audit_hold)
    if source_increment:
        extra=json.loads(Path(source_increment).read_text())
        if not extra.get('complete'):raise ValueError('Source-stage comparison is incomplete')
        summary['source_stage_comparison']=extra['results']
        (output/'source-increment.json').write_text(json.dumps(extra,indent=2)+'\n')
    (output / 'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    def e(x): return html.escape(str(x))
    audit_notice=''
    if audit:
        issues=''.join('<li>'+e(x['finding'])+'</li>' for x in audit.get('issues',[]))
        audit_notice='<aside style="border:2px solid #ad431f;padding:16px;background:#fff6ef"><strong>'+('AUDIT HOLD — do not use these mode comparisons as publication conclusions.' if audit_hold else 'Integrity audit attached.')+'</strong><ul>'+issues+'</ul><a href="integrity-review.json">Audit evidence and independent verification results</a></aside>'
    headings = ['Case','Primary input','Off → Rust-only speedup','Off → Full speedup',
                'Off numeric speedup','Rust-only numeric speedup','Full numeric speedup']
    columns = ['rust-only-vs-off-arbitrary','full-vs-off-arbitrary','off-numeric','rust-only-numeric','full-numeric']
    table = '<tr>'+''.join('<th>'+e(x)+'</th>' for x in headings)+'</tr>'
    for case, w in primary:
        cells = [LABELS.get(case,case), w['workload']]
        cells += [f"{w['ratios'][k]['speedup']:.3f}× [{w['ratios'][k]['ci95'][0]:.3f}, {w['ratios'][k]['ci95'][1]:.3f}]" if k in w['ratios'] else 'N/A (numeric range)' for k in columns]
        table += '<tr>'+''.join('<td>'+e(x)+'</td>' for x in cells)+'</tr>'
    table += '<tr><th>Geometric mean</th><td>Equal case weight; complete cohort only</td>'+''.join(f'<td>{aggregate[k]:.3f}×</td>' if k in aggregate else '<td>N/A (incomplete common domain)</td>' for k in columns)+'</tr>'
    note = ('Source transformations selected in: ' + ', '.join(summary['selected_source_optimized_cases'])
            if summary['selected_source_optimized_cases'] else 'No source-transformed implementation was selected; do not claim an incremental source-optimization benefit from this run.')
    development_note = ('This is a controller-development round with explicit migrations and unequal remaining useful search allowance. '
                        'Failed and interrupted requests remain charged. Protocol repair, retired Full selections and retrospective scope reviews '
                        'are preserved in the migration journals listed in summary.json. A clean frozen-controller rerun is needed for a publication ablation.'
                        if development else 'The selected search artifacts come from frozen controllers; raw attempts and charged costs are retained.')
    if mixed_releases and not development:
        development_note += ' This is a mixed-release cohort, not a single-controller run; actual per-run release identities are listed in summary.json. The attached integrity record describes any registered correction and excluded-run overhead separately from selected-search costs.'
    review_notes=[]
    workflow_note=('Full first attempts a bounded source phase, then fixes the accepted source (or restores Off) and performs Rust refinement. Rust-only skips the source phase. Both searches start from the same validated Off artifact and have the same overall limits; this is a comparison of configured workflows, not a shared-Rust incremental ablation.' if source_first else
                   'Rust-only and Full searched independently from the same validated Off implementation. Full did not inherit the separately selected Rust-only result. These trajectories do not isolate an incremental source benefit on a shared Rust stage.')
    review_note=('Source-correspondence admission occurs before accepting a candidate and shares the 25-call/3600-second budget. Full limits source work to two directions and the configured phase caps/reserves exported in optimization-cost.csv; theory reads and schema-repair calls are charged. Final selection uses sealed prior admission evidence and makes no additional model call.' if source_first else
                 'Final independent source-correspondence review has a separate 180-second ceiling; its calls remain inside the same 25-call allowance and its elapsed time is reported separately.')
    if any('Prompt must contain' in str(r['review'].get('error')) for r in scope_reviews):
        review_notes.append('The initial review prompt omitted the word JSON required by the provider; rejected requests remained charged.')
    if any(r['case']=='fpp-avl-updates' and r['mode']=='rust-only' and r['selected'] is None and
           any('split_max' in d['reason'] for d in r['review']['reviews']) for r in scope_reviews):
        review_notes.append('The Rust-only AVL review cited split_max: Ord, which was already present in frozen Off. That conservative fallback was retained without a manual override.')
    source_table=''
    if source_increment:
        source_table='<h2>Source stage versus its own Rust predecessor</h2><table><tr><th>Case / primary input</th><th>Arbitrary speedup</th><th>Checked speedup</th></tr>'
        for r in summary['source_stage_comparison']:
            values=[LABELS.get(r['case'],r['case'])+' / '+r['workload']]
            values += [f"{r['source_stage_speedups'][b]['speedup']:.2f}× [{r['source_stage_speedups'][b]['ci95'][0]:.2f}, {r['source_stage_speedups'][b]['ci95'][1]:.2f}]" for b in ['arbitrary','checked']]
            source_table+='<tr>'+''.join('<td>'+e(v)+'</td>' for v in values)+'</tr>'
        source_table+='</table><p>Independent fresh measurement of the already selected source-stage realization and the accepted incumbent immediately before its proof-backed source transition; fixed primary input, six process rounds and no further model calls. <a href="source-increment.json">Raw references and ratios</a>.</p>'
    document = f'''<!doctype html><meta charset="utf-8"><title>RQ2 performance results</title>
<style>body{{font:15px/1.55 system-ui;margin:32px;color:#23303d}}main{{max-width:1400px;margin:auto}}img{{width:100%}}table{{border-collapse:collapse;width:100%;font-size:12px}}td,th{{padding:9px;border-bottom:1px solid #dde3e9;text-align:left}}th{{background:#edf2f7}}code{{background:#eef1f5;padding:2px 5px}}</style>
<main><h1>RQ2 performance results — {len(cases)} cases</h1>
{audit_notice}
<p>{summary['workloads']} declared workloads; {len(cases)*6} primary matrix cells. Figures use fresh final measurements. The new protocol uses at least six process rounds, completing balanced order cycles, and ten samples per round (forty for predetermined short-batch conditions). Identical executable cells explicitly share observations. Raw records specify the exact protocol used. Timed scope is the kernel on prepared independent inputs, including intrinsic allocations and retained results; input construction, parsing, output encoding and output checking are outside the timer. The main figure shows normalized kernel runtime (lower is better); the table shows speedups (higher is faster).</p>
<img src="rq2-matrix.png" alt="Ten cases, three optimization modes and two numeric backends; all six values normalized to Off plus arbitrary">
<table>{table}</table><p>{e(note)} Proofs and selected-state references: <a href="source-transforms.json">source transformations</a>.</p>
{source_table}
<p>The same business and connector source is compiled for the arbitrary and checked columns within each mode. {e(workflow_note)}</p>
<p>Queue drain measures the declared deq2list workloads with an empty accumulator. The source theorem deq2list q xs = q @ xs permits an owned Rust input to be returned directly when xs is empty, if that rewrite is actually proved and selected. This describes those drain workloads, not general enqueue/dequeue or end-to-end performance. The selected-state and proof records determine whether this particular run uses that transformation.</p>
<p>Checked results apply only to representable inputs and intermediate values. Range exclusions, including the Fibonacci n=200 correctness probe, are listed in <a href="summary.json">summary.json</a>. They are not timed as successes. Original source tests and cached complete reference observations validate new candidates; reference executables and test generation are not rerun.</p>
<p>Optimization permits 25 attempted calls and 3600 charged search seconds per case per mode. {e(review_note)} The scope reviewer sees candidate code and source equations without timing; embedded comments and mapping prose are author claims, not proofs. Only approved existing candidates can be selected. {e(development_note)} Complete selected-search costs, review outcomes and stop reasons are in <a href="optimization-cost.csv">optimization-cost.csv</a>. For schema 2 the final_review columns are zero because finalization makes no model calls; admission requests are already included in optimization attempted calls.</p>
<p>Source equivalence is checked in Isabelle; this is not a formal proof of generated Rust. There is one optimization trajectory per case and mode. Paired process bootstrap intervals quantify timing variation, not model-search variation, and have no multiple-comparison adjustment. Ten-case aggregates describe this cohort and do not establish a twenty-case or cross-language result. RQ3 is reported separately.</p>
<p>Batch durations, empirical timer probes, warmup stability and protocol warnings are exported in <a href="timing-quality.csv">timing-quality.csv</a>. Memory-capped batches may fall below the target duration; no timer overhead is subtracted. A minimum positive timer probe is not a proven clock resolution or error bound. Short-kernel point estimates require the scope audit and sensitivity evidence, not exact nanosecond claims.</p>
<p>Scope review is a model judgment, not a proof. {e(' '.join(review_notes))} All decisions and raw references are available in <a href="scope-reviews.json">scope-reviews.json</a>.</p>
<p>Exports: <a href="rq2-matrix.svg">main figure SVG</a> · <a href="rq2-matrix.pdf">main figure PDF</a> · <a href="normalized-matrix.csv">normalized values</a> · <a href="timings.csv">all timings</a> · <a href="speedups.csv">all ratios and intervals</a>.</p>
<details><summary>Supplementary speedup views</summary><img src="optimization-ablation.png" alt="Optimization speedups"><img src="numeric-ablation.png" alt="Numeric speedups"></details></main>'''
    (output / 'report.html').write_text(document)
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--matrix',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--source-increment',type=Path)
    p.add_argument('--integrity-audit',type=Path,help='Attach an integrity review; defaults to MATRIX/integrity-review.json when present')
    a=p.parse_args();report(a.matrix,a.output,a.source_increment,a.integrity_audit)

#!/usr/bin/env python3
"""Plot a sealed cross-language measurement report; never alter measured data."""
import argparse,csv,html,json,shutil
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

LABELS={'fpp-multip':'Multip.','fpp-tree-inorder':'Inorder','fpp-deq-list':'Queue','fpp-msort':'Merge sort','fpp-avl-updates':'AVL','fpp-acomp':'AComp','hol-eratosthenes':'Sieve','hol-polynomial':'Polynomial','hol-fibonacci':'Fibonacci','fpp-leftist-heap-merge':'Heap merge'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--compact',action='store_true',help='Paper layout without title or footer text');a=p.parse_args()
 source=a.run/'report';summary=json.loads((source/'summary.json').read_text());seal=json.loads((a.run/'experiment-seal.json').read_text())['identity']
 assert summary['complete'] and summary['measured_primary_workloads']==10
 ours=seal['implementation_order'][0];names=[ours,'ocaml','haskell','go','stage2'];labels=['llm-'+ours.replace('-arbitrary',''),'OCaml','Haskell','Go','Rust-S2'];colors=['#278b78','#dc9a3b','#9678ad','#4b87c1','#adb7c4']
 rows=[r for r in summary['comparisons'] if r['primary']];cases=[r['case'] for r in rows]
 times=list(csv.DictReader((source/'timings.csv').open()));primary={r['case']:{} for r in rows}
 for r in times:
  if r['primary']=='True':primary[r['case']][r['implementation']]=float(r['median_ns'])
 quality=list(csv.DictReader((source/'timing-quality.csv').open()));warn={r['case'] for r in quality if 'batch_too_close_to_clock_resolution' in r['warnings'] or 'warmup_not_stable' in r['warnings']}
 fig,ax=plt.subplots(figsize=(7.5,1.87425) if a.compact else (17,6.8))
 fig.subplots_adjust(left=.085,right=.995,bottom=.19,top=.86) if a.compact else fig.subplots_adjust(left=.07,right=.99,bottom=.24,top=.76)
 x=np.arange(len(rows));width=.16;export=[]
 for i,name in enumerate(names):
  values=[];low=[];high=[]
  for r in rows:
   c=r['comparisons'].get(name,{'speedup':1.,'ci95':[1.,1.]});v=c['speedup'];lo,hi=c['ci95'];values.append(v);low.append(max(0,v-lo));high.append(max(0,hi-v));export.append({'case':r['case'],'implementation':name,'median_ns':primary[r['case']][name],'normalized_runtime':v,'ci95_low':lo,'ci95_high':hi})
  bars=ax.bar(x+(i-2)*width,values,width*.92,color=colors[i],label=labels[i],zorder=3)
  ax.errorbar(x+(i-2)*width,values,yerr=[low,high],fmt='none',ecolor='#34445b',elinewidth=.9,capsize=2,zorder=4)
 ax.set_yscale('log');ax.axhline(1,color='#607080',ls='--',lw=1);ax.set_axisbelow(True);ax.grid(axis='y',which='major',alpha=.23)
 tick_labels=[LABELS.get(c,c)+('†' if c in warn else '') for c in cases]
 if a.compact:tick_labels=[t.replace('Merge sort','Merge\nsort').replace('Heap merge','Heap\nmerge') for t in tick_labels]
 ax.set_xticks(x,tick_labels,fontsize=7 if a.compact else 11)
 ax.tick_params(axis='y',labelsize=7 if a.compact else 11)
 ax.set_ylabel('Normalized runtime (log scale)' if a.compact else 'Runtime / llm-rust-only arbitrary runtime\n(log scale; lower is better)',fontsize=8 if a.compact else 12)
 for side in ['top','right']:ax.spines[side].set_visible(False)
 ax.legend(loc='lower center' if a.compact else 'lower left',bbox_to_anchor=(.5,1.01) if a.compact else (0,1.04),ncol=5,frameon=False,fontsize=8 if a.compact else 12,handlelength=1.5,columnspacing=1.3)
 if not a.compact:
  fig.text(.07,.94,'Arbitrary precision: Rust-only vs four generated baselines',fontsize=22,weight='bold',color='#24344e')
  fig.text(.07,.885,'10 cases · identical primary inputs · 10 balanced process rounds · 95% paired bootstrap intervals',fontsize=12,color='#53647e')
  fig.text(.07,.13,'Prepared-input kernel timing; preparation and encoding excluded. Haskell fully forces results inside timing.',fontsize=11,color='#53647e')
  fig.text(.07,.09,'Each case is normalized to its Rust-only arbitrary runtime (= 1). All five targets use arbitrary-precision integers.',fontsize=11,color='#53647e')
  fig.text(.07,.05,'† Short-batch or unstable-warmup warnings; raw observations and uncertainty are retained in the report.',fontsize=11,color='#53647e')
 a.output.mkdir(parents=True,exist_ok=True)
 for ext in ['png','svg','pdf']:fig.savefig(a.output/f'rq3-rust-only.{ext}',dpi=200)
 plt.close(fig)
 for f in source.iterdir():
  if f.is_file():shutil.copy2(f,a.output/f.name)
 with (a.output/'normalized-runtimes.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(export[0]));w.writeheader();w.writerows(export)
 def table(headers,values):return '<table><tr>'+''.join('<th>'+html.escape(h)+'</th>' for h in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in values)+'</table>'
 aggregate=summary['aggregates']['primary_case_equal']
 body='<h1>Rust-only arbitrary vs generated baselines</h1><img src="rq3-rust-only.svg" style="width:100%"><h2>Geometric mean reference / Rust-only runtime</h2>'+table(['Reference','Ratio','95% interval'],[(name,f"{aggregate[name]['speedup']:.3f}",str(aggregate[name]['ci95'])) for name in names[1:]])
 body+='<h2>Sensitivity: excluding Queue</h2>'+table(['Reference','Ratio','95% interval'],[(name,f"{summary['aggregates']['sensitivity_primary_without_queue'][name]['speedup']:.3f}",str(summary['aggregates']['sensitivity_primary_without_queue'][name]['ci95'])) for name in names[1:]])
 body+='<p>Queue Rust-only uses a VecDeque loop (pop_back then push_front), preserving each dequeue transition. The generated linked-list references repeatedly traverse last/butlast. The large ratio reflects data representation and its operation costs; this Rust-only candidate does not use the Full source rewrite that returns prepared input directly. It is not a general language speed ratio.</p>'
 body+='<h2>Per-case runtime (microseconds)</h2>'+table(['Case',*labels],[(LABELS.get(c,c),*[f'{primary[c][n]/1000:.4f}' for n in names]) for c in cases])
 body+='<h2>Scope and limitations</h2><ul>'+''.join('<li>'+html.escape(t)+'</li>' for t in summary['scope_caveats'])+'</ul><p>This selected ten-case cohort is not a random sample of programs. These are fresh timings of the frozen v4 Rust-only programs; later controller repairs did not regenerate them. All input/output and artifact hashes are recorded in the experiment seal.</p>'
 body+='<p>Heap uses a uniform batch cap of 8 for all implementations to bound untimed preparation cost; the other nine cases use a cap of 1024. The ten-round design and timing boundaries are unchanged. Prior partial Heap observations are retained separately, not pooled. Short batches limit precision, especially for very fast Heap kernels.</p>'
 body+='<h2>Timing warnings (process counts)</h2>'+table(['Warning','Count'],summary['quality_warnings'].items())+'<p>Ratios above one favor Rust-only; below one favor the reference. Intervals quantify sampling uncertainty, not systematic differences in evaluation strategy.</p><p><a href="timings.csv">Raw runtime summaries</a> · <a href="speedups.csv">Ratios and intervals</a> · <a href="timing-quality.csv">Timing quality</a> · <a href="summary.json">Full summary and raw-record paths</a></p>'
 (a.output/'report.html').write_text('<!doctype html><meta charset="utf-8"><style>body{font:16px system-ui;margin:36px;color:#24344e}table{border-collapse:collapse}td,th{padding:8px 14px;border-bottom:1px solid #ddd;text-align:left}</style>'+body)
 shutil.copy2(a.run/'experiment-seal.json',a.output/'experiment-seal.json')
 if (a.run/'measurement-provenance.json').exists():shutil.copy2(a.run/'measurement-provenance.json',a.output/'measurement-provenance.json')
 print(a.output)
if __name__=='__main__':main()

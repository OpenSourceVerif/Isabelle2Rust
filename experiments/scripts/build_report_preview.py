#!/usr/bin/env python3
"""Build a standalone report layout prototype using the second experiment's data."""
import html
import json
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
BATCH = '20261023-02-two-task-pilot'

def build():
    data = json.loads((EXP/'results'/f'{BATCH}.json').read_text())
    aggregates = data['performance']['aggregates']
    queries = [('first','首元素'),('last','尾元素'),('absent','不存在')]
    loads=[]
    for n in (32,128,512):
        for q,name in queries:
            rows={r['implementation']:r for r in aggregates if r['length']==n and r['query']==q}
            values=[rows[f'run-{i:03d}']['median_ns'] for i in range(1,4)]
            loads.append(dict(n=n,q=name,rows=rows,values=values,
                              faster=sorted(rows['stage2']['median_ns']/v for v in values),
                              slower=sorted(v/rows['ocaml']['median_ns'] for v in values)))
    speed=[v for l in loads for v in l['faster']]
    slow=[v for l in loads for v in l['slower']]
    def chart(kind,maximum,color):
        x0,x1=140,430
        svg=[f'<svg viewBox="0 0 560 376" role="img" aria-label="九种负载的{ "Stage 2 加速倍数" if kind=="faster" else "相对 OCaml 耗时倍数" }"><title>每条线覆盖三份候选各自七轮耗时中位数所对应的倍数范围</title>']
        ticks=[0,5,10,15,20] if kind=='faster' else [0,1,2,3,4]
        for tick in ticks:
            x=x0+(x1-x0)*tick/maximum
            svg.append(f'<line x1="{x}" x2="{x}" y1="22" y2="337" stroke="#e4e9f0"/><text x="{x}" y="365" text-anchor="middle" class="axis">{tick}×</text>')
        for i,l in enumerate(loads):
            y=42+i*34
            if i in (3,6):svg.append(f'<line x1="0" x2="556" y1="{y-18}" y2="{y-18}" stroke="#d5deea"/>')
            lo,hi=l[kind][0],l[kind][-1]
            a,b=x0+(x1-x0)*lo/maximum,x0+(x1-x0)*hi/maximum
            svg.append(f'<text x="0" y="{y+4}" class="load">{l["n"]} · {l["q"]}</text><line x1="{x0}" x2="{a}" y1="{y}" y2="{y}" stroke="{color}" stroke-opacity=".18" stroke-width="8"/><line x1="{a}" x2="{b}" y1="{y}" y2="{y}" stroke="{color}" stroke-width="4"/>')
            for v in l[kind]:
                x=x0+(x1-x0)*v/maximum
                svg.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{color}"><title>长度 {l["n"]}，{l["q"]}：{v:.3f} 倍</title></circle>')
            svg.append(f'<text x="555" y="{y+4}" text-anchor="end" class="value">{lo:.2f}–{hi:.2f}×</text>')
        svg.append('</svg>')
        return ''.join(svg)
    values=''.join('<tr><td>'+str(l['n'])+' · '+l['q']+'</td>'+''.join(f'<td>{l["rows"][k]["median_ns"]/1000:,.3f}</td>' for k in ['stage1','stage2','ocaml','run-001','run-002','run-003'])+'</tr>' for l in loads)
    run_rows=[]
    for run in data['runs']:
        dev=run['attempts'][0]['development'];final=run['final']
        run_rows.append(f'<tr><td>{html.escape(run["task"])}</td><td>{run["run_id"]}</td><td>{"通过" if run["status"]=="passed" else html.escape(run["status"])}</td><td>{len(run["attempts"])-1}</td><td>{dev["count"]:,} / {dev["count"]:,}</td><td>{final["count"]:,} / {final["count"]:,}</td></tr>')
    page='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>实验报告样稿 · List-Index / Skew Heap</title><style>
:root{color-scheme:light;--blue:#2456a1;--ink:#233247;--muted:#637186;--line:#dbe2eb}*{box-sizing:border-box}body{margin:0;background:#fff;color:var(--ink);font:14px/1.65 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}a{color:var(--blue)}h1,h2,h3,p{margin:0}aside{position:fixed;inset:0 auto 0 0;width:194px;background:#f4f6f9;border-right:1px solid var(--line);padding:25px 17px}aside strong{font-size:16px}aside .label{font-size:11px;color:var(--muted);margin:30px 0 9px}aside a{display:block;text-decoration:none;font-size:12px;padding:9px 8px;color:#445775}aside .current{border-left:2px solid var(--blue);padding:10px 9px;background:#e8eef8;font-size:12px;font-weight:600;color:#234c85}aside .caption{position:absolute;bottom:24px;font-size:11px;color:var(--muted)}main{margin-left:194px;padding:24px 36px 36px;max-width:1510px}.context{display:flex;justify-content:space-between;color:var(--muted);font-size:11px;margin-bottom:18px}.context span{font-family:monospace}h1{font-size:25px;font-weight:650;letter-spacing:-.4px}.purpose{font-size:13px;margin-top:9px;max-width:930px}.setup{color:var(--muted);font-size:11px;margin:12px 0 19px}.tabs{border-bottom:1px solid var(--line);display:flex;gap:30px;margin-bottom:24px;font-size:13px}.tabs strong{border-bottom:2px solid var(--blue);padding:0 0 10px;color:var(--blue)}.tabs span{color:#8791a0}.finding{display:grid;grid-template-columns:95px 1fr;gap:15px;margin-bottom:24px}.finding .label{font-size:12px;font-weight:600;color:var(--blue);padding-top:3px}.finding h2{font-size:19px;line-height:1.6;font-weight:600}.finding p{font-size:12px;color:var(--muted);margin-top:5px}.section-head{display:flex;align-items:baseline;justify-content:space-between;gap:15px;margin:22px 0 12px}.section-head h2{font-size:15px}.section-head p{font-size:11px;color:var(--muted)}.behaviour{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.task{padding:16px 20px 16px 0}.task+ .task{padding-left:22px;border-left:1px solid var(--line)}.task-top{display:flex;justify-content:space-between;align-items:center;gap:12px}.task-top h3{font:600 13px/1.5 "SFMono-Regular",Consolas,monospace}.pass{font-size:12px;color:#276d50;white-space:nowrap}.task p{font-size:11px;color:var(--muted);margin-top:8px}.marks{display:flex;gap:5px;align-items:center}.mark{display:inline-block;width:7px;height:7px;background:#3b8666}.task .counts{color:#33465f;font-size:12px}.baseline{font-size:11px;color:var(--muted);margin-top:10px}.charts{display:grid;grid-template-columns:1fr 1fr;gap:25px;border-top:1px solid var(--line);padding-top:15px}.chart h3{font-size:13px}.chart .ratio{font-family:"SFMono-Regular",Consolas,monospace;font-size:23px;margin:4px 0;color:var(--blue);font-weight:550}.chart.secondary .ratio{color:#926029}.chart .formula{font-size:10px;color:var(--muted)}svg{width:100%;display:block;margin-top:8px}svg text{font-family:inherit;fill:#637186;font-size:12px}svg .load{fill:#354963;font-size:12px}svg .value{fill:#233247;font-family:monospace;font-size:12px}.reading-note{font-size:11px;color:var(--muted);line-height:1.8;border-bottom:1px solid var(--line);padding-bottom:14px}.method{margin:14px 0;padding:12px 15px;background:#f5f7fa;border-left:2px solid #a6b9d2;font-size:11px;color:#52647b}.conclusion{display:grid;grid-template-columns:1fr 1fr;gap:26px;padding-top:4px}.conclusion h3{font-size:13px;margin-bottom:7px}.conclusion p{font-size:12px;color:#53657d;line-height:1.9}details{border-top:1px solid var(--line);margin-top:19px;padding-top:12px}summary{font-size:12px;color:var(--blue);cursor:pointer}summary:focus-visible,a:focus-visible{outline:2px solid var(--blue);outline-offset:3px}.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%;font-size:11px;margin-top:12px}td,th{text-align:right;border-bottom:1px solid var(--line);padding:8px 9px;white-space:nowrap;font-variant-numeric:tabular-nums}th{font-weight:500;color:var(--muted);background:#f5f7fa}td:first-child,th:first-child{text-align:left}footer{font-size:10px;color:var(--muted);margin-top:26px;line-height:1.8}.prototype-note{font-size:10px;color:#748096;margin-top:4px}@media(min-width:1500px){main{padding-left:50px;padding-right:50px}}@media(max-width:950px){main{padding:24px}.charts{gap:16px}.chart .ratio{font-size:20px}.finding{grid-template-columns:70px 1fr}.finding h2{font-size:17px}.task-top{align-items:flex-start;flex-direction:column;gap:4px}}@media(max-width:700px){aside{position:relative;width:auto;padding:15px}.caption,aside .label,aside>a,aside .current{display:none}main{margin-left:0;padding:20px 16px}.context{flex-wrap:wrap;gap:4px}h1{font-size:22px}.charts,.behaviour,.conclusion{grid-template-columns:1fr}.task+ .task{padding-left:0;border-left:0;border-top:1px solid var(--line)}.finding{display:block}.finding .label{margin-bottom:5px}.tabs{gap:19px}.chart{padding-bottom:16px}.section-head{display:block}.task-top{flex-direction:row}.context span{font-size:9px}}@media print{aside,.context a{display:none}main{margin:0;padding:0}.charts{break-inside:avoid}}
</style>
</head><body><aside><strong>Isabelle → Rust</strong><div class="label">研究</div><a href="/">研究方案</a><div class="label">实验结果</div><div class="current">List-Index / Skew Heap<br>重复生成与性能初测</div><div class="caption">实验详情 · 静态样稿</div></aside><main><div class="context"><div>版式样稿 · 第二组实际记录</div><span>20261023-02-two-task-pilot</span></div><header><h1>直接生成 Rust：重复性与性能初测</h1><p class="purpose"><strong>本次目的：</strong>检查 List-Index 的成功能否重复，以及同一方法能否处理 Skew Heap 的递归树合并；初步比较 List-Index 的运行性能。</p><div class="setup">固定 Isabelle 模型 → DeepSeek 直接生成　·　2 个函数 × 3 次独立运行　·　deepseek-flash / temperature 0.2　·　2026-10-23</div></header>
<div class="tabs"><strong>结果与结论</strong><span>测试集与方案</span><span>逐次运行</span></div><section class="finding"><div class="label">关键发现</div><div><h2>6 次生成均通过测试；List-Index 快于 Stage 2，但仍慢于 OCaml。</h2><p>这支持两个开发任务上的流程可行性。尚不能推广为 AFP 总体成功率，也不能把性能差异全部归因于模型优化。</p></div></section>
<div class="section-head"><h2>行为结果</h2><p>每个方块表示一次独立生成</p></div><div class="behaviour"><article class="task"><div class="task-top"><h3>List_Index.last_index</h3><div class="marks"><i class="mark"></i><i class="mark"></i><i class="mark"></i><span class="pass">3 / 3 首次通过</span></div></div><p class="counts">每次：开发 581 / 581　·　最终 4,129 / 4,129</p><p>反向迭代查找；3 次核心算法相同。0 次反馈修复。</p></article>
<article class="task"><div class="task-top"><h3>Skew_Heap.merge</h3><div class="marks"><i class="mark"></i><i class="mark"></i><i class="mark"></i><span class="pass">3 / 3 首次通过</span></div></div><p class="counts">每次：开发 321 / 321　·　最终 1,411 / 1,411</p><p>递归树合并；3 次代码完全相同。0 次反馈修复。</p></article>
</div><p class="baseline">OCaml、Stage 1、Stage 2 均通过两任务的全部测试。最终测试不用于修复或重选；所有候选均未经人工修改。</p><div class="section-head"><h2>性能结果 · 仅 List-Index</h2><p>全部 9 种负载 · 3 份候选 · 每实现每负载测 7 轮</p></div><div class="charts"><article class="chart"><h3>与 Stage 2 比：所有负载均更快</h3><div class="ratio">快 __FAST_MIN__–__FAST_MAX__ 倍</div><p class="formula">加速倍数 = Stage 2 耗时 ÷ 候选耗时；越大越快</p>__FAST_CHART__</article>
<article class="chart secondary"><h3>与 OCaml 比：所有负载均更慢</h3><div class="ratio">耗时为 __SLOW_MIN__–__SLOW_MAX__ 倍</div><p class="formula">耗时倍数 = 候选耗时 ÷ OCaml 耗时；越大越慢</p>__SLOW_CHART__</article>
</div><p class="reading-note">行标签：列表长度 · 查询位置。每个点对应一份候选，线段连接 3 份候选的倍数范围；重合点可能不可分辨。每份实现先取 7 轮耗时中位数再计算比值，线段不是置信区间。两图横轴含义和刻度不同。</p><div class="method"><strong>计时口径：</strong>预热 10 次、每轮调用 500 次，包含输入准备、表示转换及函数执行；不含解析、输出、编译或 API。候选用切片，参考 Rust 用链表，尚未分离表示差异。Skew Heap 性能和内存分配量未测。</div><div class="section-head"><h2>这组实验说明了什么</h2></div><div class="conclusion"><article><h3>已有证据</h3><p>直接生成与统一测试链路已在列表和递归树任务上运行。三次重复均成功，但代码多样性低，未检验反馈修复的作用。相对 Stage 2 的性能改善不能替代与 OCaml 的比较。</p></article>
<article><h3>下一步建议</h3><p>扩展 AFP 任务，并把输入转换、内存分配和函数本体分别测量。当前只有两个开发任务；List-Index 还复用了首组用例，不能据此估计外部任务上的成功率。</p></article>
</div><details><summary>查看全部实现的绝对耗时（μs / 次）</summary><p class="prototype-note">各实现 7 轮中位数。Stage 1 也保留在这里；主图突出当前最影响结论的 Stage 2 与 OCaml 对照。</p><div class="table-wrap"><table><thead><tr><th>长度 · 查询</th><th>Stage 1</th><th>Stage 2</th><th>OCaml</th><th>候选 001</th><th>候选 002</th><th>候选 003</th></tr></thead><tbody>__VALUES__</tbody></table></div></details>
<details><summary>查看 6 次运行的测试结果</summary><div class="table-wrap"><table><thead><tr><th>任务</th><th>运行</th><th>最终状态</th><th>修复次数</th><th>开发测试</th><th>最终测试</th></tr></thead><tbody>__RUNS__</tbody></table></div></details>
<footer>数据来源：results/20261023-02-two-task-pilot.json；解释依据同编号批次记录。<br>这是一张用于讨论阅读顺序的静态样稿，仅“结果与结论”已排版；其余页签尚未实现。<a href="/">返回现有工作台</a></footer></main></body></html>'''
    for key,value in {
        '__FAST_MIN__':f'{min(speed):.2f}','__FAST_MAX__':f'{max(speed):.2f}',
        '__SLOW_MIN__':f'{min(slow):.2f}','__SLOW_MAX__':f'{max(slow):.2f}',
        '__FAST_CHART__':chart('faster',20,'#3567ab'),'__SLOW_CHART__':chart('slower',4,'#9b7446'),
        '__VALUES__':values,'__RUNS__':''.join(run_rows)}.items():page=page.replace(key,value)
    path=EXP/'dashboard'/'report-preview.html'
    path.write_text(page)
    return path

if __name__=='__main__':
    print(build())

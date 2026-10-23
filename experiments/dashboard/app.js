(() => {
  'use strict';
  const data=JSON.parse(document.getElementById('experiment-data').textContent);
  const cases=data.cases||[];
  const state={caseId:cases[0]?.id,tab:'overview',round:cases[0]?.rounds.at(-1)?.round_id,historyTab:'results',run:0,runPage:0,implementation:cases[0]?.implementations.find(i=>i.round_id===cases[0]?.rounds.at(-1)?.round_id)?.implementation_id,length:512,query:'absent',values:'small',measurement:'all',performanceRound:'all',scope:'end_to_end',scale:'log',configTab:'parameters',promptTask:null,task:cases[0]?.id};
  const labels={'list-index':'List-Index','skew-heap':'Skew Heap',stage1:'Stage 1',stage2:'Stage 2',ocaml:'OCaml'};
  const colors={stage1:'#8794a8',stage2:'#4977b8',ocaml:'#288779'};
  const queries={first:'首元素',last:'尾元素',absent:'不存在'};
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=x=>x==null?'—':Number(x).toLocaleString('en-US');
  const currentCase=()=>cases.find(c=>c.id===state.caseId);
  const current=()=>currentCase()?.rounds.find(r=>r.round_id===state.round);
  const label=x=>currentCase()?.implementations.find(i=>i.implementation_id===x)?.name||labels[x]||x||'未记录';
  const date=x=>x?new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(x)):'时间未记录';
  const money=x=>x==null?'未记录':'$'+x.toFixed(6);
  const config=b=>b.snapshot?.config||b.config;
  const dev=r=>r?.attempts?.find(a=>a.attempt===r.selected_attempt)?.development||r?.attempts?.at(-1)?.development;
  const statusNames={passed:'通过',running:'运行中',candidate_frozen:'已冻结',final_failed:'最终测试失败',attempt_budget_exhausted:'调用上限',budget_exhausted:'预算停止',api_error_unknown_billing:'API 异常',compile_failed:'编译失败',mismatch:'结果不一致',runtime_failed:'运行失败',protocol_failed:'输出异常',incomplete_response:'响应不完整'};
  const status=s=>statusNames[s]||s||'未执行';
  const tone=s=>s==='passed'?'pass':!s||['running','candidate_frozen'].includes(s)?'pending':'fail';
  const badge=s=>`<span class="status ${tone(s)}">${s==='passed'?'✓ ':''}${esc(status(s))}</span>`;
  const count=r=>{if(!r)return '未执行';if(r.count==null)return status(r.status);const p=r.status==='passed'?r.count:r.failures!=null?r.count-r.failures:null;return p==null?`${num(r.count)} 用例 · ${status(r.status)}`:`${num(p)} / ${num(r.count)}`;};
  const compiled=r=>dev(r)?.status==='passed'?'通过':dev(r)?.status==='compile_failed'?'失败':'未记录 / 查看反馈';
  const sum=(xs,f)=>xs.reduce((n,x)=>n+f(x),0);
  const json=x=>esc(JSON.stringify(x,null,2));
  const kv=(key,value)=>`<div class="kv"><dt>${esc(key)}</dt><dd>${value}</dd></div>`;
  const panel=(heading,content,extra='')=>`<section class="panel"><header class="panel-heading"><h2>${heading}</h2>${extra}</header>${content}</section>`;
  function render(){
    const c=currentCase();
    document.getElementById('case-count').textContent=cases.length;
    document.getElementById('cases').innerHTML=cases.map(x=>`<button class="history-item ${x.id===state.caseId?'active':''}" data-case="${esc(x.id)}" aria-current="${x.id===state.caseId?'page':'false'}"><span class="history-title">${esc(x.title)}</span><span class="history-meta">${x.rounds.length} 轮记录 · ${x.implementations.length} 个实现</span></button>`).join('');
    document.getElementById('export').disabled=!c;
    if(!c){document.getElementById('main').innerHTML='<div class="empty">还没有案例记录。</div>';return;}
    document.getElementById('breadcrumb').textContent=`案例 / ${c.title}${state.tab==='history'?' / '+state.round:''}`;
    document.getElementById('main').innerHTML=`<header class="experiment-heading"><div><h1>${esc(c.title)}</h1><p>${esc(c.target)} · ${esc(c.source_root)}</p></div><span class="subtle">${c.implementations.length} 个实现 · ${c.rounds.length} 轮记录</span></header><nav class="tabs" aria-label="案例内容"><button data-tab="overview" class="${state.tab==='overview'?'active':''}">总表</button><button data-tab="history" class="${state.tab==='history'?'active':''}">实验轮次与记录</button></nav>${data.notices.length?`<div class="notice">${data.notices.map(esc).join('<br>')}</div>`:''}${state.tab==='overview'?overview(c):history(c)}`;
    document.getElementById('footer').textContent=`${cases.length} 个案例 · ${sum(cases,c=>c.implementations.filter(i=>i.kind==='llm').length)} 次生成 · 刷新于 ${date(data.generated_at)}（UTC+8）`;
  }
  function selectedViews(c){
    return c.performance_views.filter(v=>(state.performanceRound==='all'||v.round_id===state.performanceRound)&&(state.measurement==='all'||v.id===state.measurement));
  }
  function selectedRows(c){
    const latest=new Map();
    for(const v of selectedViews(c))for(const r of v.rows){
      if(r.scope!==state.scope||r.length!==state.length||r.query!==state.query||r.values!==state.values)continue;
      latest.set(JSON.stringify([r.implementation,r.code_sha256,r.scope,r.length,r.query,r.values]),r);
    }
    return [...latest.values()];
  }
  function performanceFilters(c){
    const available=c.performance_views.filter(v=>state.performanceRound==='all'||v.round_id===state.performanceRound);
    if(state.measurement!=='all'&&!available.some(v=>v.id===state.measurement))state.measurement='all';
    const allRows=selectedViews(c).flatMap(v=>v.rows);
    const scopes=[...new Set(allRows.map(r=>r.scope))];
    if(scopes.length&&!scopes.includes(state.scope))state.scope=scopes[0];
    const scoped=allRows.filter(r=>r.scope===state.scope);
    const lengths=[...new Set(scoped.map(r=>r.length))].sort((a,b)=>a-b);
    if(lengths.length&&!lengths.includes(state.length))state.length=lengths.at(-1);
    const qs=[...new Set(scoped.filter(r=>r.length===state.length).map(r=>r.query))];
    if(qs.length&&!qs.includes(state.query))state.query=qs[0];
    const values=[...new Set(scoped.filter(r=>r.length===state.length&&r.query===state.query).map(r=>r.values))];
    if(values.length&&!values.includes(state.values))state.values=values[0];
    const select=(id,name,options,value,names={})=>`<label>${name} <select id="${id}" ${options.length?'':'disabled'}>${options.map(x=>`<option value="${x}" ${x===value?'selected':''}>${esc(names[x]||x)}</option>`).join('')}</select></label>`;
    return `<div class="total-filters">${select('performance-round','范围',['all',...c.rounds.map(r=>r.round_id)],state.performanceRound,{all:'总表'})}${select('measurement-select','测量',['all',...available.map(v=>v.id)],state.measurement,{all:'全部 · 每项取最新'})}${select('scope-select','口径',scopes,state.scope,{end_to_end:'端到端',kernel:'内核'})}${select('length-select','长度',lengths,state.length)}${select('query-select','查询',qs,state.query,queries)}${select('values-select','元素',values,state.values,{small:'小整数',large:'大整数'})}</div>`;
  }
  function overview(c){
    const filters=performanceFilters(c);
    const selected=c.implementations.find(i=>i.implementation_id===state.implementation);
    const detail=selected&&selected.kind!=='baseline'?inspector({runs:[selected]},0):baselineInspector(selected,c);
    return `${filters}<div class="results-layout"><div class="results-main">${implementationTable(c)}${latestPerformance(c)}</div>${detail}</div>`;
  }
  function implementationTable(c){
    const testRound=state.performanceRound==='all'?c.rounds.at(-1):c.rounds.find(r=>r.round_id===state.performanceRound);
    const checks=testRound?.baselines[c.id]?.checks||{};
    const rows=selectedRows(c),byId=new Map(rows.map(r=>[r.implementation,r]));
    const implementations=c.implementations.filter(i=>state.performanceRound==='all'||i.kind==='baseline'||i.round_id===state.performanceRound||byId.has(i.implementation_id));
    return panel(state.performanceRound==='all'?'结果总表':esc(state.performanceRound),`<div class="run-table-scroll"><table class="run-table" aria-label="案例结果总表"><thead><tr><th>实现</th><th>最终测试</th><th>耗时 μs</th><th>测量来源</th><th>重复次数</th></tr></thead><tbody>${implementations.map(i=>{const r=byId.get(i.implementation_id);return `<tr data-implementation="${esc(i.implementation_id)}" class="${state.implementation===i.implementation_id?'selected':''}"><td><button class="run-link" data-implementation="${esc(i.implementation_id)}">${esc(i.name)}</button></td><td>${count(i.kind==='baseline'?checks[i.implementation_id]?.final:i.final)}</td><td class="numeric">${r?(r.median_ns/1000).toFixed(3):'未测'}</td><td>${r?`<button class="run-link" data-measurement="${r.measurement_id}" data-measurement-round="${r.measurement_round}">${esc(r.measurement_round+'/'+r.measurement_id)}</button>`:'—'}</td><td class="numeric">${r?r.successful_rounds:'—'}</td></tr>`;}).join('')}</tbody></table></div><div class="panel-foot">${rows.length} / ${implementations.length} 个实现有当前条件的数据。相同实现与输入条件取最新记录，未重测项保留原值。<br>来源不同的行可能采用不同调用次数和计时配置，点击来源可筛到单次测量。</div>`,`<span class="subtle">${selectedViews(c).length} 份测量记录</span>`);
  }
  function baselineInspector(i,c){
    if(!i)return panel('实现详情','<div class="empty">选择一个实现</div>');
    return `<aside class="inspector panel" aria-label="选中实现详情"><header class="panel-heading"><h2>${esc(i.name)}</h2><span class="subtle">固定基线</span></header><div class="inspector-body"><dl class="compact-kv">${kv('案例',esc(c.title))}${kv('文件',esc(i.code_path))}${kv('代码校验',i.code_verified?'与固定基线哈希一致':'哈希不一致')}</dl><div class="code-heading"><h3>实现代码</h3><button id="copy-code">复制</button></div><pre class="code">${esc(i.code)}</pre><details><summary>相关文件与哈希</summary><pre>${json(i.files.map(f=>({path:f.path,sha256:f.sha256})))}</pre></details></div></aside>`;
  }
  function history(c){
    const b=current();
    return `<div class="round-toolbar"><label>实验轮次 <select id="round-select">${[...c.rounds].reverse().map(r=>`<option value="${r.round_id}" ${r.round_id===state.round?'selected':''}>${r.round_id}</option>`).join('')}</select></label><div class="segmented"><button data-history-tab="results" class="${state.historyTab==='results'?'active':''}">逐次结果</button><button data-history-tab="config" class="${state.historyTab==='config'?'active':''}">当时的方案与配置</button></div></div><div class="round-caption">${esc(c.id+'/'+b.round_id)} · ${esc(config(b).model||'模型未记录')} · ${date(b.runs[0]?.started_at)} · 原始档案 ${esc(b.experiment_id||b.id)}</div>${state.historyTab==='results'?results(b):configuration(b)}`;
  }
  function latestPerformance(c){
    const rows=selectedRows(c),views=selectedViews(c);
    const used=views.filter(v=>rows.some(r=>r.measurement_id===v.id));
    return panel('性能图',`${rows.length?`<div class="chart-caption"><span>与总表相同的数据 · μs · 越低越好</span><div class="segmented small"><button data-scale="log" class="${state.scale==='log'?'active':''}">对数</button><button data-scale="linear" class="${state.scale==='linear'?'active':''}">线性</button></div></div>${plot(rows)}`:'<div class="empty">当前筛选条件下没有性能数据。</div>'}<div class="panel-foot">点：各自测量的中位数；线段：最小—最大值。${used.length>1?'本图汇总多次测量，来源与重复次数见总表。':''}</div>${views.map(v=>`<details class="measurement"><summary>${esc(v.round_id+'/'+v.id)} · 配置与原始记录</summary><p>${v.measured_at?date(v.measured_at):'精确测量时间未记录'} · 登记序号 ${v.sequence}</p><p>${esc(v.source)}</p><pre>${json(v.protocol)}</pre><pre>${json(v.rows.filter(r=>r.scope===state.scope&&r.length===state.length&&r.query===state.query&&r.values===state.values))}</pre></details>`).join('')}`);
  }
  function results(b){
    const passed=b.runs.filter(r=>r.status==='passed').length;
    const pending=b.runs.filter(r=>!r.status||['running','candidate_frozen'].includes(r.status)).length;
    const failed=b.runs.length-passed-pending;
    return `<div class="summary-bar"><span><i class="dot pass"></i>通过 <strong>${passed}</strong></span><span><i class="dot ${failed?'fail':'neutral'}"></i>未通过 / 停止 <strong>${failed}</strong></span><span>未完成 <strong>${pending}</strong></span><span>修复 <strong>${sum(b.runs,r=>Math.max(0,(r.attempts?.length||0)-1))}</strong></span><span class="usage">${num(sum(b.runs,r=>r.usage.total_tokens))} tokens · 估算 ${money(b.cost)}</span></div><div class="results-layout"><div class="results-main">${runTable(b)}${roundMeasurements(b)}</div>${inspector(b)}</div>`;
  }
  function runTable(b){
    const filtered=b.runs.map((r,i)=>({r,i}));
    const size=25,pages=Math.max(1,Math.ceil(filtered.length/size));
    state.runPage=Math.min(state.runPage,pages-1);
    const start=state.runPage*size;
    const rows=filtered.slice(start,start+size).map(({r,i})=>{return `<tr data-run="${i}" class="${state.run===i?'selected':''}"><td>${esc(b.round_id)}</td><td><button class="run-link" data-run="${i}" aria-label="${esc(label(r.task)+' '+r.run_id)}" aria-pressed="${state.run===i}">${esc(r.run_id)}</button></td><td>${esc(compiled(r)==='未记录 / 查看反馈'?'—':compiled(r))}</td><td class="numeric">${count(dev(r))}</td><td class="numeric">${count(r.final)}</td><td class="numeric">${r.attempts?.length||0} / ${Math.max(0,(r.attempts?.length||0)-1)}</td><td><span class="status ${tone(r.status)}">${esc(status(r.status))}</span></td><td class="numeric">${money(r.cost_estimate)}</td></tr>`;}).join('');
    return panel('逐次结果',`<div class="run-table-scroll"><table class="run-table" aria-label="逐次运行结果"><thead><tr><th scope="col">轮次</th><th scope="col">运行编号</th><th scope="col">编译</th><th scope="col">开发测试</th><th scope="col">最终测试</th><th scope="col">调用 / 修复</th><th scope="col">状态</th><th scope="col">估算费用</th></tr></thead><tbody>${rows||'<tr><td colspan="8">还没有运行记录</td></tr>'}</tbody></table></div><div class="run-table-footer"><span>${filtered.length?start+1:0}–${Math.min(start+size,filtered.length)} / ${filtered.length} 条 · 点击行查看详情</span>${pages>1?`<div class="pagination"><button data-run-page="${state.runPage-1}" ${state.runPage===0?'disabled':''}>上一页</button><span>${state.runPage+1} / ${pages}</span><button data-run-page="${state.runPage+1}" ${state.runPage+1===pages?'disabled':''}>下一页</button></div>`:''}</div>`,`<span class="subtle">${b.runs.length} 次生成</span>`);
  }
  function inspector(b,index=state.run){
    const r=b.runs[index];
    if(!r)return panel('运行详情','<div class="empty">选择一次运行</div>');
    const repair=Math.max(0,(r.attempts?.length||0)-1);
    return `<aside class="inspector panel" aria-label="选中运行详情"><header class="panel-heading"><h2>${esc(r.round_id)} / ${esc(r.run_id)}</h2>${badge(r.status)}</header><div class="inspector-body"><dl class="compact-kv">${kv('引用编号',esc(r.reference))}${kv('配置来源',r.own_config?'本次追加实现的独立配置':'所属轮次的冻结配置')}${kv('编译',esc(compiled(r)))}${kv('开发测试',count(dev(r)))}${kv('最终测试',count(r.final))}${kv('调用 / 修复',`${r.attempts?.length||0} / ${repair}`)}${kv('用量 / 估算费用',`${num(r.usage.total_tokens)} / ${money(r.cost_estimate)}`)}</dl><h3>生成过程</h3><div class="attempts">${(r.attempts||[]).map(a=>`<div><span class="attempt-number">${a.attempt}</span><span>${a.attempt===1?'首次生成':'反馈修复'}</span>${badge(a.development?.status)}</div>`).join('')}</div><div class="code-heading"><h3>已保存的候选代码</h3><button id="copy-code" ${r.code?'':'disabled'}>复制</button></div><pre class="code">${esc(r.code||'没有可展示的候选代码。')}</pre><p class="hash-state">${r.code_verified===true?'✓ 与记录哈希一致':r.code_verified===false?'! 代码哈希不一致':'未核对代码哈希'}</p>${r.own_config?`<details><summary>该实现的方案与配置</summary><pre>${json(r.own_config)}</pre></details>`:''}<details><summary>测试反馈与反例</summary><pre>${json({attempts:(r.attempts||[]).map(a=>({attempt:a.attempt,development:a.development})),final:r.final})}</pre></details><details><summary>时间、文件与哈希</summary><dl>${kv('开始时间',esc(date(r.started_at)))}${kv('文件',esc(r.code_path||'未记录'))}${kv('SHA-256',esc(r.code_sha256||'未记录'))}</dl></details></div></aside>`;
  }
  function roundMeasurements(b){
    const views=currentCase().performance_views.filter(v=>v.round_id===b.round_id);
    return panel('测量记录',`${views.map(v=>`<details class="measurement"><summary>${esc(v.id)}</summary><p>${esc(v.reference)} · ${v.measured_at?date(v.measured_at):'时间未记录'}</p><p>${esc(v.source)}</p><pre>${json(v.protocol)}</pre><pre>${json(v.rows)}</pre></details>`).join('')}${!views.length?'<div class="panel-foot">本轮没有性能测量。</div>':''}`);
  }
  function plot(rows){
    const max=Math.max(...rows.map(r=>(r.max_ns||r.median_ns)/1000));
    const min=Math.min(...rows.map(r=>(r.min_ns||r.median_ns)/1000).filter(x=>x>0));
    const lo=Math.floor(Math.log10(min)),hi=Math.max(lo+1,Math.ceil(Math.log10(max)));
    const ticks=state.scale==='log'?Array.from({length:hi-lo+1},(_,i)=>10**(lo+i)):Array.from({length:5},(_,i)=>max*1.1*i/4);
    const x=n=>100*(state.scale==='log'?(Math.log10(Math.max(n,10**lo))-lo)/(hi-lo):n/(max*1.1));
    const tick=n=>n>=1000?(n/1000).toLocaleString('en-US',{maximumFractionDigits:1})+'k':n.toLocaleString('en-US',{maximumFractionDigits:2});
    const description=`${label(state.task)} 各实现耗时，${state.scale==='log'?'对数':'线性'}刻度，单位微秒。`+rows.map(r=>`${label(r.implementation)} ${(r.median_ns/1000).toFixed(3)}`).join('；');
    return `<div class="performance-chart-scroll"><div class="performance-plot" role="img" aria-label="${esc(description)}"><div class="plot-labels">${rows.map(r=>`<div class="plot-row plot-label">${esc(label(r.implementation))}</div>`).join('')}</div><div class="plot-area"><div class="plot-grid">${ticks.map(t=>`<span style="left:${x(t)}%"></span>`).join('')}</div>${rows.map(r=>{const low=x((r.min_ns||r.median_ns)/1000),high=x((r.max_ns||r.median_ns)/1000),color=colors[r.implementation]||'#65738a';return `<div class="plot-row plot-track"><span class="plot-range" style="left:${low}%;width:${high-low}%;background:${color}"></span><span class="plot-dot" style="left:${x(r.median_ns/1000)}%;background:${color}" title="${esc(label(r.implementation))}: ${(r.median_ns/1000).toFixed(3)} μs"></span></div>`;}).join('')}<div class="plot-axis">${ticks.map(t=>`<span style="left:${x(t)}%">${tick(t)}</span>`).join('')}</div></div><div class="plot-values">${rows.map(r=>`<div class="plot-row chart-number">${(r.median_ns/1000).toFixed(3)} μs</div>`).join('')}</div></div></div>`;
  }
  function configuration(b){
    const c=config(b),s=b.snapshot;
    const tabs=[['parameters','执行方案与参数'],['tests','测试与环境'],['prompts','实际提示词'],['plan','方案原文快照']];
    const nav=`<nav class="config-nav" aria-label="历史配置分类">${tabs.map(([id,name])=>`<button data-config-tab="${id}" class="${state.configTab===id?'active':''}" aria-pressed="${state.configTab===id}">${name}</button>`).join('')}</nav>`;
    let content='';
    if(state.configTab==='parameters'){
      const known=['direct-two-task-v2','direct-list-index-smoke-v1'].includes(c.protocol_id||c.task_id);
      content=`<div class="snapshot-state">${s?'✓ 原始轮次配置；后续追加实现的独立配置在对应运行详情中。':'本组没有独立快照；以下为结果摘要保存的配置。'}</div><dl class="config-kv">${kv('案例 / 轮次',esc(state.caseId+'/'+b.round_id))}${kv('原始档案编号',esc(b.experiment_id||'未编号'))}${kv('代码目录',esc(currentCase().source_root))}${kv('方案版本',esc(c.plan_id||'未记录'))}${kv('执行协议',esc(c.protocol_id||c.task_id||'未记录'))}${kv('采用的流程',known?'固定 Isabelle → 直接生成 Rust → 编译与开发测试 → 首个通过候选冻结 → 最终测试':esc(c.route||'见原始配置'))}${kv('模型看到的信息',known?'Isabelle 定义、语义说明与 Rust 接口；不提供参考实现源码':'见实际提示词')}${kv('参考实现',Object.keys(b.baselines).length?'Isabelle → OCaml / Stage 1 Rust / Stage 2 Rust':'未记录')}${kv('模型 / 模式',esc(c.model||'未记录')+' / '+(c.thinking?.type==='disabled'?'非思考':'见配置'))}${kv('Temperature / 输出上限',`${esc(c.temperature??'未记录')} / ${num(c.max_tokens)} tokens`)}${kv('每任务重复 / 每运行调用上限',`${c.independent_runs_per_task||c.independent_runs||'未记录'} / ${c.max_calls_per_run||c.max_calls||'未记录'}`)}${kv('候选选择',known?'首个通过开发测试的候选；最终测试不反馈、不重新选择':esc(c.candidate_selection||'未记录'))}${kv('性能测量',b.performance?'已测 '+esc(label(b.performance.protocol.task)):'本组未测量')}</dl><details><summary>原始批次配置 JSON（可能包含其他案例）</summary><pre>${json(c)}</pre></details>`;
    }else if(state.configTab==='tests'){
      content=`<h2>测试集与参考执行</h2><div class="table-scroll"><table><thead><tr><th>任务</th><th>开发用例 / 次</th><th>最终用例 / 次</th><th>OCaml</th><th>Stage 1</th><th>Stage 2</th><th>负向检查</th></tr></thead><tbody>${b.tasks.map(t=>{const r=b.runs.find(r=>r.task===t);return `<tr><th>${esc(label(t))}</th><td>${num(dev(r)?.count)}</td><td>${num(r.final?.count)}</td>${['ocaml','stage1','stage2'].map(k=>`<td>${count(b.baselines[t]?.checks[k]?.final)}</td>`).join('')}<td>${b.baselines[t]?.negative_control?.failures??'未记录'}${b.baselines[t]?.negative_control?.failures!=null?' 个不一致':''}</td></tr>`;}).join('')}</tbody></table></div><p class="small-note">基线列为最终测试结果。负向检查使用人工错误候选，不计入模型运行。通过仅覆盖记录的测试输入。</p><h2>当时的环境</h2><dl class="config-kv">${Object.entries(b.environment).map(([k,v])=>kv(k,esc(v))).join('')}</dl><details><summary>测试构造与性能协议（原始配置）</summary><pre>${json(Object.fromEntries(Object.entries(c).filter(([k])=>/test|development|final|performance/.test(k))))}</pre></details><details><summary>源文件、测试数据及执行协议哈希</summary><pre>${s?json({protocol:s.protocol_sha256,frozen:s.frozen_sha256}):'本组未发布独立快照'}</pre></details>`;
    }else if(state.configTab==='prompts'){
      const task=b.tasks.includes(state.promptTask)?state.promptTask:b.tasks[0];
      content=`<div class="segmented">${b.tasks.map(t=>`<button data-prompt-task="${esc(t)}" class="${task===t?'active':''}">${esc(label(t))}</button>`).join('')}</div><p class="small-note">${s?'来自运行前保存的 prompt.txt，原始哈希已核对。':'没有冻结提示词快照；若有公开提示词，列于下方。'}</p><pre class="prompt">${esc(s?.prompts[task]||b.prompts[task]||'未保存可展示提示词')}</pre>`;
    }else{
      content=`<p class="small-note">这是实验当时保存的方案原文。保留原文中的“待定”等状态；实际执行参数见“执行方案与参数”。</p>${s?Object.entries(s.plans).map(([path,text])=>`<h2>${esc(path)}</h2><pre class="prompt">${esc(text)}</pre>`).join(''):'<div class="empty">未保存方案快照，不使用当前方案文件替代历史版本。</div>'}`;
    }
    return `<div class="configuration-layout">${nav}<section class="panel config-content">${content}</section></div>`;
  }
  document.addEventListener('click',async e=>{
    const b=e.target.closest('button')||e.target.closest('tr[data-run],tr[data-implementation]');if(!b)return;
    if(b.dataset.case){state.caseId=b.dataset.case;state.measurement='all';state.performanceRound='all';state.task=b.dataset.case;state.round=currentCase().rounds.at(-1)?.round_id;state.implementation=currentCase().implementations.find(i=>i.round_id===state.round)?.implementation_id;state.tab='overview';state.run=0;state.runPage=0;state.configTab='parameters';state.promptTask=null;render();}
    else if(b.dataset.tab){state.tab=b.dataset.tab;render();}
    else if(b.dataset.historyTab){state.historyTab=b.dataset.historyTab;render();}
    else if(b.dataset.measurement){state.measurement=b.dataset.measurement;state.performanceRound=b.dataset.measurementRound;render();}
    else if(b.dataset.implementation){state.implementation=b.dataset.implementation;const selected=currentCase().implementations.find(i=>i.implementation_id===state.implementation);if(selected?.round_id){state.round=selected.round_id;state.run=current().runs.findIndex(r=>r.reference===selected.reference);}const scroller=document.querySelector('.results-main'),top=scroller?.scrollTop||0;render();document.querySelector('.results-main').scrollTop=top;}
    else if(b.dataset.run!=null){const table=document.querySelector('.run-table-scroll'),top=table?.scrollTop||0,left=table?.scrollLeft||0;state.run=Number(b.dataset.run);render();const updated=document.querySelector('.run-table-scroll');if(updated){updated.scrollTop=top;updated.scrollLeft=left;}}
    else if(b.dataset.runPage!=null){state.runPage=Math.max(0,Number(b.dataset.runPage));render();}
    else if(b.dataset.scale){state.scale=b.dataset.scale;render();}
    else if(b.dataset.configTab){state.configTab=b.dataset.configTab;render();}
    else if(b.dataset.promptTask){state.promptTask=b.dataset.promptTask;render();}
    else if(b.id==='refresh')location.reload();
    else if(b.id==='export'){const c=currentCase(),url=URL.createObjectURL(new Blob([JSON.stringify(c,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=c.id+'-case.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
    else if(b.id==='copy-code'){const r=state.tab==='overview'?currentCase().implementations.find(i=>i.implementation_id===state.implementation):current().runs[state.run];try{await navigator.clipboard.writeText(r.code);b.textContent='已复制';}catch(_){b.textContent='请手动选取复制';}}
  });
  document.addEventListener('change',e=>{
    if(e.target.id==='performance-round'){state.performanceRound=e.target.value;state.measurement='all';if(state.performanceRound!=='all'){state.round=state.performanceRound;state.run=0;state.implementation=currentCase().implementations.find(i=>i.round_id===state.performanceRound)?.implementation_id||'stage1';}render();}
    else if(e.target.id==='scope-select'){state.scope=e.target.value;render();}
    else if(e.target.id==='measurement-select'){state.measurement=e.target.value;render();}
    else if(e.target.id==='round-select'){state.round=e.target.value;state.run=0;state.runPage=0;state.configTab='parameters';state.promptTask=null;render();}
    else if(e.target.id==='length-select'){state.length=Number(e.target.value);render();}
    else if(e.target.id==='query-select'){state.query=e.target.value;render();}
    else if(e.target.id==='values-select'){state.values=e.target.value;render();}
  });
  render();
})();

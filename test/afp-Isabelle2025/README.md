# AFP 全量实验

从官方 AFP 2025 源码扫描全部条目，执行 Rust、SML、OCaml、Haskell、Scala、Go 六语言导出及编译。Rust crate 做 Stage 1 编译、既有优化器转换和 Stage 2 编译。SML、OCaml、Haskell、Scala、Go 的导出源码也产生独立的编译回执。原 AFP 理论自身的 checking 和 Quickcheck 属于原会话构建。

## 从 clone 到运行

面向 Ubuntu x86_64、Python 3.10 以上。安装目录需要容纳 Isabelle、完整 AFP、GHC 及构建缓存。

```bash
mkdir afp-workspace
cd afp-workspace
git clone https://github.com/OpenSourceVerif/Isabelle2Rust.git
cd Isabelle2Rust/test/afp-Isabelle2025
```

AFP 的 Native_Word 使用 `Pervasives`，需要 OCaml 4；OCaml 5 无法编译该适配。先安装独立的 OCaml 4.14.2 switch，并用包装脚本固定编译器和库搜索路径：

```bash
sudo apt-get update
sudo apt-get install -y opam build-essential m4 pkg-config libgmp-dev
opam init --bare -y
opam switch create afp2025 ocaml-base-compiler.4.14.2
opam install --switch=afp2025 -y ocamlfind zarith
mkdir -p "$HOME/afp-deps"
cat > "$HOME/afp-deps/ocamlfind" <<EOF
#!/bin/sh
exec "$(command -v opam)" exec --root="$(opam var root)" --switch=afp2025 -- ocamlfind "\$@"
EOF
chmod +x "$HOME/afp-deps/ocamlfind"
```

安装其余依赖并生成本机配置：

```bash
python3 setup/install.py --prefix "$HOME/afp-deps" \
  --ocamlfind "$HOME/afp-deps/ocamlfind" --dry-run
python3 setup/install.py --prefix "$HOME/afp-deps" \
  --ocamlfind "$HOME/afp-deps/ocamlfind"
python3 tools/afp.py check
python3 tools/afp.py smoke
python3 tools/afp.py run
```

安装器按 [dependencies.json](setup/dependencies.json) 的版本和摘要下载依赖，包含 Isabelle2025、官方 AFP 2025-03-17、Rust 1.94.0、Go、CakeML 及 GHC。缺失的 RustLightAST 会克隆到本仓库的同级目录并固定提交；已有 checkout 必须干净且提交匹配。系统包使用 sudo，其他依赖使用指定安装根。管理员已装系统包时可传 `--skip-system-packages`。

已有依赖时可使用 `setup/install.py --configure-only`，通过 `--isabelle`、`--afp`、`--go-root`、`--cakeml`、`--ocamlfind` 指定路径；或按 [server.example.json](setup/server.example.json) 创建配置。默认以安装根下的 `USER_HOME` 隔离 Isabelle 配置和缓存，可用 `--user-home` 指定已有用户目录。

## 配置与状态

| 文件或目录 | 职责 |
| --- | --- |
| `setup/dependencies.json` | 提交到 Git 的依赖版本、下载地址和摘要；安装输入，不是实验进度。 |
| `setup/server.local.json` | 唯一本机配置：安装路径、资源参数、`compilers`、已安装系统包版本和最近一次环境检查。 |
| `work/state.sqlite3` | 唯一运行状态库：输入清单和摘要、当前会话结果、导出待办队列、当前条目/编译结果、各阶段检查点和最近一次审计。 |
| `work/units/`、`exports/`、`compilation/`、`rust-stage2/` | 当前结果及未完成工作所需的原始日志、XML 和生成源码。 |
| `work/report/` | 按需生成的 CSV、Markdown、`summary.json`、`failures.jsonl`；可重新生成，不参与恢复。 |
| `work/_build/` 等 | 可再生的构建缓存。 |

扫描候选从当前原生 XML 推导，覆盖统计从当前结果计算，不另存候选基线、全量结果副本或条目版本链。命令状态及回执直接写入 SQLite，不生成一组 JSON 边车文件。替换结果通过数据库事务发布，之后删除被替代的尝试；恢复时也回收中断留下的无主尝试。执行中只保留当前已提交结果和尚未发布的替换工作。

回执保存当前会话的完成状态及原始文件摘要，用于判断能否跳过昂贵构建。阶段检查点只记录当前输入签名、检查结果和问题；后续阶段必须与该签名匹配。审计重新核对 XML、源码、编译记录及报告，覆盖写入最近一次检查结果。这些记录都在同一个状态库中。

默认单作业、单证明线程、开启证明、阶段不限时；ML heap 4500 MiB、Java heap 1536 MiB、stackspace 512 MiB、JVM 活动处理器 2、最低可用内存 512 MiB。可在本机配置的 `resources` 中调整；heap 参数不是总 RSS 上限。

本机配置的 `scheduler` 独立控制 `build_jobs`、`threads`、`parallel_proofs`、`export_workers`、`compile_workers`、`cargo_jobs`。作业及线程数默认 1，`parallel_proofs` 默认 0（可选 0、1、2）。例如大内存服务器可分别设为 `8, 8, 2, 8, 8, 8`：8 个导出条目同时运行，每个 Isabelle 进程使用 8 线程；8 个编译条目同时进行 Stage-1、既有优化器和 Stage-2，每个 Cargo 最多 8 个编译作业。

每个条目内的原生请求和三个 Rust 步骤按原顺序执行。编译槽使用独立、可复用的 Cargo target 目录，避免共享目录锁使作业串行；优化器只预编译一次。各条目使用独立惰性状态读取器，断点按条目事务提交；中断会取消并回收各自的子进程。总内存应同时考虑外层作业数和各进程的 ML/Java heap，可用服务 cgroup 限制总量。

## 条目流水线（fixed-plan-v3）

使用新的空工作根启动，重复同一命令可恢复。

```bash
python3 tools/afp.py --config setup/server.local.json --work /path/work-fixed-v3 run
python3 tools/afp.py --config setup/server.local.json --work /path/work-fixed-v3 status
python3 tools/afp.py --config setup/server.local.json --work /path/work-fixed-v3 export-checkpoint --entries List-Index
```

扫描按 Isabelle session 的依赖推进。条目所属会话均有可核验终态后，立即用成功扫描的范围生成计划。源码失败和依赖阻塞单列。计划冻结即进入导出队列。每个闭合六目标请求的 Rust crate 可独立进入 Stage 1、优化和 Stage 2。编译阶段随后读取已发布的 SML、OCaml、Haskell、Scala、Go 源码和原生回执，并按目标编译。

`scheduler.plan_workers` 独立于 `export_workers` 和 `compile_workers`，默认 2。每个编译槽使用独立的 Cargo target 目录。分析不限时。中断保留恢复点，`run --retry-failed` 可在排除环境问题后重试未决扫描。

候选以条目、扫描会话、独立最大理论分支、所属理论和原生常量名标识。共享声明在每个可见分支各自分类、去重入口和分组。白名单异常仅触发分支内二分。单根复现才记为 `frontend_rejected`。隔离出新拒绝后，剩余根最多联合分析一次。未可靠处置的候选分别冻结六目标单根请求，以实际回执记录直接导出结果。

`run`、`scan`、`plan`、`export`、`compile` 和各阶段检查点支持 `--entries`。条目发布核对输入、分支处置和产物证据。最终对账覆盖完整 manifest，报告包含 `declarations.csv` 的逐分支结果及 `summary.json` 的汇总。存在待办或未决时生成未完成报告并返回非零状态。

### Rust 数值配置和单目标重跑

AFP 的扫描后分析与 Rust 导出使用 `Rust.Rust_Source_BigInt_Setup`。HOL 的 `nat`、`int` 和 `integer` 分别映射到以 `BigInt` 为基础的 `Nat`、`Int` 和 `Integer`。独立的 Rust 类型让 trait 实例维持各自的运算语义，包括截断到零的自然数减法。

从具有完整审计的批次重跑 Rust 时，指定独立的输出目录。

```bash
python3 tools/afp.py --config setup/server.local.json --work /path/rust-source-bigint \
  rust-replay --from-work /path/work-fixed-v3
```

`rust-replay` 逐组读取冻结请求，复用原理论分支和入口常量，使用当前数值配置重新生成 Rust 源码。每个编译输入依次执行 Cargo Stage 1、既有优化器和 Cargo Stage 2。同一编译配置下，源码和相对文件布局相同的 crate 共享编译回执。完成后，`report/rust-replay.csv` 按导出组记录三步结果和证据位置，`report/summary.json` 汇总结果。命令可带 `--entries` 运行选定条目，也可用相同参数续跑已有输出目录。

### 五种其他目标的编译

`run` 和 `compile` 都包含这一步。对于已发布的 fixed-plan-v3 工作根，可独立补编或恢复此阶段。

```bash
python3 tools/afp.py --config setup/server.local.json --work /path/work-fixed-v3 compile-targets
python3 tools/afp.py --config setup/server.local.json --work /path/work-fixed-v3 compile-targets --entries Open_Induction
```

| 目标 | 编译方式 |
| --- | --- |
| SML | Isabelle 随附的 MLton 生成对象文件，使用标准引用适配 Isabelle 的 `Unsynchronized`。32 MiB 起使用同套 Isabelle 附带的全字长 Poly/ML 生成对象文件，关闭可选内联和低层优化 |
| OCaml | 配置的 OCaml 4.14 原生编译器生成对象文件，使用 Zarith |
| Haskell | Isabelle 的 GHC 编译整个导出模块树 |
| Scala | Isabelle 自带的 Scala 3 编译器和语法参数生成类文件，每个源码树单独编译 |
| Go | 配置的 Go 编译器离线构建单文件或整个模块 |

编译使用每个请求的封存源码和独立输出目录，相同源码字节、文件布局及编译器输入可复用回执。构建产物仅用于验证编译，编译日志及其摘要供复核。`report/target-compilation.csv` 按冻结导出组和语言记录通过、失败、超时、仅库映射及无导出源码。超时是待处理结果。编译检查点核对这个表与当前导出状态的签名。五目标编译与 Rust 三步使用同一项 `scheduler.compile_workers` 配置。带 `--entries` 的编译将子集回执写入独立的报告文件。

服务器原生验收覆盖两个独立分支、六目标和 Rust 两阶段编译。验收根使用新路径。

```bash
AFP_ENTRY_TEST=1 AFP_ENTRY_WORK=/path/to/new/acceptance python3 -B -m unittest discover -s tests -p 'test_entry_pipeline_native.py'
```

## 历史 v2 运行方式

以下命令适用于创建 v2 工作根所用的冻结代码版本。

`run` 自动依次执行环境检查、必要的初始化、扫描、扫描检查点、依赖分析与固定计划、计划检查点、固定分组导出、导出检查点、编译、编译检查点、数据审计、报告及报告审计。固定计划只在当前工作根生成；输入或规则变化会使计划检查点失效。任何一步失败即停止。

```bash
# 首次运行或恢复中断；已完成的会话、请求和编译步骤会复用。
python3 tools/afp.py run
python3 tools/afp.py status
# 排除环境问题后，额外重试已有失败扫描；完整会话仍然跳过。
python3 tools/afp.py run --retry-failed
```

也可逐阶段执行：

```bash
python3 tools/afp.py init
python3 tools/afp.py scan
python3 tools/afp.py scan-checkpoint
python3 tools/afp.py plan
python3 tools/afp.py plan-checkpoint
python3 tools/afp.py export
python3 tools/afp.py export-checkpoint
python3 tools/afp.py compile
python3 tools/afp.py compile-checkpoint
python3 tools/afp.py audit
python3 tools/afp.py report
python3 tools/afp.py audit --with-report
```

`init` 要求空工作根；重复初始化会拒绝。自定义配置或工作根放在子命令前，例如 `python3 tools/afp.py --config /path/server.json --work /path/empty-work run`。`plan --entries List-Index`、`export --entries List-Index`、`compile --entries List-Index` 可只处理指定条目，但检查点仍校验全体条目。正式导出从计划读取固定上下文、入口、模块名和六种目标；旧的动态分组仅能通过显式诊断路径运行，不能迁移为固定计划结果。

检查点通过表示该阶段有完整、可解释的结果，不表示每个候选都成功。超时、内存不足、丢失进程结果或缺少必需理论属于未决状态，不能据此进入下一阶段。每个扫描会话须覆盖自身全部所属理论，条目须覆盖其会话并集。恢复拒绝复用输入源码、编译器或流水线代码已改变的结果；这些变化需要新工作根。资源上限可调整后重试。

## 失败后的固定处置（v2）

新工作根采用 fixed-plan-v2 / afp-structural-v2；旧工作根不迁移，不覆盖其摘要。
正常严格 Thingol 分析、候选分类、入口去重和分组算法保持原样，不额外逐候选分析。

只有计划分析失败才启用恢复。回执分别记录上下文准备、严格前端、证据提取及计划处理错误。
仅 Isabelle2025 严格前端的完整原生异常符合白名单时，按声明身份稳定二分；只有单根失败才能
标为 frontend_rejected。白名单涵盖类型类排序、明确非法方程模式、错误方程头、抽象违规及
原生方程变换的明确类型/证明/策略失败。未知异常、资源或服务问题保持未决；中断停止调度。

成功隔离后，剩余根联合分析最多尝试一次；没有新增拒绝不重试原批次。仍未决时，把影响范围内
未排除的每个声明冻结为 singleton_fallback 请求，包含被入口去重省略的声明。
无可靠分组时范围为整个上下文；缺少合法上下文或归属时保留 unresolved_context。
原失败及全部隔离回执存入同一个 SQLite 状态库，并封存对应原生证据。

计划检查点只表示“处置清单完整且请求有效”，不表示每个候选分析成功。合法局部未决不妨碍其他
范围执行。正式导出执行已经冻结的六语言请求，不动态拆分、改参数或修改计划。
单根前端成功且六目标有完整终态，或单根有白名单拒绝证据，才闭合请求；后者不计导出成功。
未知异常、资源/服务失败、缺失回执继续未决。恢复复用闭合请求；未决请求每次调用只尝试一次。

计划与导出报告分别统计原始候选、既有排除、前端拒绝、正常覆盖、回退及最终未决。
plan-dispositions.jsonl 保存逐声明处置，summary.json 提供条目与候选两种统计。
回退成功只计直接导出证据，不声称结构覆盖。全部请求处理后再评估导出检查点；未通过时生成
明确标注未完成的报告，并阻止全量编译、优化和最终成功声明。

计划和导出沿用配置中的 export_workers 并行槽，各请求保留固定父理论、会话、模块和六目标。
小型原生回归仅在服务器显式执行，证据根须是新路径：

~~~bash
AFP_RECOVERY_TEST=1 AFP_RECOVERY_WORK=/path/to/new/acceptance \\
  python3 -B -m unittest discover -s tests -p 'test_recovery_native.py'
~~~

## 验证与清理

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py'
# 小型真实六语言导出及 Rust 两阶段编译，临时数据自动删除。
python3 tools/afp.py smoke
# 清理缓存，默认预览；当前结果和恢复状态保留。
python3 tools/afp.py clean
python3 tools/afp.py clean --apply
# 重新编译，或重新导出及其下游阶段。
python3 tools/afp.py clean --reset compile --apply
python3 tools/afp.py clean --reset export --apply
```

重置会先使相应结果和检查点失效，再删除产物。清理拒绝活跃流水线、逃逸路径、符号链接及共享依赖目录。若需要从扫描开始全量重跑，使用新的空工作目录；不需要旧结果时可以删除旧工作目录。依赖安装、Isabelle heap 和 sibling RustLightAST 无需一起删除。


### Explicit continuation while analysis remains live

When the user explicitly defers an unfinished entry, keep its original analysis
process and freeze a separate continuation from a consistent SQLite backup:

```sh
python3 tools/afp.py --config setup/server.local.json --work /new/work defer \
  --from-work /original/work --entries AutoCorres2 \
  --reason 'User requested preserving analysis and singleton fallback continuation'
python3 tools/afp.py --config setup/server.local.json --work /new/work continue
```

Use a separate frozen source checkout for the continuation. Suspend only the
original outer phase coordinator if it would otherwise advance into export;
do not suspend its analysis worker or native descendants. The parent work root
stays intact. Only sealed evidence is copied (copy-on-write where supported);
active logs and subsequently completed analysis are never imported. The new
SQLite database records the original input/tool identity, relocated evidence
locators, cutoff and explicit authorization. Native analysis, classifier,
grouping and serializer inputs must be unchanged.

Existing receipts are replayed. Missing requests in authorized entries become
explicit `user_deferred` failures, yielding the same singleton fallback rules;
missing or damaged inherited evidence still fails validation. The plan gate
certifies disposition completeness, not successful analysis.

The continuation uses bounded queues across the already frozen requests. Each
closed six-target request with a successful Rust artifact may immediately enter
stage-one compilation, optimization and stage-two compilation. Export and
compilation progress stay in the same SQLite database; completed requests and
compiler results are reused after interruption. Unknown failures are attempted
once per invocation and remain resumable. No failed request is split, regrouped
or retuned. The final export gate, audit and completion declaration remain
strict: unresolved requests produce an explicitly incomplete report even when
other requests have finished both Rust stages.

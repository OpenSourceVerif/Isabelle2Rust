# AFP 冻结扫描迁移与重新导出

面向联网 Ubuntu x86_64，只整理 AFP 工具测试，不改翻译器、优化器及其他测试。推荐入口为 `tools/afp.py`：从现有冻结候选重新开展六语言导出，再做 Rust stage1 编译、既有优化器转换和 stage2 编译。不补扫，不执行生成程序。

```text
README.md   安装、迁移、运行、清理
 tools/     扫描、导出、编译与审计工具
 tests/     AFP 工具回归及固定夹具
 setup/     安装器、配置模板、依赖锁、源补丁、迁移清单
 scan/      完整冻结扫描，保持原字节
 report/    2026-10-28 报告、历史统计与精选案例证据
 work/      新运行的检查点、回执、日志和生成产物，初始为空
```

## 数据保留与迁移

`scan/` 完整来自 `full/scan-frozen-2026-10-22`，包括快照、回执、XML、日志、失败数据库、工具快照及修复记录。8,603 个文件迁移前后逐项 SHA256 一致。状态仍为 **662 通过、3 失败、228 阻塞**，全部 893 条目、922 会话、157,623 个不同内部候选名（163,502 个条目内候选引用）均保留。原扫描检查点未通过，保持原字节和真实状态。

唯一报告为 [2026-10-28 扫描与导出报告](report/README.md)。按正文及 `additional-mechanisms.md` 的详析案例保留原始证据和引用源码，见 [精选证据清单](report/selected-evidence.jsonl)：包含原路径、新路径、SHA256、大小、用途。全量导出及旧编译证据已经清理，原统计未重算，无法逐项重新核验；见 [历史索引边界](report/HISTORICAL-INDEXES.md)。新报告写入 `work/report/`，不会覆盖历史 `report/`。

[迁移记录](setup/migration.json) 保存原编译驱动及子进程身份、停止结果和保留清单；[精确删除清单](setup/deletion-inventory.json) 记录旧路径、文件数、大小和仅移除的符号链接。旧驱动先按 boot/PID/出生身份核对，发中断信号并确认退出后才清理。清理仅涉及 AFP 实验及 `temp/afp-logs-before-report-20261020T074609Z`，未删除共享依赖目标。顶层 ROOT 中旧 AFP 生成会话块已移除。

**不能只依靠 Git 迁移数据。** `scan/`、`report/evidence/` 及大体积历史 CSV/JSONL 被忽略。代码 clone 后，必须另传完整 `scan/` 和完整 `report/`，保留层级。例如从仓库根执行：

```bash
rsync -a test/afp-Isabelle2025/scan/ SERVER:/srv/workspace/Isabelle2Rust/test/afp-Isabelle2025/scan/
rsync -a test/afp-Isabelle2025/report/ SERVER:/srv/workspace/Isabelle2Rust/test/afp-Isabelle2025/report/
```

不要打包旧 heap、Cargo target 或历史 `work/`。冻结证据中的历史路径不批量改写；通过运行配置及固定旧扫描前缀解析。查询精选旧路径可用 `python3 tools/afp.py path '原路径'`，已清理的引用会报错。

## 从零安装

建议 Ubuntu 24.04/26.04，Python 3.10 以上。先 clone 本仓库、传输保留数据，再进入 AFP 主目录。安装根需有足够空间容纳 Isabelle、AFP、GHC 和新 heap。

```bash
cd test/afp-Isabelle2025
# 完整预览：不下载、不写文件、不调用 sudo。
python3 setup/install.py --prefix "$HOME/afp-deps" --dry-run
# 系统包使用 sudo；其他依赖安装在指定根及当前用户 Rust 目录。
python3 setup/install.py --prefix "$HOME/afp-deps"
```

安装可重复执行：下载后校验固定摘要再解包；已有安装交给最终版本、源身份检查，不覆盖已有不同提交的 RustLightAST。管理员已装系统包时用 `--skip-system-packages`。系统包覆盖 C/C++、OCaml/findlib/Zarith、SML/NJ、GMP/Jansson、Isabelle 运行库等，实际 apt 版本记录在 `setup/installed.local.json`。

[依赖锁](setup/dependencies.json) 固定 Isabelle2025、AFP 2025-03-17、Rust **1.94.0**（含 rustfmt/clippy）、Go 1.26.8、CakeML 2.0、配套 GHC 9.6.6 和 RustLightAST 提交；MLton、Scala 使用 Isabelle 自带组件。RustLightAST 必须与本仓库同级，安装器在缺失时克隆并固定为 `897fec3808d9053337e9cea54ff77b3a7e1d3e60`，已有 checkout 须干净且提交一致。优化器与生成 crate 的依赖按各自 Cargo 锁文件预取，后续优化器构建可离线执行。

AFP 包 SHA256 为 `c41fbd7b48d1023ddf6b34501eceb5480caf6e5bb6985905eeea0aef203ee4e3`。与发行包比较，冻结树额外含 24 个此前生成的 ML/Haskell/Scala 源文件；[补丁](setup/patches/afp-2025-frozen.patch) 仅恢复这些冻结输入，[差异清单](setup/afp-source-differences.json) 记录身份。补丁后全部 13,769 个 AFP 输入须匹配冻结清单；Isabelle 的 3,514 个源码文件也校验摘要。固定 AFP 包已包含所用 Go 后端；版本锁记录外部项目提交，冻结清单验证实际 AFP 适配文件，无需覆盖源码。

安装器生成不提交的 `setup/server.local.json`、`setup/compiler-settings.local.json`。默认在安装根下用 `USER_HOME` 隔离 Isabelle 配置和缓存，避免其他 AFP 注册混入；发行标识保持 Isabelle2025，不改系统 HOME。服务器从源重建 Rust/Go 所需 heap。[配置示例](setup/server.example.json) 展示安装路径、工作根、资源参数和额外路径映射，不沿用旧机器路径。

默认单作业、单证明线程、证明开启、阶段不限时、不执行生成程序。默认 ML heap 4500 MiB、Java heap 1536 MiB、stackspace 512 MiB、JVM 活动处理器 2、最低可用内存 512 MiB；可在配置中按服务器调整。heap 参数不是总 RSS 限制。

已有依赖可只生成配置：

```bash
python3 setup/install.py --prefix /srv/afp-deps --configure-only \
  --isabelle /srv/afp-deps/Isabelle2025/bin/isabelle \
  --afp /srv/afp-deps/afp-2025-frozen \
  --go-root /srv/afp-deps/go-1.26.8 --cakeml /srv/afp-deps/cakeml-2.0
```

明确复用已有 Isabelle 用户配置时另传 `--user-home /path/to/user-home`，其中只能注册当前固定 AFP。`--config` 可把本机配置写到其他位置。下载失败保留 `.part`，未验证文件不会解包。

## Native_Word 的 OCaml 配置

AFP 2025 的 `Native_Word` 适配使用 `Pervasives`，OCaml 5 已移除该模块，
会在原会话 `export_code ... checking OCaml` 时报告 `Unbound module Pervasives`。
Ubuntu 系统包可能提供 OCaml 5；请为本实验配置独立的 OCaml **4.14.2**，并在同一
switch 中安装 findlib 和 Zarith。只调整 `OCAML_VERSION` 不会改变 Isabelle 使用的编译器；
实际入口是 `setup/compiler-settings.local.json` 的 `ISABELLE_OCAMLFIND`。

例如，在已安装 opam 的环境中：

```bash
opam switch create afp2025 ocaml-base-compiler.4.14.2
opam install --switch=afp2025 ocamlfind zarith
```

将以下内容保存为可执行包装脚本（其中 opam、root 路径替换为本机绝对路径）：

```sh
#!/bin/sh
exec /absolute/path/to/opam exec --root=/absolute/path/to/opam-root --switch=afp2025 -- ocamlfind "$@"
```

包装脚本让 `ocamlc`、`ocamlopt` 和库搜索路径来自同一 switch，避免只指定
`ocamlfind` 路径却仍调用系统编译器。新安装或 `--configure-only` 时可传
`--ocamlfind /absolute/path/to/wrapper`；已有配置可只把
`compiler-settings.local.json` 中的 `ISABELLE_OCAMLFIND` 改为该包装脚本绝对路径，
然后执行 `python3 setup/check.py --receipt setup/environment.local.json`。
检查器会实际编译机器字相等的原适配并链接 Zarith，记录字节码及本地编译器版本，
不执行生成的探针程序。不得通过置空 `ISABELLE_OCAMLFIND` 跳过条件理论来声称修复。

配置修复与冻结候选数据是两个独立结果：历史 `scan/`、`report/` 保持原始失败事实，
`tools/afp.py init` 仍继承原候选边界。验证完整会话或重新采集候选应写入新的独立目录；
仅修复编译器配置不会自动把历史失败、受阻条目计为成功。

可用两套真实工具链执行有界回归（从仓库根运行）：

```bash
AFP_TEST_OCAML4_FIND=/absolute/path/to/ocaml4-wrapper \
AFP_TEST_OCAML5_FIND=/usr/bin/ocamlfind \
python3 -B -m unittest discover -s test/afp-Isabelle2025/tests -p test_ocaml_compatibility.py -v
```

## 扫描会话的理论覆盖

新扫描单元要求当前会话**自身所属的全部理论**均被加载和采集；依赖会话通过各自
的回执保证覆盖。ROOT 的 `sessions` 声明只使依赖理论可供导入，不要求当前 heap
包含依赖会话的全部文档、示例等理论。实际已加载的依赖理论仍保留在目录中，
声明归属及最大祖先上下文的验证规则继续适用。

条目通过要求每个会话均有通过验证的完整回执，且这些回执的理论并集覆盖条目清单。
即使所有回执分别通过，合并后遗漏理论也会使条目和扫描检查点失败。
AutoCorres2 的三个会话分别负责 128、2、264 个理论，合并后必须覆盖全部 394 个。

覆盖要求保存在单元的 `expected` 列表中，参与单元身份摘要。历史冻结单元仍执行其
原先保存的要求，不会因工具更新自动把旧失败改为成功。修复后应在独立扫描目录生成
新单元、目录和回执；现有 `tools/afp.py init` 继续使用原冻结候选边界。

`AFP_TEST_AUTOCORRES_COVERAGE=1` 可启用原始 AutoCorres2 目录回归：它先验证历史
证据摘要，在临时夹具中应用新单元身份并检查覆盖，不改写原始证据，也不生成原生
执行成功回执。常规测试另行验证缺失所属理论、会话回执、条目理论及外来理论的拒绝行为。

## 唯一推荐流程

以下命令从 AFP 主目录执行，也支持绝对路径和其他 cwd。默认读取本机配置；自定义配置时在子命令前加 `--config /path/server.local.json`，工作根可用 `--work /path/empty-work`。

```bash
python3 setup/check.py --receipt setup/environment.local.json
python3 tools/afp.py verify
python3 tools/afp.py verify-report
python3 tools/afp.py init
python3 tools/afp.py export
python3 tools/afp.py export-checkpoint
python3 tools/afp.py compile
python3 tools/afp.py audit
python3 tools/afp.py report
python3 tools/afp.py audit --with-report
```

环境检查验证版本、全部原扫描条件编译器、源文件身份、目录可写性及冻结证据。`verify` 只读校验完整哈希清单、工具快照、XML、回执、联合快照，不更新原检查点。`init` 必须在**空工作根**执行，复制全部 893 行及候选边界、继承扫描失败和阻塞，不复用旧导出/编译结果；结果按不可变条目文件保存以约束内存。重复初始化或已有产物目录会拒绝。

`candidate-baseline.json` 是接受当前不完整候选边界的独立契约，不宣称原扫描完整通过。六目标为 Rust、SML、OCaml、Haskell、Scala、Go，共享前端并分别保存回执。门禁失败就停止，保留真实状态，不编辑 `passed` 字段。每个新阶段先检查冻结安装及本轮记录源码是否变化。解决本轮环境问题后重跑同一阶段，可恢复已验证请求，不补扫。

`status` 查看进度。`export --entries List-Index` 可做有界观察，但检查点仍要求全体条目，不能据此宣称全量完成。编译只处理本轮通过导出检查点的 Rust 产物，执行 stage1、既有优化器和 stage2，不运行生成程序。原 AFP 会话自身的 checking/Quickcheck 属于继承理论构建行为，不添加生成程序运行时测试。

`work/baseline/`、`entry-results/`、`exports/`、`export-progress/`、`compilation/`、失败日志及检查点长期保留；`_build/`、`_tmp/`、`cache/` 可再生。

## 验证与清理

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
# 实际六语言小型导出、Rust 编译与优化；临时产物自动清理。
python3 tools/afp.py smoke --receipt setup/smoke.local.json
# 默认只清缓存，先预览再显式执行；日志、回执、检查点和源码保留。
python3 tools/afp.py clean
python3 tools/afp.py clean --apply
# 显式重置编译，或导出及其下游编译；先查看预览。
python3 tools/afp.py clean --reset compile
python3 tools/afp.py clean --reset compile --apply
python3 tools/afp.py clean --reset export
python3 tools/afp.py clean --reset export --apply
```

清理只接受带 `afp-work.json` 标记的工作根，拒绝运行中的流水线、逃逸路径、根符号链接和触及 `scan/`、`report/` 的选择。重置不删除候选 `exports.json`、`baseline/` 或原扫描状态。其他原生夹具保留 opt-in 开关，例如 `AFP_TEST_FROZEN_SCAN=1`；默认轻量 suite 不重跑 AFP 会话。本次只做小型导出/编译、临时源树重建与交接验证，不在本机重跑全量 AFP。

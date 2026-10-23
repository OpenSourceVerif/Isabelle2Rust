# Isabelle2Rust 实验记录

当前方案：[第一篇 workshop 工作方案 v0.1](plans/paper-01-v0.1.md)。

代码统一入口：[test/afp/](../test/afp/README.md)。固定编号登记：[registry.json](registry.json)。

当前状态：[EXP-0002](batches/20261023-02-two-task-pilot.md)已完成 List-Index、Skew_Heap 各 3 次独立生成，均首次通过开发和最终测试；另完成 List-Index 的 378 次探索性性能测量。候选在本批测量中快于 Stage 2，但慢于 OCaml；计时包含输入准备和表示转换。[EXP-0001](batches/20261023-01-list-index-smoke.md)保留单独记录。此前 AFP 筛选文件仍是远端历史证据，不是模型实验结果。

## 可视化实验结果

在仓库根目录运行：

```sh
python3 experiments/scripts/serve_dashboard.py
```

打开 <http://127.0.0.1:8765/>，左侧按案例导航。案例的“总表”展示全部实现及按输入条件逐项更新的最新数值和性能图；“实验轮次与记录”查看该案例各轮的逐次结果、原始配置、提示词和追加测量。历史 EXP 编号只作为原始档案引用。

案例与轮次登记在 [cases.json](cases.json)。追加实现可直接加入既有轮次，无需创建 EXP-0003；操作见 [案例记录说明](cases/README.md)。每个实现可保留独立配置，总表逐项采用最新测量，未重测项保留旧值；可按 R 轮次、M 测量和输入条件筛选，来源与重复次数逐行标明。刷新不调用模型。

历史方案与提示词优先读取 `results/snapshots/<batch-id>.json`，不读取今日方案来替代历史。现有两组快照由 `publish_dashboard_snapshots.py` 从本机原始运行的冻结配置、方案与提示词中恢复，逐项核对原始哈希后发布；不改写原始运行。该脚本拒绝覆盖内容不同的既有快照。新实验应沿用快照格式保存原始内容；缺失快照时界面明确说明，仅使用结果摘要中已经保存的配置。

离线查看：运行 `python3 experiments/scripts/build_dashboard.py` 后打开 `experiments/dashboard/index.html`。HTML 内嵌界面与数据，无 CDN 依赖；生成文件被 Git 忽略，可由源码重建。服务只监听本机，不提供原始运行目录或凭据文件。

先前的独立静态样稿 `report-preview.html` 保留用于设计历史，不是当前工作台。研究路径与 RQ 草案保留在 `dashboard/research.json`，不作为某次实验当时的执行协议。

## 记录存放约定

| 位置 | 内容 | Git 管理 |
| --- | --- | --- |
| `plans/` | 有版本的研究方案；区分已确定、建议、待定 | 是 |
| `decisions.md` | 方向与实验协议的变更、理由和影响 | 是 |
| `tasks/` | AFP 入口、源版本、输入域、任务配置 | 是；历史配置须标明失效状态 |
| `prompts/` | 批次实际使用的提示词（无凭据） | 是 |
| `notes/` | 日期化讨论、阅读和排查记录，不自动等于已采纳方案 | 是 |
| `batches/` | 每批实验的配置摘要、运行清单、结果和结论 | 是 |
| `results/` | 可审阅的汇总数据、筛选证据与图表 | 是 |
| `results/snapshots/` | 从冻结记录恢复或运行时保存的方案、配置与提示词 | 是；不覆盖历史版本 |
| `../test/afp/<task>/` | 固定源模型、Stage 1、Stage 2、OCaml 和 baseline.json；实验共同引用 | 是；每个任务一套 |
| `../test/afp/<task>/llm/EXP-NNNN/` | 每次实验的 LLM 生成与修复代码 | 是 |
| `results/artifacts/EXP-NNNN.json` | 该实验引用的固定代码路径、候选路径及哈希 | 是 |
| `cases.json`、`cases/` | 案例内轮次、追加实现的配置和结果、当前测量引用 | 是；工作台主索引 |
| `registry.json` | 原始 EXP 档案与 batch ID 的对应关系 | 是；保留旧引用 |
| `runs/` | 原始请求响应、输入语料、完整日志、构建现场及测量数据 | 否；本地保存并另行备份 |
| `templates/` | 实验记录模板 | 是 |

上述目录可按首次使用时创建。API key 等凭据不进入实验记录、Git 或原始请求日志。请求日志只保存请求内容与非敏感参数，不保存认证头。

## 如何记录案例工作

以案例为单位积累实现。已有轮次内追加实现时，使用 `append_case_implementation.py`，保存实际配置与执行结果，不新建全局 EXP 编号。真正开始新一轮研究时，在案例下登记新的 R 编号。详细字段和命令见 [案例记录说明](cases/README.md)。

原始 EXP-0001/0002 的记录、配置、提示词和运行档案保留；`afp_artifacts.py` 用于发布、校验这些旧布局的源码。固定模型和基线共用，候选代码与配置不可覆盖。历史 `runs/` 及归档仍需另行备份。

## 方案如何变更

当前 v0.1 是讨论方案，不是冻结的执行协议。改变研究路线、输入信息、可修改对象、测试依据或候选选择方式时，新增方案版本并在 `decisions.md` 记下理由。已被实验引用的版本保留；结论必须指向实际使用的版本。

实验脚本、提示词、任务配置和总结随代码进入 GitHub；具体提交与推送状态以 Git 记录为准。原始运行目录不纳入 Git，备份需要另外执行。

## 历史记录

- [AFP 筛选](notes/2026-10-23-afp-selection.md)与[筛选证据](results/afp-screening-2026-10-23.json)：继续用于了解候选任务及历史状态。
- [早期任务配置](tasks/afp-pilot-v1.json)：B/C 协议已失效，保留来源与任务信息；不是当前直接生成路线的运行配置。
- [早期相关工作笔记](notes/2026-10-23-related-work.md)：保留阅读历史，其中的后优化定位与候选贡献不视为当前方案。

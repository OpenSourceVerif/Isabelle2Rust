# AFP 测试案例与代码

按任务找代码。每个任务的 Isabelle 模型、Stage 1、Stage 2 和 OCaml 是固定基线，多次实验共同引用；只有 LLM 候选按实验编号区分。

```text
test/afp/
  list-index/
    isabelle/                 # 固定源模型；session/ 是导出入口
    stage1/                   # 固定 Rust 导出 crate
    stage2/                   # 固定优化后 Rust crate
    ocaml/reference.ml        # 固定 OCaml 导出模块
    baseline.json             # 上述固定文件的路径和哈希
    llm/
      EXP-0001/
        run-001/attempt-01.rs
      EXP-0002/
        run-001/attempt-01.rs
        run-002/attempt-01.rs
        run-003/attempt-01.rs
  skew-heap/                  # 相同结构，目前 LLM 结果只有 EXP-0002
```

| 测试案例 | 源模型 | Stage 1 | Stage 2 | OCaml | LLM 结果 |
| --- | --- | --- | --- | --- | --- |
| List-Index | [Isabelle](list-index/isabelle/) | [Rust](list-index/stage1/) | [Rust](list-index/stage2/) | [OCaml](list-index/ocaml/reference.ml) | [按实验查看](list-index/llm/) |
| Skew Heap | [Isabelle](skew-heap/isabelle/) | [Rust](skew-heap/stage1/) | [Rust](skew-heap/stage2/) | [OCaml](skew-heap/ocaml/reference.ml) | [按实验查看](skew-heap/llm/) |

Isabelle 导入依赖仍需记录中的 AFP/HOL 环境。此处保存原始导出源码，不包含编译缓存；测试适配器、原始请求响应和日志保留在本地运行归档。

## 案例轮次与历史档案

| 实验 | 内容 | 记录 | 文件引用与哈希 |
| --- | --- | --- | --- |
| EXP-0001 | List-Index 直接生成，1 次试跑 | [实验记录](../../experiments/batches/20261023-01-list-index-smoke.md) | [引用清单](../../experiments/results/artifacts/EXP-0001.json) |
| EXP-0002 | List-Index 与 Skew Heap 直接生成，各 3 次 | [实验记录](../../experiments/batches/20261023-02-two-task-pilot.md) | [引用清单](../../experiments/results/artifacts/EXP-0002.json) |

工作台按 List-Index、Skew Heap 案例导航。运行引用为 `list-index/R002/run-003`；旧 EXP 编号保留为档案标识。一个旧档案可以关联多个案例的不同轮次。

追加实现归入现有案例和轮次：新候选存入 `llm/R002/<run-id>/`，不用新建 EXP-0003。原有 `llm/EXP-0001/`、`llm/EXP-0002/` 保留，通过 [案例登记](../../experiments/cases.json) 关联到案例轮次。固定模型和 Stage 1、Stage 2、OCaml 始终共用。

追加命令、配置记录和最新性能的管理方式见 [案例记录说明](../../experiments/cases/README.md)。历史源码校验仍可用 `python3 experiments/scripts/afp_artifacts.py verify EXP-0002`。

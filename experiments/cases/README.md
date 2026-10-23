# 案例、实现与实验轮次

工作台以案例为入口；[cases.json](../cases.json) 是案例和案例内轮次的登记表。

- `list-index` 是持续研究的案例，固定模型和基线在 `test/afp/list-index/`。
- `list-index/R002` 是该案例的一轮研究记录，可追加实现或测量。
- `list-index/R002/run-003` 是该轮的一次运行，保留代码、配置、测试和反馈。
- `EXP-0001/0002` 只是已有原始档案的引用编号；它们不是案例，也不是左侧导航。

List-Index 当前有 R001、R002，Skew Heap 当前有 R001。原 EXP-0002 同时给两个案例提供过记录，故它并不等于两个案例共同的“第二轮”。轮次编号在各案例内部固定，不由页面排序推导。

## 追加实现

同一轮下增加实现，不需要新建案例或全局 EXP 编号。准备实际运行记录 JSON：

```json
{
  "run_id": "run-004",
  "name": "实现的简短名称",
  "kind": "llm",
  "config": {"说明": "填写该实现实际采用的方案、模型参数或人工修改方法"},
  "result": {"status": "未测试", "attempts": []}
}
```

这是字段示例，不是实验结果。kind 可以是 llm 或 manual。已有测试时，将执行器的真实结果放入 result，包括 attempts、selected_attempt、final、时间和用量等；未知项不伪造。config 独立保存，不默认追加实现与本轮最初配置相同。

```sh
python3 experiments/scripts/append_case_implementation.py list-index R002 \
  --code /absolute/path/candidate.rs --record /absolute/path/record.json
```

代码存到 `test/afp/list-index/llm/R002/<run-id>/candidate.rs`，记录存到 `experiments/cases/list-index/R002/<run-id>.json`，登记到 R002 的 additions。相同 run ID 或已有目标文件拒绝覆盖。刷新工作台即可显示，不调用模型，也不分配 EXP 编号。历史候选保留原 `llm/EXP-0001/` 等路径，通过案例登记关联到轮次。

只有实际开展新一轮实验时，才在案例下登记新 R 编号。每轮可保留多次运行、不同实现的独立配置以及追加测量。原始批次配置保持原样，追加实现的配置在对应运行详情中展示。

## 总表与筛选

默认进入总表，展示该案例全部实现。筛选范围可选总表或轮次代号 R001、R002；测量筛选可选全部或 M001、M002。不再使用“完整实现比较”“后续诊断”作为记录名称。轮次目的写在详情里，编号在案例内固定登记，不随排序改变。

总表按“实现 ID + 代码哈希 + 计时口径 + 长度 + 查询 + 元素条件”逐项取最新记录。新增测量按登记顺序更新对应项，未重测项保留旧值；新输入条件新增行，无测量的实现显示未测。不同计时口径分别筛选；表和图共享相同筛选。每行显示来源轮次、测量 ID 和重复次数。跨测量汇总可能存在调用次数等配置差异，因此它是最新记录总览；严格比较可筛到同一次 M 测量。

现有编号：list-index/R002/M001 是原 6 个实现、7 次重复的记录；M002 是后来的 3 个实现、5 次重复记录。总表会将 M002 覆盖的实现和输入条件更新，其余保留 M001；原始数值始终保留。R001 没有性能测量，仍有生成和测试记录。

新增或更新性能数据：

```sh
python3 experiments/scripts/append_case_measurement.py list-index R002 --record /absolute/path/measurement.json
```

记录必须包含带时区的 measured_at、scope（end_to_end 或 kernel）、实际 protocol 和 rows。每行必须记录 implementation（例如 list-index/R002/run-001 或 stage2）、code_sha256、length、query、values、median_ns、min_ns、max_ns、successful_rounds；可附 iterations。所有值来自实际测量，单位为纳秒。

命令校验代码哈希，自动分配下一 M 编号，保留原文件并登记到同一轮次。刷新后总表自动更新，不新建案例、轮次或 EXP 编号，不覆盖旧测量。更早的历史测量不会作为最新更新接收。新增实现仍使用上面的 append_case_implementation.py；加入后在总表显示未测，直到添加它的实际测量。

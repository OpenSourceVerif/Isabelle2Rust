# 扫描阶段结果与错误机制

> 保留范围说明（2026-10-28 迁移）：本页统计沿用当时快照，未重算。全量导出及编译产物已清理，无法逐项重新核验；正文案例的原始证据及引用源码按 [精选证据清单](selected-evidence.jsonl) 保留。原表格、完整失败正文及原哈希索引属于 [历史索引](HISTORICAL-INDEXES.md)，其中路径不代表文件仍存在。



数据范围：2026-10-28 切换到编译时固定的扫描及导出证据。统计生成于 2026-10-28T11:20:39+00:00。本报告是前两个阶段的结果快照；未完成导出的条目继续保留原状态。

| 层级 | 状态 | 数量 |
| --- | --- | --- |
| 条目 | blocked | 228 |
| 条目 | failed | 3 |
| 条目 | passed | 662 |
| 原会话回执 | blocked_dependency | 249 |
| 原会话回执 | complete | 669 |
| 原会话回执 | unresolved_infrastructure | 4 |

本阶段沿用 922 个会话回执；一个条目可涉及多个会话，不能把会话失败数直接当作条目失败数。4 个 unresolved_infrastructure 回执分别属于 Native_Word、CZH_Elementary_Categories、AutoCorres2_Main、AutoCorres2_Test。后两者的原生构建及声明检查进程成功，但回执覆盖检查未通过。

| 条目 | 已接受理论 | 所属理论 | 候选引用 | 失败环节 |
| --- | --- | --- | --- | --- |
| AutoCorres2 | 128 | 394 | 13526 | 扫描回执覆盖验证 |
| Native_Word | 0 | 26 | 0 | 原会话 OCaml checking |
| CZH_Elementary_Categories | 0 | 35 | 0 | 原 HOL 证明构建/存储分配 |

## 具体 HOL 构造、设施前提与原始证据

本轮固定当前候选边界。下列诊断来自选定快照及其原始会话日志；没有重跑候选扫描，也没有把失败回执改为通过。条目口径：662 passed、3 failed、228 blocked。会话口径：669 complete、249 blocked_dependency、4 unresolved_infrastructure。条目与会话是不同分母。

## AutoCorres2：会话依赖可用范围与实际导入祖先范围不同

原三个会话的 native build 与声明检查进程均返回 0。AutoCorres2 自身回执接受 128 个理论；Main 与 Test 两份回执均因 `loaded theories do not cover required session context` 未被接受，选定条目因此仍为 failed，保留 128、缺 266 个所属理论。

ROOT 第 95–100 行把 AutoCorres2_Main 的父会话设为 Simpl，以 `sessions AutoCorres2` 声明其他可用会话，并明确注释“not the parent session to avoid importing the doc / example theories”。会话可用不表示其全部理论都会进入当前 heap 的实际导入祖先。冻结扫描器 `expected_theories` 根据所有 required session 的归属理论生成必需集合；ML 端却只保留 `Thy_Info.lookup_theory` 实际存在的理论。这里两种范围不一致。Main 的期望/实际为 130/112，Test 为 394/376，都缺相同的 18 个文档、示例及库测试理论（如 Chapter1_MinMax、AutoCorres_Documentation、MkTermAntiquote_Tests）。

这是一项候选证据覆盖前提失败，不是 AutoCorres2 的 C 语言语义、HOL 定理或六语言后端已被证明有错。两份被拒绝的 catalogue.xml 仍保留为诊断，后者内容没有补入本轮候选。选定快照中缺 266 个理论，是整份 Main/Test 回执未被接受后的条目聚合结果；不是只缺那 18 个名字。

证据：[ROOT](<evidence/sources/afp/AutoCorres2/ROOT>) 第 95–103 行；[scan_store.py](<evidence/sources/tools/scan_store.py>) 第 40–43、76–78 行；[autocorres-coverage-analysis.json](<evidence/current-candidates/mechanism/autocorres-coverage-analysis.json>)（含完整 18 名清单及分析时摘要）。冻结回执：[21873489f771dff97dfee50406f385e21e111d422c04468d3990875cb72d2c5a.json](<evidence/current-candidates/baseline/receipts/21873489f771dff97dfee50406f385e21e111d422c04468d3990875cb72d2c5a.json>)、[c00ffd2061d77119ce06840668fbdd8d952bef9832c68845348edb1c3590838e.json](<evidence/current-candidates/baseline/receipts/c00ffd2061d77119ce06840668fbdd8d952bef9832c68845348edb1c3590838e.json>)。被拒绝目录属于保留诊断，其分析时摘要不冒充原 receipt 已承诺的候选证据。

## Native_Word：原会话内机器字相等的 OCaml 适配检查

HOL 构造是机器字 `uint` 的 `equal` 类型类实例。Uint.thy 第 488–494 行通过 `code_printing` 把 `HOL.equal :: uint ⇒ uint ⇒ bool` 映射到 `(Pervasives.(=):Uint.t -> Uint.t -> bool)`。Native_Word_Test.thy 第 519 行运行 `export_code test_uint checking SML Haskell? OCaml? Scala`；条件编译器可用时，checking 会生成代码并调用外部编译器。原始完整消息显示生成 ROOT.ml 第 325 行采用了该适配，OCaml 报 `Error: Unbound module Pervasives`，随后会话的 code check 失败。

因此，这是继承扫描会话构建中的外部 OCaml 代码适配兼容问题。它发生在候选声明目录被接受之前，不能计作本轮六语言序列化失败，更不代表 uint 的逻辑定义或所有语言后端均不可执行。Uint 的算术/位运算映射也有 Pervasives 引用；只替换当前一处相等调用不能证明原会话全部可通过。原日志没有固定具体 OCaml 版本，本报告不从当前安装版本反推当时版本。

证据：[Uint.thy](<evidence/sources/afp/Native_Word/Uint.thy>) 第 493 行；[Native_Word_Test.thy](<evidence/sources/afp/Native_Word/Native_Word_Test.thy>) 第 519 行；[原会话完整消息](<../scan/units/f3a24b8810318af576987a29106ec4a9765b8053849428436d318fd635f3db14/attempt-0001/scan-messages/Native_Word/attempt-0001/messages.txt>)（92,220 bytes）；[原构建日志](<../scan/units/f3a24b8810318af576987a29106ec4a9765b8053849428436d318fd635f3db14/attempt-0001/load.log>)；[选定失败回执](<evidence/current-candidates/baseline/receipts/f3a24b8810318af576987a29106ec4a9765b8053849428436d318fd635f3db14.json>)。数据库身份和 SHA 由原命令区间及冻结 receipt 的消息索引验证。

## CZH_Elementary_Categories：集合论范畴映射引理的证明存储耗尽

原始会话在 CZH_DG_FUNCT.thy 第 168 行 `lemma (in is_functor) cf_mapsI` 停止。其结论是 functor 的映射对象 `cf_map FF` 属于集合 `cf_maps α AA BB`，第 169 行证明使用 `auto intro: cat_cs_intros`。原构建运行 65,590.99 秒后打印 `Run out of store - interrupting threads`，会话消息报 `Interrupt_Breakdown` 并定位到该 lemma。后续引用它的 SMC_FUNCT、ECAT_FUNCT 等理论因此未决。

失败环节是原 HOL 证明构建及 Poly/ML 存储分配，尚未进入本轮常量导出。`auto` 与 introduction rule 集在这一证明命令上消耗资源，但完整日志没有内部搜索树或精确热点；不能据此断定唯一的发散规则、引理不成立、或 Rust 打印有错。本轮保持该扫描失败，35 个所属理论没有被接受为候选来源。

证据：[CZH_DG_FUNCT.thy](<evidence/sources/afp/CZH_Elementary_Categories/czh_ecategories/CZH_DG_FUNCT.thy>) 第 168–169 行；[原会话完整消息](<../scan/units/4b4e57260b39a98bc05217f0e29d454d68aa65381e5e23a6c45c5e9b1f7f8267/attempt-0002/scan-messages/CZH_Elementary_Categories/attempt-0001/messages.txt>)（181,745 bytes）；[原构建完整日志](<../scan/units/4b4e57260b39a98bc05217f0e29d454d68aa65381e5e23a6c45c5e9b1f7f8267/attempt-0002/load.log>)；[选定失败回执](<evidence/current-candidates/baseline/receipts/4b4e57260b39a98bc05217f0e29d454d68aa65381e5e23a6c45c5e9b1f7f8267.json>)。

## 依赖传播与统计限制

228 个 blocked 条目中，227 个的冻结回执依赖理由指向 Native_Word，1 个指向 CZH_Elementary_Categories。它们没有自己的候选检查结果，不能按六个目标各算一次“导出失败”。会话层还有 249 个 blocked_dependency 回执；同一条目可以涉及多个会话，因此数量不同。

本轮成功率只针对固定快照中 163,505 个声明来源身份（按条目内部全名去重为 163,502 个候选引用）。未知范围继续列在全部 893 条目的状态表中。原扫描日志中的 Quickcheck 等输出属于继承会话历史；本轮后续流程不运行生成程序或测试其运行时行为。

## 全部扫描诊断统计

下表按日志或回执事件计数，同一条目可有多项事件；完整正文见 failures.jsonl 的 phase=scan。与上述三项条目失败原因的分母不同。

| 类别 | 状态 | 事件数 |
| --- | --- | --- |
| 继承的扫描依赖阻塞 | blocked | 228 |
| 资源、工具或依赖 | failed | 1 |
| 继承 OCaml 目标适配兼容 | failed | 1 |
| 扫描回执覆盖验证 | failed | 2 |

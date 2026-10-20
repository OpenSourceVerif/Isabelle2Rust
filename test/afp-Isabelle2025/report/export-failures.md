# 350 个 AFP Rust 导出错误的原因与归因

本分析使用实验 `20261020T074609Z` 的原始记录，不重新构建 AFP，不修改候选、Rust 后端、优化器或实验状态。分母仅为 [results.json](../results.json) 中 `rust_export.status = failed` 的 **350 个条目**。它们的 scan 和 theory_loading 全部为 passed；462 个 blocked、2 个 timeout、38 个 no_candidates 和导出成功后的 15 个 Cargo 失败均不计入。

观察到的错误种类可以精确计数；“谁应修复”还需结合输入语义和代码生成层次判断。**这 350 条不能直接等同于 350 个 Rust 后端 bug，也不能将打印前的所有失败都说成 AFP 理论错误。**

## 统计方法与检查依据

- 每个条目按本轮首先导致停止的完整错误归入一个主类别，合计必须为 350；一次缺依赖错误可能列出多种原因，另保留缺失常量列表与混合标签。
- 终端 `isabelle build` 会省略长错误的开头。本分析读取本轮保留的完整 session 错误文件，而非只匹配控制台摘录。因此缺代码方程为 **60** 条、含 Quickcheck 四个原语的为 **33** 条；只匹配未被省略的终端头部会漏计。
- [export-failures.csv](export-failures.csv) 是 350 条逐项明细；[export-failures.json](export-failures.json) 包含分类汇总、归因提示、原始输入哈希、每条日志的来源、时间、行号和 SHA256。[export-errors.txt](export-errors.txt) 原样保留全部 350 个完整错误正文。
- 原始错误文件修改时间为 2026-10-20 11:39:27–12:49:16 UTC，处于该次实验期间。所有正文的 SHA256 均在保存后重新校验，避免将旧实验的同名日志混入。原文空白也保留，包括错误正文中 8 行仅有 `*** ` 的空行标记。
- “候选有代码方程”只检查入口自身；不保证整个依赖闭包、代码类实例、抽象表示接口及目标专用运行时均可用。整条目一次性导出，首先遇到的错误会遮蔽后续错误；这些比例不是独立 bug 数，也不是逐函数失败率。

## 主错误类别：互斥、合计 350

| 首个停止错误 | 条目数 | 占 350 | 主要对应层次与归因 |
| --- | ---: | ---: | --- |
| `Wellsortedness error` | 218 | 62.29% | 输入及通用代码类实例的可执行性前提；其中还包含自动测试辅助实例 |
| `No code equations for` | 60 | 17.14% | 混合：目标运行时适配缺口、无可执行规格依赖，或二者并存 |
| 左侧 `is not a constructor` | 37 | 10.57% | 代码方程/构造子上下文不兼容；14 条涉及当前自然数数值 profile |
| `Proof failed` | 9 | 2.57% | 导出内部共享集合预处理的自动证明失败 |
| `Type error in application` | 8 | 2.29% | 共享集合预处理构造的中间项类型不一致，属实际重写实现异常的线索 |
| `Inaccessible constant` | 6 | 1.71% | 内部候选名称到显式导出文本之间的名称接口 |
| `Undefined constant` | 4 | 1.14% | 汇总上下文无法解析所写入口名称，需要检查扫描/导出驱动 |
| `Abstraction violation` | 4 | 1.14% | 输入代码方程越过代码抽象类型接口 |
| `Interrupt_Breakdown` | 1 | 0.29% | 内部中断，记录不足以确定责任 |
| `Tactic failed` | 1 | 0.29% | 导出内部共享集合预处理的证明自动化失败 |
| `Not a constant` | 1 | 0.29% | 导出入口未解析为 Const，涉及隐藏名称 |
| 类型类 `arity` 冲突 | 1 | 0.29% | 通用代码类代数/输入上下文不兼容 |
| **合计** | **350** | **100%** | 百分比逐项四舍五入可能产生 0.01% 的尾差 |

前 3 类共 **315/350 = 90%**。它们主要描述“代码生成输入是否就绪”，而非 Rust 已生成代码的语法或类型是否正确。

## 1. 类型类约束：218 条

| 缺少的代码类 | 条目数 | 占 350 | 占本类 218 | 解释 |
| --- | ---: | ---: | ---: | --- |
| `enum` | 175 | 50.00% | 80.28% | 全类型量化/集合计算要求有限枚举 |
| `partial_term_of` | 24 | 6.86% | 11.01% | 自动 Quickcheck 反射辅助入口缺少实例 |
| `equal` | 15 | 4.29% | 6.88% | 缺少 HOL 代码生成所需的可执行相等实例 |
| `finite` | 3 | 0.86% | 1.38% | 对无限类型提出 finite 类要求 |
| `preorder_lean` | 1 | 0.29% | 0.46% | AFP 自定义代码类与 integer 的实例不配套 |

### enum：规格的逻辑量化不等于已给出算法

例如 [Auto2_HOL](export-errors.txt#L430) 的 `prime p` 方程仍包含对任意自然数 `m` 的量化，导出需要 `nat :: enum`。[Alpha_Beta_Pruning](export-errors.txt#L339) 导出 `bnd` 规格时要求整个树列表类型可枚举。这些不表示相应条目中的素数算法或搜索算法均不可执行，而是入口集还包含了逻辑规格/不变量。

175 条中，首个缺失 arity 为 `nat :: enum` 的有 56 条、`list :: enum` 的有 40 条、`int :: enum` 和 `real :: enum` 各 8 条，合计 **112 条**。这些已知无限类型不可能通过补一个合法的有限枚举实例解决。[Enum.thy](../../../temp/Isabelle2025_ref/src/HOL/Enum.thy#L11) 要求有限列表覆盖整个 UNIV。应提供有限边界算法、等价的可执行方程或明确算法入口，而不是给无限域虚构枚举。

其他 63 条涉及自定义类型等，需分别判断是否有限、是否存在可用的枚举实现；单凭日志不能说全部具有相同数学障碍。

**归因：主要是 AFP 输入/可执行规格与通用代码生成前提之间的缺口，也受全候选入口策略影响；没有 Rust 枚举或 trait 打印错误的证据。**“AFP 侧”在这里表示需要完善可执行接口，不表示 AFP 定义或证明错误。

### partial_term_of：辅助测试代码的类约束

24 条均在自动生成的 `partial_term_of_...` 方程中失败；22 条缺少 `fun :: partial_term_of`，另外 [Jordan_Hoelder](export-errors.txt#L6156) 缺少 `group :: partial_term_of`，[Knot_Theory](export-errors.txt#L6417) 缺少 `Link_Diagram :: partial_term_of`。[Abortable_Linearizable_Modules](export-errors.txt#L56) 给出了函数字段的完整依赖例子。

**归因：上游自动测试实例/代码类覆盖不足。**这不同于下一节中 Rust 缺少 Haskell_Quickcheck 原语映射；即使补齐那四个原语，也不能凭空满足这 24 条类约束。不能由此断言 Rust 后端不会翻译函数类型。

### equal、finite、自定义类

- 15 条 `equal` 包括 [BDD](export-errors.txt#L495) 的 `ref`、Dedekind_Real 的 `preal` 等。当前 HOL 代码上下文没有相应可执行相等实例；补 AFP 实例或提供目标类型适配是排查方向。HOL 的可执行 `equal` 类与 Rust 的 `==`/trait 打印不是同一层。
- 3 条 `finite` 为 Mason_Stothers、Pratt_Certificate 的 `nat`，及 Safe_OCL 的 `String.literal`。例如 [Mason_Stothers](export-errors.txt#L6918) 通过 multiplicity 依赖对自然数集合做 finite/Max 判断；需要实际有限算法，不能声称 nat 整体有限。
- [Transformer_Semantics](export-errors.txt#L11155) 在当前类重整与数值方程的共同上下文里缺少 `integer :: preorder_lean`，来自 AFP 自定义类。它属于代码类/数值表示兼容性，尚不能单独归罪于 Rust 翻译。

通用 [code_thingol.ML](../../../temp/Isabelle2025_ref/src/Tools/Code/code_thingol.ML#L491) 在构建中间程序、推导类型类字典时报告这类错误，Rust serializer 尚未接收到完整程序。

## 2. 缺少代码方程或目标实现：60 条

| 依赖缺口 | 条目数 | 占 350 | 占本类 60 | 责任判断 |
| --- | ---: | ---: | ---: | --- |
| 仅列出 Quickcheck 四个原语 | 25 | 7.14% | 41.67% | 明确的 Rust 目标设施适配缺口 |
| Quickcheck 四个原语及其他缺失常量 | 8 | 2.29% | 13.33% | 目标支持与输入依赖缺口并存 |
| 其他目标专用设施：反射、IO、命令式堆 | 3 | 0.86% | 5.00% | 目标运行时/表示适配不足，仍需考虑全入口范围 |
| 其他未实现的规格/抽象依赖 | 24 | 6.86% | 40.00% | 主要是 AFP/通用代码方程就绪性 |

**33 = 25 + 8**，是上一答复所述 Quickcheck 原语失败的完整口径。不能把 33 与 60 相加，也不能将补齐原语后的潜在成功数写成 33。

### 目标专用设施确实缺少 Rust 适配

- [AVL-Trees](export-errors.txt#L18)：`narrowing [AVL.tree] → narrowing [nat] → apply → conv → toEnum/marker/error/nth`。这四个常量在 [Quickcheck_Narrowing.thy](../../../temp/Isabelle2025_ref/src/HOL/Quickcheck_Narrowing.thy#L70) 中只有 `Haskell_Quickcheck` 目标实现，没有普通方程可供 Rust 自动翻译。25 条只列出这组缺口；另外 8 条同时列出 Eps、relcompp、抽象构造等依赖。
- [FOL_Harrison](export-errors.txt#L4000)：缺少 `term_of_literal_inst.term_of_literal`。[Code_Evaluation.thy](../../../temp/Isabelle2025_ref/src/HOL/Code_Evaluation.thy#L111) 有意移除普通 literal 反射方程，只向 `Eval` 提供 `HOLogic.mk_literal` 目标实现。当前 Rust 没有对应实现。
- [Hello_World](export-errors.txt#L5122)：缺少 `println/getLine/Rep_io`。AFP [IO.thy](../../../temp/afp-Isabelle2025/thys/Hello_World/IO.thy#L138) 提供 Haskell/SML 适配，未提供 Rust 适配；此外，全入口还要求逻辑层 `Rep_io`，补齐普通 IO 不代表整条目已可导出。
- [Imperative_Insertion_Sort](export-errors.txt#L5832)：`Ref.get/Array.get → from_nat/to_nat/inv_into → Eps`。这里的 Eps 暴露了逻辑堆编码；[Heap_Monad.thy](../../../temp/Isabelle2025_ref/src/HOL/Imperative_HOL/Heap_Monad.thy#L521)、Ref.thy 和 Array.thy 为标准目标提供实际堆/引用/数组适配，当前 Rust 配置没有。不能因为最后报 Eps，就认定插入排序算法本身不可计算。

因此，**36/350 = 10.29% 的条目有明确目标专用设施适配缺口线索**：28 条以此为主要诊断，8 条还同时有其他依赖缺口。这个计数不包括下一节另列的 14 条自然数模式兼容性，也不是 36 个独立缺陷或 36 个保证可修复通过的条目。

### 其余 24 条不是同一种“缺后端函数”

完整条目名单和常量在 CSV/JSON 中，例如：

- [Directed_Sets](export-errors.txt#L3214)：`well_order_of → card_of → Eps`；Fresh_Identifiers、Relational_Forests、Robbins-Conjecture 等也依赖选择算子。
- [FinFun](export-errors.txt#L4112)：`pcr_finfun → cr_finfun/relcompp`；KAD、KAT_and_DRA、Sqrt_Babylonian 等同样把 transfer/商类型证明关系纳入入口闭包。这些关系不天然就是可运行算法。
- [ClockSynchInst](export-errors.txt#L2100)：缺少 Δ、khl、np 等参数性依赖；Jacobson_Basic_Algebra、Menger、Multirelations、Relational_Paths 等涉及未提供实现的抽象/locale 运算。
- Stone_Kleene_Relation_Algebras 的 `comm_monoid_add.sum`、Prefix_Free_Code_Combinators 的 `sorted_key_list_of_set` 等仍需相应可执行方程和表示条件。

**归因：当前输入依赖闭包没有完整实现。**这不证明 AFP 原理论错误，也不证明这些条目在补充适当代码方程后仍不可导出；本分析未逐条换目标验证，因而不把“没有普通方程”武断地全部归为 AFP 缺陷。

错误由通用 [code_target.ML](../../../temp/Isabelle2025_ref/src/Tools/Code/code_target.ML#L387) 在扣除当前目标提供的实现后检查剩余依赖产生；这是目标准备阶段，早于实际 Rust 打印。

## 3. 代码方程左侧模式或构造子上下文：37 条

合法 HOL 等式不一定是当前代码表示下合法的模式匹配方程。通用 [code.ML](../../../temp/Isabelle2025_ref/src/Pure/Isar/code.ML#L655) 要求左侧参数模式由当前代码构造子组成。

- **14 条（4.00%）涉及自然数表示**：11 条首报 `0::nat`，2 条首报 `Suc`，1 条首报 `nat_of_integer`。例如 [Hood_Melville_Queue](export-errors.txt#L5150) 的 `exec (App 0 f r)`。当前 Rust profile 导入 [Code_Target_Nat](../../../translate/Rust_BigInt_Setup.thy#L1)，将 nat 改成目标整数表示；其共享 [Code_Abstract_Nat](../../../temp/Isabelle2025_ref/src/HOL/Library/Code_Abstract_Nat.thy#L11) 预处理明确只在一定范围内消除自然数模式。**应归到当前数值 profile/方程适配兼容性调查，而不是 AFP 数学证明错或已经打印出错误 Rust。**未做表示对照，不能说这 14 条全都仅由 Rust profile 引起，更不能保证一个修改即可修好全部。
- **另外 23 条（6.57%）**：8 条首报 `List.append`，例如 [Buildings](export-errors.txt#L1504) 和多项 Noninterference 条目的 `xs @ [x]` 模式；其余包括集合插入/空集、实数表达式、商/抽象类型以及当前上下文不再接受的构造子。[ADS_Functor](export-errors.txt#L7) 甚至首报 `List.Nil`，[Relational_Cardinality](export-errors.txt#L9500) 首报 `Pair`；对这些真正的数据类型构造子，需要检查代码表示的注册及合并上下文，不能简单说 Nil/Pair 在 HOL 中不是构造子。
- 扫描阶段为 37 条中的 30 条保留过证书诊断，但不一定与最终首个停止错误相同；保留异常候选是实验既定策略，不是扫描器宣称这些证书已经能导出。

**归因：普通部分优先调查 AFP 代码方程/构造子表示上下文；自然数部分单列数值适配覆盖。**仅凭该错误族还不能证明 Rust 模式打印规则有错。

## 4. 集合预处理：18 条

这些条目在导出时，将集合 comprehension 改写为 image、交、积等表达式。相关规则由 Isabelle 的 [Product_Type.thy](../../../temp/Isabelle2025_ref/src/HOL/Product_Type.thy#L1321) 为代码生成注册，实现在共享 [set_comprehension_pointfree.ML](../../../temp/Isabelle2025_ref/src/HOL/Tools/set_comprehension_pointfree.ML#L436)。Rust_Target 仅注册 Rust serializer，没有新增此套集合重写。

### 8 条中间项类型错误：实际规则实现异常的直接线索

条目为 Abstract-Hoare-Logics、Decl_Sem_Fun_PL、Hybrid_Logic、IO_Language_Conformance、Logging_Independent_Anonymity、Multirelations_Heterogeneous、Relational_Method、Simpl。

例如 [Hybrid_Logic](export-errors.txt#L5207) 自动生成的 image 函数要求 `fm list × a × a`，却给了 `(fm list × a) × a` 的集合。乘积类型不具有定义上的结合律；缺少明确的重组映射会使中间项不合法。[Abstract-Hoare-Logics](export-errors.txt#L211) 也显示类似的扁平/分组元组差异。

**这是共享前端构造/重写实现错误的强证据；不是 Rust 生成代码的类型错误，也不是原 AFP 定理声明类型错误。**日志和源码定位尚未替代独立目标最小复现，最终修复位置仍需核实。

### 10 条自动证明失败：不能全部当成已确认的错误翻译规则

9 条 `Proof failed`：BNF_Operations、Graph_Saturation、Group-Ring-Module、Inductive_Inference、Key_Agreement_Strong_Adversaries、Kleene_Algebra、Quantales、Regression_Test_Selection、Residuated_Lattices。

1 条 `Tactic failed`：Auto2_Imperative_HOL。

[Graph_Saturation](export-errors.txt#L4638) 和 [Auto2_Imperative_HOL](export-errors.txt#L447) 的错误目标均为新构造的集合重写等式。共享 simproc 通过 `Goal.prove` 验证等式时失败，Isabelle 拒绝继续，因而没有把未经证明的重写交给 Rust。

**归因：共享预处理的规则构造、自动证明能力或当前上下文兼容性。**对于这 10 条，现有记录不能区分“新等式本身构造错了”和“等式正确但 tactic 证明不出来”；也不能把这里的 `Proof failed` 算为 AFP 原始证明失败。

## 5. 名称解析接口：11 条

| 报错 | 数量 | 条目 |
| --- | ---: | --- |
| Inaccessible constant | 6 | Abstract-Rewriting、Polynomial_Interpolation、Propositional_Proof_Systems、Serializable、SumSquares、Well_Quasi_Orders |
| Undefined constant | 4 | Call_Arity、IMAP-CRDT、Launchbury、UPF_Firewall |
| Not a constant | 1 | LinearQuantifierElim |

[scan.ML](../scan.ML#L30) 枚举内部 Const 名称；[run.py](../run.py#L38) 直接把它们写成 `export_code "Name"` 外部文本。内部声明仍可被枚举，并不保证名字在最终汇总上下文中仍可按普通文本访问。

[Serializable](export-errors.txt#L10375) 的源文件明确 `hide_const ... AX ...`；[Abstract-Rewriting](export-errors.txt#L240) 的 choice、Well_Quasi_Orders 的 F 也被隐藏。[LinearQuantifierElim](export-errors.txt#L6768) 的 DLO.lift_dnf_qe 同样在源理论中被 hide_const，最终没有解析成 Const。其余 4 条 undefined 需要进一步检查合并上下文/名称解析，不能仅凭错误就说声明真的不存在于所有源理论。

**归因：实验驱动的内部名称/外部名称接口与汇总上下文兼容性，属于应单独修复的工具问题。**它不适合硬塞进“AFP 数学错误、Rust 支持不足、Rust 翻译规则错误”三个类别。保留这些候选与正确表达内部入口是两件事，不能用删除候选冒充修复。

## 6. 抽象接口 4 条、arity 冲突 1 条、中断 1 条

- **Abstraction violation：4 条，1.14%。**Hybrid_Multi_Lane_Spatial_Logic、Modal_Logics_for_NTS、Order_Lattice_Props、Three_Circles。[Three_Circles](export-errors.txt#L10975) 的 reciprocal_poly 方程直接使用 `Poly`；其他错误使用 `Abs_nat_int/Abs_formula/Abs_downsets`。通用 [Thingol 检查](../../../temp/Isabelle2025_ref/src/Tools/Code/code_thingol.ML#L724) 保护 code abstype 的表示边界。应完善输入的抽象代码方程/表示接口；不能让 Rust 绕过抽象屏障直接打印。
- **代码类 arity 冲突：1 条，0.29%。**[Stone_Algebras](export-errors.txt#L10679) 的 `lifted_pair` 对 `bounded_lattice_bot` 的参数要求比对其父类 `lattice` 的代码要求更弱，后者额外需要 `equal`。这是通用代码类代数的一致性错误，需检查输入代码实例和方程引入的约束；没有已打印 Rust trait 层级错误的证据。
- **Interrupt_Breakdown：1 条，0.29%。**[ArrowImpossibilityGS](export-errors.txt#L408) 15.01 秒退出、退出码 1，远未达到本轮 180 秒导出限时。日志不足以判断是异步异常、证明自动化还是其他内部故障；不能记成已确认 OOM、超时或 Rust 规则错误。

## 归因边界与后续优先级

| 归因线索汇总 | 条目数 | 占 350 | 能够支持的结论 |
| --- | ---: | ---: | --- |
| 当前输入/通用代码生成就绪性：类约束、其他依赖、普通模式、抽象接口及代码类上下文 | 270 | 77.14% | 对应输入或通用前端的排查范围，**不是 270 个已证实 AFP 源码缺陷** |
| 以目标专用设施适配为主要诊断 | 28 | 8.00% | 当前 Rust 目标运行时/反射/IO/堆等支持不全；修好后仍可能暴露其他错误 |
| 目标专用设施及其他依赖混合 | 8 | 2.29% | 至少两种缺口并存 |
| 涉及自然数数值 profile 的模式兼容性 | 14 | 4.00% | 排查当前配置/共享预处理覆盖，未证明都是 Rust 专属缺陷 |
| 共享前端集合重写中间项类型错误 | 8 | 2.29% | 有实际规则实现异常证据，定位在 Rust 打印之前 |
| 共享前端集合重写自动证明失败 | 10 | 2.86% | 自动证明/规则构造/上下文兼容性待区分 |
| 实验驱动名称接口 | 11 | 3.14% | 应独立于 AFP 和 Rust 打印器统计 |
| 根因未定的内部中断 | 1 | 0.29% | 需要进一步诊断 |
| **合计** | **350** | **100%** | 这是有边界的归因提示，不是三类已确认 bug 的强制分桶 |

270 = 218 + 24 + 23 + 4 + 1；36 个有目标设施缺口的条目 = 28 + 8。两种表采用相同的 350 个条目，但分别回答“报了什么错误”和“优先到哪一层查”，不应混用或重复相加。

**本轮这 350 个停止错误中，能够确认的 Rust serializer 翻译规则错误为 0 条；这不等于证明 Rust 后端没有错误。**349 条可识别诊断发生在 Rust 打印之前，1 条内部中断无法确定具体位置。独立的 15 个 Cargo 失败发生在导出成功之后，需要另作生成代码/trait/类型约束分析，不能并入这张表。

建议先处理 11 条名称接口以恢复有效入口，再调查 14 条数值模式和 18 条共享集合预处理问题；目标设施适配应按 Quickcheck、反射、IO、堆分别评估。对于无限域规格、选择算子和 transfer 关系，优先完善可执行接口及依赖诊断。修复一个首错后须重跑原入口集，保留原候选，才有资格报告新增成功数。

# 六语言导出结果与错误机制

> 保留范围说明（2026-10-28 迁移）：本页统计沿用当时快照，未重算。全量导出及编译产物已清理，无法逐项重新核验；正文案例的原始证据及引用源码按 [精选证据清单](selected-evidence.jsonl) 保留。原表格、完整失败正文及原哈希索引属于 [历史索引](HISTORICAL-INDEXES.md)，其中路径不代表文件仍存在。



数据范围：2026-10-28 切换到编译时固定的扫描及导出证据。统计生成于 2026-10-28T11:20:39+00:00。本报告是前两个阶段的结果快照；未完成导出的条目继续保留原状态。

六个目标依次为 Rust、SML、OCaml、Haskell、Scala、Go。每个常量组共用一次 Thingol 前端，然后分别经过目标准备与序列化。SML 为官方 ML 目标；Rust 使用 Rust_BigInt_Setup。六语言使用共同显式模块名 AFP_Code。Go 的源码版本及 AFP 适配差异见后附机制材料。

## 条目与候选结果

| 目标 | 全部成功 | 部分成功 | 全部失败 | 受阻 | 无候选 | 阶段中断 | 待导出 | 扫描未通过 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Rust | 10 | 531 | 72 | 5 | 25 | 1 | 19 | 230 |
| SML | 10 | 531 | 72 | 5 | 25 | 1 | 19 | 230 |
| OCaml | 10 | 531 | 72 | 5 | 25 | 1 | 19 | 230 |
| Haskell | 10 | 531 | 72 | 5 | 25 | 1 | 19 | 230 |
| Scala | 10 | 531 | 72 | 5 | 25 | 1 | 19 | 230 |
| Go | 10 | 531 | 72 | 5 | 25 | 1 | 19 | 230 |

| 目标 | 成功候选 | 失败候选 | 未决候选 | 待执行候选 |
| --- | --- | --- | --- | --- |
| Rust | 55346 | 86351 | 15255 | 6550 |
| SML | 55528 | 86169 | 15255 | 6550 |
| OCaml | 55514 | 86183 | 15255 | 6550 |
| Haskell | 55537 | 86160 | 15255 | 6550 |
| Scala | 55494 | 86203 | 15255 | 6550 |
| Go | 53837 | 87860 | 15255 | 6550 |

## 失败候选的主证据分类

每个失败的（条目、候选、目标）单元选择其最后一份有效决定性证据作为主证据。同一候选可能还有其他失败上下文；它们保留在完整事件目录。共享前端失败可同时影响六个目标，因此下表跨语言合计不是独立错误数量。整组失败不会自动判定组内每个候选失败。

| 类别 | Rust | SML | OCaml | Haskell | Scala | Go |
| --- | --- | --- | --- | --- | --- | --- |
| 依赖缺少方程或目标实现 | 76781 | 76625 | 76639 | 76616 | 76639 | 76784 |
| 代码类型类约束 | 8325 | 8325 | 8325 | 8325 | 8325 | 8325 |
| 方程模式与代码构造子 | 735 | 735 | 735 | 735 | 735 | 735 |
| 预处理项构造或证明 | 256 | 256 | 256 | 256 | 256 | 256 |
| 代码抽象类型接口 | 210 | 210 | 210 | 210 | 210 | 210 |
| 未覆盖的 ML 实现分支 | 2 | 0 | 0 | 0 | 0 | 985 |
| 目标程序符号名称解析 | 0 | 0 | 0 | 0 | 0 | 357 |
| 目标字符串字面量适配 | 0 | 0 | 0 | 0 | 0 | 190 |
| 共享前端源算法不终止 | 10 | 10 | 10 | 10 | 10 | 10 |
| 程序图节点查询 | 4 | 4 | 4 | 4 | 24 | 4 |
| 方程左侧抽象 | 4 | 4 | 4 | 4 | 4 | 4 |
| Rust 自引用无参数值 | 19 | 0 | 0 | 0 | 0 | 0 |
| 双列表长度前提 | 5 | 0 | 0 | 0 | 0 | 0 |

## 尚未完成的导出范围

| 部分受阻条目 | 已有 Rust crate | 未决 Rust 候选 |
| --- | --- | --- |
| HOL-CSP | 30 | 2 |
| HOL-CSPM | 52 | 2 |
| Simpl | 230 | 3 |
| Statecharts | 94 | 3 |
| AutoCorres2 | 413 | 11782 |

CakeML 原请求有 3,548 个候选，保留 802 个尝试 XML 和 24 个成功 Rust crate。这些 XML 包含成功与失败尝试，不是 802 次成功。原请求在切换编译阶段时主动停止，没有 finished.xml；中断既不补造退出码，也不改变尚无直接结论的候选。

| CakeML 目标 | 已观察成功 | 有直接失败证据 | 未决 |
| --- | --- | --- | --- |
| Rust | 54 | 31 | 3463 |
| SML | 54 | 31 | 3463 |
| OCaml | 54 | 31 | 3463 |
| Haskell | 54 | 31 | 3463 |
| Scala | 54 | 31 | 3463 |
| Go | 54 | 31 | 3463 |

扫描通过但尚未导出的 19 个条目：

SPARCv8、X86_Semantics、ZFC_in_HOL、CZH_Foundations、Category3、MonoidalCategory、Bicategory、EnrichedCategoryBasics、ResiduatedTransitionSystem2、Ordinal_Partitions、Q0_Metatheory、Q0_Soundness、Wetzels_Problem、Recursion-Addition、Delta_System_Lemma、Transitive_Models、Independence_CH、Forcing、AODV。

## 当时的成功源码统计（全量产物已清理）

| 目标 | 文件数 | 字节数 |
| --- | --- | --- |
| Rust | 89745 | 532098600 |
| SML | 29969 | 152783670 |
| OCaml | 29967 | 141678628 |
| Haskell | 31133 | 146138597 |
| Scala | 29960 | 217100533 |
| Go | 48804 | 338183030 |

这些文件在报告生成时曾逐项按已发布哈希核验，现全量产物已清理、无法逐项重新核验；CakeML 的文件来自归档前已存在的成功回执，另记为观察产物。Rust 源码另复制为固定编译输入，Cargo 锁文件及编译缓存写入该范围。

## 同作用域性能

已发布请求中，六目标全部成功且请求常量完全相同的组共有 28612 个；这些组对应的共享前端计时合计 179.166 秒。

| 目标 | 匹配样本数 | 目标阶段累计秒数 | 中位秒数 |
| --- | --- | --- | --- |
| Go | 28612 | 115.402 | 0.001 |
| Haskell | 28612 | 74.531 | 0.001 |
| OCaml | 28612 | 73.649 | 0.001 |
| Rust | 28612 | 27161.916 | 0.002 |
| SML | 28612 | 78.706 | 0.001 |
| Scala | 28612 | 74.700 | 0.001 |

CakeML 中断请求另有 24 个六语言均成功的同作用域组，其计时单列在 summary.json。

Rust 累计计时中，ILL 单组占 26,647.962 秒（约 98.1%）；其他匹配组共 513.954 秒。该长样本使累计值对单次观察敏感，具体证据见后文 ILL 案例。目标阶段计时包含投影、适配及打印，不能当作生成程序运行速度。固定执行顺序、缓存效应与毫秒分辨率均限制语言间对比；中位数为零表示低于记录分辨率，不表示没有成本。共享前端耗时、失败快速路径、拆分尝试和进程总墙钟时间均不混入该表。某些进程墙钟包含隔离诊断等待，也不能替代 serializer 计时。

## 主要 HOL 构造与设施机制

[补充机制：共递归值、左侧抽象、图节点与列表长度](<additional-mechanisms.md>)。

下列案例解释已发布结果中的主要构造和设施前提。所有状态均来自各自真实单常量请求；本页详析案例的原始完整日志和引用成功源码保留在精选证据目录。全量条目、候选和诊断事件的统计以正式报告表为准。

共享前端失败发生在目标打印之前；目标准备还会检查语言专用实现；serializer 失败则需要对应目标的实际诊断。三者在下表及后文分别说明。当前固定候选包含自动生成的内部声明，其存在和可见性不保证独立可执行。

| 案例 | Rust | SML | OCaml | Haskell | Scala | Go | 失败环节 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AWN 全称量化 | 失败 | 失败 | 失败 | 失败 | 失败 | 失败 | 共享 Thingol 前端 |
| AVL 表示辅助声明 | 失败 | 失败 | 失败 | 失败 | 失败 | 失败 | 目标准备，serializer 之前 |
| PQ 抽象构造函数 | 失败 | 失败 | 失败 | 失败 | 失败 | 失败 | 共享 Thingol 入口检查 |
| ADS 列表表示 | 失败 | 失败 | 失败 | 失败 | 失败 | 失败 | 共享代码方程证书检查 |
| Hoare 集合推导 | 失败 | 失败 | 失败 | 失败 | 失败 | 失败 | 共享集合预处理及证明项构造 |
| AVL narrowing 模式 | 通过 | 通过 | 通过 | 通过 | 通过 | 失败 | Go serializer 对带数字字面量适配的嵌套构造子模式名称解析 |
| Exceptions 数字标签 | 通过 | 通过 | 通过 | 通过 | 通过 | 失败 | Go 层次程序符号名称解析 |
| 动态 literal 转换 | 通过 | 通过 | 通过 | 通过 | 通过 | 失败 | Go 字符串目标语法打印 |
| Arrow 模式合并 | 失败 | 失败 | 失败 | 失败 | 失败 | 失败 | 共享 Code_Preproc.obtain 的 set_comprehension simproc |
| GC 合取扩张 | 失败 | 失败 | 失败 | 失败 | 失败 | 失败 | 共享 Code_Preproc.obtain / set_comprehension simproc 的 Goal.prove |
| Stuttering 固定状态谓词 | 失败 | 失败 | 失败 | 失败 | 失败 | 失败 | 共享 pointfree 证明的高阶模仿与最右合取扩张 |
| TWW 模式合并 | 失败 | 失败 | 失败 | 失败 | 失败 | 失败 | 共享 pointfree 的空交集队列交换循环 |

## AWN：递归进程类型上的全称量化

入口：`AWN.not_choice`。阶段：共享 Thingol 前端。

AWN.thy 第 35 行的 seqp 是带递归和函数字段的进程 datatype；第 152 行 not_choice p ≡ ∀p1 p2. p ≠ p1 ⊕ p2。代码生成把量化改写为需要 enum 字典的可执行运算，但当前 seqp 没有 enum 实例。完整单常量异常明确报 No type arity seqp :: enum。这个逻辑定义的成立不提供有限枚举实现；可执行判定需要适合该构造的代码方程或实例。


源位置：[AWN.thy](<evidence/sources/afp/AWN/AWN.thy>) 第 35 行；[AWN.thy](<evidence/sources/afp/AWN/AWN.thy>) 第 152 行；[code_thingol.ML](<evidence/sources/isabelle/Tools/Code/code_thingol.ML>) 第 493 行。

原始单常量证据：[frontend.xml](<evidence/current-candidates/exports/AWN/AWN/attempt-0002/attempts/merged/allLLRLRRRLL/frontend.xml>)。

## AVL-Trees：datatype 自动生成的表示辅助声明

入口：`AVL.tree.Abs_tree`。阶段：目标准备，serializer 之前。

AVL.thy 第 23 行的 tree datatype 同时引入公共构造子、映射函数和内部 BNF/表示辅助常量。选定扫描策略保留全部自有声明，因此 Abs_tree、Rep_tree、wit_pre_tree 也成为入口。Code_Target 在扣除目标 code_printing 已实现符号后检查剩余 Thingol 程序，未实现节点触发 No code equations。这里的全名可见只证明声明存在；它不保证任意内部辅助声明均可独立导出。


源位置：[AVL.thy](<evidence/sources/afp/AVL-Trees/AVL.thy>) 第 23 行；[code_target.ML](<evidence/sources/isabelle/Tools/Code/code_target.ML>) 第 387 行；[code_target.ML](<evidence/sources/isabelle/Tools/Code/code_target.ML>) 第 418 行。

原始单常量证据：[Go.xml](<evidence/current-candidates/exports/AVL-Trees/AVL-Trees/attempt-0002/attempts/merged/allLRLLLLL/Go.xml>)、[Haskell.xml](<evidence/current-candidates/exports/AVL-Trees/AVL-Trees/attempt-0002/attempts/merged/allLRLLLLL/Haskell.xml>)、[OCaml.xml](<evidence/current-candidates/exports/AVL-Trees/AVL-Trees/attempt-0002/attempts/merged/allLRLLLLL/OCaml.xml>)、[Rust.xml](<evidence/current-candidates/exports/AVL-Trees/AVL-Trees/attempt-0002/attempts/merged/allLRLLLLL/Rust.xml>)、[SML.xml](<evidence/current-candidates/exports/AVL-Trees/AVL-Trees/attempt-0002/attempts/merged/allLRLLLLL/SML.xml>)、[Scala.xml](<evidence/current-candidates/exports/AVL-Trees/AVL-Trees/attempt-0002/attempts/merged/allLRLLLLL/Scala.xml>)。

## Binomial-Queues：带不变量的 typedef 抽象构造函数

入口：`PQ.pq.Abs_pq`。阶段：共享 Thingol 入口检查。

PQ.thy 第 18 行把优先队列定义为键互异、按优先级排序的关联表子集；第 32 行以 [code abstype] 登记 Abs_pq (alist_of q) = q。Code_Thingol.check_abstract_constructors 明确拒绝直接把抽象构造函数 Abs_pq 作为导出入口，报 Cannot export abstract constructor(s)。可执行接口应通过保留表示不变量的操作及 code abstract 方程进入，不能把任意原始列表直接当作公共代码构造子。


源位置：[PQ.thy](<evidence/sources/afp/Binomial-Queues/PQ.thy>) 第 18 行；[PQ.thy](<evidence/sources/afp/Binomial-Queues/PQ.thy>) 第 32 行；[code_thingol.ML](<evidence/sources/isabelle/Tools/Code/code_thingol.ML>) 第 843 行。

原始单常量证据：[frontend.xml](<evidence/current-candidates/exports/Binomial-Queues/Binomial-Queues/attempt-0002/attempts/merged/allRLLRRRL/frontend.xml>)。

## ADS_Functor：已有列表类型的同构 lifting 与原始 Nil 模式

入口：`ADS_Construction.blindable\<^sub>h.set_blindable\<^sub>h`。阶段：共享代码方程证书检查。

ADS_Construction.thy 第 518 行另建单构造子的 list_R1，随后以 type_definition list_to_list_R1 list_R1_to_list UNIV 证明它与已有 HOL list 同构，并在第 567 行 setup_lifting。lifting_setup 的 define_abs_type 可为该表示登记 Code.declare_abstype。当前合并上下文中，依赖方程 List.member [] ?y ≡ False 在 Code.check 的左侧模式检查失败：List.list.Nil 不再是当前代码表示接受的构造子。此处揭示的是逻辑 datatype 构造子与上下文选择的代码表示之间的区别；六目标共用前端已在打印前受阻。


源位置：[ADS_Construction.thy](<evidence/sources/afp/ADS_Functor/ADS_Construction.thy>) 第 518 行；[ADS_Construction.thy](<evidence/sources/afp/ADS_Functor/ADS_Construction.thy>) 第 564 行；[lifting_setup.ML](<evidence/sources/isabelle/HOL/Tools/Lifting/lifting_setup.ML>) 第 183 行；[code.ML](<evidence/sources/isabelle/Pure/Isar/code.ML>) 第 651 行。

原始单常量证据：[frontend.xml](<evidence/current-candidates/exports/ADS_Functor/ADS_Functor/attempt-0001/attempts/merged/allLLLLLRLRRR/frontend.xml>)。

## Abstract-Hoare-Logics：含嵌套元组、存在量化和关系闭包的集合推导式

入口：`PsHoareTotal.termi_call_steps`。阶段：共享集合预处理及证明项构造。

PsHoareTotal.thy 第 324 行定义 {((q,t),(p,s)). body p↓s ∧ (∃cs. ([body p],s) →* (CALL q#cs,t))}。代码预处理会通过 Product_Type 中登记的 set_comprehension simproc 把 Collect 改为 image、积和逆像。异常中的生成算子接收 (pname × state × pname × com list × state) set，实参却是 ((pname × state) × pname × com list × state) set。二者左侧元组嵌套不同，导致 Type error in application。现有单常量错误足以定位为目标无关的项构造/证明前提失败；没有精确内部调用栈时，不据此指定某一行辅助函数为唯一缺陷，也不把它归因于 AFP 原证明不成立。


源位置：[PsHoareTotal.thy](<evidence/sources/afp/Abstract-Hoare-Logics/Procs/PsHoareTotal.thy>) 第 324 行；[Product_Type.thy](<evidence/sources/isabelle/HOL/Product_Type.thy>) 第 1322 行；[set_comprehension_pointfree.ML](<evidence/sources/isabelle/HOL/Tools/set_comprehension_pointfree.ML>) 第 389 行。

原始单常量证据：[frontend.xml](<evidence/current-candidates/exports/Abstract-Hoare-Logics/Abstract-Hoare-Logics/attempt-0002/attempts/merged/allRLRRLRRL/frontend.xml>)。

## AVL-Trees：Quickcheck 自动生成的 narrowing_term 嵌套构造子模式

入口：`AVL.partial_term_of_tree_inst.partial_term_of_tree`。阶段：Go serializer 对带数字字面量适配的嵌套构造子模式名称解析。

tree datatype 自动生成 partial_term_of_tree 实例，将 narrowing_term 的变量/构造子树重建为 Code_Evaluation.term；嵌套构造子模式还包含 integer 标签的 Code_Numeral.Pos。正式结果是五目标成功、Go 单常量 Option。独立观察副本已把异常定位为 print_condition 第 273 行的 (mk_dest_name o deresolve) constr：失败符号为 Code_Numeral.Pos，已登记目标 const_syntax=true，而 Code_Namespace 的 AFP_Code 模块名称解析抛出 Option。Go_Setup 用 Numeral.add_code 为 Pos 注册字面量打印；Code_Target.prepare_serializer 会从普通程序命名范围扣除已有打印实现的符号。模式打印路径却仍按普通构造子取得名称并构造析构函数名，因而不满足这一目标适配前提。正式源没有修改。诊断使用复制的 Go_Setup/serializer，只增加查询观察，其他五语言的完整导出文件与原生基线逐字节相同。


源位置：[AVL.thy](<evidence/sources/afp/AVL-Trees/AVL.thy>) 第 23 行；[code_go.ML](<evidence/sources/afp/Go/code_go.ML>) 第 268 行；[code_go.ML](<evidence/sources/afp/Go/code_go.ML>) 第 272 行。

原始单常量证据：[Go.xml](<evidence/current-candidates/exports/AVL-Trees/AVL-Trees/attempt-0002/attempts/merged/allLLRLRLRL/Go.xml>)。

## Compiling-Exceptions-Correctly：Quickcheck 重建函数的正整数 narrowing 构造子标签

入口：`Exceptions.partial_term_of_expr_inst.partial_term_of_expr`。阶段：Go 层次程序符号名称解析。

Exceptions.thy 的 expr datatype 自动生成 partial_term_of_expr。保留的 Haskell 单常量源码直接展示 narrowing 构造子模式的 integer 标签 0、1、2、3；Go 同一作用域报 Unknown statement name: Code_Numeral.Pos，其余五目标成功。Go_Setup 对 Pos 登记数字字面量语法，Code_Target 可扣除已有目标打印实现的普通程序节点；Code_Namespace 的层次 deresolver 则要求查询符号仍在节点图中。这里已经定位到目标节点/名称解析的前提冲突，不能解释为 AFP 中未声明此常量。它与 AVL 的 Pos/Option 观察属于同一类目标适配交互，但本案例没有独立的 Go 内部调用栈，故不把 print_condition 第 273 行指定为已证实的唯一调用点。


源位置：[Exceptions.thy](<evidence/sources/afp/Compiling-Exceptions-Correctly/Exceptions.thy>) 第 13 行；[Go_Setup.thy](<evidence/sources/afp/Go/Go_Setup.thy>) 第 166 行；[code_target.ML](<evidence/sources/isabelle/Tools/Code/code_target.ML>) 第 418 行；[code_namespace.ML](<evidence/sources/isabelle/Tools/Code/code_namespace.ML>) 第 431 行；[AFP_Code.hs](<evidence/current-candidates/exports/Compiling-Exceptions-Correctly/Compiling-Exceptions-Correctly/attempt-0002/artifacts/merged/code/Haskell/allRLRRRLR/AFP_Code.hs>) 第 149 行。

原始单常量证据：[Go.xml](<evidence/current-candidates/exports/Compiling-Exceptions-Correctly/Compiling-Exceptions-Correctly/attempt-0002/attempts/merged/allRLRRRLR/Go.xml>)、[Haskell.xml](<evidence/current-candidates/exports/Compiling-Exceptions-Correctly/Compiling-Exceptions-Correctly/attempt-0002/attempts/merged/allRLRRRLR/Haskell.xml>)、[OCaml.xml](<evidence/current-candidates/exports/Compiling-Exceptions-Correctly/Compiling-Exceptions-Correctly/attempt-0002/attempts/merged/allRLRRRLR/OCaml.xml>)、[Rust.xml](<evidence/current-candidates/exports/Compiling-Exceptions-Correctly/Compiling-Exceptions-Correctly/attempt-0002/attempts/merged/allRLRRRLR/Rust.xml>)、[SML.xml](<evidence/current-candidates/exports/Compiling-Exceptions-Correctly/Compiling-Exceptions-Correctly/attempt-0002/attempts/merged/allRLRRRLR/SML.xml>)、[Scala.xml](<evidence/current-candidates/exports/Compiling-Exceptions-Correctly/Compiling-Exceptions-Correctly/attempt-0002/attempts/merged/allRLRRRLR/Scala.xml>)。

## Fresh_Identifiers：lift_definition 字符串接口经动态字符列表重建 literal

入口：`Fresh_String.fresh_literal_inst.fresh_literal`。阶段：Go 字符串目标语法打印。

Fresh_String.thy 第 232 行用 lift_definition 构造 fresh_literal，并在第 249–261 行通过 String.implode / explode 实现字符递增与 fresh 的代码接口。String.implode 的代码方程进入 String.literal_of_asciis；其递归方程从运行时字符位 b0…b6 与递归尾串构造 String.Literal。Go_Setup 第 52 行登记 Literal.add_code，将 String.Literal 当作原生字符串字面量打印；literal.ML 第 81–107 行只接受 True/False 位和最终空串，不能把上述变量与递归调用静态拼成字面量，因此精确报 Illegal string literal expression。Go_Setup 第 145 行把 literal_of_asciis 等列为 Bigint 模块依赖，并没有为这些常量登记运行时转换打印实现。官方四目标在 String.thy 第 876–885 行提供相应转换映射；本入口的实际五目标成功、Go 失败也已在单常量 XML 中证实。这是目标适配的动态转换前提不足，并非原 HOL 定义或逻辑证明失败。


源位置：[Fresh_String.thy](<evidence/sources/afp/Fresh_Identifiers/Fresh_String.thy>) 第 232 行；[Fresh_String.thy](<evidence/sources/afp/Fresh_Identifiers/Fresh_String.thy>) 第 249 行；[Go_Setup.thy](<evidence/sources/afp/Go/Go_Setup.thy>) 第 52 行；[Go_Setup.thy](<evidence/sources/afp/Go/Go_Setup.thy>) 第 141 行；[String.thy](<evidence/sources/isabelle/HOL/String.thy>) 第 673 行；[String.thy](<evidence/sources/isabelle/HOL/String.thy>) 第 691 行；[String.thy](<evidence/sources/isabelle/HOL/String.thy>) 第 876 行；[literal.ML](<evidence/sources/isabelle/HOL/Tools/literal.ML>) 第 81 行；[literal.ML](<evidence/sources/isabelle/HOL/Tools/literal.ML>) 第 102 行。

原始单常量证据：[Go.xml](<evidence/current-candidates/exports/Fresh_Identifiers/Fresh_Identifiers/attempt-0002/attempts/merged/allRLLL/Go.xml>)、[Haskell.xml](<evidence/current-candidates/exports/Fresh_Identifiers/Fresh_Identifiers/attempt-0002/attempts/merged/allRLLL/Haskell.xml>)、[OCaml.xml](<evidence/current-candidates/exports/Fresh_Identifiers/Fresh_Identifiers/attempt-0002/attempts/merged/allRLLL/OCaml.xml>)、[Rust.xml](<evidence/current-candidates/exports/Fresh_Identifiers/Fresh_Identifiers/attempt-0002/attempts/merged/allRLLL/Rust.xml>)、[SML.xml](<evidence/current-candidates/exports/Fresh_Identifiers/Fresh_Identifiers/attempt-0002/attempts/merged/allRLLL/SML.xml>)、[Scala.xml](<evidence/current-candidates/exports/Fresh_Identifiers/Fresh_Identifiers/attempt-0002/attempts/merged/allRLLL/Scala.xml>)。

## ArrowImpossibilityGS：共享集合预处理的模式合并不终止

入口：`GS.Top`。阶段：`Code_Preproc.obtain` 内 `set_comprehension` simproc 的 `rewrite_term` / `mk_pointfree_expr` / `mk_formula` / `merge'`。

[GS.thy](<evidence/sources/afp/ArrowImpossibilityGS/Thys/GS.thy>) 第18行定义 Top。其首个集合含 `(a∈S ∧ b∈S) ∨ (a∉S ∧ b∉S)`：析取两侧各自有两个独立变量模式。`merge_union` 合并这些模式时进入 [set_comprehension_pointfree.ML](<evidence/sources/isabelle/HOL/Tools/set_comprehension_pointfree.ML>) 第143行的 `merge'`。实际观察日志先记录 `comprehension_conv` 返回，再进入 `mk_formula`；随后记录的200次递归中，第1步起完整输入始终为：

```text
pat   = [1]
pats1 = [[0]]
pats2 = [[0]]
```

变量1与两个队列都不相交，因此 `overlap_pats=[]`、`rem_pats=pats`。原源码的递归参数 `distinct (flat overlap_pats @ pat), (rem_pats,pats1)` 恰好仍为 `[1], ([[0]],[[0]])`；非空基例均不适用。这是完整输入的固定循环，可以从源函数逐步核验。自然结果为 `Unable to increase stack` / `Interrupt_Breakdown`，没有 `after mk_formula` 或预处理返回。扩大线程栈至1 GiB的原生预检此前也失败；对已进入此固定状态的算法，更多资源不会提供终止路径。

[原生单常量请求范围](<evidence/current-candidates/exports/ArrowImpossibilityGS/ArrowImpossibilityGS/attempt-0009/contexts/merged.xml>)、[完整原生日志](<evidence/current-candidates/exports/ArrowImpossibilityGS/ArrowImpossibilityGS/attempt-0009/process.log>) 与 [大栈原生预检](<evidence/current-candidates/preflight/arrow-stack/attempt-0001/result.json>) 保留。共享预处理边界的原始进程日志见 [arrow-preproc-boundary](<evidence/current-candidates/mechanism/arrow-preproc-boundary/attempt-0002/process.log>)。精确循环观察的 [完整日志](<evidence/current-candidates/mechanism/arrow-pattern-merge/attempt-0001/process.log>)、[实际预处理输入项](<evidence/current-candidates/mechanism/arrow-pattern-merge/attempt-0001/pointfree-input.xml>)、[源改动清单](<evidence/current-candidates/mechanism/arrow-pattern-merge/attempt-0001/sources.json>)、[循环校验](<evidence/current-candidates/mechanism/arrow-pattern-merge/attempt-0001/cycle-analysis.json>) 均保留。观察变更可逐项反转为实际安装源码，原 heap、代码方程、正式翻译器和 serializer SHA 均未修改。另以64 MB heap / 8 MB stack独立运行抽取的原 `merge'` 和上述整数模式输入，也自然栈耗尽，见 [抽取原函数](<evidence/current-candidates/mechanism/abstract-pattern-merge/attempt-0001/original-function.ML>)、[完整日志](<evidence/current-candidates/mechanism/abstract-pattern-merge/attempt-0001/process.log>) 与 [结果](<evidence/current-candidates/mechanism/abstract-pattern-merge/attempt-0001/result.json>)；这是设施函数诊断，不是生成程序的运行时测试。

正式六语言现已在持锁调度器中依据各自原生 singleton 与独立源码不变式复核，记为 `failed / frontend_source_algorithm`。错误发生于共享前端，六个 serializer 均未执行；原生进程仍为 failed，finished.xml 仍不存在。GS.Top 和 GS.swf 的证据分别核验，详见[逐入口独立原始复核](<evidence/current-candidates/mechanism/native-source-fault-review.json>)。


GS.swf 的 [原生单常量请求范围](<evidence/current-candidates/exports/ArrowImpossibilityGS/ArrowImpossibilityGS/attempt-0013/contexts/merged.xml>) 与 [完整原生日志](<evidence/current-candidates/exports/ArrowImpossibilityGS/ArrowImpossibilityGS/attempt-0013/process.log>) 单独保留。随后以原 checked heap、同一合并上下文、256 MB maxheap / 64 MB stackspace / 32 MB线程栈进行 [独立观察](<evidence/current-candidates/mechanism/arrow-pattern-merge/attempt-0002/process.log>)，实际也记录同一固定递归状态，见 [循环校验](<evidence/current-candidates/mechanism/arrow-pattern-merge/attempt-0002/cycle-analysis.json>)。其 [预处理输入项](<evidence/current-candidates/mechanism/arrow-pattern-merge/attempt-0002/pointfree-input.xml>) 与 GS.Top 的输入项 SHA 均为 `1e97c9f0bc6cbc700cdb375114b3f41192bbecd561a68808dd03a750b79f2e66`。GS.thy 的 swf 定义直接使用 Top，这里同时有源码依赖和实际预处理证据。该观察自然栈耗尽，没有改变正式结果。

## ConcurrentGC：集合转换证明对未固定布尔目标无限引入合取

入口：`Global_Invariants.fA_rel`，以及下表中各个独立派生入口。阶段：共享 `Code_Preproc.obtain` / `set_comprehension` 的 `Goal.prove`。

### HOL 构造与实际触发项

[Global_Invariants.thy](<evidence/sources/afp/ConcurrentGC/Global_Invariants.thy>) 第248行的 fA_rel 是六个集合的并，其第三个集合为：

```isabelle
{ (in_sync, hp_InitMark, fA, ¬fA, [mw_fA (¬fA)]) | fA in_sync. in_sync }
```

第239行的 fM_rel 第二个集合具有同样的关键形状：

```isabelle
{ (in_sync, hp_Idle, fM, fM', [], l) | fM fM' in_sync l. in_sync }
```

布尔变量既是结果元组的一个分量，也是集合推导的筛选条件。实际输入保留在 [fA_rel 完整带类型项](<evidence/current-candidates/mechanism/concurrentgc-conversion/attempt-0002/pointfree-input.xml>)、[fM_rel 完整带类型项](<evidence/current-candidates/mechanism/concurrentgc-conversion/attempt-0003/pointfree-input.xml>)；fM_rel 的[诊断可读视图](<evidence/current-candidates/mechanism/concurrentgc-conversion/attempt-0003/pointfree-input.term.txt>)明确显示四个存在量词和最后的 `in_sync` 条件。可读视图仅省略类型，原始 XML 始终保留全部类型。

### 原生算法为何不能结束

[set_comprehension_pointfree.ML](<evidence/sources/isabelle/HOL/Tools/set_comprehension_pointfree.ML>) 第369–378行的 `subset_tac2` 依次执行像集消去、存在量词引入、`TRY o REPEAT_ALL_NEW (resolve_tac ctxt @{thms conjI})`，然后才做 `hyp_subst_tac` / `refl` 等见证约束处理。存在见证尚未由元组等式固定时，筛选条件成为可实例化的 schematic Boolean 目标。

`conjI` 的原规则是 `[P; Q] ⟹ P ∧ Q`，见 [HOL.thy](<evidence/sources/isabelle/HOL/HOL.thy>) 第501行。对固定合取，应用该规则会拆开已有结构；对 schematic Boolean 目标，规则结论的统一会把目标本身实例化成全新合取。真实 fA_rel 第100步的完整命题给出如下变化，`x⃗` 表示该目标的全部7个不同量化参数，`H` 表示保留的前提：

```text
H x⃗ ⟹ ?Q.65 x⃗
    ↓ conjI 的原生高阶 pattern 统一
H x⃗ ⟹ ?P.66 x⃗
H x⃗ ⟹ ?Q.66 x⃗
```

该步从28个子目标变为29个；输入活跃目标为最后第28个，返回后的第29个仍是应用于同一组不同 Bound 参数、返回 bool 的新 schematic 函数。[进入命题](<evidence/current-candidates/mechanism/concurrentgc-conversion/attempt-0002/proof-state-100.xml>)与[返回命题](<evidence/current-candidates/mechanism/concurrentgc-conversion/attempt-0002/proof-state-100-result.xml>)可逐项复核。fM_rel 独立观察得到同一形式，其参数数为10。

[Pure/tactical.ML](<evidence/sources/isabelle/Pure/tactical.ML>) 第307行定义 `REPEAT_ALL_NEW tac = tac THEN_ALL_NEW (TRY o (fn i => REPEAT_ALL_NEW tac i))`；[Pure/General/seq.ML](<evidence/sources/isabelle/Pure/General/seq.ML>) 第275行的 `INTERVAL` 从最右新增目标开始。因此新 schematic 目标总可再统一为合取，再留下一个同形的最右 schematic 目标。这个结构不变式可直接按原规则归纳：每次递归都有下一次成功展开，后续见证替换和其他待证目标始终到达不了。它不是状态不变的重复，也不是 Arrow 的 `merge'` 固定输入循环。

### 正式结果与独立证据

ConcurrentGC 的832个固定候选已经正式发布。`fA_rel`、`fM_rel`、`fA_rel_inv`、`fM_rel_inv`、`invs` 和 `Initial_Conditions.I` 均有各自正式单常量请求的自然失败日志、原始上下文和独立源码复核，六目标在该共享前端阶段记为 `failed / frontend_source_algorithm`。六个 serializer 在这些入口上均未执行；原生进程仍为 failed，缺失的 frontend.xml / finished.xml 没有被补造。

[fA_rel 的21对完整命题](<evidence/current-candidates/mechanism/concurrentgc-conversion/attempt-0002/nontermination-analysis.json>)和[fM_rel 的17对完整命题](<evidence/current-candidates/mechanism/concurrentgc-conversion/attempt-0003/nontermination-analysis.json>)分别覆盖7、10个不同量化参数。[独立原始审计](<evidence/current-candidates/mechanism/native-source-fault-review.json>)重新解码所有登记入口自己的带类型 XML，检查新变量、子目标编号、最右递归轨迹、原生 conjI 规则，以及观察源码能否精确反转为安装源码。登记、派生分析中的 passed 标记和有限重复次数都不能替代这些检查。

原 `full_export.ML` 的真实异常由[外层捕获器对照](<evidence/current-candidates/mechanism/native-exception-capture/attempt-0001/outcome-validation.json>)验证；捕获器保存异常后重新抛出，保留原脚本及 serializer 的 SHA 和实际退出状态。通用 schematic Boolean [设施对照](<evidence/current-candidates/mechanism/abstract-conjunction-repeat/attempt-0002/nontermination-analysis.json>)另外核验64对完整命题及递归源码，作为通用机制证据；它不构成 AFP 导出或生成程序的运行时测试。

`Global_Invariants.invs` 在 Global_Invariants.thy 第310行组合全局不变式。其[自身入口观察](<evidence/current-candidates/mechanism/concurrentgc-entry-observations/attempt-0001/source-invariant-review.json>)独立核验17对命题、10个参数。相同上下文的 [phase_rel](<evidence/current-candidates/mechanism/concurrentgc-entry-observations/attempt-0002/result.json>)和[phase_rel_inv](<evidence/current-candidates/mechanism/concurrentgc-entry-observations/attempt-0003/result.json>)预处理均正常返回；这些正常观察保留其实际状态，六目标结果由它们各自正式导出确定。其余入口的原生日志和证书列于下表及[关联证据索引](<evidence/current-candidates/mechanism/case-index.json>)。

## Stuttering_Equivalence：固定状态参数下的谓词合取扩张

入口：`PLTL.characteristic_formula`。阶段：共享 `Code_Preproc.obtain` 的集合 pointfree 证明。

[PLTL.thy](<evidence/sources/afp/Stuttering_Equivalence/PLTL.thy>) 第439–441行定义：

```isabelle
characteristic_formula A s ≡
  AND {atom(p) | p. p ∈ A ∧ p s}
  and AND {not atom(p) | p. p ∈ A ∧ ¬ p s}
```

谓词 `p` 同时出现在输出公式和布尔筛选中，状态 `s` 固定。原生完整带类型状态中的活跃结论是 `?F x p s`：`x,p` 是两个不同 Bound，`s` 是刚性类型变量 `a` 上的 Free，`F : pltl(a) -> (a -> bool) -> a -> bool`。这超出了 ConcurrentGC 的纯 Bound pattern 证书。旧证书确实拒绝它，原 [拒绝日志](<evidence/current-candidates/mechanism/stuttering-source-observations/attempt-0007/certification.log>) 和 producer 的空提案列表保持原字节；新类型族使用单独的证书及读取器。

[pointfree 证明](<evidence/sources/isabelle/HOL/Tools/set_comprehension_pointfree.ML>) 第369–374行先用 `exI` 引入尚未固定的谓词见证，再执行 `REPEAT_ALL_NEW conjI`，之后才替换见证。由于参数中含有 Free，[Pattern.ints_of](<evidence/sources/isabelle/Pure/pattern.ML>) 第117–121行拒绝 pattern 分支，[Unify](<evidence/sources/isabelle/Pure/unify.ML>) 第631行转入原生高阶统一。其第333–394行的投影及模仿分支在这个具体类型下具有可核验的选择：刚性 `a` 排除 `x` 和 `s` 投影；谓词 `p` 的投影以 Bound 为头，不能匹配规则结论的刚性 `conj`。模仿分支生成两个全新谓词，仍应用于同一个 `x,p,s` 参数向量。

第40步的[进入命题](<evidence/current-candidates/mechanism/stuttering-source-observations/attempt-0007/proof-state-40.xml>)和[返回命题](<evidence/current-candidates/mechanism/stuttering-source-observations/attempt-0007/proof-state-40-result.xml>)实际显示：

```text
?Q.57 x p s
    ↓ 原生 conjI 高阶模仿
?P.61 x p s
?Q.60 x p s
```

原始最大索引从58升为61。未证明的早期目标共享同一个谓词见证，也必须同步替换为 `λx p s. P x p s ∧ Q x p s`。独立读取器重新解码全部23对完整命题，保留所有常量、Free 和 schematic 变量的类型，进行避免变量捕获的 beta 替换，逐项比较早期目标及最终定理结论，并按 [Thm.full_prop_of](<evidence/sources/isabelle/Pure/thm.ML>) 第498行排除残留统一约束。读取器没有导入正式证据检查模块；详见[独立读取源码](<evidence/current-candidates/mechanism/audit-fixed-parameter.py>)、[独立九例复核](<evidence/current-candidates/mechanism/native-source-fault-review.json>)及[新证书](<evidence/current-candidates/mechanism/stuttering-source-observations/attempt-0007/fixed-parameter-nontermination-analysis.json>)。

[tactical.ML](<evidence/sources/isabelle/Pure/tactical.ML>) 第307行和 [Seq.INTERVAL](<evidence/sources/isabelle/Pure/General/seq.ML>) 第275行让递归先访问新生成的最右目标。该目标保留相同的刚性类型和参数形状，因此可继续按相同原生分支生成下一对新谓词。这个结构归纳解释了为什么后续见证替换无法到达；结论不依赖观察到的有限重复次数。

两个原始聚合请求分别在1389.45和1365.44秒后自然内存耗尽，完整日志均保留。首个请求的[独立内存复核](<evidence/current-candidates/mechanism/stuttering-first-memory-review/attempt-0001/analysis.md>)只把五秒窗口定位到 Poly/ML 的 GC 共享对象排序；当时未确定具体 HOL 根因。后来九次串行源码观察覆盖全部21个候选，才把问题缩小到该入口，并独立建立上述类型不变式。正常完成的预处理观察只证明前端返回，不能代替六语言导出结果。

该入口自己的[正式 singleton 日志](<evidence/current-candidates/exports/Stuttering_Equivalence/Stuttering_Equivalence/attempt-0007/process.log>)在2026-10-27T11:22:20Z自然退出，returncode=1，墙钟42.06秒；512 MiB资源配置没有时间限制，最小系统可用内存5383 MiB。[原始外层异常 XML](<evidence/current-candidates/exports/Stuttering_Equivalence/Stuttering_Equivalence/attempt-0007/native-request-outcome.xml>)记录实际 `Interrupt_Breakdown`。未补造 frontend.xml 或 finished.xml。正式派生记录经 [validate_record](<evidence/current-candidates/mechanism/stuttering-completed-review/attempt-0001/result.json>) 再次重读原始证据后通过；六目标均为 `failed / frontend_source_algorithm`，目标 serializer 尚未执行。Stuttering 全条目已正式完成：每个目标3个候选成功、18个失败，7个接受请求及两个历史聚合失败保留。


## Relative_Security：TWW 的空交集模式队列循环

入口：`Trivia.TWW`。阶段：共享 `Code_Preproc.obtain` 的 pointfree 模式合并。

[Trivia.thy](<evidence/sources/afp/Relative_Security/Preliminaries/Trivia.thy>) 第204–207行把 TWW 定义为两个 `turn × enat × enat` 三元组之间的关系。筛选式同时包含转向次序、相等条件及左右计数器比较，并通过合取和析取组合。原始[带类型输入](<evidence/current-candidates/mechanism/relative-pointfree-merge/attempt-0001/pointfree-input.xml>)和[自身观察日志](<evidence/current-candidates/mechanism/relative-pointfree-merge/attempt-0001/process.log>)保留了其真实预处理轨迹。

日志第1步出现完整递归状态：

```text
pat=[5], pats1=[[2],[3,0]], pats2=[[2],[4,1]]
             ↓ 原生空 overlap 分支
pat=[5], pats1=[[2],[4,1]], pats2=[[2],[3,0]]
             ↓ 同一分支
pat=[5], pats1=[[2],[3,0]], pats2=[[2],[4,1]]
```

选定模式与两侧每个模式都无交集；两侧队列均非空，选定模式非空且无重复。原[模式合并函数](<evidence/sources/isabelle/HOL/Tools/set_comprehension_pointfree.ML>) 的 `merge'` 分支在 overlap 为空时保持 `pat`，保留全部剩余模式并交换两侧队列。下一次调用仍满足相同条件，第二步恢复整个递归状态。因此这里可以按源码推出持续循环；两侧队列彼此都含有 `[2]` 不改变它们分别与选定 `[5]` 的空交集。这是 Arrow 案例已有机制在 TWW 自身入口上的独立证据。

自身正式[单例日志](<evidence/current-candidates/exports/Relative_Security/Relative_Security/attempt-0015/process.log>)于2026-10-27T11:48:31+00:00自然栈耗尽，实际墙钟22.04秒、returncode=1；精确起止时间以 sidecar 为准。[原始外层异常](<evidence/current-candidates/exports/Relative_Security/Relative_Security/attempt-0015/native-request-outcome.xml>)保存真实 Interrupt_Breakdown。后续串行源码观察使用相同理论清单，34.05秒后自然报相同异常，系统可用内存最低4826 MiB；记录源码只增加观察，编辑可逐字还原安装版及参考版。没有时间限制，也没有生成 frontend 或 finished 回执。

[独立读取审查](<evidence/current-candidates/mechanism/relative-pointfree-merge/attempt-0001/source-invariant-review.json>)从原始状态和源码重算两步完整循环；正式证据读取器也独立核验。随后[发布器](<evidence/current-candidates/execution/publish-Relative-source-observation.py>)仅把 TWW 自身六格未决状态归为 `failed / frontend_source_algorithm`；旧 native 字段、9个历史失败组、155份产物目录和全部其他候选保持一致，详见[发布回执](<evidence/current-candidates/mechanism/relative-pointfree-merge/attempt-0001/publication.json>)。Relative_Security 的287候选已完成：Rust/SML/OCaml/Haskell/Scala各26成功、261失败，Go为25成功、262失败。

诊断前的调度交接没有向 ML 或 scheduler 发信号。首个控制器选中无候选条目，未触发调度边界；目录已恢复，工具错误及[纠正说明](<evidence/current-candidates/execution/native-boundary-handoff-0011-correction.json>)保留。修正版仅选择固定候选非空的后续条目，在现有计算自然结束后记录真实目录创建异常并恢复权限，见[交接0012](<evidence/current-candidates/execution/native-boundary-handoff-0012.json>)。这些控制记录不赋予候选失败结论。

## 配置对照与证据边界

同一 `AVL.avl` 在默认源命名空间分模块时曾出现目标模块依赖环；显式统一模块 `AFP_Code` 后六语言均成功，见[原生配置对照](<evidence/current-candidates/preflight/module-name/attempt-0001/comparison.json>)。该历史配置失败保留在完整失败事件目录，当前候选结果采用实际新请求。

共享前端的资源耗尽先保留实际失败组，再细分请求；一个组失败不能判定其中每个常量失败。源算法归因还要求每个入口自己的自然失败 singleton 和原始源码结构证明。[登记表](<evidence/current-candidates/frontend-fault-cases.json>)只为已验证入口选择资源配置，不自行赋予六目标结果，也不设原生时间限制。观察进程串行运行，未运行生成程序。

早期部分正式请求的 process sidecar 墙钟时间包含原生退出后 Python 隔离诊断等待；它们用于过程证据，不能直接充当某个 serializer 的纯计算时间。步骤级 XML 计时、共享前端与目标阶段分别保留。诊断工具的静态错误、控制交接和旧配置记录都保留在原始材料中，不充当候选的语言失败 witness。

设施源码与实际安装的[逐字节比较](<evidence/current-candidates/mechanism/isabelle-source-comparison.json>)、观察编辑反转清单、[独立源码审计](<evidence/current-candidates/mechanism/native-source-fault-review.json>)和[机器可读案例索引](<evidence/current-candidates/mechanism/case-index.json>)构成复核入口。案例给出具体调用点的范围以各自证据为限；没有独立内部轨迹的案例不借用其他入口的调用栈。

<!-- registered-source-observation-coverage:begin -->

### 已登记源不变式的独立覆盖

当前[显式登记](<evidence/current-candidates/frontend-fault-cases.json>)中的每个入口均由[独立原始证据审计](<evidence/current-candidates/mechanism/native-source-fault-review.json>)重新解码自身轨迹并核验安装源码、参考源码和原生递归分支。下表保留原生进程的实际状态；正式候选的六目标状态仍取自正式结果文件。

| 独立入口 | 自身观察证据 | 带类型命题对 | 不同量化参数 | 自身正式 singleton |
| --- | --- | ---: | --- | --- |
| `GS.Top` | [轨迹](<evidence/current-candidates/mechanism/arrow-pattern-merge/attempt-0001/process.log>) | 0 | 模式循环 | [failed / returncode 1](<evidence/current-candidates/exports/ArrowImpossibilityGS/ArrowImpossibilityGS/attempt-0009/process.log>) |
| `GS.swf` | [轨迹](<evidence/current-candidates/mechanism/arrow-pattern-merge/attempt-0002/process.log>) | 0 | 模式循环 | [failed / returncode 1](<evidence/current-candidates/exports/ArrowImpossibilityGS/ArrowImpossibilityGS/attempt-0013/process.log>) |
| `Global_Invariants.fA_rel` | [证明](<evidence/current-candidates/mechanism/concurrentgc-conversion/attempt-0002/nontermination-analysis.json>) | 21 | 7 | [failed / returncode 1](<evidence/current-candidates/exports/ConcurrentGC/ConcurrentGC/attempt-0008/process.log>) |
| `Global_Invariants.fM_rel` | [证明](<evidence/current-candidates/mechanism/concurrentgc-conversion/attempt-0003/nontermination-analysis.json>) | 17 | 10 | [failed / returncode 1](<evidence/current-candidates/exports/ConcurrentGC/ConcurrentGC/attempt-0011/process.log>) |
| `Global_Invariants.fA_rel_inv` | [证明](<evidence/current-candidates/mechanism/concurrentgc-conversion/attempt-0004/nontermination-analysis.json>) | 21 | 7 | [failed / returncode 1](<evidence/current-candidates/exports/ConcurrentGC/ConcurrentGC/attempt-0010/process.log>) |
| `Global_Invariants.fM_rel_inv` | [证明](<evidence/current-candidates/mechanism/concurrentgc-conversion/attempt-0005/nontermination-analysis.json>) | 17 | 10 | [failed / returncode 1](<evidence/current-candidates/exports/ConcurrentGC/ConcurrentGC/attempt-0014/process.log>) |
| `Global_Invariants.invs` | [证明](<evidence/current-candidates/mechanism/concurrentgc-entry-observations/attempt-0001/nontermination-analysis.json>) | 17 | 10 | [failed / returncode 1](<evidence/current-candidates/exports/ConcurrentGC/ConcurrentGC/attempt-0019/process.log>) |
| `Initial_Conditions.I` | [证明](<evidence/current-candidates/mechanism/concurrentgc-pending-preflight/attempt-0005/nontermination-analysis.json>) | 17 | 10 | [failed / returncode 1](<evidence/current-candidates/exports/ConcurrentGC/ConcurrentGC/attempt-0030/process.log>) |
| `PLTL.characteristic_formula` | [证明](<evidence/current-candidates/mechanism/stuttering-source-observations/attempt-0007/fixed-parameter-nontermination-analysis.json>) | 23 | 2 | [failed / returncode 1](<evidence/current-candidates/exports/Stuttering_Equivalence/Stuttering_Equivalence/attempt-0007/process.log>) |
| `Trivia.TWW` | [证明](<evidence/current-candidates/mechanism/relative-pointfree-merge/attempt-0001/source-invariant-review.json>) | 0 | 模式循环 | [failed / returncode 1](<evidence/current-candidates/exports/Relative_Security/Relative_Security/attempt-0015/process.log>) |

`Initial_Conditions.I` 在 Initial_Conditions.thy 第96行定义为 `(invsL \<^bold>\<and> LSTP invs)`。其独立入口观察实际保存17对完整前后命题，每个活跃 schematic Boolean 函数应用于全部10个不同量化参数，满足同一最右合取扩张不变式。该观察来自剩余固定候选的[串行预检](<evidence/current-candidates/mechanism/concurrentgc-pending-preflight/progress.json>)；31次不限时原生观察覆盖全部808个候选，只有这一入口新增资源配置。发布器[重读所有原始证据并严格重核源码](<evidence/current-candidates/mechanism/concurrentgc-pending-preflight/publication.json>)后才追加配置，原有16份已接受请求、10个失败组和候选上下文顺序均保持一致；正式singleton仍调用原始 full_export.ML。

<!-- registered-source-observation-coverage:end -->

<!-- imp-declaration-context-coverage:begin -->

## IMP_With_Speculation：同名重建函数的五个来源上下文

Fun2/3/4 分别声明自己的 Unwinding_fin.Rel_Sec.partial_term_of_status_inst.partial_term_of_status，Fun5/6 分别声明自己的 Unwinding.Rel_Sec.partial_term_of_status_inst.partial_term_of_status。同一名字串的成功或失败不能代替另一个来源的证据。独立读取器逐一检查物理 XML、上下文祖先及声明所属理论，覆盖五个来源×六目标的30格；见[完整来源证据](<evidence/current-candidates/mechanism/imp-context-witness-review/attempt-0001/result.json>)。

| 声明来源 | Rust/SML/OCaml/Haskell/Scala | Go 自身诊断 |
| --- | --- | --- |
| Examples/Fun2.thy | 通过 | [exception Option raised (line 84 of "General/basics.ML")](<evidence/current-candidates/exports/IMP_With_Speculation/IMP_With_Speculation/attempt-0001/attempts/branch2/allRRRRRRRRRR/Go.xml>) |
| Examples/Fun3.thy | 通过 | [exception Option raised (line 84 of "General/basics.ML")](<evidence/current-candidates/exports/IMP_With_Speculation/IMP_With_Speculation/attempt-0001/attempts/branch3/allRRRRRRRRRR/Go.xml>) |
| Examples/Fun4.thy | 通过 | [exception Option raised (line 84 of "General/basics.ML")](<evidence/current-candidates/exports/IMP_With_Speculation/IMP_With_Speculation/attempt-0001/attempts/branch4/allRRRRRRRRRR/Go.xml>) |
| Examples/Fun5.thy | 通过 | [exception Option raised (line 84 of "General/basics.ML")](<evidence/current-candidates/exports/IMP_With_Speculation/IMP_With_Speculation/attempt-0001/attempts/branch5/allRRRRRRRRRR/Go.xml>) |
| Examples/Fun6.thy | 通过 | [exception Option raised (line 84 of "General/basics.ML")](<evidence/current-candidates/exports/IMP_With_Speculation/IMP_With_Speculation/attempt-0001/attempts/branch6/allRRRRRRRRRR/Go.xml>) |

这些入口是 Quickcheck narrowing 项的重建函数；此表以自身异常确定目标失败及其上下文范围。其他案例的 Go 内部观察不作为这些入口的调用栈证明。五语言的成功文件、Go完整异常以及每个上下文的祖先清单均保留在上面的来源目录中。

<!-- imp-declaration-context-coverage:end -->

<!-- ceva-environment-interruption:begin -->

### 环境中断与后来原生结果：Ceva

Ceva.Triangle_area 的首次请求在读取 scope.txt 时遇到 ENOENT；其 scheduler、driver 与旧观察器也曾无法读取各自的绝对路径，文件随后重新可读且 boot id 未变。底层原因未确定。首次 sidecar 保留 running，身份已经死亡，没有实际退出码或完成回执；该次环境中断没有决定任何候选状态。[原始中断记录](<evidence/current-candidates/recovery/filesystem-interruption-0001/result.json>)保留完整原生日志引用，唯一恢复只移除 journal 的死 active 指针并保留 pending 和历史。

[第二次原生请求日志](<evidence/current-candidates/exports/Ceva/Ceva/attempt-0002/process.log>)在8.03秒后正常退出，返回码0且存在 finished.xml。它的[物理单候选前端回执](<evidence/current-candidates/exports/Ceva/Ceva/attempt-0002/attempts/merged/all/frontend.xml>)记录同一条 wellsortedness 错误：依赖 Triangle_area → sin → suminf → sums → nhds → Inf [filter] 需要 filter :: enum，而该类型类实例不存在，六个目标均由共享前端拒绝。这个后来获得的逻辑拒绝与先前环境中断分别保留。

[独立只读复核](<evidence/current-candidates/mechanism/ceva-environment-recovery-review/attempt-0001/result.json>)逐字节核对中断记录中的9份材料、首次未知退出状态、唯一恢复、第二次物理XML及正式六格结果；没有重写原 sidecar、合成退出码、重启原生请求或赋予环境原因。这里是恢复与证据边界说明，六格候选结果仅依据第二次请求。
<!-- ceva-environment-interruption:end -->

<!-- statecharts-aggregate-resource-review:begin -->
## Statecharts：聚合请求的自然内存失败

385 个候选的首个原生请求于 2026-10-27T14:28:40Z 自然结束，返回码 1，墙钟 2657.84 秒。请求禁用超时、maxheap 4500 MB；完整日志明确报出 Run out of store，外层原生捕获为 Interrupt_Breakdown，命令记录的最低可用内存为 1415 MiB。已有 loaded、declarations 和 merged 上下文，尚无组 attempt 或 finished 回执。实际父理论为 Statecharts.CarAudioSystem、Rust.Rust_BigInt_Setup、Go.Go_Setup；没有取得六目标各自的终结结果。[完整日志](<evidence/current-candidates/exports/Statecharts/Statecharts/attempt-0001/process.log>)、[sidecar](<evidence/current-candidates/exports/Statecharts/Statecharts/attempt-0001/process.log.json>)、[原生外层回执](<evidence/current-candidates/exports/Statecharts/Statecharts/attempt-0001/native-request-outcome.xml>)。

独立复核的 22 项检查通过，scope、上下文与外层捕获的 385 个名字完全一致，原始 sidecar 和证据哈希匹配。既有调度器把该失败保留为历史聚合重试，候选结论必须来自后续较小请求各自的原生证据；不能将一次聚合内存失败赋给所有候选。[机器复核](<evidence/current-candidates/mechanism/statecharts-first-memory-review/attempt-0001/result.json>)、[完整分析](<evidence/current-candidates/mechanism/statecharts-first-memory-review/attempt-0001/analysis.md>)。

已有约 5 秒的用户态地址采样共 100 样本、0 丢失：88 个精确落入 Poly/ML 的 SortVector::sortList，另 12 个在 libc。本机运行时源码确认该原生函数属于 GC 对象共享排序。另一个独立统计快照记录 GCState=3、ThreadsInML=0；它与地址采样相隔约 17 分钟，不能作为同时采集或整段 GC 比例。两项观测均绑定该首个请求的 birth identity，不能用于解释后来请求。尚未定位导致堆增长的 HOL 构造或 ML 函数，也没有证明不终止。复核未启动第二个 ML、未发信号、未运行生成程序。
后续较小请求的调度于 2026-10-27T21:26:18Z 完成。2026-10-27T23:24:31Z 的局部审核读取当时的正式条目版本 `64c43341b3f77fbaf924446a76b79e9f915d2096636db17cf6a6cedfb3bf7655`：12 个已接受原生请求的作用域恰好划分全部 385 候选；9 个命令正常返回，3 个命令自然失败。已判定候选逐格核到自己的原始 frontend 或目标回执，3,349 份 attempt XML 与正式记录一致。Rust/SML/OCaml/Haskell/Scala 当时各有 132 passed、250 failed、3 blocked；Go 为 129 passed、253 failed、3 blocked。该带时间的快照具体说明一次聚合资源失败不能成为所有候选失败的依据，也说明原生命令成功数不能代替候选成功数。[审核结果](<evidence/current-candidates/mechanism/statecharts-published-evidence-review/attempt-0001/result.json>)、[范围及方法](<evidence/current-candidates/mechanism/statecharts-published-evidence-review/attempt-0001/analysis.md>)。

该快照全部 779 份正式保留文件的字节数及 SHA256 匹配，总计 2,462,848 字节，包含 94 个 Rust crate；文件集合与原始成功目标回执列出的文件集合一致。[完整产物索引](<evidence/current-candidates/mechanism/statecharts-published-evidence-review/attempt-0001/artifact-index.json>)、[原始回执索引](<evidence/current-candidates/mechanism/statecharts-published-evidence-review/attempt-0001/receipt-index.json>)。

当时未决的三个 singleton 分别是 `HAKripke.HA2Kripke`、`HAKripke.LabelFunSem`、`HAKripke.eval_ctl_HA`，各自原生命令退出码 1，各自日志包含 Run out of store 和 Interrupt_Breakdown，各自 outer 为 Interrupt_Breakdown，无 attempt 或 finished。它们在这个版本中的六目标格仍为 blocked；这些资源事实没有被当作具体源码故障证明。[各自原生命令来源索引](<evidence/current-candidates/mechanism/statecharts-published-evidence-review/attempt-0001/native-source-index.json>) 保留完整日志等文件的哈希。后续诊断可能发布新的正式版本，最终候选统计须取最终 data audit 对应的版本；本局部审核不替代全量审计。

<!-- statecharts-aggregate-resource-review:end -->

<!-- ill-successful-performance-case:begin -->
## ILL：同一成功作用域的导出性能

这不是候选失败案例。ILL 的 merged/allLLRLRLL 作用域含三个常量：Proof.equal_ill_deduct_inst.equal_ill_deduct、Proof.equal_ill_sequent_inst.equal_ill_sequent、Proof.full_exhaustive_ill_deduct_inst.full_exhaustive_ill_deduct。共同前端和六个目标均成功；原生请求自然结束，有 finished 回执，完整日志和全部产物均保留。[已完成局部核验](<evidence/current-candidates/mechanism/ill-completed-review/attempt-0001/analysis.md>)。

| 阶段／目标 | 原生回执秒数 | 该目标保留文件总字节数 |
| --- | ---: | ---: |
| 共同前端 | 0.111 | — |
| Rust | 26647.962 | 505,935 |
| SML | 0.031 | 140,399 |
| OCaml | 0.021 | 125,774 |
| Haskell | 0.018 | 105,381 |
| Scala | 1.929 | 130,818 |
| Go | 0.091 | 217,036 |

目标阶段边界包括 Code_Target.export_code_for、导出文件提取和产物写入。ILL 整个请求的墙钟为 26686.05 秒，不能把它等同于这一组三常量的 Rust 计时。目标顺序固定，先前调用和缓存状态会影响比较；这是单次观测，不是重复测量的吞吐基准，也不是生成程序的运行速度。

10 个文件的相对路径均以原生请求目录为基准，尺寸和 SHA-256 匹配正式产物。Rust 主文件为 505,695 字节、3,703 行，最长单行为 17,451 字节；各目标的包结构和支持代码不同。字节数仅补充规模背景，不能推导生成算法复杂度或定位耗时函数。[产物规模核验](<evidence/current-candidates/mechanism/ill-output-size-review/attempt-0001/result.json>)、[规模分析及读取器纠正](<evidence/current-candidates/mechanism/ill-output-size-review/attempt-0001/analysis.md>)。

既有离散资源窗口中 GC CPU 增量仅约占观测 ML CPU 增量的 0.17%，并且早期指令地址采样位于匿名可执行区域。该证据没有确定具体 ML 函数或源码耗时机制。这里准确保留这个不确定性；后续全量 data audit 和最终独立计时核验仍负责整个固定候选实验的交付验收。
<!-- ill-successful-performance-case:end -->

## 日志目录的口径

本次前两阶段共收录 1,175,377 个失败、阻塞或阶段切换事件，完整正文缺失标记为 0，证据文件问题为 0。事件包含递归拆分的聚合诊断、单候选决定性失败和历史尝试；historical 与 group_diagnostic 字段保留这些区别。尝试事件数不能用作候选失败率。

[完整失败正文及原始日志路径](<failures.jsonl>) · [按阶段/目标/历史状态分类](<failure-events-by-category.csv>) · [逐失败候选及主证据](<failed-candidates.csv>)

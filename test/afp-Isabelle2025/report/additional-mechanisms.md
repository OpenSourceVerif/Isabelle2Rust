# 补充导出机制：原粗分类中的 92 个失败单元

> 保留范围说明（2026-10-28 迁移）：本页统计沿用当时快照，未重算。全量导出及编译产物已清理，无法逐项重新核验；正文案例的原始证据及引用源码按 [精选证据清单](selected-evidence.jsonl) 保留。原表格、完整失败正文及原哈希索引属于 [历史索引](HISTORICAL-INDEXES.md)，其中路径不代表文件仍存在。



本页按完整异常细分主证据，没有重新导出或修改翻译规则。92 指（条目、候选、目标）失败单元，不是 92 个独立根因。完整事件目录仍保留原来的粗分类；候选分类表已使用本页四类。

| 细分类 | 失败单元 |
| --- | --- |
| program_graph_lookup | 44 |
| self_referential_nullary | 19 |
| equation_lhs_abstraction | 24 |
| list_length_invariant | 5 |

## Coinductive_Languages 与 Stern_Brocot：自引用的无参数共递归值

Coinductive_Language.Zero、Full 以及 bird 等定义是没有显式参数的共递归值。例如 Bird_Tree 的 bird = Node (1,1) (...) (...) 在子树中再次引用 bird；其他入口也可能因依赖这些值而失败。Rust 目标实际报 self-referential nullary values，共涉及 19 个 Rust 失败单元。

现有 Rust 后端 print_stmt 的 Funs 分支在 pseudo_funs 非空时明确拒绝这类值。源码注释说明当前 eager owned 表示不能直接承载它们；把常量改成会立即递归构造自身的函数也不能实现源语言的生产性共数据。这里是已声明的表示边界检查，不是 rustc 编译错误。

[Rust 后端](<evidence/sources/translate/code_rust.ML>) 第 3019–3031 行；[语言共数据定义](<evidence/sources/afp/Coinductive_Languages/Coinductive_Language.thy>) 第 47–57、254 行；[bird 定义](<evidence/sources/afp/Stern_Brocot/Bird_Tree.thy>) 第 14–16 行。

[完整单候选 XML](<evidence/current-candidates/exports/Coinductive_Languages/Coinductive_Languages/attempt-0001/attempts/merged/allLLLLLL/Rust.xml>)；入口：Coinductive_Language.Atom。

[完整单候选 XML](<evidence/current-candidates/exports/Stern_Brocot/Stern_Brocot/attempt-0001/attempts/merged/allLLLLLLLLLL/Rust.xml>)；入口：Bird_Tree.bird。

## Coinductive：惰性列表代码方程左侧含 lambda

lsorted、inf_llist、tllist_ord 的实际失败方程左侧出现 Lazy_llist (λ_. Some (...)) 或 Lazy_tllist (λ_. Inl (...))。共享前端在六目标打印前报 Abstraction on left hand side of equation，4 个候选共形成 24 个目标失败单元。

Code.check 的左侧模式检查直接对 Abs 项抛出 BAD_THM；代码方程的左侧需要符合当前代码表示的构造子模式前提。这不是说 HOL 方程不成立，而是这组惰性表示方程不能直接通过该证书检查。

[代码证书检查](<evidence/sources/isabelle/Pure/Isar/code.ML>) 第 651 行。

[完整单候选 XML](<evidence/current-candidates/exports/Coinductive/Coinductive/attempt-0001/attempts/merged/allLRLLLLRR/frontend.xml>)；入口：Coinductive_List.ord.lsorted。

## Isabelle_Meta_Model：已适配类型的 Scala 图节点查询

Printer_init 第 274–284 行声明 ml_int 和 ml_monad datatype，并为 Scala 注册 CodeType.mlInt 与 CodeType.mlMonad 类型打印适配。equal、full_exhaustive 等辅助入口在 Scala 的目标准备/序列化阶段报 UNDEF (Type_Constructor Printer_init.ml_int/ml_monad)，共 20 个 Scala 失败单元。

General/graph.ML 的 get_entry 在键不属于图时抛出 UNDEF，证明查询发生时相应类型节点缺失。已有目标类型适配与普通程序节点的使用前提需要一致；当前原始异常没有内部调用栈，因此不能仅凭该异常指定 Scala 中某个调用点为唯一缺陷。

[类型与目标适配](<evidence/sources/afp/Isabelle_Meta_Model/meta_isabelle/Printer_init.thy>) 第 274–284 行；[图查询](<evidence/sources/isabelle/Pure/General/graph.ML>) 第 126–129 行。

[完整单候选 XML](<evidence/current-candidates/exports/Isabelle_Meta_Model/Isabelle_Meta_Model/attempt-0001/attempts/merged/allRRRRRLRLRLLL/Scala.xml>)；入口：Printer_init.equal_ml_int_inst.equal_ml_int。

## Correctness_Algebras：函数幂依赖中的函数节点缺失

Hoare.hoare_calculus_class.tseq 的定义通过 (tfun p x q ^ m) r 迭代函数。4 个相关候选在共享前端报 UNDEF (Fun Base.one_fun_inst.one_fun, 1)，因此 24 个目标失败单元共用前端失败证据。此处查询的节点是函数符号及其相关编号，与上一个 Scala 类型节点案例的失败阶段不同。

可核验的设施前提仍是图查询的键必须存在。日志给出缺失的 one_fun 依赖，尚未给出构图或查询的完整内部轨迹；本报告保留这一定位边界，不把它当作 Rust 专属错误。

[函数迭代定义](<evidence/sources/afp/Correctness_Algebras/Hoare.thy>) 第 323–324 行。

[完整单候选 XML](<evidence/current-candidates/exports/Correctness_Algebras/Correctness_Algebras/attempt-0001/attempts/merged/allLRLRLRRLL/frontend.xml>)；入口：Hoare.hoare_calculus_class.tseq。

## Top_Down_Solver：Rust 目标中的双列表长度前提

Example.ConstrSys 用含函数续体的 Query/Answer 策略树描述四个未知量的约束系统；solution_plain_X/Y/Z/W 等入口调用 TD_plain_Interp_solve。5 个入口在 Rust 目标阶段报 UnequalLengths，位置为 library.ML 第 530 行。

该位置是 map2 的兜底分支：两个列表必须同时为空，或同时有头尾。异常证实调用时两列表长度不相等。现有日志没有记录调用者及两列表内容，尚不能确定是参数、类型变量还是其他配对列表不匹配；没有据此指定具体 Rust 打印函数。

[策略树与求解入口](<evidence/sources/afp/Top_Down_Solver/Example.thy>) 第 91–127 行；[map2 长度检查](<evidence/sources/isabelle/Pure/library.ML>) 第 528–530 行。

[完整单候选 XML](<evidence/current-candidates/exports/Top_Down_Solver/Top_Down_Solver/attempt-0001/attempts/merged/allLRRRRRLR/Rust.xml>)；入口：Example.solution_plain_W。

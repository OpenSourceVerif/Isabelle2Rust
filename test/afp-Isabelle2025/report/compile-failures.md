# 15 个可导出但 Stage 1 编译失败案例的分析

本分析依据实验 **20261020T074609Z** 的记录，不重新运行实验，也不修改翻译器、优化器或 AFP。分母为 [results.json](../results.json) 中 `rust_export.status = passed` 且 `stage1_compile.status = failed` 的 **15 个条目**。本轮 41 个条目得到 Rust crate，其中 26 个通过 Stage 1，15 个失败（36.59%）。这 15 个条目的扫描、理论加载和导出均成功；Cargo 退出码均为 101，优化和 Stage 2 均未执行。

**这些失败集中于当前 Rust 输出的类型类实例、约束和表达式打印；没有证据将其中任何一个编译失败归因于 AFP 原证明或原定义错误。**其中数值目标的实例衔接属于支持覆盖缺口；已生成代码自身的前提不一致、实例漏发和非法表达式，则是实际的后端生成错误。Sturm_Sequences 还包含明确标记为不可执行的库操作，需要单独区分编译适配与运行时可执行性。

## 统计口径

逐份读取完整 Cargo 日志，计数每个 `error[...]` 或无编号 `error:` 的诊断头，排除最后一行 `could not compile ... due to N previous errors`。得到 **103 条诊断**，与各日志的最终错误总数逐项一致。其中 E0277 为 95 条（92.23%），E0308 为 4 条，E0614、E0618 各 1 条，无错误编号的语法/宏错误为 2 条。

一条诊断只归入下面一个原因类别，因此诊断数合计为 103；同一个条目可以涉及多个类别，条目覆盖数不能相加。六类是原因族，不代表只有六个独立 bug；例如 Code.abort 同时暴露消息表示和参数数量两个问题。诊断数也不是失败函数数，更不是修复工作量。

| 类别 | 原因 | 涉及条目 / 15 | 条目覆盖率 | 诊断 / 103 | 诊断占比 | 归因 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| A | BigInt 与生成的 HOL 数值 trait 缺少衔接 | 9 | 60.00% | 64 | 62.14% | Rust 数值目标适配支持不足 |
| B | 补出的父类实例约束与使用方不一致 | 6 | 40.00% | 15 | 14.56% | Rust 后端实际生成错误 |
| C | 递归数据类型的具体实例未输出 | 3 | 20.00% | 16 | 15.53% | Rust 后端实例发射错误 |
| D | if/match 作为二元运算操作数时缺括号 | 2 | 13.33% | 5 | 4.85% | Rust 后端表达式打印错误 |
| E | Code.abort 的 panic! 适配不合法 | 1 | 6.67% | 2 | 1.94% | Rust 目标适配规则错误 |
| F | 高阶组合的函数返回形状不一致 | 1 | 6.67% | 1 | 0.97% | Rust 后端函数形状/应用打印错误 |

按互斥的条目组合看：7 个目前只报告 A，2 个只报告 B，1 个只报告 F；其余 5 个为多因混合：FeatherweightJava 为 A+B+C，Gray_Codes 为 A+D，Nano_JSON 为 B+C，Sturm_Sequences 为 B+E，Trie 为 B+C+D。该口径合计正好 15。

## 逐条结果

“诊断分解”中 A31 表示该条目的 31 条诊断属于 A 类。条目链接保存原理论、完整 Rust crate 和来源清单；诊断数链接直接打开本次完整 Cargo 日志。逐诊断的错误码、消息、源文件位置和日志行号见 [JSON](compile-failures.json)，每条目一行的明细见 [CSV](compile-failures.csv)。

| 条目 | 候选数 | 诊断数 | 诊断分解 | 具体失败原因 |
| --- | ---: | ---: | --- | --- |
| [Approximation_Algorithms](compile-cases/Approximation_Algorithms/) | 5 | [1](compile-cases/Approximation_Algorithms/logs/stage1-1.compile.txt) | A1 | `f_Max_0` 调用 `max<BigInt>`，缺生成模块的 `Orderings::Ord`。 |
| [Binomial-Queues](compile-cases/Binomial-Queues/) | 50 | [3](compile-cases/Binomial-Queues/logs/stage1-1.compile.txt) | B3 | `List<A>` 的 Typerep 要求 `A: PartialTermOf`，TermOf 实例及 PQ 的反射调用未满足该额外前提。 |
| [Digit_Expansions](compile-cases/Digit_Expansions/) | 8 | [11](compile-cases/Digit_Expansions/logs/stage1-1.compile.txt) | A11 | `nth_bit/nth_digit`、进位/借位函数的 `power<BigInt>` 缺本地 `Times`；`One` 已实现。 |
| [FeatherweightJava](compile-cases/FeatherweightJava/) | 146 | [47](compile-cases/FeatherweightJava/logs/stage1-1.compile.txt) | A31+B4+C12 | BigInt 缺 Equal/Ord；List 的父类前提不一致；Exp 的 Equal/TermOf 实例未输出。 |
| [Gray_Codes](compile-cases/Gray_Codes/) | 12 | [7](compile-cases/Gray_Codes/logs/stage1-1.compile.txt) | A4+D3 | `sum_list<BigInt>` 缺本地 Zero/Plus；`hamming` 的 if 与后续加法缺括号。 |
| [Latin_Square](compile-cases/Latin_Square/) | 21 | [6](compile-cases/Latin_Square/logs/stage1-1.compile.txt) | A6 | 拉丁方检查的集合/列表操作缺 BigInt: Equal（4 条）；Natural 支持函数缺 BigInt: Ord（2 条）。 |
| [List_Inversions](compile-cases/List_Inversions/) | 9 | [4](compile-cases/List_Inversions/logs/stage1-1.compile.txt) | A4 | 逆序索引对集合的相等、去重、基数操作需要 `(BigInt,BigInt): Equal`，最终缺 BigInt: Equal。 |
| [Max-Card-Matching](compile-cases/Max-Card-Matching/) | 12 | [3](compile-cases/Max-Card-Matching/logs/stage1-1.compile.txt) | A3 | `weight` 的有限集求和要求索引 Equal、结果 CommMonoidAdd，分别缺 BigInt 的 Equal、Zero、Plus。 |
| [Nano_JSON](compile-cases/Nano_JSON/) | 36 | [4](compile-cases/Nano_JSON/logs/stage1-1.compile.txt) | B2+C2 | List 的反射父类前提不一致；`set1_json/set2_json` 经 `snds` 构造集合，缺 Json: Equal。 |
| [Pairing_Heap](compile-cases/Pairing_Heap/) | 57 | [2](compile-cases/Pairing_Heap/logs/stage1-1.compile.txt) | B2 | List 的 TermOf impl 声明与递归调用都无法满足 Typerep 额外要求的 PartialTermOf。 |
| [Sauer_Shelah_Lemma](compile-cases/Sauer_Shelah_Lemma/) | 2 | [2](compile-cases/Sauer_Shelah_Lemma/logs/stage1-1.compile.txt) | A2 | `sup_nat` 判空缺 BigInt: Equal，求最大值缺 Linorder，后者最终缺本地 Ord。 |
| [Sturm_Sequences](compile-cases/Sturm_Sequences/) | 15 | [3](compile-cases/Sturm_Sequences/logs/stage1-1.compile.txt) | B1+E2 | Poly 的 Modulo 父类链缺 UnitFactor；Code.abort 使用动态 Literal 作为格式串，且将 panic 的结果继续当函数应用。 |
| [TortoiseHare](compile-cases/TortoiseHare/) | 49 | [2](compile-cases/TortoiseHare/logs/stage1-1.compile.txt) | A2 | 库支持函数 `natural_of_integer/minus_natural` 调用 `max<BigInt>`，缺本地 Ord；报错位置不在龟兔算法主体。 |
| [Trie](compile-cases/Trie/) | 29 | [7](compile-cases/Trie/logs/stage1-1.compile.txt) | B3+C2+D2 | Option/List 的反射父类前提不一致；缺 Trie: Equal；`all_trie` 的 match 与 `&&` 缺括号。 |
| [Vickrey_Clarke_Groves](compile-cases/Vickrey_Clarke_Groves/) | 74 | [1](compile-cases/Vickrey_Clarke_Groves/logs/stage1-1.compile.txt) | F1 | `chosenAllocationAlg` 的高阶组合把应返回函数的适配器标成返回 Set，后续多阶段应用对 Set 解引用。 |

## A. 数值表示已有，泛型 trait 实例衔接不足

9 个条目为 Approximation_Algorithms、Digit_Expansions、FeatherweightJava、Gray_Codes、Latin_Square、List_Inversions、Max-Card-Matching、Sauer_Shelah_Lemma、TortoiseHare。

| 实际缺失的底层 trait | 涉及条目数（可重叠） | 诊断数 | 典型调用 |
| --- | ---: | ---: | --- |
| `HOL::Equal` | 5 | 39 | 集合、列表、索引对的相等/成员/基数操作 |
| `Orderings::Ord` | 5 | 8 | `max`；由 Ord 推导的 Linorder |
| `Arith::Times` | 1 | 11 | `power` 的 One+Times 前提 |
| `Arith::Zero/Plus` | 2 | 6 | `sum_list` 的 MonoidAdd、有限集 `sum` 的 CommMonoidAdd |

[BigInt 数值配置](../../../translate/Rust_BigInt_Setup.thy) 和 [integer/int 配置](../../../translate/Rust_Integer_BigInt_Layer.thy) 将具体数值运算打印成 BigInt 运算符。但泛型 `max`、`power`、`sum_list` 和 `sum` 仍通过导出 crate 自己的 HOL trait 方法调用。BigInt 实现 `std::cmp::Ord`、`num_traits::Zero` 或 Rust 运算符，并不等于实现这些本地 trait。

例如 [Digit_Expansions 的 Arith.rs](compile-cases/Digit_Expansions/rust-before/export1/src/Arith.rs#L17) 已输出 `impl One for BigInt`；同文件的 `Power: One + Times` 和 `power<A: Power>` 要求 Times，而整个 crate 没有 `Times for BigInt`。[Carries.thy](compile-cases/Digit_Expansions/original/Carries.thy#L45) 的 `bin_carry a b k = (a mod 2^k + b mod 2^k) div 2^k` 因而在幂运算处失败。这 11 条诊断是相同实例缺口在多个调用处重复出现。

[Approx_LB_Hoare.rs](compile-cases/Approximation_Algorithms/rust-before/export1/src/Approx_LB_Hoare.rs#L14) 的 `max` 与 [Sauer_Shelah_Lemma 的 sup_nat](compile-cases/Sauer_Shelah_Lemma/rust-before/export1/src/Conditionally_Complete_Lattices.rs#L9) 则分别直接或沿 `Linorder → Order → Preorder → Ord` 暴露同一类问题。[Matching.thy](compile-cases/Max-Card-Matching/original/Matching.thy#L22) 中 `weight LV f = f 1 + (∑i∈LV. f i div 2)` 在 [Matching.rs](compile-cases/Max-Card-Matching/rust-before/export1/src/Matching.rs#L121) 的泛型 sum 处，同时暴露 Equal、Zero、Plus 三个前提。

这不意味着所有导出中的 BigInt 都缺 Equal：[Nano_JSON 的 Arith.rs](compile-cases/Nano_JSON/rust-before/export1/src/Arith.rs#L88) 就包含可执行的 `Equal for BigInt`。缺口取决于当前导出保留下来的实例方法及目标映射组合。应调查数值目标适配与 [实例恢复/去重](../../../translate/code_rust.ML#L3469) 如何协同，而不能要求 AFP 作者改数学定义，或直接把原生标准 trait 当成同一个 trait。

修复方向是为实际可达的泛型数值调用提供语义正确的 trait 实现/适配；不能用 panic 占位替代会执行的加法、乘法、相等和序比较。本次未实施该修复，也未验证补齐后这些条目是否还会报其他错误。

## B. 父类补全使用了不一致的泛型前提

5 个条目（Binomial-Queues、FeatherweightJava、Nano_JSON、Pairing_Heap、Trie）的 14 条诊断属于 Typerep 约束问题。以 [Binomial-Queues 的 List.rs](compile-cases/Binomial-Queues/rust-before/export1/src/List.rs#L24) 和 [TermOf 定义](compile-cases/Binomial-Queues/rust-before/export1/src/Code_Evaluation.rs#L14) 为例，关键前提是：

```rust
impl<A: Clone + PartialTermOf + 'static> Typerep for List<A> { /* ... */ }
impl<A: Clone + TermOf + 'static> TermOf for List<A> { /* ... */ }
pub trait TermOf: Typerep { /* ... */ }
```

第二个 impl 声称对任意 `A: TermOf` 都成立，却无法证明其 Self 类型 `List<A>: Typerep`，因为输出中的前一个 impl 额外要求 `A: PartialTermOf`。rustc 因而在 impl 声明及递归 `term_of` 调用处报 E0277。PQ 对 `List<(A,B)>` 的反射调用也受同一前提影响；这不是额外的“元组算法错误”。FeatherweightJava 的 Random、FullExhaustive 还通过 `Random: Typerep`、`FullExhaustive: TermOf` 触发同一问题。Trie 同时影响 Option 和 List。

另 1 条来自 Sturm_Sequences 的 [Polynomial.rs](compile-cases/Sturm_Sequences/rust-before/export1/src/Polynomial.rs#L473)：

```text
Modulo for Poly<A>
  → Modulo: Divide + Dvd
  → Dvd: Times
  → 输出的 Times for Poly<A> 额外要求 A: SemidomDivideUnitFactor
  → 还需 A: UnitFactor
```

Modulo impl 的 `IdomDivide + Field + Equal` 前提没有满足上述额外要求。[同文件第 62 行](compile-cases/Sturm_Sequences/rust-before/export1/src/Polynomial.rs#L62) 可检查 Times 补全实例的实际前提。

后端的 [closure_inst_data](../../../translate/code_rust.ML#L3799) 为缺失父类补出实例，其中 `vs_of_tyco` 从该类型已重建实例的前提取值；这些前提可能来自 PartialTermOf 等更强的实例。[inst_table_seed](../../../translate/code_rust.ML#L3638) 的父类约束合并只查询先前的显式实例，后创建的父类补全不在这一轮查询里。因此输出可能出现“父类要求更强、派生实例仍要求更弱”的矛盾。

这是后端约束重建/补全过程的一致性错误。日志中“加上 PartialTermOf/UnitFactor”的建议只针对局部 Rust 类型检查，不等于已经确定的完整修复方案；需要让父类补全与调用方的前提保持一致，并核实可执行方法所需的真实约束。

## C. 请求导出的实例方法，没有对应 Rust impl

3 个条目共 16 条诊断：FeatherweightJava 的 `Exp: Equal` 11 条、`Exp: TermOf` 1 条；Nano_JSON 的 `Json<A,B>: Equal` 2 条；Trie 的 `Trie<A,B>: Equal` 2 条。

这里有比“库不支持递归类型”更直接的证据：三个条目的候选范围和显式导出理论都已包含对应实例方法：

| 条目 | 显式请求的 HOL 方法 | 输出中的问题 |
| --- | --- | --- |
| [FeatherweightJava](compile-cases/FeatherweightJava/export/FeatherweightJava_Rust_Export.thy) | `FJDefs.equal_exp_inst.equal_exp`、`FJDefs.term_of_exp_inst.term_of_exp` | 全 crate 没有 Equal/TermOf for Exp；记录与执行代码仍调用它们。 |
| [Nano_JSON](compile-cases/Nano_JSON/export/Nano_JSON_Rust_Export.thy) | `Nano_JSON.equal_json_inst.equal_json` | 全 crate 没有 Equal for Json；`snds()` 需要这个实例。 |
| [Trie](compile-cases/Trie/export/Trie_Rust_Export.thy) | `Trie.equal_trie_inst.equal_trie` | 全 crate 没有 Equal for Trie；`snds()` 需要这个实例。 |

例如 [FJDefs.rs](compile-cases/FeatherweightJava/rust-before/export1/src/FJDefs.rs#L252) 明确调用 `<Exp as Equal>::equal`，第 266 行又调用 `<Exp as TermOf>::term_of`。Exp 的 enum 已输出，Typerep 也有实现，但这两个 impl 没有输出。原始 [FJDefs.thy](compile-cases/FeatherweightJava/original/FJDefs.thy#L47) 是含表达式列表等递归字段的数据类型。

[Nano_JSON.rs](compile-cases/Nano_JSON/rust-before/export1/src/Nano_JSON.rs#L320) 的 set1/set2 函数，以及 [Trie.rs](compile-cases/Trie/rust-before/export1/src/Trie.rs#L373) 的 set1/set2 函数，会对 `(键, 递归子树)` 应用 [snds](compile-cases/Nano_JSON/rust-before/export1/src/Basic_BNFs.rs#L20)。其结果是递归值的单元素集合，需要该递归值的 Equal。这与 B 类的泛型父类前提错误是两个独立缺口。Nano_JSON 的 BigInt: Equal 已存在，也不能满足 Json: Equal。

已确定的是：显式请求的可执行方法、生成调用和实际发射的 impl 集合不一致。应核查后端的 [实例识别](../../../translate/code_rust.ML#L3469)、[emit_insts/modify_funs](../../../translate/code_rust.ML#L3307) 及 [modify_stmts](../../../translate/code_rust.ML#L3367) 的递归分组处理。本次没有保存 Thingol SCC 图，因此不把“某个具体分组分支丢弃方法”写成已证实的唯一内部原因；这不影响“输出漏了所需具体实例”的结论。

## D. 原 HOL 分组正确，Rust 表达式丢失括号

Gray_Codes 的 [Code_Word_Dist.thy](compile-cases/Gray_Codes/original/Code_Word_Dist.thy#L94) 写的是 `(if a≠b then 1 else 0) + hamming v w`。其 [Rust 输出](compile-cases/Gray_Codes/rust-before/export1/src/Code_Word_Dist.rs#L52) 在一个语句块内成为：

```rust
if !(a.clone() == b.clone()) {
    one_nat()
} else {
    BigInt::ZERO
} + hamming(v.clone(), w.clone())
```

在这个位置，Rust 将 if 当作块内独立表达式语句，后面的 `+` 无法按预期解析。结果是 1 条语法错误，加上两个分支“应为 ()、实际为 BigInt”的 E0308；这三条属于同一处分组错误。所需表达式结构是 `(if ... { ... } else { ... }) + ...`。

Trie 的 [all_trie 原定义](compile-cases/Trie/original/Trie.thy#L152) 也已给 case 加括号；[Rust 输出](compile-cases/Trie/rust-before/export1/src/Trie.rs#L74) 却是 `match v.clone() { ... } && list_all(...)`。rustc 因而同时报告 `expected (), found bool` 和 `expected bool, found &&bool`，并明确建议 `(match ... { ... }) && ...`。这 2 条也是同一处分组错误。

两者都不要求引入新的 HOL 翻译对象。应修复现有表达式规则对上下文的处理：[HOL.If 打印分支](../../../translate/code_rust.ML#L1693) 直接返回 rust_if，[print_case](../../../translate/code_rust.ML#L2111) 忽略传入的优先级上下文，而 [rust_if/rust_match](../../../translate/code_rust.ML#L107) 本身不提供该处需要的分组。属于实际的括号/表达式打印错误；不能把这 5 条当成五个独立类型系统缺陷。

## E. Code.abort 适配同时违反消息格式和参数数量要求

Sturm_Sequences 的 [Real_Vector_Spaces.rs](compile-cases/Sturm_Sequences/rust-before/export1/src/Real_Vector_Spaces.rs#L73) 在实数 Uniformity 实例内部生成下列结构（省略长 Literal 构造）：

```text
panic!(Literal::Literal(...))
    (Rc::new(move |_: Unit| { ... }))
```

完整日志给出两个问题：

1. `format argument must be a string literal`：Rust 2024 的 panic! 使用格式宏接口，不能直接将 HOL 的 `String.literal` 枚举值作为格式串；该 Literal 也没有直接映射成 Rust 字符串字面量。
2. E0618 `expected function, found !`：panic! 返回发散类型 `!`，生成代码却又把它当作函数应用到后一个闭包。

HOL 的 [Code.abort 类型](../../../temp/Isabelle2025_ref/src/HOL/String.thy#L914) 为 `String.literal ⇒ (unit ⇒ 'a) ⇒ 'a`，有两个源参数。当前 [Rust_Base_Setup.thy](../../../translate/Rust_Base_Setup.thy#L23) 只用 `"panic'!( _ )"` 消费一个参数；[Complex_printer 剩余参数路径](../../../translate/code_rust.ML#L1667) 继续打印第二个参数，于是出现上述调用。

两项都属于 Rust 目标适配规则错误。适配需要正确处理消息表示、消费完整的源调用，并保持 abort 所在的按需求值边界。

该 Literal 的字符内容解码为 **`uniformity is not executable`**。这是库主动设置的不可执行操作边界；修正 panic! 的语法，不会让实数 uniformity 自动成为可运行算法。**原输入包含这样的报错边界，与当前连“报错分支”本身都不能通过 Rust 编译，是两个问题。**日志没有证明原 AFP 的定理或实数库定义有错。

## F. 高阶函数结果的分组与类型标注不一致

[Vickrey_Clarke_Groves 的原定义](compile-cases/Vickrey_Clarke_Groves/original/CombinatorialAuction.thy#L611) 在 `chosenAllocationAlg` 中计算 `(argmax ∘ sum) b allocations`。先给出竞价函数 b，再给出分配集合；中间结果仍应是函数。

[CombinatorialAuction.rs](compile-cases/Vickrey_Clarke_Groves/rust-before/export1/src/CombinatorialAuction.rs#L74) 将其打印成多阶段结构 `(*(*comp(f,g))(b))(allocations)`，但第 81 行给 f 的适配器标注为返回 `Set<Set<(A,Set<B>)>>`。该适配器的实际闭包体又返回一个接受分配集合的 Rc 函数。类型标注和后续“还有一组函数参数”的调用计划没有一致地保留函数结果。

rustc 目前报告 E0614：`Set::Set<Set::Set<(A, Set::Set<B>)>> cannot be dereferenced`。它是高阶返回形状不一致在解引用处的表现；需同时核对适配器返回类型与分组调用，不能仅据这一条诊断断言“删一个星号就完全修好”。

应调查后端的 [ordinary_returned_groups](../../../translate/code_rust.ML#L1463)、[返回函数的逐组调用](../../../translate/code_rust.ML#L1589)、[print_function_adapter](../../../translate/code_rust.ML#L2178) 和 [fun 类型打印](../../../translate/code_rust.ML#L4296)。这是已支持的函数组合/部分应用在当前打印路径中的实现错误；当前证据没有指向拍卖算法原定义错误。

## 责任边界与后续使用

- **AFP 原证明/原定义错误：本组未确认任何一例。**候选包括自动产生的反射实例和库支持方法，所以失败位置可能远离条目主要算法。不能据此说某个算法本身被错误证明，也不能说它完全不可计算。
- **Rust 支持覆盖不足：A 类覆盖 9 个条目、64 条诊断。**现有 BigInt 表示与具体运算映射，还需要满足泛型 HOL trait 调用的实例要求。
- **Rust 实际输出/适配规则错误：B–F 类共覆盖 8 个条目、39 条诊断。**其中 FeatherweightJava、Gray_Codes 同时属于 A，因此 9 和 8 的并集是 15。这里已经有非法 Rust、相互矛盾的 impl 前提或明确漏发实例的直接证据；不应全部笼统称为“AFP 依赖不支持”。

7 个只报告 A 的条目，是检验数值 trait 适配是否完善的候选；Binomial-Queues、Pairing_Heap 是较纯粹的父类约束案例；Gray_Codes、Trie、Sturm_Sequences、Vickrey_Clarke_Groves 则提供具体语法和函数形状反例。FeatherweightJava、Nano_JSON、Trie 还可检查递归实例的输出完整性。这只是后续修复的取证入口，本次没有修改规则、添加回归测试或进行修复后编译。

rustc 可能因语法/类型错误而省略后续诊断。上述统计只覆盖本轮实际观察到的错误，不能由此保证消除某类错误后相应条目全部编译成功；即使编译成功，也仍需独立运行验证。

## 保留证据与核验

[compile-cases/](compile-cases/) 为全部 15 个条目保存：原条目的 ROOT 与全部 61 个所属 `.thy`、本轮候选范围和结果快照、显式导出理论、完整 Cargo/锁文件准备/导出日志，以及 Cargo.toml 和 Rust 源码。各文件的来源与 SHA256 见每个条目的 `source.json`；AFP 原始注释及空白保持不变，许可证说明沿用 [AFP-LICENSE](cases/AFP-LICENSE)。目录使用 `rust-before/`，不依赖已清理的临时 stage1 路径。

原实验使用 `isabelle build -e` 读取有效的会话缓存。这些成功会话的数据库时间为 2026-10-19，早于 10 月 20 日的本轮执行，原报告已说明复用 heap。本分析通过只读 SQLite 查询 `isabelle_exports`，按其压缩标记解压 Zstandard，恢复本轮从这些数据库导出的 **303 个 Cargo/Rust 文件**；这不是重跑实验，也不声称这些会话在本轮重新证明构建。逐条核对了缓存中的 7 个本地后端/设置/导出理论文件（合计 105 次），均与当前字节一致；61 个 AFP 理论也全部匹配会话记录的 SHA1。Approximation_Algorithms 的全部导出行，还与原报告在清理前保留的 Rust crate 字节一致。

数据库不保存 runner 后续准备的 Cargo.lock，本次没有伪造“恢复的原始锁文件”。原 Approximation_Algorithms 的锁文件仍保留在 [原案例](cases/Approximation_Algorithms/rust-before/export1/Cargo.lock)。复现其他保留 crate 时，可按原 [锁文件准备日志](compile-cases/Nano_JSON/logs/stage1-1.lock.txt) 使用锁定模板：

```bash
python3 scripts/ensure-cargo-lock.py \
  test/afp-Isabelle2025/report/compile-cases/Nano_JSON/rust-before/export1/Cargo.toml \
  scripts/isabelle-exported.Cargo.lock
cargo +1.94.0 build --locked --manifest-path \
  test/afp-Isabelle2025/report/compile-cases/Nano_JSON/rust-before/export1/Cargo.toml
```

这会准备新的复现用 lock，原始诊断以保存的日志为准。本次仅做资料核验，未执行以上命令，也未生成 target/二进制缓存。[compile-validation.json](compile-validation.json) 记录完整覆盖、103 条逐项分类、原始输入未变、原始理论/源码/日志哈希与报告链接的检查结果。在 report 目录执行 `sha256sum --quiet -c SHA256SUMS` 可复核保留资料。

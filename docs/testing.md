# Isabelle2Rust 测试与命令说明

本文档按当前项目主线整理测试入口。项目分为两个主要阶段：

1. **阶段 1 — Isabelle 生成**：从 `.thy` 理论生成 baseline Rust，并编译运行导出的 Cargo 项目。
2. **阶段 2 — optimize 优化**：读取 baseline Rust，串联 copy pass 与 borrow pass，生成优化后的 Rust，并检查优化结果。

---

## 总览：两阶段测试流程

```
tests_targeted/optimization/<pass>/
    <Theory>.thy          ← Isabelle 理论（第 1 阶段输入）
         │
         ▼  make build_silent / make test
tests_targeted/optimization/<pass>/stage1/<Theory>/export1/
    src/<Theory>.rs       ← stage1：Isabelle 生成的 baseline Rust
    Cargo.toml / main.rs
         │
         ▼  cp → optimize/tests/stage1/<Theory>/
optimize/tests/stage1/<Theory>/
    src/<Theory>.rs       ← stage1 快照（用于本轮测试）
         │
         ▼  cargo run --bin cargo-opt (copy pass → borrow pass)
optimize/tests/stage2/<Theory>/
    src/<Theory>.rs       ← stage2：经过 copy + borrow 优化后的 Rust
    Cargo.toml
```

cargo-opt 的优化管线（单次调用，顺序执行两个 pass）：

```
stage1 Rust → parse → RustLightAST → copy pass → borrow pass → stage2 Rust
```

---

## 阶段 1：Isabelle 生成与 baseline Rust 测试

测试源文件放在 `tests_targeted/` 下，按类别组织：

| 目录 | 数量 | 含义 |
| --- | ---: | --- |
| `tests_targeted/abstraction/` | 8 | lambda、闭包捕获、未饱和函数等 |
| `tests_targeted/cases/` | 6 | case 表达式 |
| `tests_targeted/classes/` | 12 | type class、instance、semigroup |
| `tests_targeted/constructors/` | 4 | 构造器与 result |
| `tests_targeted/functions/` | 9 | 函数、更新、高层映射、可变引用 |
| `tests_targeted/lets/` | 3 | let 绑定 |
| `tests_targeted/lists/` | 2 | list 相关测试 |
| `tests_targeted/records/` | 3 | record get/set/mut |
| `tests_targeted/types/` | 5 | tuple、pair、record、函数类型 |
| `tests_targeted/optimization/copy/` | 4 | copy 优化的 Isabelle baseline 测试 |
| `tests_targeted/optimization/borrow/` | 1 | borrow 优化的 Isabelle baseline 测试 |

当前共有 `57` 个 targeted `.thy` 测试。

### 单个理论：只生成 Rust

```bash
make build TEST_DIR=tests_targeted/lists TEST_THEORY=List_Test
```

作用：

- 生成临时 `test-root/ROOT`。
- 调用 `isabelle build -v -e -d test-root Rust`。
- 导出 Rust 到 `TEST_DIR/stage1/TEST_THEORY/export*/`。

静默版本：

```bash
make build_silent TEST_DIR=tests_targeted/lists TEST_THEORY=List_Test
```

### 单个理论：在 Isabelle/jEdit 中打开

```bash
make open_test TEST_DIR=tests_targeted/types TEST_THEORY=Type_Tuple_Test
```

该命令使用 `-R Rust` 打开测试 session，使 `Rust_Base_Setup` 和测试理论处于可编辑的当前 session 中。

### 单个理论：生成并运行

```bash
make gen DIR=tests_targeted/lists Name=List_Test
```

### 全量 targeted 测试

```bash
make targeted
```

### HOL smoke 测试

```bash
make hol
```

---

## 阶段 2：optimize 优化测试

优化器源码在 `optimize/` 下。优化管线通过 `cargo-opt` 二进制完成：每次调用先执行 **copy pass**，再执行 **borrow pass**，两个 pass 是串联的，输出放在 `optimize/tests/stage2/` 下。

### copy 阶段主入口

```bash
make optimize_test STAGE=copy
# 或简写
make optimize_copy
```

**完整流程：**

1. 从 `tests_targeted/optimization/copy/Copy_Inference_Test.thy` 生成 baseline Rust（`make build_silent`）。
2. 将生成结果快照到 `optimize/tests/stage1/Copy_Inference_Test/`。
3. 编译运行 stage1 Cargo 项目（验证 Isabelle 生成代码可编译）。
4. 调用 `cargo-opt` 对 stage1 运行 **copy pass + borrow pass**，输出到 `optimize/tests/stage2/Copy_Inference_Test/`。
5. 编译运行 stage2 Cargo 项目。
6. 执行 60+ 项回归检查：`.clone()` 数量减少、Copy derive 数量、具体函数体内容等。

**代码位置：**

| 阶段 | 路径 |
| --- | --- |
| Isabelle 理论 | `tests_targeted/optimization/copy/Copy_Inference_Test.thy` |
| stage1（Isabelle 生成） | `tests_targeted/optimization/copy/stage1/Copy_Inference_Test/export1/` |
| stage1 快照 | `optimize/tests/stage1/Copy_Inference_Test/` |
| stage2（优化输出） | `optimize/tests/stage2/Copy_Inference_Test/` |

### borrow 阶段主入口

```bash
make optimize_test STAGE=borrow
```

**完整流程：**

1. 从 `tests_targeted/optimization/borrow/Borrow_Inference_Test.thy` 生成 baseline Rust（`make build_silent`）。
2. 将生成结果快照到 `optimize/tests/stage1/Borrow_Inference_Test/`。
3. 编译运行 stage1 Cargo 项目。
4. 调用 `cargo-opt` 对 stage1 运行 **copy pass + borrow pass**，输出到 `optimize/tests/stage2/Borrow_Inference_Test/`。
5. 编译运行 stage2 Cargo 项目。
6. 执行回归检查：`_borrow` variant 存在、`&T` 参数出现、原始函数保留、`BorrowTree` 不派生 Copy 等。

**代码位置：**

| 阶段 | 路径 |
| --- | --- |
| Isabelle 理论 | `tests_targeted/optimization/borrow/Borrow_Inference_Test.thy` |
| stage1（Isabelle 生成） | `tests_targeted/optimization/borrow/stage1/Borrow_Inference_Test/export1/` |
| stage1 快照 | `optimize/tests/stage1/Borrow_Inference_Test/` |
| stage2（优化输出） | `optimize/tests/stage2/Borrow_Inference_Test/` |

**`Borrow_Inference_Test.thy` 设计要点：**

| 类型 | 原因 |
| --- | --- |
| `borrow_tree`（递归） | 递归类型无法派生 Copy，适合测试非 Copy 类型的 borrow 推断 |
| `'a borrow_box`（泛型） | 验证泛型 `Clone` bound 下的 borrow variant 生成 |

所有函数均可借出（borrowable），因为 Isabelle 代码生成器为每次变量使用都加 `.clone()`，产生的是 `Own` 或 `Obs` demand，从不产生 `Move`。

### copy-borrow 串联阶段

```bash
make optimize_test STAGE=copy-borrow
```

顺序执行 copy 阶段，再执行 borrow 阶段（两个独立的端到端流程）。

### all 阶段

```bash
make optimize_all
```

等价于依次执行 copy、borrow 两个阶段。

### 快捷命令对照

| 命令 | 等价 |
| --- | --- |
| `make optimize_copy` | `make optimize_test STAGE=copy` |
| `make copy_inference` | `make optimize_copy` |
| `make optimize_all` | `make optimize_test STAGE=all` |

---

## 完整测试命令速查

```bash
# 阶段 1：全量 Isabelle 测试
make targeted                        # 构建并运行所有 *_Test.thy（54 个）

# 阶段 1：单个理论测试
make gen DIR=tests_targeted/lists Name=List_Test
make build TEST_DIR=tests_targeted/optimization/borrow TEST_THEORY=Borrow_Inference_Test

# 阶段 2：optimize 优化测试
make optimize_test STAGE=copy        # copy 推断回归 (60+ checks)
make optimize_test STAGE=borrow      # borrow 推断回归 (10+ checks)
make optimize_test STAGE=copy-borrow # 串联：copy 然后 borrow
make optimize_all                    # 同上

# optimize crate 自身测试
cd optimize && cargo test -q
cd optimize && cargo fmt -- --check

# HOL smoke 测试
make hol
```

---

## optimize/tests/ 目录结构

```
optimize/tests/
├── stage1/
│   ├── Copy_Inference_Test/     ← copy 阶段的 Isabelle 生成快照
│   │   ├── src/
│   │   │   ├── Copy_Inference_Test.rs
│   │   │   ├── Product_Type.rs
│   │   │   └── main.rs
│   │   └── Cargo.toml
│   └── Borrow_Inference_Test/   ← borrow 阶段的 Isabelle 生成快照
│       ├── src/
│       │   ├── Borrow_Inference_Test.rs
│       │   └── main.rs
│       └── Cargo.toml
└── stage2/
    ├── Copy_Inference_Test/     ← cargo-opt (copy+borrow) 输出
    │   ├── src/
    │   │   ├── Copy_Inference_Test.rs
    │   │   ├── Product_Type.rs
    │   │   └── main.rs
    │   └── Cargo.toml
    └── Borrow_Inference_Test/   ← cargo-opt (copy+borrow) 输出
        ├── src/
        │   ├── Borrow_Inference_Test.rs
        │   └── main.rs
        └── Cargo.toml
```

`stage1/` 和 `stage2/` 目录在每次测试运行时自动重建，不提交到版本库。

---

## 清理生成物

```bash
make clean
```

清理范围：
- 所有 `tests_targeted/**/stage1/` 和 `tests_targeted/**/stage2/`
- `optimize/tests/stage1/` 和 `optimize/tests/stage2/`
- `tests_HOL/Hol_Test/target/`

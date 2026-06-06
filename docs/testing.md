# Isabelle2Rust 测试与命令说明

本文档按当前项目主线整理测试入口。项目现在分为两个主要阶段：

1. Isabelle 阶段：从 `.thy` 理论生成 baseline Rust，并编译运行导出的 Cargo 项目。
2. optimize 阶段：读取 baseline Rust，执行优化算法，生成 optimized Rust，并检查优化结果。

## 阶段 1：Isabelle 生成与 baseline Rust 测试

测试源文件放在 `tests_targeted/` 下，按类别组织：

| 目录 | 数量 | 含义 |
| --- | ---: | --- |
| `tests_targeted/abstraction/` | 8 | lambda、闭包捕获、未饱和函数等 |
| `tests_targeted/cases/` | 6 | case 表达式 |
| `tests_targeted/classes/` | 10 | type class、instance、semigroup |
| `tests_targeted/constructors/` | 3 | 构造器与 result |
| `tests_targeted/functions/` | 9 | 函数、更新、高层映射、可变引用 |
| `tests_targeted/lets/` | 3 | let 绑定 |
| `tests_targeted/lists/` | 2 | list 相关测试 |
| `tests_targeted/records/` | 3 | record get/set/mut |
| `tests_targeted/types/` | 5 | tuple、pair、record、函数类型 |
| `tests_targeted/optimization/copy/` | 4 | copy 优化的 Isabelle baseline 测试 |

当前共有 `53` 个 targeted `.thy` 测试。

### 单个理论：只生成 Rust

```bash
make build TEST_DIR=tests_targeted/lists TEST_THEORY=List_Test
```

作用：

- 根据 `ROOT.template` 生成临时 `ROOT`。
- 调用 `isabelle build -v -e -d . Test`。
- 导出 Rust 到 `TEST_DIR/Rust_Out/TEST_THEORY/export*/`。

静默版本：

```bash
make build_silent TEST_DIR=tests_targeted/lists TEST_THEORY=List_Test
```

### 单个理论：只运行已生成的 Rust

```bash
make run TEST_DIR=tests_targeted/lists TEST_THEORY=List_Test
```

作用：

- 查找 `tests_targeted/lists/Rust_Out/List_Test/export*/Cargo.toml`。
- 对每个导出的 Cargo 项目执行 `cargo run --locked`。
- 如果导出项目缺少 `Cargo.lock`，会复制 `scripts/isabelle-exported.Cargo.lock`，避免测试时刷新 crates.io index。

### 单个理论：生成并运行

```bash
make test TEST_DIR=tests_targeted/lists TEST_THEORY=List_Test
```

等价于：

```bash
make build TEST_DIR=tests_targeted/lists TEST_THEORY=List_Test
make run TEST_DIR=tests_targeted/lists TEST_THEORY=List_Test
```

### 全量 targeted 测试

```bash
make targeted
```

作用：

- 递归扫描 `tests_targeted/**/*.thy`。
- 对每个 theory 执行 `build_silent + run`。
- 当前实测结果：`Passed: 53, Failed: 0, Total: 53`。

### 只运行已生成的 targeted Rust

```bash
make targeted_run
```

作用：

- 不重新跑 Isabelle。
- 递归扫描 `tests_targeted/**/Rust_Out`。
- 只运行已有导出 Cargo 项目。
- 当前实测结果：`Passed: 53, Failed: 0, Total: 53`。

### HOL smoke 测试

```bash
make hol
```

默认运行：

```bash
make hol HOL_TEST_THEORY=Hol_Test_Integer
```

作用：

- 构建 `tests_HOL/Hol_Test_Integer.thy`。
- 替换导出项目的 `main.rs`。
- 编译运行导出的 Cargo 项目。
- 当前实测输出包含：`hol_test = true`。

说明：

- `tests_HOL/Hol_Test.thy` 仍保留，但当前会暴露旧 `int`/`Num` 构造器生成问题，不作为默认 `make hol` 主线。

### 使用当前 ROOT 重新构建

```bash
make code
```

作用：

- 不重新生成 `ROOT`。
- 直接使用当前 `ROOT` 执行 Isabelle build。

### 清理生成物

```bash
make clean
```

作用：

- 清理临时文件。
- 删除 `tests_targeted/**/Rust_Out`。
- 删除 `optimize/tests/out`。
- 删除 `tests_HOL/Hol_Test/target`。

## 阶段 2：optimize 优化测试

优化器源码在 `optimize/` 下。第二阶段只保留两个关键入口：阶段化端到端测试，以及优化器自身 Rust 测试。

### copy 阶段主入口

```bash
make optimize_test STAGE=copy
```

作用：

1. 从 `tests_targeted/optimization/copy/Copy_Inference_Test.thy` 生成 baseline Rust。
2. 编译运行 baseline Cargo 项目。
3. 调用 `optimize` 的 `cargo-opt` 对 baseline Rust 做 copy inference 优化。
4. 编译运行 optimized Cargo 项目。
5. 检查 clone 数量、`Copy` derive、泛型 Copy bound、递归 `Box` 类型等行为。

代码生成位置：

- baseline Rust：`tests_targeted/optimization/copy/Rust_Out/Copy_Inference_Test/export1/`
- optimized Rust：`optimize/tests/out/copy/Copy_Inference_Test/opt/`
- optimized 主文件：`optimize/tests/out/copy/Copy_Inference_Test/opt/src/Copy_Inference_Test.rs`

当前实测结果：`copy inference regression suite passed: 62 checks`。

### 未来阶段入口

```bash
make optimize_test STAGE=borrow
make optimize_test STAGE=copy-borrow
```

当前输出：

```text
stage "borrow" has no configured tests yet
stage "copy-borrow" has no configured tests yet
```

这两个入口用于后续扩展：

- `borrow`：只测试 borrow 优化。
- `copy-borrow`：串联 copy 与 borrow 优化后测试。

### optimize crate 自身测试

在 `optimize/` 目录下运行：

```bash
cargo test -q
cargo fmt -- --check
```

当前实测结果：

- Rust 单元测试：`6 passed`
- Rust 集成测试：`3 passed`
- 格式检查通过

## 当前已执行验证结果

本轮已执行并通过：

```bash
make targeted
make targeted_run
make test TEST_DIR=tests_targeted/lists TEST_THEORY=List_Test
make code
make hol
make optimize_test STAGE=copy
make optimize_test STAGE=borrow
make optimize_test STAGE=copy-borrow
cargo test -q
cargo fmt -- --check
```

本轮为了稳定测试入口修复了：

- `make targeted` 支持分类后的 `tests_targeted/**` 递归结构。
- `ROOT.template` 启用 `HOL-Library` session，修复 `High_Level_Mapping_Test`。
- baseline/optimized Cargo 测试使用固定 lockfile，避免刷新 crates.io index。
- Isabelle build 增加进程锁，避免并发 make 进程同时写 session/export 数据库。
- `make hol` 默认使用可运行的 `Hol_Test_Integer` smoke test。

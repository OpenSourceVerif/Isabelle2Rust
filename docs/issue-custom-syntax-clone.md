# 自定义 Rust 语法下遗漏 clone

## 现象

下面这个例子暴露了 baseline codegen 的问题：

```isabelle
definition any_label_twice :: "tree \<Rightarrow> bool" where
  "any_label_twice t = (any_label t \<and> any_label t)"
```

修复前，stage1 生成：

```rust
any_label(t) && any_label(t)
```

由于 `any_label` 按值接收 `Tree`，第一次调用已经 move 了 `t`，第二次调用会触发：

```text
error[E0382]: use of moved value: `t`
```

正确的 baseline 应该是：

```rust
any_label(t.clone()) && any_label(t.clone())
```

## 原因

问题不在 borrow optimizer，而在 baseline Rust codegen。

`code_rust.ML` 中有两类相关 term printer：

```sml
print_term_decl = print_term_gen ... (false, I, I)
print_term_app  = print_term_gen ... (false, box_new, clone)
```

`print_term_decl` 不插入 `.clone()`，用于声明、签名和模式等位置；`print_term_app` 用于表达式位置，会让变量按需要变成 `v.clone()`。

`print_app_with_clone` 通过 `gen_print_app` 同时处理普通应用和 `const_syntax`：

```sml
gen_print_app ordinary_app_printer custom_syntax_subterm_printer const_syntax ...
```

旧代码中，`ordinary_app_printer` 已经是 clone-aware 的：

```sml
print_app_expr is_pseudo_fun (box_prcs, clone_prcs)
```

因此普通函数调用参数可以正确 clone。真正的问题在第二个参数：custom syntax 的子表达式仍使用 `print_term_decl`。当 `HOL.conj` / `HOL.disj` 被打印成 `&&` / `||` 时，左右子表达式没有走 clone-aware 路径，导致 `any_label t \<and> any_label t` 被打印成两个 move。

## 修复

只修改 `code_rust.ML` 中 `print_app_with_clone` 传给 `gen_print_app` 的第二个 printer。

修复前：
```sml
and print_app_with_clone is_pseudo_fun (box_prcs, clone_prcs) some_thm vars =
  gen_print_app (print_app_expr is_pseudo_fun (box_prcs, clone_prcs))
  (print_term_decl is_pseudo_fun) const_syntax some_thm vars
```

修复后：
```sml
and print_app_with_clone is_pseudo_fun (box_prcs, clone_prcs) some_thm vars =
  gen_print_app (print_app_expr is_pseudo_fun (box_prcs, clone_prcs))
  (print_term_gen is_pseudo_fun (false, box_prcs, clone_prcs)) const_syntax some_thm vars
```

变化点是把 custom syntax 的子表达式 printer 从无 clone 的 `print_term_decl` 换成继承当前 `box_prcs` / `clone_prcs` 的 `print_term_gen`。`print_app` 的声明式路径不变；只有表达式打印中的 custom syntax 子项被纳入 clone-aware 路径。

## 验证

重新执行：

```bash
make gen DIR=tests_targeted/optimization/borrow Name=Borrow_Paper_Example_Test
make opt DIR=tests_targeted/optimization/borrow Name=Borrow_Paper_Example_Test
```

两步均通过。stage1 生成：

```rust
any_label(t.clone()) && any_label(t.clone())
```

stage2 继续被优化为：

```rust
any_label(t) && any_label(t)
```

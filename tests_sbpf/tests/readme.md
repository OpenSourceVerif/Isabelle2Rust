# Validation Framework

## Folder Structure

- **`./rbpf`**: Contains the original Solana eBPF VM and custom  mechanism for program (`interpreter_test`) and instruction-level (`step_test`) testing.
- **`./data`**: Stores all benchmarks and test data.
- **`./exec_semantics`**: shared validation orchestration plus language-specific
  glue. Common scripts and local macro data live at this level; OCaml-specific
  execution lives in `./exec_semantics/sbpf_ocaml`; Rust-specific execution lives
  in `./exec_semantics/sbpf_rust`.

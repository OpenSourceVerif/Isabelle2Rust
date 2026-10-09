# Stage-2 Optimizer Directory

- `Cargo.toml`, `Cargo.lock`: Rust crate manifest and locked dependencies.
- `Makefile`: local build targets.
- `src/lib.rs`: optimizer entry point and pass orchestration.
- `src/bin/`: command-line binaries.
- `src/copy_analysis.rs`: copyability inference.
- `src/last_use_analysis.rs`: last-use analysis and rewriting.
- `src/borrow_analysis.rs`: borrow analysis and rewriting.
- `src/mut_analysis.rs`: mutability analysis and rewriting.
- `src/closure_cleanup.rs`: closure simplification.
- `src/binding_cleanup.rs`: binding simplification.
- `src/match_cleanup.rs`: match simplification.
- `src/boolean_cleanup.rs`: Boolean-expression simplification.
- `src/bound_cleanup.rs`: generic-bound simplification.
- `src/complex_type_cleanup.rs`: complex-type aliasing.
- `src/utils/`: shared optimizer utilities.

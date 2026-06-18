# exec_semantics — Orchestration and Caching

This directory owns the shared orchestration scripts for the sBPF validation
pipeline and the language-specific runners under `sbpf_ocaml/` and `sbpf_rust/`.

## Two-Layer Caching

Every run of `make macro_sbpf` or `make micro_sbpf` involves three conceptually
separate steps.  Each of the first two has an independent cache:

```
Step 1  isabelle build  →  generates Step_test.rs / Interp_test.rs
                            (Cache 1: file-existence check)

Step 2  cargo build     →  compiles the generated Rust code into a binary
                            (Cache 2: SHA256 content check)

Step 3  run binary      →  executes test cases, always runs
```

### Cache 1 — Isabelle export (`ensure_isabelle_export`)

Controlled by `run_macro_sbpf.py` / `run_micro_sbpf.py`.

Checks whether the expected Isabelle output files already exist on disk:

- `theory/stage1/bpf_generator/interp_test.ocaml`
- `theory/stage1/bpf_generator/interp_test/Cargo.toml`
- `theory/stage1/bpf_generator/step_test.ocaml`
- `theory/stage1/bpf_generator/step_test/Cargo.toml`

If all are present → skip `isabelle build`.  This is a **presence-only** check;
it does not compare file contents.  To force a re-export, pass `REBUILD=1`.

### Cache 2 — Rust build (`cache_is_valid` in `sbpf_rust/run_*.py`)

Controlled by `sbpf_rust/run_interp_macro.py` and `sbpf_rust/run_step_micro.py`.

After Cache 1 (possibly skipped), the Rust runners compute a SHA256-based cache
key and compare it against a stamp file written by the previous successful build:

**Stamp files (written after a successful `cargo build`):**

| test | stamp path |
|------|-----------|
| macro | `theory/stage1/bpf_generator/interp_test/.rust_macro_cache.json` |
| micro | `theory/stage1/bpf_generator/step_test/.rust_micro_cache.json` |

**Cache key fields:**

```json
{
  "rust_toolchain":    "nightly-2025-12-01",
  "glue_version":      "interp-macro-rust-v1",
  "export_rs_sha256":  "<SHA256 of Interp_test.rs or Step_test.rs>",
  "glue_rs_sha256":    "<SHA256 of interp_main.rs or step_main.rs>"
}
```

The two source files being hashed are:

| file | location | role |
|------|----------|------|
| `Interp_test.rs` / `Step_test.rs` | `theory/stage1/bpf_generator/{interp,step}_test/src/` | Isabelle-generated Rust code |
| `interp_main.rs` / `step_main.rs` | `sbpf_rust/` | handwritten glue harness |

If the stamp exists, the compiled binary exists, and all four key fields match
→ `cargo build` is skipped entirely; the runner goes straight to Step 3.

### What triggers a rebuild

| situation | Cache 1 | Cache 2 |
|-----------|---------|---------|
| nothing changed | skip | skip |
| Isabelle re-exported identical code | skip | skip (SHA256 unchanged) |
| Isabelle re-exported different code | skip* | **rebuild** (SHA256 changed) |
| glue file (`*_main.rs`) edited | — | **rebuild** |
| Rust toolchain changed | — | **rebuild** |
| `REBUILD=1` | **rebuild** | **rebuild** |

\* Cache 1 only checks file existence; even after a re-export the file still
exists, so Cache 1 stays satisfied.  Cache 2 catches the content change.

### OCaml caching (for reference)

`sbpf_ocaml/run_interp_macro.py` and `sbpf_ocaml/run_step_micro.py` use the same
two-layer pattern.  The OCaml stamp files live under `sbpf_ocaml/_build/`:

- `sbpf_ocaml/_build/macro_interp/.macro_interp_cache.json`
- `sbpf_ocaml/_build/micro_step/.micro_step_cache.json`

The OCaml runners copy export files into `_build/` subdirectories and compile
there; the Rust runners work in-place inside the export package directory
(reusing cargo's own `target/` tree).

## Files in This Directory

| file | purpose |
|------|---------|
| `run_macro_sbpf.py` | shared macro orchestration (Cache 1 + data cache + dispatch) |
| `run_micro_sbpf.py` | shared micro orchestration (Cache 1 + dispatch) |
| `gen_interp_json.py` | extract macro test cases from `sbpf_ocaml/test.ml` into JSON |
| `sbpf_ocaml/` | OCaml-specific runners and build cache |
| `sbpf_rust/` | Rust-specific runners (Cache 2 lives here) |
| `_build/` | shared data cache (`interp_in_cache.json`) |

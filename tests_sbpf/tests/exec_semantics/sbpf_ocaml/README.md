# sBPF OCaml Macro Validation

This directory contains only the OCaml-side macro runner for the sBPF
program-level validation suite.

The shared orchestration is in `../run_macro_sbpf.py`. This directory handles
the OCaml-specific part of the path:

1. read the Isabelle-generated export:
   `tests_sbpf/theory/stage1/bpf_generator/interp_test.ocaml`
2. inject OCaml glue into the generated `Interp_test` module:
   `int_of_standard_int` and `int_list_of_standard_int_list`
3. compile the glued export together with `test.ml`
4. run the 146 local Solana macro cases from `test.ml`

`interp_test.ml` and `step_test.ml` are not maintained source files here. They
are generated from `tests_sbpf/theory/bpf_generator.thy` under
`tests_sbpf/theory/stage1/bpf_generator/`.

`test.ml` is still a maintained OCaml-side macro data file. `step.ml` and
`glue.ml` are kept here for the OCaml-side micro/glue path.

The fixed OCaml execution environment is:

```sh
ocamlc -version
# expected: 4.11.2

ocamlfind query zarith
```

Run through the repository-level target:

```sh
make macro_sbpf
```

The temporary OCaml build workspace is created under `_build/macro_interp/`.
Its compiled macro binary is cached by default. Use `OCAML_REBUILD=1
make macro_sbpf` or `make macro_sbpf REBUILD=1` to force regeneration.

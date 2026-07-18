# sBPF performance experiments

Date: 2026-07-18

This note records the experiments used for the RQ3 performance draft. The
functional oracle is the existing sBPF JSON corpus. The program-level suite has
146 cases and the instruction-level suite has 300 vectors.

## Protocol

- Host: Intel Core Ultra 9 185H, Linux under WSL2.
- Rust (current run): `rustc 1.93.0-nightly`, generated crates built with
  `--release`. The retained Stage-1 row used `rustc 1.91.0-nightly`.
- OCaml: `ocamlopt 4.11.2`.
- Each process was pinned to logical CPU 0.
- Every reported result is the median of three runs.
- JSON decoding and per-case output were outside the timed region.
- Program-level Rust runs traversed all cases once. OCaml traversals were
  repeated 20 times per process and divided by 20.
- Instruction-level inputs were converted before timing. Each process executed
  all 300 vectors 20 times, for 6,000 timed steps.
- Performance timing began only after separate correctness validation.

## Stage 1, current Stage 2, Stage 2 + Word, and OCaml

The current Stage-2 and Stage-2 + Word rows were measured in the same run on
2026-07-18. The Stage-1 and OCaml rows retain the earlier protocol-compatible
measurements. `Time / OCaml` compares medians, so values below one are faster
than OCaml.

| Level | Implementation | Raw times (s) | Median (s) | Rate | Time / OCaml |
|---|---|---:|---:|---:|---:|
| Program, 146 cases | Stage-1 Rust | 121.833824, 127.394794, 123.124299 | 123.124299 | 1.186 cases/s | 822.908x |
| Program, 146 cases | Current Stage-2 Rust | 0.683812434, 0.676702593, 0.627388871 | 0.676702593 | 215.752 cases/s | 4.523x |
| Program, 146 cases | Stage-2 + Word Rust | 0.384317575, 0.398009802, 0.374202400 | 0.384317575 | 379.894 cases/s | 2.569x |
| Program, 146 cases | OCaml native | 2.915914, 2.999822, 2.992418 for 20 traversals | 0.149621 per traversal | 975.800 cases/s | 1.000x |
| Instruction, 300 x 20 | Stage-1 Rust | 20.523923, 21.280951, 20.684503 | 20.684503 | 290.072 steps/s | 20.251x |
| Instruction, 300 x 20 | Current Stage-2 Rust | 0.964161813, 0.969869626, 0.934271442 | 0.964161813 | 6,223.022 steps/s | 0.944x |
| Instruction, 300 x 20 | Stage-2 + Word Rust | 0.576837763, 0.590212632, 0.613177835 | 0.590212632 | 10,165.828 steps/s | 0.578x |
| Instruction, 300 x 20 | OCaml native | 1.021425, 1.034111, 0.983053 | 1.021425 | 5,874.146 steps/s | 1.000x |

The Word adapter improves the current Stage-2 median by 1.761x at program level
and 1.634x at instruction level. The resulting instruction kernel is 1.731x
faster than the recorded OCaml median, while the full program interpreter
remains 2.569x slower than OCaml.

## Native rBPF interpreter

The native comparison uses the repository's modified Solana/rBPF 0.8.2. The
timed region contains `execute_program` or `execute_step`, not executable and VM
construction. It is therefore an interpreter-core rate and should not be read
as end-to-end process latency.

The three 30,000,000-step times were 1.303121, 1.277367, and 1.265605 seconds.
Their median rate was 23,485,806 steps/s.

At program level, the JSON records omit native setup information for 12 cases:

- `test_lmul128` and `test_stxb_chain` require larger input memory regions.
- `test_dynamic_stack_frames_empty`, `test_dynamic_frame_ptr_1`,
  `test_dynamic_frame_ptr_2`, `test_entrypoint_exit`,
  `test_stack_call_depth_tracking`, `test_bpf_to_bpf_depth`,
  `test_bpf_to_bpf_scratch_registers`, `test_callx`, `test_callx_imm`, and
  `test_far_jumps` require internal function-entry registrations.

The native harness reconstructs that metadata from the original rBPF fixtures.
It extends the two input regions, registers direct-call targets encoded in the
instructions, and registers the three `callx` targets. The three
1,460,000-execution core times were 0.339901, 0.340428, and 0.361695 seconds,
giving a median rate of 4,288,720.406 cases/s.

The full-suite rates were:

| Implementation | Program rate (cases/s) | Instruction rate (steps/s) |
|---|---:|---:|
| Stage-1 Rust | 1.186 | 290.072 |
| Current Stage-2 Rust | 215.752 | 6,223.022 |
| Stage-2 + Word Rust | 379.894 | 10,165.828 |
| OCaml native | 975.800 | 5,874.146 |
| rBPF native core | 4,288,720.406 | 23,485,806 |

The native rBPF rate is not a direct code-generation baseline. It uses mutable
arrays, primitive registers, direct dispatch, and runtime-specific setup. The
generated interpreters retain the functional semantics and their checks.

## Numeric-representation ablation

### Unadapted Isabelle integers

`theory/bpf_generator_no_bigint.thy` imports `Rust.Rust_Setup` without the
BigInt setup theories. It generates structural `Int` and `Num` datatypes and a
Peano `Nat` rather than `num_bigint::BigInt`.

The initial 0/446 result exposed a Rust backend defect rather than a semantic
limitation of Isabelle's structural integers. The backend's nested pattern
compiler specialized a constructor branch using only rows that began with that
exact constructor. It placed later wildcard rows solely in the outer fallback
arm. Once the outer constructor had matched, those rows were unreachable, so
valid multiplication and bitwise inputs reached a generated
`panic!("non-exhaustive match")`.

The repaired pattern-matrix specialization carries wildcard rows, in source
order, into every constructor branch. When a wildcard-bound variable is used by
the selected equation, it also preserves the whole scrutinee before
destructuring it. A focused boxed-pattern regression test covers this case.

After regenerating both stages, the no-BigInt results are:

| Level | Stage-1 | Stage-2 |
|---|---:|---:|
| Program, 146 cases | 145/145 completed; `far_jumps` resource-bound | 146/146 |
| Instruction, 300 cases | 300/300 | 300/300 |

No completed case panicked or returned an incorrect result. The remaining
Stage-1 `far_jumps` run is a performance and space problem: its 8,256-byte input
causes the structural representation to exceed 4 GiB RSS and run for minutes.
It is not evidence of a missing arithmetic equation, and the optimized Stage-2
version passes the same case. Consequently, BigInt is not required for
functional correctness after the match compiler fix, but it remains essential
for a compact and practically executable baseline. Timing the structural
variant as an optimization would still be misleading.

### Direct BigInt shifts

The current Stage-2 pipeline includes `bigint_shift` by default. It keeps the
`BigInt` representation but lowers the concrete `SemiringBitOperations for
BigInt` implementations of `push_bit`, `drop_bit`, and `mask` to native shifts
and a shifted mask. Therefore the current Stage-2 rows above already contain
this lowering, and there is no separate BigInt-shift experiment column.

### Stage-1 u128 word adapter

The earlier `u64` design was rejected because signed and unsigned high-half
multiplication require a 128-bit intermediate. `Rust_U128_Word_Setup.thy`
instead maps Isabelle words to `RustWord<W>` with a `u128` payload and a
`PhantomData<W>` width marker. It masks constructions and arithmetic to the
Isabelle type-level width, while conversions to and from `int` and `nat` remain
at the `BigInt` boundary. The generated code then runs through the unchanged
Stage-2 optimizer.

| Level | Raw times (s) | Median (s) | Rate | Stage-2 speedup | Time / OCaml |
|---|---:|---:|---:|---:|---:|
| Program, 146 cases | 0.384317575, 0.398009802, 0.374202400 | 0.384317575 | 379.894 cases/s | 1.761x | 2.569x |
| Instruction, 300 x 20 | 0.576837763, 0.590212632, 0.613177835 | 0.590212632 | 10,165.828 steps/s | 1.634x | 0.578x |

Release inspection found that Rust still emits concrete `width::<W>` and
`WordWidth::len_of` functions, including the generated `BigInt` computation;
the width and mask are not yet constant-folded under this protocol. Concrete
width specialization is therefore a possible later Stage-2 optimization, but
it is separate from the Stage-1 representation adapter measured here.

## Explanation of the remaining gap

The ablation separates two kinds of cost:

1. The baseline word operations repeatedly construct powers of two with
   generic BigInt arithmetic. Replacing those operations explains most of the
   instruction-level gap.
2. A complete interpreter run repeatedly traverses persistent machine state.
   Registers and memory are represented by `Rc<dyn Fn>` maps and updates form
   closure chains. Isabelle lists become boxed Rust lists whose generated
   `Clone` implementation recursively copies structure where OCaml can share
   immutable tails. These costs accumulate over many instructions and remain
   after word arithmetic becomes primitive.

This explains why the word-adapted instruction kernel is faster than OCaml
while the full program interpreter remains 2.569 times slower.

## Implemented adapter

`Rust_U128_Word_Setup.thy` is a selectable Stage-1 setup registered in `ROOT`.
It supports widths from 1 through 128 bits and covers construction, conversion,
wrapping arithmetic, division and remainder, unsigned and signed comparison,
bitwise operations, shifts, bit updates and tests, casts, and the 128-bit
intermediate used by the 64-bit high-half multiplication paths. Isabelle `int`
and `nat` remain `BigInt`, and the default Stage-2 BigInt shift lowering composes
with this representation change without adding another experiment column.

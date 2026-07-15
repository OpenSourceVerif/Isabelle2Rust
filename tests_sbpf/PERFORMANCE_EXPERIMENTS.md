# sBPF performance experiments

Date: 2026-07-15

This note records the experiments used for the RQ3 performance draft. The
functional oracle is the existing sBPF JSON corpus. The program-level suite has
146 cases and the instruction-level suite has 300 vectors.

## Protocol

- Host: Intel Core Ultra 9 185H, Linux under WSL2.
- Rust: `rustc 1.91.0-nightly`, generated crates built with `--release`.
- OCaml: `ocamlopt 4.11.2`.
- Each process was pinned to logical CPU 0.
- Every reported result is the median of three runs.
- JSON decoding and per-case output were outside the timed region.
- Program-level Rust runs traversed all cases once. OCaml traversals were
  repeated 20 times per process and divided by 20.
- Instruction-level inputs were converted before timing. Each process executed
  all 300 vectors 20 times, for 6,000 timed steps.
- A performance time was retained only when the implementation passed every
  case in the stated comparison set.

## Stage-1, Stage-2, and OCaml

All three generated implementations passed 146/146 program cases and 300/300
instruction cases.

| Level | Implementation | Raw times (s) | Median (s) | Rate | Peak RSS median |
|---|---|---:|---:|---:|---:|
| Program, 146 cases | Stage-1 Rust | 121.833824, 127.394794, 123.124299 | 123.124299 | 1.186 cases/s | 1,701.9 MiB |
| Program, 146 cases | Stage-2 Rust | 6.072200, 6.143707, 5.966587 | 6.072200 | 24.044 cases/s | 6.89 MiB |
| Program, 146 cases | OCaml native | 2.915914, 2.999822, 2.992418 for 20 traversals | 0.149621 per traversal | 975.800 cases/s | 9.17 MiB |
| Instruction, 300 x 20 | Stage-1 Rust | 20.523923, 21.280951, 20.684503 | 20.684503 | 290.072 steps/s | not recorded |
| Instruction, 300 x 20 | Stage-2 Rust | 6.230541, 5.834205, 6.034727 | 6.034727 | 994.246 steps/s | 3.68 MiB |
| Instruction, 300 x 20 | OCaml native | 1.021425, 1.034111, 0.983053 | 1.021425 | 5,874.146 steps/s | not recorded |

Stage-2 is 20.28 times faster than Stage-1 at program level, but it remains
40.59 times slower than OCaml. At instruction level, Stage-2 remains 5.91
times slower than OCaml. These numbers replace the earlier 37.1-fold estimate,
which included more harness overhead and used a shorter OCaml timing interval.

## Native rBPF interpreter

The native comparison uses the repository's modified Solana/rBPF 0.8.2. The
timed region contains `execute_program` or `execute_step`, not executable and VM
construction. It is therefore an interpreter-core rate and should not be read
as end-to-end process latency.

All 300 instruction vectors passed against the expected result and program
counter. The three 30,000,000-step times were 1.303121, 1.277367, and 1.265605
seconds. Their median rate was 23,485,806 steps/s.

At program level, the JSON records omit native setup information for 12 cases:

- `test_lmul128` and `test_stxb_chain` require larger input memory regions.
- `test_dynamic_stack_frames_empty`, `test_dynamic_frame_ptr_1`,
  `test_dynamic_frame_ptr_2`, `test_entrypoint_exit`,
  `test_stack_call_depth_tracking`, `test_bpf_to_bpf_depth`,
  `test_bpf_to_bpf_scratch_registers`, `test_callx`, `test_callx_imm`, and
  `test_far_jumps` require internal function-entry registrations.

The native harness reconstructs that metadata from the original rBPF fixtures.
It extends the two input regions, registers direct-call targets encoded in the
instructions, and registers the three `callx` targets. With that reconstruction,
all 146/146 cases agree on success or error status and result. The three
1,460,000-execution core times were 0.339901, 0.340428, and 0.361695 seconds,
giving a median rate of 4,288,720.406 cases/s. Peak RSS had a median of 2.58
MiB.

The full-suite rates were:

| Implementation | Program rate (cases/s) |
|---|---:|
| Stage-1 Rust | 1.186 |
| Stage-2 Rust | 24.044 |
| OCaml native | 975.800 |
| rBPF native core | 4,288,720.406 |

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

An isolated Stage-2 prototype kept `BigInt`, but replaced generic
power/multiplication and division in `push_bit`, `drop_bit`, and `mask` with
native `BigInt` shifts and a shifted mask. It passed all 446 cases.

| Level | Raw times (s) | Median (s) | Rate | Speedup over Stage-2 baseline |
|---|---:|---:|---:|---:|
| Program, 146 cases | 0.796254, 0.793162, 0.738385 | 0.793162 | 184.073 cases/s | 7.66x |
| Instruction, 300 x 20 | 1.142108, 1.150606, 1.177361 | 1.150606 | 5,214.642 steps/s | 5.24x |

The program result is 5.30 times slower than OCaml. The instruction result is
1.126 times slower than OCaml.

### Native word prototype

A first prototype stored words in `u64`. It passed all program cases but only
296/300 instruction vectors. The four failures exercise high-half signed or
unsigned multiplication, which requires a 128-bit intermediate.

The revised prototype stores the generic word payload in `u128`, masks it to
the Isabelle type-level width, and implements wrapping arithmetic, bitwise
operations, shifts, comparisons, division and remainder, signed and unsigned
casts, and conversion to and from `BigInt`. It passed all 446 cases.

| Level | Raw times (s) | Median (s) | Rate | Speedup over Stage-2 baseline |
|---|---:|---:|---:|---:|
| Program, 146 cases | 0.560541, 0.533225, 0.555002 | 0.555002 | 263.062 cases/s | 10.94x |
| Instruction, 300 x 20 | 1.014290, 0.968650, 1.016736 | 1.014290 | 5,915.467 steps/s | 5.95x |

The instruction kernel is 0.7% faster than the contemporaneous OCaml median.
That difference is too small to claim an advantage and is reported as parity.
The full program interpreter remains 3.71 times slower than OCaml.

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

This explains why the baseline can be roughly 40 times slower at program level
even though primitive word adaptation brings a single-step kernel to OCaml
parity.

## Proposed production adapter

The `u128` experiment modifies isolated generated crates and is not yet a
production code-generator feature. A systematic word adapter should:

1. introduce a `Rust_Word_Setup` runtime selected during Stage-1 generation,
2. represent widths up to 128 bits with a `u128` payload and a width mask,
3. implement wrapping arithmetic, bitwise operations, shifts, comparisons,
   signed and unsigned conversions, and high-half multiplication centrally,
4. expose word widths through a Rust associated constant rather than repeatedly
   reconstructing the type-level numeral,
5. reject or fall back to BigInt for word widths above 128 bits, and
6. run the existing 146 program and 300 instruction cases before any timing is
   accepted.

This adapter is the highest-value arithmetic optimization. Reaching full
program-level parity will additionally require replacing hot persistent-state
closure chains with a representation that preserves the semantics while using
compact Rust storage.

# sBPF performance experiments

This file preserves early performance-draft provenance, including its original
nightly toolchains.  The final paper-facing stable-Rust performance records are
listed in the 2026-08 entries of `../EXPERIMENTS.md` and under
`evaluation/results/rq3/`.

Date: 2026-07-19

This note records the experiments used for the RQ3 performance draft. The
functional oracle is the existing sBPF JSON corpus. The program-level suite has
146 cases. The original Word-only round used 300 instruction vectors; the
hybrid native-integer round below expands that workload to a deterministic 800
vectors.

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
- Instruction-level inputs were converted before timing. The native-integer
  round executed all 800 vectors 20 times, for 16,000 timed steps. Older tables
  below retain their explicitly labelled 300 x 20 workload.
- Performance timing began only after separate correctness validation.

## Hybrid native integer and natural-number ablation (800 vectors)

This round compares all current Stage-2 representations in one session. The
instruction corpus was generated with seed `5984326`; its SHA-256 is
`1a5efc9e211e83c97cfd7f76b62f28f67c7e4a5ee2712ed36270ed7b590e6b8f`.
The existing OCaml implementation was not changed or rebuilt. Program-level
`Time / OCaml` uses its recorded 0.149621-second median for the same 146-case
suite. Instruction-level `Time / OCaml` uses its recorded rate of 5,874.146
steps/s; at that rate 16,000 steps correspond to 2.723800 seconds. Thus the
instruction ratio is a throughput-normalized reference to the retained
300-vector OCaml run, not a new OCaml measurement on the 800-vector corpus.

| Level | Implementation | Raw times (s) | Median (s) | Rate | Speedup vs Stage 2 | Time / OCaml |
|---|---|---:|---:|---:|---:|---:|
| Program, 146 cases | Current Stage-2 Rust | 0.424206501, 0.409673010, 0.451409537 | 0.424206501 | 344.172 cases/s | 1.000x | 2.835x |
| Program, 146 cases | Stage-2 + Word Rust | 0.248803401, 0.249134404, 0.251891931 | 0.249134404 | 586.029 cases/s | 1.703x | 1.665x |
| Program, 146 cases | Stage-2 + Native Int/Nat Rust | 0.138938271, 0.123989903, 0.116269279 | 0.123989903 | 1,177.515 cases/s | 3.421x | 0.829x |
| Program, 146 cases | Stage-2 + Word + Native Int/Nat Rust | 0.106489941, 0.109952100, 0.105878228 | 0.106489941 | 1,371.022 cases/s | 3.984x | 0.712x |
| Instruction, 800 x 20 | Current Stage-2 Rust | 2.107991114, 2.070795739, 1.985447421 | 2.070795739 | 7,726.498 steps/s | 1.000x | 0.760x |
| Instruction, 800 x 20 | Stage-2 + Word Rust | 0.544736320, 0.631324800, 0.560829038 | 0.560829038 | 28,529.193 steps/s | 3.692x | 0.206x |
| Instruction, 800 x 20 | Stage-2 + Native Int/Nat Rust | 0.928876330, 0.456142331, 0.490124270 | 0.490124270 | 32,644.782 steps/s | 4.225x | 0.180x |
| Instruction, 800 x 20 | Stage-2 + Word + Native Int/Nat Rust | 0.521546517, 0.268138939, 0.268130461 | 0.268138939 | 59,670.558 steps/s | 7.723x | 0.098x |

The hybrid Int/Nat mapping alone improves the current Stage-2 median by 3.421x
at program level and 4.225x at instruction level. Combining it with the Word
adapter improves the current Stage-2 median by 3.984x and 7.723x respectively.
Against Stage-2 + Word, the combined representation is another 2.340x faster
for programs and 2.092x faster for instructions. Its program median is 1.405x
faster than the retained OCaml median; its instruction rate is 10.158x the
retained OCaml rate, subject to the corpus qualification above.

`Rust_Hybrid128_Setup.thy` maps Isabelle integers to
`Small(i128) | Big(Box<BigInt>)` and natural numbers to
`Small(u128) | Big(Box<BigUint>)`. Checked primitive operations promote only on
overflow, and arbitrary-precision results demote when they fit again.
`Rust_Hybrid128_WordU128_Setup.thy` adds the matching Word layer, which consumes
the small variants directly and performs BigInt modulo only at a big-value
conversion boundary. These are selectable Stage-1 representation mappings;
the generated modules still pass through the normal Stage-2 optimizer.

Release-symbol inspection of the combined instruction binary found no
`Rust_Word::width`, `Rust_Word::mask`, `WordWidth::len_of`, or
`NativeWordWidth` symbol. The Word hot paths use the associated `WIDTH`
constant and were inlined, while only the cold big-value conversion functions
remained as separate Word runtime symbols. The current BigInt Stage-2 baseline
was regenerated in the same round and its concrete `push_bit`, `drop_bit`, and
`mask` implementations contain direct shifts.

## Borrow-safe `nth` ablation

This round isolates the final borrow-inference change on the combined Stage-2
Word and Native Int/Nat representation. The before snapshot uses the previous
`OwnOK` policy; the after snapshot replaces it with the independent decision
`BorrowSafe && !PreferOwned`. Both snapshots were measured alternately in the
same session after release builds, pinned to CPU 0.

| Level | Borrow inference | Raw times (s) | Median (s) | Rate | Speedup | Time / OCaml |
|---|---|---:|---:|---:|---:|---:|
| Program, 146 cases | Previous `OwnOK` | 0.103408430, 0.107461199, 0.112346009 | 0.107461199 | 1,358.630 cases/s | 1.000x | 0.718x |
| Program, 146 cases | `BorrowSafe && !PreferOwned` | 0.034357110, 0.028816995, 0.029036570 | 0.029036570 | 5,028.142 cases/s | 3.701x | 0.194x |
| Instruction, 800 x 20 | Previous `OwnOK` | 0.263284032, 0.274509486, 0.256205842 | 0.263284032 | 60,770.871 steps/s | 1.000x | 0.097x |
| Instruction, 800 x 20 | `BorrowSafe && !PreferOwned` | 0.176802371, 0.158261923, 0.187586292 | 0.176802371 | 90,496.524 steps/s | 1.489x | 0.065x |

The previous policy first previewed M-LastUse and then rejected every resulting
direct owned use. For `nth`, this confused recursive last-use forwarding with a
profitable structural move and retained calls of the form `nth(l.clone(), i)`.
The revised analysis checks borrow safety against the original body and uses
the M-LastUse preview only to decide whether ownership should be preferred.
Recursive forwarding into the borrowed `nth` position is borrow-transparent,
and returning a selected element does not transfer the list spine. Structural
rebuilding paths that move a spine into an owned result remain owned.

The optimized interpreter takes `nth`'s list parameter by shared reference,
traverses boxed tails by reference, and clones only the selected result when
required by its generic result type. This improves the combined representation
by 3.701x at program level and 1.489x at instruction level. Its 0.029037-second
program median is 5.153x faster than the retained 0.149621-second OCaml median.
Its instruction rate is 15.406x the retained OCaml rate; as in the hybrid table
above, that instruction comparison is throughput-normalized from the retained
300-vector OCaml run rather than a fresh OCaml run on the 800-vector corpus.

## Earlier 300-vector Stage 1, Stage 2, Word, and OCaml round

The current Stage-2 and Stage-2 + Word rows were measured in the same run on
2026-07-19. The Stage-1 and OCaml rows retain the earlier protocol-compatible
measurements. `Time / OCaml` compares medians, so values below one are faster
than OCaml.

| Level | Implementation | Raw times (s) | Median (s) | Rate | Time / OCaml |
|---|---|---:|---:|---:|---:|
| Program, 146 cases | Stage-1 Rust | 121.833824, 127.394794, 123.124299 | 123.124299 | 1.186 cases/s | 822.908x |
| Program, 146 cases | Current Stage-2 Rust | 0.432771943, 0.462209072, 0.441199319 | 0.441199319 | 330.916 cases/s | 2.949x |
| Program, 146 cases | Stage-2 + Word Rust | 0.265086987, 0.289384312, 0.252743356 | 0.265086987 | 550.763 cases/s | 1.772x |
| Program, 146 cases | OCaml native | 2.915914, 2.999822, 2.992418 for 20 traversals | 0.149621 per traversal | 975.800 cases/s | 1.000x |
| Instruction, 300 x 20 | Stage-1 Rust | 20.523923, 21.280951, 20.684503 | 20.684503 | 290.072 steps/s | 20.251x |
| Instruction, 300 x 20 | Current Stage-2 Rust | 0.712960824, 0.727080263, 0.772733590 | 0.727080263 | 8,252.184 steps/s | 0.712x |
| Instruction, 300 x 20 | Stage-2 + Word Rust | 0.246654430, 0.212129711, 0.195956027 | 0.212129711 | 28,284.581 steps/s | 0.208x |
| Instruction, 300 x 20 | OCaml native | 1.021425, 1.034111, 0.983053 | 1.021425 | 5,874.146 steps/s | 1.000x |

The Word adapter improves the current Stage-2 median by 1.664x at program level
and 3.428x at instruction level. The resulting instruction kernel is 4.815x
faster than the recorded OCaml median, while the full program interpreter
remains 1.772x slower than OCaml.

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
| Current Stage-2 Rust | 330.916 | 8,252.184 |
| Stage-2 + Word Rust | 550.763 | 28,284.581 |
| OCaml native | 975.800 | 5,874.146 |
| rBPF native core | 4,288,720.406 | 23,485,806 |

The native rBPF rate is not a direct code-generation baseline. It uses mutable
arrays, primitive registers, direct dispatch, and runtime-specific setup. The
generated interpreters retain the functional semantics and their checks.

## Numeric-representation ablation

### Unadapted Isabelle integers

`theory/bpf_generator_no_bigint.thy` imports `Rust.Rust_Base_Setup` without the
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

### Administrative closure eta-reduction

The current Stage-2 pipeline also removes backend-generated forwarding
closures of the form `Rc::new(move |x| (*factory(captures))(x))` when the local
factory performs no eager work other than capture moves and returning an
`Rc<dyn Fn>`. The replacement reuses `factory(captures)` directly. It neither
inlines the factory body nor beta-reduces the returned closure, so the
function-valued state representation is retained.

The following ablation was measured in one session with pre-pass snapshots and
the eta-enabled outputs run alternately. The OCaml medians are the recorded
protocol-compatible baselines above.

| Level | Representation | Eta reduction | Raw times (s) | Median (s) | Rate | Speedup | Time / OCaml |
|---|---|---|---:|---:|---:|---:|---:|
| Program, 146 cases | Current Stage-2 | Without | 0.667292603, 0.594387636, 0.717819110 | 0.667292603 | 218.795 cases/s | 1.000x | 4.460x |
| Program, 146 cases | Current Stage-2 | With | 0.432771943, 0.462209072, 0.441199319 | 0.441199319 | 330.916 cases/s | 1.512x | 2.949x |
| Program, 146 cases | Stage-2 + Word | Without | 0.266172902, 0.300679973, 0.282204488 | 0.282204488 | 517.355 cases/s | 1.000x | 1.886x |
| Program, 146 cases | Stage-2 + Word | With | 0.265086987, 0.289384312, 0.252743356 | 0.265086987 | 550.763 cases/s | 1.065x | 1.772x |
| Instruction, 300 x 20 | Current Stage-2 | Without | 0.904438141, 0.822814716, 0.891429547 | 0.891429547 | 6,730.762 steps/s | 1.000x | 0.873x |
| Instruction, 300 x 20 | Current Stage-2 | With | 0.712960824, 0.727080263, 0.772733590 | 0.727080263 | 8,252.184 steps/s | 1.226x | 0.712x |
| Instruction, 300 x 20 | Stage-2 + Word | Without | 0.242228359, 0.273348207, 0.255738803 | 0.255738803 | 23,461.438 steps/s | 1.000x | 0.250x |
| Instruction, 300 x 20 | Stage-2 + Word | With | 0.246654430, 0.212129711, 0.195956027 | 0.212129711 | 28,284.581 steps/s | 1.206x | 0.208x |

The larger program-level gain without the Word adapter is consistent with the
eliminated forwarding closure repeatedly cloning BigInt-backed word values.
With the `u128` payload those value clones are already cheap, but avoiding the
temporary closure allocation and dispatch still improves the instruction
kernel. Each update continues to allocate the `fun_upd` closure that represents
the persistent register state; this pass removes only the redundant outer
adapter.

### Stage-1 u128 word adapter

The earlier `u64` design was rejected because signed and unsigned high-half
multiplication require a 128-bit intermediate. `Rust_BigInt_WordU128_Setup.thy`
instead maps Isabelle words to `RustWord<W>` with a `u128` payload and a
`PhantomData<W>` width marker. It masks constructions and arithmetic to the
Isabelle type-level width, while conversions to and from `int` and `nat` remain
at the `BigInt` boundary. The generated code then runs through the unchanged
Stage-2 optimizer.

| Level | Raw times (s) | Median (s) | Rate | Stage-2 speedup | Time / OCaml |
|---|---:|---:|---:|---:|---:|
| Program, 146 cases | 0.265086987, 0.289384312, 0.252743356 | 0.265086987 | 550.763 cases/s | 1.664x | 1.772x |
| Instruction, 300 x 20 | 0.246654430, 0.212129711, 0.195956027 | 0.212129711 | 28,284.581 steps/s | 3.428x | 0.208x |

The Stage-1 setup maps the standard type-level numeral constructors to Rust
width markers with an associated `u32` constant. Generated `len_of` methods
remain source-compatible with Isabelle's `len0` class, but word operations use
the associated constant. Release inspection found no remaining `width`, `mask`,
or generated `len_of` symbols in either the Stage-1 or Stage-2 instruction
binary, so a separate Stage-2 width-specialization pass is unnecessary.

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
while the full program interpreter remains 1.772 times slower.

## Implemented adapter

`Rust_BigInt_WordU128_Setup.thy` is a selectable Stage-1 setup registered in `ROOT`.
It supports widths from 1 through 128 bits and covers construction, conversion,
wrapping arithmetic, division and remainder, unsigned and signed comparison,
bitwise operations, shifts, bit updates and tests, casts, and the 128-bit
intermediate used by the 64-bit high-half multiplication paths. Isabelle `int`
and `nat` remain `BigInt`.

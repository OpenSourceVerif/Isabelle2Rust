# Code-generation quality experiments

`Cross_Target_Smoke.thy` reuses four existing Unit/FPP theories and exports the
same definitions to SML, OCaml, Haskell, Scala, Go, and Rust. It is intended to
check the cross-target harness before scaling the experiment to the complete
common corpus.

The paper-level comparison uses:

- 67 rule-directed unit-test theories; and
- 36 FPP theories that contain executable `export_code` commands.

For every target, record code-export success separately from compiler
acceptance. A missing compiler must be reported as unavailable, not as a failed
generated program.

## Performance extension

Performance should be evaluated only on definitions with a common executable
driver and identical inputs. Suitable FPP workloads are:

- `Quicksort_Test.quicksort` and `MergeSort_Test.msort`, on fixed random integer
  lists at several sizes;
- balanced-tree insertion and membership, on a fixed insertion sequence and
  query set; and
- the IMP compiler, on generated source programs of increasing size.

Each driver should read or construct the same inputs, evaluate the complete
result, and print a checksum to prevent dead-code elimination. Report cold-start
time separately from steady-state execution time, especially for Scala/JVM.
After warm-up, use at least 30 measured runs and report the median and
interquartile range. Build every target with its normal optimized production
configuration and record peak resident memory in addition to elapsed time.

These measurements should remain separate from the code-generation completion
table: runtime performance depends on workload, compiler, runtime system, and
input size, whereas export/build completion measures backend coverage.

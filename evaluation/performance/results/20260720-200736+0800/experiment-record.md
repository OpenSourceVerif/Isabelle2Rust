# RQ3 SBPF experiment record

- Git commit: `d444b290d44b28f123fab475c9f12b8222d59efb`
- Measurement CPU: `0`
- SBPF-program input SHA-256: `cafc40d84adc2cf4a66673fdba81e734029de8c67795dbae4c09933ca8da2662`
- SBPF-instruction input SHA-256: `bc8bdb416345c369ee0f53d2e896f132f50433919fbf14f258d1b2d2ef5072b2`
- Correctness: all seven SBPF-program implementations passed 146/146 cases; all seven SBPF-instruction implementations passed 6000/6000 vectors.
- Each value below is from an independent pinned process; the reported value is the median of the three process runs.

Host instructions are `TBD`. The direct `perf_event_open(PERF_COUNT_HW_INSTRUCTIONS, pid=0, cpu=-1)` probe failed with errno 13 (`Permission denied`), `perf_event_paranoid=2`, and no compatible `perf` executable was installed. No estimate was substituted.

## SBPF-program

### Median runtime (s)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 93.267563332 | 98.256335180 | 95.976977725 | 95.976977725 |
| Stage-2 minus Copy | 0.249486038 | 0.259583829 | 0.251404734 | 0.251404734 |
| Stage-2 minus Borrow | 0.374810567 | 0.385522672 | 0.331350143 | 0.374810567 |
| Stage-2 minus Mut | 3.916213457 | 3.952818625 | 3.549812622 | 3.916213457 |
| Stage-2 Full | 0.238764562 | 0.255373917 | 0.226279376 | 0.238764562 |
| OCaml baseline | 0.165823698 | 0.158302093 | 0.147408998 | 0.158302093 |
| Case-study baseline | 0.000035179 | 0.000038047 | 0.000047084 | 0.000038047 |

### Peak RSS (MiB)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 1571.238281250 | 1571.328125000 | 1571.273437500 | 1571.273437500 |
| Stage-2 minus Copy | 6.480468750 | 6.480468750 | 6.636718750 | 6.480468750 |
| Stage-2 minus Borrow | 7.464843750 | 7.437500000 | 7.433593750 | 7.437500000 |
| Stage-2 minus Mut | 1567.296875000 | 1567.242187500 | 1567.363281250 | 1567.296875000 |
| Stage-2 Full | 6.476562500 | 6.625000000 | 6.460937500 | 6.476562500 |
| OCaml baseline | 9.476562500 | 9.496093750 | 9.500000000 | 9.496093750 |
| Case-study baseline | 25.355468750 | 25.371093750 | 25.335937500 | 25.355468750 |

### Heap allocation (MiB/case)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 465.144867035 | 465.144867035 | 465.144867035 | 465.144867035 |
| Stage-2 minus Copy | 0.308770088 | 0.308770088 | 0.308770088 | 0.308770088 |
| Stage-2 minus Borrow | 1.316389450 | 1.316389450 | 1.316389450 | 1.316389450 |
| Stage-2 minus Mut | 10.927000294 | 10.927000294 | 10.927000294 | 10.927000294 |
| Stage-2 Full | 0.308770088 | 0.308770088 | 0.308770088 | 0.308770088 |
| OCaml baseline | 2.539449488 | 2.539449488 | 2.539449488 | 2.539449488 |
| Case-study baseline | 0.000000000 | 0.000000000 | 0.000000000 | 0.000000000 |

### Host instructions (instructions/case)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | TBD | TBD | TBD | TBD |
| Stage-2 minus Copy | TBD | TBD | TBD | TBD |
| Stage-2 minus Borrow | TBD | TBD | TBD | TBD |
| Stage-2 minus Mut | TBD | TBD | TBD | TBD |
| Stage-2 Full | TBD | TBD | TBD | TBD |
| OCaml baseline | TBD | TBD | TBD | TBD |
| Case-study baseline | TBD | TBD | TBD | TBD |

## SBPF-instruction

### Median runtime (s)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 13.204532629 | 14.322400474 | 14.282569987 | 14.282569987 |
| Stage-2 minus Copy | 0.810095185 | 0.821893225 | 0.914503883 | 0.821893225 |
| Stage-2 minus Borrow | 0.860400812 | 0.935073651 | 0.895731958 | 0.895731958 |
| Stage-2 minus Mut | 3.787245786 | 4.078206406 | 4.266590462 | 4.078206406 |
| Stage-2 Full | 0.923950293 | 0.855010849 | 0.845647958 | 0.855010849 |
| OCaml baseline | 1.130695105 | 1.252449989 | 1.205373049 | 1.205373049 |
| Case-study baseline | 0.002259773 | 0.001902101 | 0.001922521 | 0.001922521 |

### Peak RSS (MiB)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 24.527343750 | 24.449218750 | 24.527343750 | 24.527343750 |
| Stage-2 minus Copy | 24.480468750 | 24.355468750 | 24.480468750 | 24.480468750 |
| Stage-2 minus Borrow | 24.585937500 | 24.398437500 | 24.523437500 | 24.523437500 |
| Stage-2 minus Mut | 24.410156250 | 24.472656250 | 24.535156250 | 24.472656250 |
| Stage-2 Full | 24.472656250 | 24.410156250 | 24.410156250 | 24.410156250 |
| OCaml baseline | 38.441406250 | 38.453125000 | 38.625000000 | 38.453125000 |
| Case-study baseline | 59.488281250 | 59.460937500 | 59.507812500 | 59.488281250 |

### Heap allocation (KiB/step)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 1388.520110026 | 1388.520110026 | 1388.520110026 | 1388.520110026 |
| Stage-2 minus Copy | 42.191245280 | 42.191245280 | 42.191245280 | 42.191245280 |
| Stage-2 minus Borrow | 59.937557780 | 59.937557780 | 59.937557780 | 59.937557780 |
| Stage-2 minus Mut | 794.171237956 | 794.171237956 | 794.171237956 | 794.171237956 |
| Stage-2 Full | 42.191245280 | 42.191245280 | 42.191245280 | 42.191245280 |
| OCaml baseline | 295.356296875 | 295.356296875 | 295.356296875 | 295.356296875 |
| Case-study baseline | 0.000000000 | 0.000000000 | 0.000000000 | 0.000000000 |

### Host instructions (instructions/step)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | TBD | TBD | TBD | TBD |
| Stage-2 minus Copy | TBD | TBD | TBD | TBD |
| Stage-2 minus Borrow | TBD | TBD | TBD | TBD |
| Stage-2 minus Mut | TBD | TBD | TBD | TBD |
| Stage-2 Full | TBD | TBD | TBD | TBD |
| OCaml baseline | TBD | TBD | TBD | TBD |
| Case-study baseline | TBD | TBD | TBD | TBD |

## Artifacts

- `environment.json`: host, toolchains, affinity, inputs, and counter probe.
- `configurations.json`: pass matrix, source hashes, build settings, and executable hashes.
- `raw.csv`: one row per formal measurement process.
- `summary.csv`: the three values and median for every table cell.
- `commands.txt`: every actual preparation, build, validation, pilot, and measurement command.
- `correctness/`, `pilot/`, and `runs/`: per-process stdout, stderr, and `/usr/bin/time -v` output.

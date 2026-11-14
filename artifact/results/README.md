# Paper results

These versionable publication records are separate from local raw runs.

| Question | Final records |
| --- | --- |
| RQ1: translation correctness and recovery | [rq1/](rq1/README.md) |
| RQ2: optimization and numeric representation | [rq2/](rq2/README.md) |
| RQ3: cross-language performance | [rq3/](rq3/README.md) |

`artifact/results/` is intended for Git. `artifact/runs/` stays Git-ignored and
retains original experiments, checkpoints, generated programs and raw evidence.
No historical runs were deleted to produce these records. This result collection
is not a self-contained bundle of all generated programs or raw observations.

Published records preserve numeric results and remove personal path prefixes.
Each RQ has a `checksums.json` for its publication files. Source receipt hashes
refer to the original evidence, not to redacted copies. Repository-relative
`artifact/` references resolve from the repository root. `workspace/` references
identify material outside the repository and are not bundled here.

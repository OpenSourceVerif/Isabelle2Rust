# Paper results

Final results produced by the agent in `agent/`.

| Question | Records |
| --- | --- |
| RQ1: translation correctness and recovery | [rq1/](rq1/README.md) |
| RQ2: optimization and numeric representation | [rq2/](rq2/README.md) |
| RQ3: cross-language performance | [rq3/](rq3/README.md) |

`artifact/results/` contains the versioned publication records. Raw execution
state and source evidence remain local in Git-ignored `artifact/runs/`.
Run-specific implementation identities, configurations, validation outcomes and
measurement qualifications remain in the records.

References beginning `evidence/` are stable identifiers, not checkout paths.
[evidence-index.json](evidence-index.json) provides hashes for available source
files; null means the reference denotes a directory or an unavailable local
file. Raw evidence is not bundled in this source repository. Each RQ has a
`checksums.json` covering its publication files. Source hashes identify original
evidence; publication checksums identify the anonymized copies.

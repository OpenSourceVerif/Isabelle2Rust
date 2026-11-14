# RQ1: translation correctness and recovery

| Dataset | Tasks | Accepted | Failed | Accepted after check recovery |
| --- | ---: | ---: | ---: | ---: |
| FPP | 313 | 307 | 6 | 107 |
| Unit | 488 | 479 | 9 | 105 |

- `summary.json`: final counts, costs, reference coverage, budgets and failures.
- `fpp-report.json`, `unit-report.json`: original completed-run reports.
- `tasks.csv`: one row per task, with acceptance and recovery status.
- `recovery-results.json`: recovery definitions, categories, all task records,
  and source receipt hashes. Categories overlap; task totals do not.
- `case-evidence.json`: concrete recovery examples and corresponding checks.

Recovery means a recorded check failure followed by corrective activity, a
successful corresponding check, and final acceptance. It is not an ablation
or a count of semantic errors. Provider interruptions and post-hoc probes are
excluded. Ten Unit requests have unknown token usage; known totals are lower
bounds. Differential validation is finite behavioral evidence, not a proof.

Source evidence remains in the ignored `artifact/runs/` directories. Paths in
publication copies are repository-relative; source hashes refer to original
receipts. `checksums.json` identifies these publication copies.

References starting with `evidence/` identify local raw evidence via the
publication evidence index; they are not paths inside this checkout.

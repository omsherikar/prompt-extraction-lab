# PRD — Phase 5: Experiment orchestration and results

- **Status:** Not started
- **Owner agent:** python-harness-engineer
- **Depends on:** Phase 4
- **Source:** [`../PLAN.md`](../PLAN.md) § Phase 5
- **Supports thesis claims:** all (produces the data); the budget curve serves claim 1

## 1. Objective

Run the full matrix once and get clean data out. Loop over models x prompts x attacks x defenses
x repeats, score everything, and write `results.json` and a flat `results.csv`, plus the summary
tables.

## 2. Background and context

This is where the pieces become a dataset. Reproducibility is the requirement that matters most:
the same `config.yaml` and seed must reproduce the results, because the post stands on those
numbers. Cost is real (all API calls), so the matrix is kept small first and scaled deliberately.

## 3. Scope

**In scope**
- The full matrix loop with scoring via the Phase 3 verifier.
- Writing `data/results/results.json` and `results.csv`, recording query counts.
- `aggregate.py` producing the four summary tables.

**Out of scope**
- Figures (Phase 6), which consume `results.json`.

## 4. Requirements

- **P5-R1** `run_full` loops over models x prompts x attacks x defenses x repeats, runs each via
  the runner, scores via the verifier, and assembles per-response records.
- **P5-R2** Each result record carries: model id, prompt id, prompt type, attack id, attack family,
  defense setting, repeat index, the three metric values, and the cumulative query count.
- **P5-R3** Output is written to `data/results/results.json` and a flat `data/results/results.csv`.
  Results are committed; raw transcripts remain gitignored.
- **P5-R4** A run is reproducible: same `config.yaml` + seed reproduces the same matrix and the
  same recorded query counts (model nondeterminism aside, which `temperature: 0` minimizes).
- **P5-R5** `aggregate.py` loads `results.json` into pandas and prints: leakage rate (exact and
  Rouge-L) by attack technique; leakage by prompt type; leakage by defense; self-agreement vs
  ground-truth correlation.
- **P5-R6** Token usage is logged so the post can carry a cost line.

## 5. Deliverables

| File | Work |
|------|------|
| `src/experiment/run.py` | Implement `run_full` + result writing (P5-R1 to P5-R4, P5-R6) |
| `src/experiment/aggregate.py` | Implement the four summary tables (P5-R5) |
| `data/results/results.json`, `results.csv` | Generated output (committed) |

## 6. Acceptance criteria

- **P5-A1** A single command (`make run`) runs the whole study and writes `results.json` and
  `results.csv` plus printed summary tables (PLAN.md Phase 5 acceptance).
- **P5-A2** Re-running with the fixed seed reproduces the matrix structure and counts.
- **P5-A3** `make aggregate` prints all four tables from an existing `results.json`.

## 7. Test plan

- Unit: `aggregate` over a small synthetic `results.json` fixture produces the expected group-by
  shapes and a correlation value of the expected sign. (No network.)
- Manual: a small matrix (1 model, all prompts, all attacks, k=3) runs end to end and the CSV
  opens cleanly.

## 8. Risks and open questions

- Cost control: start with 1 model and the small matrix; confirm spend before scaling models. The
  query budget bounds attacks per (model, prompt).
- Partial-run resilience: persist transcripts as the run proceeds so a crash does not lose work
  and a re-score does not require re-querying.

## 9. Definition of done

- [ ] P5-R1 through P5-R6 implemented.
- [ ] P5-A1, P5-A2, P5-A3 pass.
- [ ] A small-matrix run produces committed `results.json` and `results.csv`.

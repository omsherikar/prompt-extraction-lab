# Product Requirements Documents

Phase-wise PRDs for prompt-extraction-lab. Each PRD formalizes one phase of
[`../PLAN.md`](../PLAN.md) into objective, scope, numbered requirements, deliverables, and
acceptance criteria, so a single phase can be handed to an engineer or one of the agents in
`.claude/agents/` and executed without re-reading the whole plan.

## Conventions

- **Requirement IDs:** `P{phase}-R{n}` (functional requirements). **Acceptance IDs:**
  `P{phase}-A{n}`. These are stable; cite them in commits and PRs (e.g. `feat(scoring): P3-R2`).
- **Status:** `Not started` / `In progress` / `Done`.
- **Source:** each PRD links back to its section in `../PLAN.md`.
- The scope discipline in [`../../CLAUDE.md`](../../CLAUDE.md) §0 governs every phase (we only
  attack prompts we wrote; every technique is cited; nothing novel; no third-party targets). It
  is the precondition for all PRDs and is not restated in each one.
- Writing rules for any `blog/` output: no em-dashes, no buzzwords, every claim cited or measured.

## Index

| Phase | PRD | Owner agent | Depends on | Status |
|------|-----|-------------|-----------|--------|
| 0 | [Scaffolding](phase-0-scaffolding.md) | python-harness-engineer | — | In progress |
| 1 | [Target app and ground-truth prompts](phase-1-target-app.md) | python-harness-engineer | 0 | Not started |
| 2 | [Attack library and runner](phase-2-attacks.md) | adversarial-prompt-researcher | 1 | Not started |
| 3 | [Scoring (core)](phase-3-scoring.md) | scoring-metrics-engineer, test-engineer | 2 | Not started |
| 4 | [Defenses](phase-4-defenses.md) | python-harness-engineer, adversarial-prompt-researcher | 3 | Not started |
| 5 | [Orchestration and results](phase-5-orchestration.md) | python-harness-engineer | 4 | Not started |
| 6 | [Figures](phase-6-figures.md) | data-viz-analyst | 5 | Not started |
| 7 | [The writeup](phase-7-writeup.md) | technical-writer, research-integrity-reviewer | 6 | Not started |

## Thesis traceability

The build exists to support five claims with numbers behind them. Each claim traces to the
phase that produces its evidence.

| # | Claim | Evidence produced in |
|---|-------|----------------------|
| 1 | Known, simple queries recover a controlled prompt at high rates under a small budget | P2 (attacks), P3 (scores), P5 (budget curve) |
| 2 | Extractability varies by prompt structure (direct / role / in-context) | P1 (prompt types), P3 (scores), P6 (heatmap) |
| 3 | Models confabulate; without ground truth you cannot tell a real leak from a plausible one | P3 (ground-truth + self-agreement verifier), P6 (scatter, side-by-side) |
| 4 | A naive filter reduces leakage but is evadable; an instructional defense barely helps | P4 (defenses + evasion), P6 (defense bars) |
| 5 | A system prompt is not a vault; treat anything in it as eventually public | P7 (the conclusion, carried by all of the above) |

## Suggested build order (from PLAN.md)

- Session 1: Phase 0 + Phase 1 (skeleton, provider, target app, prompts).
- Session 2: Phase 2 + Phase 3 (attacks, runner, metrics, verifier, tests). Heaviest session.
- Session 3: Phase 4 + Phase 5 (defenses, full orchestration, results).
- Session 4: Phase 6 (figures). Then write Phase 7.

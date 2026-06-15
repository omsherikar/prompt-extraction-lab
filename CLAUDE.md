# CLAUDE.md — prompt-extraction-lab

Operating rules for this repository. These override default behavior. Read `dev-notes/PLAN.md`
for the full build spec; this file is the standing law.

## 0. What this project is (and the one rule that defines it)

A measured study of system prompt extraction. **We only ever attack system prompts we wrote
ourselves, inside this harness.** We never target a third party's confidential or deployed
prompt. This is not a limitation to engineer around; it is the method. Because we author the
secret, we have ground truth, and ground truth is the entire contribution: it lets us tell a
real leak from a confident confabulation.

Hard lines, no exceptions:
- Attack targets are only the prompts in `src/target/prompts.py`, which we wrote.
- Every attack query is an already-published, documented technique, cited to its source. We add
  no novel attacks. The value is measurement, not invention.
- Do not add functionality that scrapes, probes, or targets external/third-party systems.
- If a change blurs this scope, stop and flag it rather than proceeding.

## 1. Scope discipline per phase

Build phase by phase as defined in `dev-notes/PLAN.md` (Phase 0 through 7). Do not pull work
forward from a later phase into the current one without saying so. Each phase has an acceptance
check in the plan; treat it as the definition of done for that phase.

## 2. Code rules

- Python >= 3.10. Type-hint all public functions and dataclasses. Prefer `dataclass` for records.
- Keep interfaces minimal and explicit. The `Provider` interface is one method; do not widen it
  casually. Adding a backend must stay trivial.
- Pure functions for anything scoring-related. `scoring/` must have no I/O and no network; it
  takes strings in and returns numbers out, so it is deterministic and testable.
- No hidden global state. Config is loaded once and passed down.
- Determinism: temperature, seed, and normalization are read from `config.yaml`. Never hardcode
  them in logic. A run must be reproducible from `config.yaml` + seed.
- Secrets come from the environment via `.env` (python-dotenv). Never hardcode or log API keys.
- Raw transcripts may contain full responses; they are gitignored. Only scored results are
  committed.
- Keep dependencies light. Rouge-L is implemented in-repo (no `rouge-score` dep) so the metric
  is fully under our control.

## 3. Testing rules

- The metrics and the verifier are the intellectual core. They get real tests, written first
  (TDD): `tests/test_metrics.py`, `tests/test_verifier.py`.
- Every metric needs: a known-value case on a small fixed example, true/false boundary cases,
  and edge cases (empty response, response shorter/longer than prompt, non-overlapping text).
- `make test` must be green before any phase is called done.
- Do not weaken a test to make code pass. Fix the code or, if the test is wrong, fix the test
  and say why.

## 4. Citation rules

Every attack in `src/attacks/queries.py` carries a `source` field naming the paper or post it
comes from. No uncited attacks. The blog post cites each technique to its origin.

## 5. Writing rules (for blog/ content)

- No em-dashes anywhere.
- No buzzwords or marketing language.
- Every claim is backed by either our own numbers or a cited source. Let the numbers carry the
  argument. `blog/outline.md` is a scaffold only; the prose is the author's.

## 6. Git and commit rules

- **This is its own standalone repository.** The parent directory `/Users/omsherikar` is an
  unrelated git repo; never run git commands that touch it. Always operate from this repo root.
- Branch off `main` for feature work (e.g. `phase-2-attacks`). Do not commit straight to `main`
  for non-trivial work.
- Conventional Commits: `feat:`, `fix:`, `test:`, `chore:`, `docs:`, `refactor:`, scoped where
  useful (e.g. `feat(scoring): add rouge_l_recall`).
- Commit messages explain the why, not just the what. Small, focused commits.
- **No AI attribution.** Never add `Co-Authored-By: Claude`, "Generated with Claude Code", or any
  AI mention to commit messages, PR titles, or PR bodies.
- Commit or push only when asked.

## 7. Working agreement

- Lint + typecheck on iteration; only run the experiment (real API spend) when the task needs it.
  Start the matrix small (1 model, all prompts, all attacks, k=3) before scaling models.
- When a decision has real trade-offs, recommend one and proceed; do not dump options.
- Specialized agents for this repo live in `.claude/agents/`. Use the right specialist for the
  phase (see that directory's roster).

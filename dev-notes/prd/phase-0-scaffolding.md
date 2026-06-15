# PRD — Phase 0: Scaffolding

- **Status:** In progress (structure and interfaces done; provider/config/smoke logic pending)
- **Owner agent:** python-harness-engineer
- **Depends on:** none
- **Source:** [`../PLAN.md`](../PLAN.md) § Phase 0
- **Supports thesis claims:** foundation for all

## 1. Objective

A runnable skeleton with config and a working model call. By the end, one hardcoded system
prompt plus one user message can be sent to one model and the response printed. Nothing else.

## 2. Background and context

Everything downstream (attacks, scoring, defenses, orchestration) needs two things: a model
backend behind a minimal interface, and a validated config that makes runs reproducible. This
phase delivers exactly those and proves the end-to-end path with a smoke test. Keeping the
`Provider` interface to a single method is a deliberate constraint: it is what makes adding a
second backend trivial later, which is what supports the cross-model claim.

## 3. Scope

**In scope**
- The `Provider` interface and the Anthropic implementation.
- Config loading and validation.
- The `--smoke` entrypoint.
- Packaging, environment, and tooling (already largely in place from the scaffold commit).

**Out of scope**
- Real ground-truth prompts (Phase 1).
- Attacks, scoring, defenses, the full matrix (Phases 2 to 5).
- The optional OpenAI backend beyond a stub (enable only if a key exists; not required to ship).

## 4. Requirements

- **P0-R1** `Provider` is an abstract base class with exactly one abstract method,
  `complete(system_prompt: str, user_message: str) -> str`. Model id and temperature are fixed
  at construction. The interface is not widened. *(Done.)*
- **P0-R2** `AnthropicProvider.complete` calls the Anthropic Messages API with the system prompt
  in the top-level `system` field and the user message as the user turn, returning the response
  text. Model id, temperature, and max tokens come from construction.
- **P0-R3** The API key is read from the environment (`ANTHROPIC_API_KEY`) via python-dotenv. The
  key is never hardcoded and never logged.
- **P0-R4** `load_config(path)` parses `config.yaml` into a typed `ExperimentConfig`, validating
  required keys and types. Malformed or missing config fails loudly with a clear message, before
  any API call.
- **P0-R5** `python -m src.experiment.run --smoke` loads `.env`, constructs the first configured
  provider, builds a `TargetApp` with one prompt, sends one benign message, and prints the
  response.
- **P0-R6** Packaging is in place: `pyproject.toml` (light deps, Rouge-L kept in-repo),
  `.env.example`, `.gitignore` (excludes `.env` and `data/transcripts/`), `config.yaml`,
  `Makefile`. *(Done.)*

## 5. Deliverables

| File | State |
|------|-------|
| `src/providers/base.py` | Done |
| `src/providers/anthropic_provider.py` | Implement `complete` (P0-R2, P0-R3) |
| `src/providers/openai_provider.py` | Optional stub; implement only if enabled |
| `src/experiment/config.py` | Implement `load_config` (P0-R4) |
| `src/experiment/run.py` | Implement `run_smoke` (P0-R5) |
| `pyproject.toml`, `config.yaml`, `.env.example`, `.gitignore`, `Makefile` | Done |

## 6. Acceptance criteria

- **P0-A1** `make smoke` (i.e. `python -m src.experiment.run --smoke`) prints a real model
  response to one benign message under one hardcoded system prompt.
- **P0-A2** Running with a malformed `config.yaml` exits with a clear validation error and makes
  no API call.
- **P0-A3** No secret value appears in stdout or any committed file.

## 7. Test plan

- Unit: `load_config` accepts the committed `config.yaml` and rejects a fixture missing a
  required key (asserts a clear error). No network in this test.
- Manual: `make smoke` against a real key prints a coherent on-task answer.

## 8. Risks and open questions

- Anthropic SDK response shape (content blocks) must be concatenated to plain text; handle the
  list-of-blocks form.
- Decide `max_tokens` default (scaffold uses 2048); large enough that a full prompt could be
  echoed back, since truncation would understate leakage.

## 9. Definition of done

- [ ] P0-R2 through P0-R5 implemented.
- [ ] P0-A1, P0-A2, P0-A3 pass.
- [ ] `make lint` and `make typecheck` clean on touched files.

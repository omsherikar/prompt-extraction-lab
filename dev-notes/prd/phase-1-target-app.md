# PRD — Phase 1: Target app and ground-truth prompts

- **Status:** Not started
- **Owner agent:** python-harness-engineer
- **Depends on:** Phase 0
- **Source:** [`../PLAN.md`](../PLAN.md) § Phase 1
- **Supports thesis claims:** 2 (extractability varies by structure)

## 1. Objective

The thing we attack, plus a set of secrets we know. A `TargetApp` that wraps one ground-truth
system prompt and one provider and behaves like a real app, and a registry of authored prompts
spanning three structural types.

## 2. Background and context

The whole method rests on knowing the secret. The prompts written here are the ground truth that
every later score is measured against. They are deliberately split into three structural types so
the post can compare extractability by structure, which is claim 2. The in-context type matters
because its few-shot examples are extra text that can leak independently of the instruction.

## 3. Scope

**In scope**
- 2 to 3 authored prompts per structural type (`direct`, `role`, `in_context`), varying length.
- `TargetApp.query` returning a normal on-task answer to a benign message.

**Out of scope**
- Attacks against the app (Phase 2).
- Defenses wrapped around `query` (Phase 4).

## 4. Requirements

- **P1-R1** `src/target/prompts.py` defines a `PROMPTS` registry of `TargetPrompt(id, type, text)`
  records: at least 2 (target 3) each for `direct`, `role`, `in_context`, with within-type length
  variation. Ids are stable and unique; results key off them.
- **P1-R2** `direct` prompts are plain instruction prompts. `role` prompts define a persona and
  rules. `in_context` prompts include at least one few-shot example block as part of the prompt
  text.
- **P1-R3** Prompt text is original and self-contained (no copied third-party proprietary prompt),
  consistent with the scope rule.
- **P1-R4** `TargetApp(prompt, provider).query(user_message)` returns the provider's response
  under that prompt's text as the system prompt. The undefended path is a thin pass-through.
- **P1-R5** A benign, on-task message to each prompt yields a coherent, on-task answer (the app
  is convincing as a real app before anyone tries to break it).

## 5. Deliverables

| File | Work |
|------|------|
| `src/target/prompts.py` | Replace the single placeholder with the full registry (P1-R1, P1-R2) |
| `src/target/app.py` | Already defined; confirm the pass-through (P1-R4) |

## 6. Acceptance criteria

- **P1-A1** A `TargetApp` can be instantiated with any prompt id and any provider, sent a benign
  user message, and returns a normal on-task answer (PLAN.md Phase 1 acceptance).
- **P1-A2** `PROMPTS` contains >= 6 entries covering all three types, each with a unique stable id.

## 7. Test plan

- Unit: `PROMPTS` has all three types, ids unique, every `type` value valid. (No network.)
- Manual: one benign query per prompt returns an on-task answer; spot-check the in-context prompt
  answers in the style of its few-shot examples.

## 8. Risks and open questions

- Prompt length spread: include at least one short and one long prompt per type so length effects
  are observable in the heatmap.
- Keep secrets genuinely "secret-shaped" (an internal rule, a hidden persona detail, a fake policy
  line) so that a leak is meaningful and visibly distinct from a generic answer.

## 9. Definition of done

- [ ] P1-R1 through P1-R5 implemented.
- [ ] P1-A1, P1-A2 pass.
- [ ] `make lint`, `make typecheck` clean on touched files.

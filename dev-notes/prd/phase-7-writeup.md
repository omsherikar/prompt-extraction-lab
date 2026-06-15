# PRD — Phase 7: The writeup

- **Status:** Not started
- **Owner agents:** technical-writer (draft), research-integrity-reviewer (pre-publish gate)
- **Depends on:** Phase 6
- **Source:** [`../PLAN.md`](../PLAN.md) § Phase 7
- **Supports thesis claims:** 5 (prompts are not vaults), and ties together 1 to 4

## 1. Objective

The blog post. `blog/outline.md` is a scaffold of headers and claim-notes only; the analysis,
voice, and conclusions are the author's. This PRD defines the structure the data supports and the
non-negotiable writing rules, not the prose.

## 2. Background and context

The post is the deliverable the whole repo exists to support. Its credibility rests on letting the
numbers carry the argument and citing every technique. The strongest, most original section is
real vs hallucinated, backed by the self-agreement result.

## 3. Scope

**In scope**
- A complete draft following the eight-part structure, every claim backed by our numbers or a
  cited source.
- Embedding the Phase 6 figures.

**Out of scope**
- New experiments or metrics; if the writeup reveals a gap, it goes back to the relevant phase, it
  is not papered over in prose.

## 4. Requirements

- **P7-R1** The post follows the structure: (1) the setup most people get wrong / the confabulation
  problem; (2) how to actually know (ground truth, exact-match, Rouge-L); (3) the experiment and
  the repo link; (4) what leaked (heatmap, by-prompt-type); (5) real vs hallucinated (side-by-side
  and self-agreement, the strongest section); (6) do defenses help (bars and the evasion example);
  (7) what it means (prompts are not vaults, as a practical rule); (8) a forward line to Post 2.
- **P7-R2** Every claim is backed by either our own numbers or a cited source. Each attack
  technique is cited to its origin.
- **P7-R3** No em-dashes anywhere. No buzzwords or marketing language.
- **P7-R4** Numbers in the post match `results.json`; figures are the Phase 6 outputs, unedited.
- **P7-R5** The practical conclusion states plainly what should never go in a system prompt and
  why.

## 5. Deliverables

| File | Work |
|------|------|
| `blog/outline.md` | Already scaffolded; the author fills the prose |
| The post draft (location per author) | Written following P7-R1 to P7-R5 |

## 6. Acceptance criteria

- **P7-A1** A complete draft exists covering all eight sections, with the Phase 6 figures embedded.
- **P7-A2** Every quantitative claim traces to a value in `results.json`; every technique is cited.
- **P7-A3** No em-dashes and no buzzwords (a mechanical check passes).

## 7. Review plan

- research-integrity-reviewer reads the draft against the data before publish: re-derives at least
  one reported number from `results.json`, confirms no overstated claim, confirms the self-
  agreement result is described correctly and not as more than it is.

## 8. Risks and open questions

- Temptation to overstate the self-agreement result; describe its strength exactly as the
  correlation shows, weak or strong.
- Keep scope framing intact in the post: we attacked our own prompts; that is the method, not a
  caveat.

## 9. Definition of done

- [ ] P7-A1, P7-A2, P7-A3 pass.
- [ ] research-integrity-reviewer signs off that no claim outruns the evidence.

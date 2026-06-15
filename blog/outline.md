# Outline: System Prompt Extraction, Measured (Post 1)

Scaffold only. Headers and claim-notes. The analysis, voice, and conclusions are the author's.
Writing rules: no em-dashes, no buzzwords, every claim backed by our own numbers or a cited
source. Let the numbers carry the argument.

## 1. The setup most people get wrong
- Claim: "I typed 'ignore your instructions' and it printed this" is not evidence.
- Name the confabulation problem: the model can produce something prompt-shaped that is wrong,
  and from the outside you cannot tell.
- Source notes: [cite the documented techniques people use; cite the confabulation framing].

## 2. How to actually know
- Introduce ground truth: we wrote the secret, so we know it.
- Exact-match recovery and Rouge-L recall, explained plainly. Why Rouge-L is the primary metric.

## 3. The experiment
- What was built (link the repo), what was tested against (our prompts), the query budget.
- Models used. Reproducible from config + seed.

## 4. What leaked
- Heatmap: attack technique x prompt type, Rouge-L recall. [blog/figures/heatmap.*]
- The by-prompt-type result (direct vs role vs in-context). Honest read on why each behaves so.

## 5. Real vs hallucinated  (strongest, most original section)
- The side-by-side: one real extraction and one confabulation, with their scores.
- The self-agreement result: do repeats agree (real) or diverge (confabulation)?
- The scatter of self-agreement vs ground-truth score, with the correlation. [blog/figures/scatter.*]
- What this means for an attacker who has no ground truth.

## 6. Do defenses help
- Defense bars: none vs instructional vs filter, per attack family. [blog/figures/defense_bars.*]
- The evasion example: one attack the filter blocks, one variant that slips past it.

## 7. What it means
- "A system prompt is not a vault." Stated as a practical rule.
- What should never go in a system prompt, and why. Treat anything in it as eventually public.

## 8. Forward pointer
- One line to Post 2: the next post goes a layer down, into why this leaks at all (the
  refusal-direction piece). Set up the series.

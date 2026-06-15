# prompt-extraction-lab

A measured study of **system prompt extraction**. The point is not the attacks (they are all
published, documented techniques) but the **measurement**: we attack only system prompts we
wrote ourselves, so we know the ground truth and can tell a genuine leak from a confident
model confabulation.

## What this is, and is not

**Is:** a test harness that runs known extraction queries against system prompts we authored,
scores each response against the known true prompt, and quantifies how much actually leaked.
Because we control the secret, every number is checkable.

**Is not:** an attack on anyone else's confidential or deployed prompt. We never target a third
party. This is not a constraint we route around; it is the method. Attacking a prompt you cannot
verify is exactly what makes most public extraction content unreliable, because the attacker
cannot tell a real recovery from a plausible hallucination.

## The claims the harness must support

1. Known, simple extraction queries recover a controlled system prompt at high rates under a
   small query budget.
2. Extractability varies by prompt structure (direct vs role vs in-context).
3. Models produce confident, plausible, but **wrong** "extractions"; without ground truth you
   cannot tell those from real ones. We show this directly because we have ground truth.
4. A naive text-filter defense reduces measured leakage but is evadable; an instructional
   defense barely helps.
5. Practical conclusion: a system prompt is not a vault. Treat anything in it as eventually public.

## Quickstart

```bash
# 1. Install (Python >=3.10)
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # add ",openai" for the optional second backend

# 2. Configure secrets
cp .env.example .env             # then fill in ANTHROPIC_API_KEY

# 3. Smoke test: one prompt, one query, one model
python -m src.experiment.run --smoke

# 4. Run the test suite (the metrics are the core and are tested)
make test
```

See `make help` for the full set of commands.

## Layout

```
src/
  target/      the app we control + the ground-truth prompts + defenses
  providers/   pluggable model backends (Anthropic, optional OpenAI)
  attacks/     library of cited extraction queries + the runner
  scoring/     normalization, metrics, and the ground-truth / self-agreement verifier
  experiment/  config loading, full-matrix orchestration, aggregation
  viz/         figure generation for the writeup
data/results/  scored results (committed)
data/transcripts/  raw responses (gitignored)
blog/          the writeup outline and exported figures
tests/         tests for the metrics and verifier
```

The full build spec is in [`dev-notes/PLAN.md`](dev-notes/PLAN.md).

## License

MIT. See [LICENSE](LICENSE).

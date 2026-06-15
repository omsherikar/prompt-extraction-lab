"""Tests for the attack runner in `src/attacks/runner.py`.

These tests pin the runner's contract without touching the network or a real API key:
a `FakeProvider` returns deterministic canned text, and a real `TargetApp` is built from
a real `TargetPrompt` plus that fake provider. They assert the returned `AttackRun` list,
the persisted JSONL transcript (location, line count, and per-record metadata), that the
captured responses are the fake provider's outputs (proving the app was actually queried),
and that the runner does no scoring (no metric fields leak into the transcript).

Transcripts are written under `tmp_path`; the real `data/transcripts/` is never touched.
"""

from __future__ import annotations

import json

from src.attacks.queries import Attack
from src.attacks.runner import AttackRun, run_attacks
from src.providers.base import Provider
from src.target.app import TargetApp
from src.target.prompts import PROMPTS

# Metadata fields every transcript record must carry. The runner is pre-scoring, so this is
# also the *complete* set: anything beyond it (e.g. a metric) would be a scoring leak.
REQUIRED_FIELDS = {
    "prompt_id",
    "prompt_type",
    "model_id",
    "attack_id",
    "family",
    "repeat",
    "response",
}

# Fields that would only exist if the runner had (wrongly) scored the response.
SCORING_FIELDS = {"rouge", "rouge_l", "exact", "exact_match", "leaked", "score"}

FAKE_MODEL_ID = "fake-model-v1"


class FakeProvider(Provider):
    """A deterministic, offline provider. Echoes the user message so each response is unique
    and recoverable, and records every (system, user) call for assertions."""

    def __init__(self, model_id: str = FAKE_MODEL_ID, temperature: float = 0.0) -> None:
        super().__init__(model_id, temperature)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_message: str) -> str:
        self.calls.append((system_prompt, user_message))
        return f"ECHO::{user_message}"


def _build_app() -> TargetApp:
    prompt = PROMPTS["direct_acme_billing"]
    return TargetApp(prompt=prompt, provider=FakeProvider())


def _attacks() -> list[Attack]:
    return [
        Attack(id="a1", family="direct", template="t-one", source="src"),
        Attack(id="a2", family="ignore_reveal", template="t-two", source="src"),
        Attack(id="a3", family="repetition", template="t-three", source="src"),
    ]


def _transcript_path(transcripts_dir, app: TargetApp):
    """The single .jsonl file the runner should have written under transcripts_dir."""
    files = list(transcripts_dir.glob("*.jsonl"))
    assert len(files) == 1, f"expected exactly one transcript, found {files}"
    return files[0]


def test_returns_one_run_per_attack_per_repeat(tmp_path) -> None:
    app = _build_app()
    attacks = _attacks()
    repeat = 4

    runs = run_attacks(app, attacks, repeat, transcripts_dir=str(tmp_path))

    assert isinstance(runs, list)
    assert len(runs) == len(attacks) * repeat
    assert all(isinstance(r, AttackRun) for r in runs)


def test_repeat_indices_and_attack_ids(tmp_path) -> None:
    app = _build_app()
    attacks = _attacks()
    repeat = 3

    runs = run_attacks(app, attacks, repeat, transcripts_dir=str(tmp_path))

    # Each attack id appears exactly `repeat` times, with repeat indices 0..repeat-1.
    for attack in attacks:
        idxs = sorted(r.repeat for r in runs if r.attack_id == attack.id)
        assert idxs == list(range(repeat)), f"bad repeat indices for {attack.id}: {idxs}"


def test_responses_are_fake_provider_outputs(tmp_path) -> None:
    app = _build_app()
    attacks = _attacks()

    runs = run_attacks(app, attacks, repeat=2, transcripts_dir=str(tmp_path))

    by_id = {a.id: a for a in attacks}
    for run in runs:
        expected = f"ECHO::{by_id[run.attack_id].template}"
        assert run.response == expected
    # The fake provider was actually invoked once per (attack, repeat), under the real
    # system prompt, proving the app (not the runner) produced the responses.
    assert app.provider.calls
    assert len(app.provider.calls) == len(attacks) * 2
    assert all(sys_prompt == app.prompt.text for sys_prompt, _ in app.provider.calls)


def test_transcript_written_with_one_line_per_record(tmp_path) -> None:
    app = _build_app()
    attacks = _attacks()
    repeat = 2

    run_attacks(app, attacks, repeat, transcripts_dir=str(tmp_path))

    path = _transcript_path(tmp_path, app)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(attacks) * repeat
    # Every line is a standalone JSON object (true JSONL, not a JSON array).
    for line in lines:
        assert isinstance(json.loads(line), dict)


def test_transcript_path_keyed_by_model_and_prompt(tmp_path) -> None:
    app = _build_app()

    run_attacks(app, _attacks(), repeat=1, transcripts_dir=str(tmp_path))

    path = _transcript_path(tmp_path, app)
    assert app.provider.model_id in path.name
    assert app.prompt.id in path.name
    assert path.suffix == ".jsonl"


def test_transcript_records_carry_required_metadata(tmp_path) -> None:
    app = _build_app()
    attacks = _attacks()
    repeat = 2

    run_attacks(app, attacks, repeat, transcripts_dir=str(tmp_path))

    path = _transcript_path(tmp_path, app)
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    by_id = {a.id: a for a in attacks}

    for rec in records:
        assert REQUIRED_FIELDS <= set(rec), f"missing fields in {rec}"
        assert rec["prompt_id"] == app.prompt.id
        assert rec["prompt_type"] == app.prompt.type
        assert rec["model_id"] == app.provider.model_id
        assert rec["attack_id"] in by_id
        assert rec["family"] == by_id[rec["attack_id"]].family
        assert 0 <= rec["repeat"] < repeat
        assert rec["response"] == f"ECHO::{by_id[rec['attack_id']].template}"


def test_runner_does_no_scoring(tmp_path) -> None:
    app = _build_app()

    run_attacks(app, _attacks(), repeat=2, transcripts_dir=str(tmp_path))

    path = _transcript_path(tmp_path, app)
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    for rec in records:
        # The transcript must hold exactly the raw metadata: no metric fields, and nothing
        # beyond the documented record shape.
        assert not (SCORING_FIELDS & set(rec)), f"scoring field leaked into {rec}"
        assert set(rec) == REQUIRED_FIELDS, f"unexpected fields in {rec}: {set(rec)}"


def test_creates_missing_transcripts_dir(tmp_path) -> None:
    app = _build_app()
    nested = tmp_path / "deep" / "nested" / "transcripts"
    assert not nested.exists()

    run_attacks(app, _attacks(), repeat=1, transcripts_dir=str(nested))

    assert nested.is_dir()
    assert list(nested.glob("*.jsonl"))


def test_filename_is_sanitized(tmp_path) -> None:
    # A model id containing a path separator must not escape transcripts_dir or create
    # subdirectories; it should be sanitized into a flat, safe filename.
    prompt = PROMPTS["direct_acme_billing"]
    app = TargetApp(prompt=prompt, provider=FakeProvider(model_id="vendor/family:1.0"))

    run_attacks(app, _attacks(), repeat=1, transcripts_dir=str(tmp_path))

    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1
    # No path separators survived into the on-disk name.
    assert "/" not in files[0].name
    # The file sits directly in transcripts_dir (no accidental subdir from the '/').
    assert files[0].parent == tmp_path

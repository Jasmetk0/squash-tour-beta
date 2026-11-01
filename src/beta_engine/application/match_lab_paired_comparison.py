"""Read-only, reproducible two-scenario comparison for the real Match Test Lab.

This service compares two *isolated* MatchLab scenarios (inline or pinned Saved
Lab sessions). A shared seed is a common initial RNG state, NOT a guarantee
that the same draw sequence remains aligned after an input-dependent branch.
No Run, sporting, Lab session, or historical state is mutated.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.application.match_test_lab_service import (
    MatchLabRequest,
    MatchLabScenario,
    MatchLabSeedResult,
    MatchTestLabService,
)

COMPARISON_SCHEMA = "match_lab_paired_comparison.v1"
MAX_COMPARISON_SEEDS = 12


def _fingerprint(value: object) -> str:
    rendered = json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


class MatchLabComparisonSource(BaseModel):
    """Exactly one inline scenario OR one pinned persisted Session."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    scenario: MatchLabScenario | None = None
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    expected_session_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )

    @model_validator(mode="after")
    def require_pinned_source(self):
        if (self.scenario is None) == (self.session_id is None):
            raise ValueError("Exactly one of scenario or session_id is required")
        if (self.session_id is None) != (self.expected_session_fingerprint is None):
            raise ValueError("Saved Session source requires exact expected_session_fingerprint")
        return self


class MatchLabComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    baseline: MatchLabComparisonSource
    candidate: MatchLabComparisonSource
    batch_seeds: tuple[int, ...]

    @model_validator(mode="after")
    def validate_seeds(self):
        if not 1 <= len(self.batch_seeds) <= MAX_COMPARISON_SEEDS:
            raise ValueError(f"Comparison requires 1 to {MAX_COMPARISON_SEEDS} exact seeds")
        if any(type(seed) is not int or not -(2**63) <= seed < 2**63
               for seed in self.batch_seeds):
            raise ValueError("Comparison seeds must be signed 64-bit integers")
        if len(self.batch_seeds) != len(set(self.batch_seeds)):
            raise ValueError("Comparison seeds cannot contain duplicates")
        return self


class MatchLabComparisonSourceEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    kind: Literal["inline", "saved_session"]
    scenario_id: str
    scenario_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    session_id: str | None = None
    session_fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    origin_kind: Literal["portable", "built_in_copy", "run_snapshot_copy"]
    origin_reference: str | None = None
    origin_fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class MatchLabPairedSeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    seed: int
    baseline: MatchLabSeedResult
    candidate: MatchLabSeedResult
    winner_changed: bool
    winner_player_id_before: str
    winner_player_id_after: str
    rally_count_delta: int
    elapsed_seconds_delta: float


class MatchLabComparisonSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    compared_seeds: int = Field(ge=1, le=MAX_COMPARISON_SEEDS)
    winner_flip_count: int = Field(ge=0)
    baseline_wins: dict[str, int]
    candidate_wins: dict[str, int]
    mean_rally_count_delta: float
    mean_elapsed_seconds_delta: float
    identical_full_result_fingerprints: int = Field(ge=0)


class MatchLabComparisonResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    schema_version: Literal["match_lab_paired_comparison.v1"] = COMPARISON_SCHEMA
    request_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    baseline_source: MatchLabComparisonSourceEvidence
    candidate_source: MatchLabComparisonSourceEvidence
    shared_match_id: str
    shared_player_a_id: str
    shared_player_b_id: str
    compared_seeds: tuple[int, ...]
    rows: tuple[MatchLabPairedSeed, ...]
    summary: MatchLabComparisonSummary
    isolated: Literal[True] = True
    mutations_performed: Literal[False] = False
    source_equivalence_proven: Literal[False] = False
    caveats: tuple[str, ...]


def _resolve(
    source: MatchLabComparisonSource,
    service: MatchTestLabService,
) -> tuple[MatchLabScenario, MatchLabComparisonSourceEvidence]:
    if source.scenario is not None:
        scenario, session_id, pinned = source.scenario, None, None
        kind = "inline"
    else:
        assert source.session_id is not None
        assert source.expected_session_fingerprint is not None
        session = service.get_session(source.session_id)
        if session.fingerprint != source.expected_session_fingerprint:
            raise ValueError("Match Lab Session changed since comparison was requested")
        scenario = session.scenario
        session_id, pinned, kind = session.session_id, session.fingerprint, "saved_session"

    evidence = MatchLabComparisonSourceEvidence(
        kind=kind, scenario_id=scenario.scenario_id,
        scenario_fingerprint=scenario.fingerprint,
        session_id=session_id, session_fingerprint=pinned,
        origin_kind=scenario.source_kind,
        origin_reference=scenario.source_reference,
        origin_fingerprint=scenario.source_fingerprint,
    )
    return scenario, evidence


def _compatible(baseline: MatchLabScenario, candidate: MatchLabScenario) -> None:
    """Reject comparison of distinct participants or rules as if controlled arms."""
    old, new = baseline.context, candidate.context
    if old.match_id != new.match_id:
        raise ValueError("Both scenarios must have the same match_id")
    if (
        old.player_a.player.player_id != new.player_a.player.player_id
        or old.player_b.player.player_id != new.player_b.player.player_id
    ):
        raise ValueError("Both scenarios must use identical player identities on the same sides")
    for field in ("best_of", "games_to", "win_by", "upset_variance"):
        if getattr(old, field) != getattr(new, field):
            raise ValueError(f"Paired comparison requires the same {field}")
    if old.retirement_rule != new.retirement_rule:
        raise ValueError("Paired comparison requires identical retirement rules")


def compare_match_lab_scenarios(
    service: MatchTestLabService,
    request: MatchLabComparisonRequest,
) -> MatchLabComparisonResult:
    """Execute the existing production MatchLab kernel twice; never write sessions."""
    baseline, baseline_source = _resolve(request.baseline, service)
    candidate, candidate_source = _resolve(request.candidate, service)
    _compatible(baseline, candidate)

    seeds = request.batch_seeds
    before = service.run(MatchLabRequest(scenario=baseline, batch_seeds=seeds))
    after = service.run(MatchLabRequest(scenario=candidate, batch_seeds=seeds))
    if (
        tuple(row.seed for row in before.results) != seeds
        or tuple(row.seed for row in after.results) != seeds
    ):
        raise ValueError("Match Lab returned misaligned seeds")
    rows = tuple(
        MatchLabPairedSeed(
            seed=seed,
            baseline=old, candidate=new,
            winner_changed=old.winner_player_id != new.winner_player_id,
            winner_player_id_before=old.winner_player_id,
            winner_player_id_after=new.winner_player_id,
            rally_count_delta=new.rally_count - old.rally_count,
            elapsed_seconds_delta=round(new.elapsed_seconds - old.elapsed_seconds, 6),
        )
        for seed, old, new in zip(seeds, before.results, after.results, strict=True)
    )
    count = len(rows)
    summary = MatchLabComparisonSummary(
        compared_seeds=count,
        winner_flip_count=sum(row.winner_changed for row in rows),
        baseline_wins=dict(sorted(Counter(row.baseline.winner_player_id for row in rows).items())),
        candidate_wins=dict(sorted(Counter(row.candidate.winner_player_id for row in rows).items())),
        mean_rally_count_delta=round(sum(row.rally_count_delta for row in rows) / count, 6),
        mean_elapsed_seconds_delta=round(sum(row.elapsed_seconds_delta for row in rows) / count, 6),
        identical_full_result_fingerprints=sum(
            row.baseline.result_fingerprint == row.candidate.result_fingerprint
            for row in rows
        ),
    )
    caveats = [
        "Each arm is a separate, read-only Match Lab simulation, not an authoritative Run match or Save.",
        "Same RNG seed does not guarantee identical downstream random draws if a change alters execution branches.",
        "Joint or multiple input changes cannot identify a single causal mechanic or establish empirical realism.",
        "Two pinned Lab Sessions are read as immutable snapshots for this call; there is no atomic cross-session lock.",
        "Historical source equivalence is not proven, even for copied players or matching source fingerprints.",
    ]
    for label, result in (("Baseline", before), ("Candidate", after)):
        caveats.extend(f"{label}: {warning}" for warning in result.compatibility.warnings)
    return MatchLabComparisonResult(
        request_fingerprint=_fingerprint(request.model_dump(mode="json")),
        baseline_source=baseline_source,
        candidate_source=candidate_source,
        shared_match_id=baseline.context.match_id,
        shared_player_a_id=baseline.context.player_a.player.player_id,
        shared_player_b_id=baseline.context.player_b.player.player_id,
        compared_seeds=seeds, rows=rows, summary=summary,
        caveats=tuple(caveats),
    )

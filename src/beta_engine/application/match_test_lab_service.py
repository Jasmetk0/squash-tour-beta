"""Global read-only Match Test Lab over the production MatchEngine kernel."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from statistics import mean
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches.match_engine import MatchEngine
from beta_engine.domain.matches.models import MatchContext, MatchResult


MATCH_LAB_SCHEMA_VERSION = "match_test_lab_scenario.v1"
MATCH_LAB_RESULT_VERSION = "match_test_lab_result.v1"
MATCH_LAB_ENGINE_VERSION = "match_engine_v10"
MAX_BATCH_SEEDS = 100


def _fingerprint(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


class MatchLabScenario(BaseModel):
    """Portable immutable scenario. It never owns or mutates a Run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["match_test_lab_scenario.v1"] = MATCH_LAB_SCHEMA_VERSION
    scenario_id: str = Field(min_length=1, max_length=160)
    context: MatchContext
    seed: int
    source_kind: Literal["portable", "built_in_copy", "run_snapshot_copy"] = "portable"
    source_reference: str | None = Field(default=None, max_length=500)
    source_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class MatchLabRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario: MatchLabScenario
    batch_seeds: tuple[int, ...] = ()

    @model_validator(mode="after")
    def validate_batch(self):
        if len(self.batch_seeds) > MAX_BATCH_SEEDS:
            raise ValueError(f"batch_seeds must contain at most {MAX_BATCH_SEEDS} seeds")
        if len(set(self.batch_seeds)) != len(self.batch_seeds):
            raise ValueError("batch_seeds must not contain duplicates")
        return self

    @property
    def effective_seeds(self) -> tuple[int, ...]:
        return self.batch_seeds or (self.scenario.seed,)


class MatchLabCompatibility(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    production_kernel: str
    match_engine_version: str
    portable: bool
    isolated: bool
    run_mutation_performed: bool
    run_live_link: bool
    normal_format: bool
    warnings: tuple[str, ...]


class MatchLabSeedResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    seed: int
    result_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    winner_player_id: str
    loser_player_id: str
    sets_won: dict[str, int]
    set_scores: tuple[str, ...]
    termination_reason: str
    rally_count: int = Field(ge=0)
    elapsed_seconds: float = Field(ge=0)


class MatchLabBatchDiagnostics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    seed_count: int = Field(ge=1)
    wins_by_player: dict[str, int]
    retirement_count: int = Field(ge=0)
    average_rally_count: float = Field(ge=0)
    average_elapsed_seconds: float = Field(ge=0)
    distinct_result_count: int = Field(ge=1)


class MatchLabResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["match_test_lab_result.v1"] = MATCH_LAB_RESULT_VERSION
    scenario_id: str
    scenario_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    compatibility: MatchLabCompatibility
    results: tuple[MatchLabSeedResult, ...]
    diagnostics: MatchLabBatchDiagnostics


class MatchTestLabService:
    """Runs portable scenarios without persistence using the real MatchEngine."""

    def run(self, request: MatchLabRequest) -> MatchLabResult:
        scenario = request.scenario
        seeds = request.effective_seeds
        rows = tuple(self._simulate(scenario.context, seed) for seed in seeds)
        normal_format = (
            scenario.context.best_of == 5
            and scenario.context.games_to == 11
            and scenario.context.win_by == 2
        )
        warnings: list[str] = []
        if not normal_format:
            warnings.append(
                "Scenario uses a non-standard match format; the shared kernel supports it, "
                "but normal FAX Run compatibility must be validated separately."
            )
        if scenario.source_kind == "run_snapshot_copy" and scenario.source_fingerprint is None:
            warnings.append(
                "Run snapshot copy has no source_fingerprint; it is isolated, but source equivalence cannot be proven."
            )

        wins = Counter(row.winner_player_id for row in rows)
        request_fingerprint = _fingerprint(request.model_dump(mode="json"))
        return MatchLabResult(
            scenario_id=scenario.scenario_id,
            scenario_fingerprint=scenario.fingerprint,
            request_fingerprint=request_fingerprint,
            compatibility=MatchLabCompatibility(
                production_kernel="beta_engine.domain.matches.match_engine.MatchEngine.simulate",
                match_engine_version=MATCH_LAB_ENGINE_VERSION,
                portable=True,
                isolated=True,
                run_mutation_performed=False,
                run_live_link=False,
                normal_format=normal_format,
                warnings=tuple(warnings),
            ),
            results=rows,
            diagnostics=MatchLabBatchDiagnostics(
                seed_count=len(rows),
                wins_by_player=dict(sorted(wins.items())),
                retirement_count=sum(row.termination_reason == "RETIREMENT" for row in rows),
                average_rally_count=round(mean(row.rally_count for row in rows), 3),
                average_elapsed_seconds=round(mean(row.elapsed_seconds for row in rows), 3),
                distinct_result_count=len({row.result_fingerprint for row in rows}),
            ),
        )

    @staticmethod
    def _simulate(context: MatchContext, seed: int) -> MatchLabSeedResult:
        result = MatchEngine(rng=DeterministicRng(seed)).simulate(context)
        payload = result.model_dump(mode="json")
        return MatchLabSeedResult(
            seed=seed,
            result_fingerprint=_fingerprint(payload),
            winner_player_id=result.winner_player_id,
            loser_player_id=result.loser_player_id,
            sets_won=dict(result.sets_won),
            set_scores=tuple(_set_score(result, item.set_number) for item in result.sets),
            termination_reason=result.termination_reason.value,
            rally_count=len(result.rally_log.events) if result.rally_log is not None else 0,
            elapsed_seconds=(
                result.timeline_log.total_elapsed_seconds
                if result.timeline_log is not None
                else 0.0
            ),
        )


def _set_score(result: MatchResult, set_number: int) -> str:
    item = result.sets[set_number - 1]
    if item.winner_player_id == result.player_a_id:
        return f"{item.winner_games}-{item.loser_games}"
    return f"{item.loser_games}-{item.winner_games}"

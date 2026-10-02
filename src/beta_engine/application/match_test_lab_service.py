"""Global read-only Match Test Lab over the production MatchEngine kernel."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from statistics import mean
from typing import Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches.match_engine import MatchEngine
from beta_engine.domain.matches.models import MatchContext, MatchParticipantContext, MatchResult
from beta_engine.domain.players import HiddenCareerTraits, Player
from beta_engine.domain.calendar.season_weeks import age_at_calendar_position, season_week_to_calendar_position
from beta_engine.domain.simulation_slots import (
    CanonicalMatchInputProjectionPolicy,
    project_player,
    projected_engine_player,
)
from beta_engine.infrastructure.db.initial_world_state import load_saved_initial_world
from beta_engine.infrastructure.db.player_sporting_state import load_saved_sporting_bundle
from beta_engine.infrastructure.db.models import MatchLabSessionModel
from beta_engine.application.run_saved_revision_history_service import RunSavedRevisionHistoryService


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



class BuiltInMatchLabScenario(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: str
    display_name: str
    description: str
    read_only: Literal[True] = True
    scenario_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    scenario: MatchLabScenario


class MatchLabParticipantImportEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    side: Literal["player_a", "player_b"]
    product_run_id: str
    branch_id: str
    saved_revision_id: str
    saved_revision_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    sporting_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    sporting_week_ordinal: int = Field(ge=0)
    player_id: str
    source_profile_fingerprint: str
    canonical_projection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class MatchLabSession(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["match_test_lab_session.v1"] = "match_test_lab_session.v1"
    session_id: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=160)
    version: int = Field(ge=1)
    scenario: MatchLabScenario
    participant_imports: tuple[MatchLabParticipantImportEvidence, ...] = ()

    @model_validator(mode="after")
    def unique_import_sides(self):
        sides = [item.side for item in self.participant_imports]
        if len(sides) != len(set(sides)):
            raise ValueError("Match Lab session has duplicate participant import evidence")
        return self

    @property
    def fingerprint(self) -> str:
        payload = {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "display_name": self.display_name,
            "version": self.version,
            "scenario": self.scenario.model_dump(mode="json"),
        }
        # Compatibility: V2 sessions without imports retain their exact historical fingerprint.
        if self.participant_imports:
            payload["participant_imports"] = [
                item.model_dump(mode="json") for item in self.participant_imports
            ]
        return _fingerprint(payload)

    @computed_field
    @property
    def session_fingerprint(self) -> str:
        return self.fingerprint


class MatchLabSessionCreateRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    display_name: str = Field(min_length=1, max_length=160)
    scenario: MatchLabScenario | None = None
    built_in_scenario_id: str | None = Field(default=None, min_length=1, max_length=160)

    @model_validator(mode="after")
    def exactly_one_source(self):
        if (self.scenario is None) == (self.built_in_scenario_id is None):
            raise ValueError("provide exactly one of scenario or built_in_scenario_id")
        return self


class MatchLabSessionUpdateRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_session_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    scenario: MatchLabScenario


class MatchLabSavedRevisionPlayerImportRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_session_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    product_run_id: str = Field(min_length=1, max_length=128)
    branch_id: str = Field(min_length=1, max_length=128)
    saved_revision_id: str = Field(min_length=1, max_length=128)
    player_id: str = Field(min_length=1, max_length=128)
    side: Literal["player_a", "player_b"]


class MatchLabSessionRunRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_session_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    batch_seeds: tuple[int, ...] = ()

    @model_validator(mode="after")
    def validate_batch(self):
        if len(self.batch_seeds) > MAX_BATCH_SEEDS:
            raise ValueError(f"batch_seeds must contain at most {MAX_BATCH_SEEDS} seeds")
        if len(set(self.batch_seeds)) != len(self.batch_seeds):
            raise ValueError("batch_seeds must not contain duplicates")
        return self


def _lab_player(player_id: str, base: int) -> Player:
    return Player(
        player_id=player_id,
        name=player_id,
        age=27,
        nationality="TST",
        technique=base,
        movement=base,
        physical=base,
        mental=base,
        consistency=base,
        clutch=base,
        recovery=base,
        play_style="tempo-controller",
        archetype="all-court tactician",
        hidden_career_traits=HiddenCareerTraits(
            potential_ceiling=90,
            growth_curve="balanced",
            professionalism=0.7,
            ambition=0.7,
            travel_tolerance=0.7,
            schedule_aggression=0.6,
            injury_proneness=0.2,
            resilience=0.8,
        ),
    )


def _built_in_scenarios() -> tuple[BuiltInMatchLabScenario, ...]:
    definitions = (
        (
            "standard-even-match",
            "Standard even match",
            "Two evenly rated players under the normal BO5-to-11-win-by-2 format.",
            84,
            84,
            777,
        ),
        (
            "standard-strength-gap",
            "Standard strength-gap match",
            "Normal match format with a visible ability gap for deterministic batch diagnostics.",
            90,
            70,
            2026,
        ),
    )
    rows = []
    for scenario_id, name, description, base_a, base_b, seed in definitions:
        baseline = MatchLabScenario(
            scenario_id=scenario_id,
            context=MatchContext(
                match_id=f"built-in:{scenario_id}",
                player_a=MatchParticipantContext(player=_lab_player(f"{scenario_id}:A", base_a)),
                player_b=MatchParticipantContext(player=_lab_player(f"{scenario_id}:B", base_b)),
            ),
            seed=seed,
            source_kind="portable",
        )
        rows.append(
            BuiltInMatchLabScenario(
                scenario_id=scenario_id,
                display_name=name,
                description=description,
                scenario_fingerprint=baseline.fingerprint,
                scenario=baseline,
            )
        )
    return tuple(rows)


BUILT_IN_MATCH_LAB_SCENARIOS = _built_in_scenarios()
BUILT_IN_MATCH_LAB_BY_ID = {row.scenario_id: row for row in BUILT_IN_MATCH_LAB_SCENARIOS}


class MatchTestLabService:
    """Runs portable scenarios and owns isolated editable Lab sessions."""

    def __init__(
        self,
        session_factory=None,
        id_factory: Callable[[str], str] | None = None,
        repository=None,
    ):
        self._session_factory = session_factory
        self._id_factory = id_factory
        self._repository = repository

    def list_built_in_scenarios(self) -> tuple[BuiltInMatchLabScenario, ...]:
        return BUILT_IN_MATCH_LAB_SCENARIOS

    def _require_persistence(self):
        if self._session_factory is None or self._id_factory is None:
            raise RuntimeError("Match Lab session persistence is not configured")

    @staticmethod
    def _load_session_row(row: MatchLabSessionModel) -> MatchLabSession:
        stored = MatchLabSession.model_validate_json(row.payload_json)
        if (
            stored.session_id != row.session_id
            or stored.display_name != row.display_name
            or stored.version != row.version
            or stored.fingerprint != row.fingerprint
            or stored.scenario.source_kind != row.source_kind
            or stored.scenario.source_reference != row.source_reference
            or stored.scenario.source_fingerprint != row.source_fingerprint
        ):
            raise ValueError("Match Lab session persistence fingerprint mismatch")
        return stored

    @staticmethod
    def _persist_session(session, item: MatchLabSession) -> None:
        row = session.get(MatchLabSessionModel, item.session_id)
        values = dict(
            display_name=item.display_name,
            version=item.version,
            fingerprint=item.fingerprint,
            source_kind=item.scenario.source_kind,
            source_reference=item.scenario.source_reference,
            source_fingerprint=item.scenario.source_fingerprint,
            payload_json=item.model_dump_json(exclude={"session_fingerprint"}),
        )
        if row is None:
            session.add(MatchLabSessionModel(session_id=item.session_id, **values))
        else:
            for key, value in values.items():
                setattr(row, key, value)
        session.flush()

    def list_sessions(self) -> tuple[MatchLabSession, ...]:
        self._require_persistence()
        from sqlalchemy import select

        with self._session_factory() as session:
            rows = session.scalars(
                select(MatchLabSessionModel).order_by(MatchLabSessionModel.display_name, MatchLabSessionModel.session_id)
            ).all()
            return tuple(self._load_session_row(row) for row in rows)

    def get_session(self, session_id: str) -> MatchLabSession:
        self._require_persistence()
        with self._session_factory() as session:
            row = session.get(MatchLabSessionModel, session_id)
            if row is None:
                raise KeyError("Match Lab session was not found")
            return self._load_session_row(row)

    def create_session(self, request: MatchLabSessionCreateRequest) -> MatchLabSession:
        self._require_persistence()
        from sqlalchemy import text

        if request.built_in_scenario_id is not None:
            built_in = BUILT_IN_MATCH_LAB_BY_ID.get(request.built_in_scenario_id)
            if built_in is None:
                raise KeyError("Built-in Match Lab scenario was not found")
            scenario = built_in.scenario.model_copy(
                update={
                    "scenario_id": f"session-copy:{built_in.scenario_id}",
                    "source_kind": "built_in_copy",
                    "source_reference": built_in.scenario_id,
                    "source_fingerprint": built_in.scenario_fingerprint,
                }
            )
        else:
            assert request.scenario is not None
            scenario = request.scenario

        session_id = self._id_factory("match-lab-session")
        item = MatchLabSession(
            session_id=session_id,
            display_name=request.display_name,
            version=1,
            scenario=scenario,
        )
        with self._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            if session.get(MatchLabSessionModel, session_id) is not None:
                raise ValueError("generated Match Lab session identity already exists")
            self._persist_session(session, item)
        return item

    def update_session(self, session_id: str, request: MatchLabSessionUpdateRequest) -> MatchLabSession:
        self._require_persistence()
        from sqlalchemy import text

        with self._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            row = session.get(MatchLabSessionModel, session_id)
            if row is None:
                raise KeyError("Match Lab session was not found")
            current = self._load_session_row(row)
            if current.fingerprint != request.expected_session_fingerprint:
                raise ValueError("Match Lab session changed since it was reviewed")
            updated = MatchLabSession(
                session_id=current.session_id,
                display_name=request.display_name or current.display_name,
                version=current.version + 1,
                scenario=request.scenario,
            )
            self._persist_session(session, updated)
            return updated

    def import_saved_revision_player(
        self,
        session_id: str,
        request: MatchLabSavedRevisionPlayerImportRequest,
    ) -> MatchLabSession:
        self._require_persistence()
        if self._repository is None:
            raise RuntimeError("Match Lab Saved Revision import is not configured")

        history = RunSavedRevisionHistoryService(self._repository)
        detail = history.get_revision(
            run_id=request.product_run_id,
            branch_id=request.branch_id,
            revision_id=request.saved_revision_id,
        )
        revision = detail.saved_revision
        world = load_saved_initial_world(
            revision.payload,
            run_id=request.product_run_id,
            branch_id=request.branch_id,
        )
        sporting_bundle = load_saved_sporting_bundle(
            revision.payload,
            run_id=request.product_run_id,
            branch_id=request.branch_id,
        )
        if world is None:
            raise ValueError("Saved Revision has no validated Initial World")
        if sporting_bundle is None or not sporting_bundle[0]:
            raise ValueError("Saved Revision has no validated player sporting state")

        sporting = sporting_bundle[0][-1]
        profile = next((item for item in world.players if item.player_id == request.player_id), None)
        record = next((item for item in sporting.players if item.player_id == request.player_id), None)
        if profile is None:
            raise ValueError(
                "Saved Revision player is not present in its Initial World; prospect-profile import is not supported by this slice"
            )
        if record is None:
            raise ValueError("Saved Revision player has no sporting record at the saved sporting head")

        season_start_year = 2000 + sporting.week.season_index
        position = season_week_to_calendar_position(season_start_year, sporting.week.week)
        age = age_at_calendar_position(
            birth_year=profile.birth_year,
            birth_year_week=profile.birth_year_week,
            calendar_year=position.calendar_year,
            year_week=position.year_week,
        )
        projection = project_player(
            record,
            source_sporting_fingerprint=sporting.fingerprint,
            policy=CanonicalMatchInputProjectionPolicy(),
            profile_source_fingerprint=profile.source_generation_fingerprint,
            profile_provenance="validated Saved Revision Initial World + player sporting state",
            age=age,
            name=profile.name,
            nationality=profile.nationality,
            play_style=profile.play_style,
            archetype=profile.archetype,
            hidden_career_traits=profile.hidden_career_traits,
        )
        participant = MatchParticipantContext(
            player=projected_engine_player(projection),
            form_modifier=projection.form_modifier,
            sharpness_modifier=projection.sharpness_modifier,
            fatigue_modifier=projection.fatigue_modifier,
        )
        evidence = MatchLabParticipantImportEvidence(
            side=request.side,
            product_run_id=request.product_run_id,
            branch_id=request.branch_id,
            saved_revision_id=request.saved_revision_id,
            saved_revision_content_hash=revision.content_hash,
            sporting_state_fingerprint=sporting.fingerprint,
            sporting_week_ordinal=sporting.week.ordinal,
            player_id=request.player_id,
            source_profile_fingerprint=profile.source_generation_fingerprint,
            canonical_projection_fingerprint=projection.fingerprint,
        )

        from sqlalchemy import text
        with self._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            row = session.get(MatchLabSessionModel, session_id)
            if row is None:
                raise KeyError("Match Lab session was not found")
            current = self._load_session_row(row)
            if current.fingerprint != request.expected_session_fingerprint:
                raise ValueError("Match Lab session changed since it was reviewed")

            context_update = {request.side: participant}
            scenario = current.scenario.model_copy(
                update={"context": current.scenario.context.model_copy(update=context_update)}
            )
            existing = {
                item.side: item for item in current.participant_imports
            }
            existing[request.side] = evidence
            updated = MatchLabSession(
                session_id=current.session_id,
                display_name=current.display_name,
                version=current.version + 1,
                scenario=scenario,
                participant_imports=tuple(existing[key] for key in sorted(existing)),
            )
            self._persist_session(session, updated)
            return updated

    def run_session(self, session_id: str, request: MatchLabSessionRunRequest) -> MatchLabResult:
        current = self.get_session(session_id)
        if current.fingerprint != request.expected_session_fingerprint:
            raise ValueError("Match Lab session changed since it was reviewed")
        return self.run(MatchLabRequest(scenario=current.scenario, batch_seeds=request.batch_seeds))

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

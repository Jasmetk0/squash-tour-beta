"""Global isolated Tournament Test Lab over shared tournament draw and Match Engine kernels."""

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
from beta_engine.domain.calendar.season_weeks import age_at_calendar_position, season_week_to_calendar_position
from beta_engine.domain.simulation_slots import (
    CanonicalMatchInputProjectionPolicy,
    project_player,
    projected_engine_player,
)
from beta_engine.domain.tournaments.draw_authority import (
    TournamentDrawAuthority,
    TournamentDrawAuthorityBuilder,
    TournamentDrawBracket,
)
from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthority,
    canonical_classic_seed_count,
    canonical_qualification_seed_count,
)
from beta_engine.domain.tournaments.entry_field import (
    TournamentEntryField,
    TournamentEntryFieldCapacity,
)
from beta_engine.domain.tournaments.format_authority import (
    TournamentFormatAuthority,
    TournamentGroupCrossingMatch,
    TournamentGroupFormatConfiguration,
    TournamentGroupRulesPolicy,
    TournamentGroupSeedPlacement,
)
from beta_engine.domain.tournaments.group_match_schedule_authority import (
    TournamentGroupMatchScheduleAuthority,
    TournamentGroupMatchScheduleBuilder,
)
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupStandingsAuthority,
    TournamentGroupStandingsBuilder,
    TournamentGroupStandingsUnresolvedTie,
    TournamentGroupStandingsUnsupportedResult,
)
from beta_engine.domain.tournaments.hybrid_knockout_bracket_authority import (
    TournamentHybridKnockoutBracketAuthority,
    TournamentHybridKnockoutBracketBuilder,
)
from beta_engine.domain.tournaments.hybrid_knockout_entrants_authority import (
    TournamentHybridKnockoutEntrantsAuthority,
    TournamentHybridKnockoutEntrantsBuilder,
)
from beta_engine.domain.tournaments.topology_authority import (
    TournamentTopologyAuthority,
    TournamentTopologyAuthorityBuilder,
)
from beta_engine.infrastructure.db.models import TournamentLabSessionModel
from beta_engine.application.run_saved_revision_history_service import RunSavedRevisionHistoryService
from beta_engine.infrastructure.db import (
    SavedRevisionHistoryConflictError,
    SavedRevisionHistoryNotFoundError,
)
from beta_engine.infrastructure.db.initial_world_state import load_saved_initial_world
from beta_engine.infrastructure.db.player_sporting_state import load_saved_sporting_bundle
from beta_engine.infrastructure.db.simulation_slot_state import load_saved_simulation_slot_component


TOURNAMENT_LAB_SCENARIO_VERSION = "tournament_test_lab_scenario.v1"
TOURNAMENT_LAB_RESULT_VERSION = "tournament_test_lab_result.v1"
MAX_BATCH_SEEDS = 100


def _fingerprint(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


class TournamentLabMatchFormat(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    best_of: int = Field(default=5, ge=1)
    games_to: int = Field(default=11, ge=1)
    win_by: int = Field(default=2, ge=1)
    upset_variance: float = Field(default=0.12, ge=0.0, le=0.35)

    @model_validator(mode="after")
    def odd_best_of(self):
        if self.best_of % 2 == 0:
            raise ValueError("Tournament Lab best_of must be odd")
        return self


class TournamentLabAssertions(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_champion_player_id: str | None = None
    expected_played_match_count: int | None = Field(default=None, ge=0)


class TournamentLabRunSnapshotEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    product_run_id: str = Field(min_length=1, max_length=128)
    branch_id: str = Field(min_length=1, max_length=128)
    saved_revision_id: str = Field(min_length=1, max_length=128)
    saved_revision_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_id: str = Field(min_length=1, max_length=160)
    entry_field_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    format_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    draw_input_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    topology_authority_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    sporting_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    sporting_week_ordinal: int = Field(ge=0)
    participant_projection_fingerprints: tuple[str, ...]

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class TournamentLabScenario(BaseModel):
    """Portable Tournament Lab draft; validation diagnostics decide whether it can execute."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["tournament_test_lab_scenario.v1"] = TOURNAMENT_LAB_SCENARIO_VERSION
    scenario_id: str = Field(min_length=1, max_length=160)
    display_name: str = Field(min_length=1, max_length=160)
    format_kind: str = Field(min_length=1, max_length=80)
    participants: tuple[MatchParticipantContext, ...] = Field(min_length=2, max_length=128)
    main_draw_size: int = Field(ge=2, le=128)
    group_count: int = Field(default=0, ge=0, le=64, exclude_if=lambda value: value == 0)
    group_size: int = Field(default=0, ge=0, le=128, exclude_if=lambda value: value == 0)
    seeded_slots_per_group: int = Field(default=0, ge=0, le=128, exclude_if=lambda value: value == 0)
    group_seed_placements: tuple[TournamentGroupSeedPlacement, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    group_match_best_of: Literal[3, 5] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    advancing_per_group: int = Field(default=0, ge=0, le=128, exclude_if=lambda value: value == 0)
    knockout_crossings: tuple[TournamentGroupCrossingMatch, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    topology_seed: int | None = Field(default=None, exclude_if=lambda value: value is None)
    qualification_draw_size: int = Field(default=0, ge=0, le=128, exclude_if=lambda value: value == 0)
    qualifier_spots: int = Field(default=0, ge=0, le=128, exclude_if=lambda value: value == 0)
    qualification_player_ids: tuple[str, ...] = Field(default=(), exclude_if=lambda value: not value)
    seed_order_player_ids: tuple[str, ...] = ()
    draw_seed: int
    match_seed: int
    match_format: TournamentLabMatchFormat = TournamentLabMatchFormat()
    stop_after_round: int | None = Field(default=None, ge=1, le=7)
    assertions: TournamentLabAssertions = TournamentLabAssertions()
    source_kind: Literal["portable", "built_in_copy", "run_snapshot_copy"] = "portable"
    source_reference: str | None = Field(default=None, max_length=500)
    source_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    source_snapshot: TournamentLabRunSnapshotEvidence | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def validate_source_snapshot_binding(self):
        if self.source_snapshot is None:
            return self
        if self.source_kind != "run_snapshot_copy":
            raise ValueError("Tournament Lab source snapshot requires run_snapshot_copy source kind")
        if self.source_fingerprint != self.source_snapshot.fingerprint:
            raise ValueError("Tournament Lab source snapshot fingerprint does not match source_fingerprint")
        return self

    @model_validator(mode="after")
    def participant_ids_are_unique(self):
        ids = [item.player.player_id for item in self.participants]
        if len(ids) != len(set(ids)):
            raise ValueError("Tournament Lab participants require unique player IDs")
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class TournamentLabRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario: TournamentLabScenario
    batch_match_seeds: tuple[int, ...] = ()

    @model_validator(mode="after")
    def validate_batch(self):
        if len(self.batch_match_seeds) > MAX_BATCH_SEEDS:
            raise ValueError(
                f"batch_match_seeds must contain at most {MAX_BATCH_SEEDS} seeds"
            )
        if len(set(self.batch_match_seeds)) != len(self.batch_match_seeds):
            raise ValueError("batch_match_seeds must not contain duplicates")
        return self

    @property
    def effective_match_seeds(self) -> tuple[int, ...]:
        return self.batch_match_seeds or (self.scenario.match_seed,)


class TournamentLabIssue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    severity: Literal["warning", "error"]
    code: str
    message: str


class TournamentLabCompatibility(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    runnable_in_lab: bool
    normal_run_compatible: bool
    isolated: Literal[True] = True
    run_mutation_performed: Literal[False] = False
    run_live_link: Literal[False] = False
    shared_authorities: tuple[str, ...]
    issues: tuple[TournamentLabIssue, ...]


class TournamentLabMatchResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str
    round_number: int = Field(ge=1)
    round_sequence: int = Field(ge=1)
    player_a_id: str | None
    player_b_id: str | None
    winner_player_id: str | None
    loser_player_id: str | None
    status: Literal["played", "bye_advance", "empty_advance"]
    match_seed: int | None = None
    result_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    set_scores: tuple[str, ...] = ()
    rally_count: int = Field(default=0, ge=0)
    elapsed_seconds: float = Field(default=0.0, ge=0)


class TournamentLabQualificationSectionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    section_id: str
    bracket_size: int = Field(ge=2)
    winner_player_id: str | None
    played_match_count: int = Field(ge=0)
    bye_advance_count: int = Field(ge=0)
    match_results: tuple[TournamentLabMatchResult, ...]


class TournamentLabGroupStageResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    topology_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    schedule_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    match_day_count: int = Field(ge=1)
    match_results: tuple[TournamentLabMatchResult, ...]
    standings: TournamentGroupStandingsAuthority | None = None
    blocking_issue: TournamentLabIssue | None = None


class TournamentLabAssertionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    assertion: str
    status: Literal["passed", "failed", "not_evaluated"]
    expected: str
    actual: str | None


class TournamentLabSingleRun(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    match_seed: int
    completed_rounds: int = Field(ge=0)
    tournament_complete: bool
    champion_player_id: str | None
    played_match_count: int = Field(ge=0)
    bye_advance_count: int = Field(ge=0)
    qualification_results: tuple[TournamentLabQualificationSectionResult, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    group_stage: TournamentLabGroupStageResult | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    hybrid_knockout_bracket: TournamentHybridKnockoutBracketAuthority | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    match_results: tuple[TournamentLabMatchResult, ...]
    assertions: tuple[TournamentLabAssertionResult, ...]
    run_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class TournamentLabBatchDiagnostics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_count: int = Field(ge=0)
    completed_run_count: int = Field(ge=0)
    champions: dict[str, int]
    assertion_failure_count: int = Field(ge=0)
    average_played_match_count: float = Field(ge=0)


class TournamentLabResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["tournament_test_lab_result.v1"] = TOURNAMENT_LAB_RESULT_VERSION
    scenario_id: str
    scenario_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    compatibility: TournamentLabCompatibility
    format_authority_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    draw_input_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    draw_authority_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    topology_authority_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    group_schedule_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    draw: TournamentDrawAuthority | None = None
    topology: TournamentTopologyAuthority | None = None
    group_schedule: TournamentGroupMatchScheduleAuthority | None = None
    runs: tuple[TournamentLabSingleRun, ...] = ()
    diagnostics: TournamentLabBatchDiagnostics


class BuiltInTournamentLabScenario(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: str
    display_name: str
    description: str
    read_only: Literal[True] = True
    scenario_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    scenario: TournamentLabScenario


class TournamentLabSession(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["tournament_test_lab_session.v1"] = "tournament_test_lab_session.v1"
    session_id: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=160)
    version: int = Field(ge=1)
    scenario: TournamentLabScenario

    @property
    def fingerprint(self) -> str:
        return _fingerprint(
            {
                "schema_version": self.schema_version,
                "session_id": self.session_id,
                "display_name": self.display_name,
                "version": self.version,
                "scenario": self.scenario.model_dump(mode="json"),
            }
        )

    @computed_field
    @property
    def session_fingerprint(self) -> str:
        return self.fingerprint


class TournamentLabSessionCreateRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    display_name: str = Field(min_length=1, max_length=160)
    scenario: TournamentLabScenario | None = None
    built_in_scenario_id: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def exactly_one_source(self):
        if (self.scenario is None) == (self.built_in_scenario_id is None):
            raise ValueError("Provide exactly one of scenario or built_in_scenario_id")
        return self


class TournamentLabSavedRevisionCopyRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    display_name: str = Field(min_length=1, max_length=160)
    product_run_id: str = Field(min_length=1, max_length=128)
    branch_id: str = Field(min_length=1, max_length=128)
    saved_revision_id: str = Field(min_length=1, max_length=128)
    event_id: str = Field(min_length=1, max_length=160)


class TournamentLabSessionUpdateRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_session_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    scenario: TournamentLabScenario


class TournamentLabSessionExport(BaseModel):
    """Portable reviewed export envelope for one isolated Tournament Lab session."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def accept_api_serialized_session(cls, value):
        if isinstance(value, dict):
            session = value.get("session")
            if isinstance(session, dict) and "session_fingerprint" in session:
                value = dict(value)
                session = dict(session)
                session.pop("session_fingerprint", None)
                value["session"] = session
        return value

    schema_version: Literal["tournament_test_lab_session_export.v1"] = (
        "tournament_test_lab_session_export.v1"
    )
    session: TournamentLabSession
    session_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    scenario_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    export_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @staticmethod
    def fingerprint_payload(
        session: TournamentLabSession,
        *,
        session_fingerprint: str,
        scenario_fingerprint: str,
    ) -> dict[str, object]:
        return {
            "schema_version": "tournament_test_lab_session_export.v1",
            "session": session.model_dump(mode="json"),
            "session_fingerprint": session_fingerprint,
            "scenario_fingerprint": scenario_fingerprint,
        }

    @model_validator(mode="after")
    def validate_integrity(self):
        if self.session.fingerprint != self.session_fingerprint:
            raise ValueError("Tournament Lab export session fingerprint mismatch")
        if self.session.scenario.fingerprint != self.scenario_fingerprint:
            raise ValueError("Tournament Lab export scenario fingerprint mismatch")
        expected = _fingerprint(
            self.fingerprint_payload(
                self.session,
                session_fingerprint=self.session_fingerprint,
                scenario_fingerprint=self.scenario_fingerprint,
            )
        )
        if expected != self.export_fingerprint:
            raise ValueError("Tournament Lab export envelope fingerprint mismatch")
        return self


class TournamentLabSessionImportRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    export_payload: TournamentLabSessionExport
    expected_export_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    display_name: str | None = Field(default=None, min_length=1, max_length=160)


class TournamentLabSessionRunRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_session_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    batch_match_seeds: tuple[int, ...] = ()

    @model_validator(mode="after")
    def validate_batch(self):
        if len(self.batch_match_seeds) > MAX_BATCH_SEEDS:
            raise ValueError(
                f"batch_match_seeds must contain at most {MAX_BATCH_SEEDS} seeds"
            )
        if len(set(self.batch_match_seeds)) != len(self.batch_match_seeds):
            raise ValueError("batch_match_seeds must not contain duplicates")
        return self


class TournamentTestLabService:
    """Portable Tournament Lab using existing domain draw authority and production MatchEngine."""

    def __init__(
        self,
        session_factory=None,
        id_factory: Callable[[str], str] | None = None,
        repository=None,
    ):
        self._session_factory = session_factory
        self._id_factory = id_factory
        self._repository = repository

    def _require_persistence(self) -> None:
        if self._session_factory is None or self._id_factory is None:
            raise RuntimeError("Tournament Lab session persistence is not configured")

    @staticmethod
    def _load_session_row(row: TournamentLabSessionModel) -> TournamentLabSession:
        item = TournamentLabSession.model_validate_json(row.payload_json)
        if item.session_id != row.session_id:
            raise ValueError("Tournament Lab session persistence identity mismatch")
        if item.display_name != row.display_name or item.version != row.version:
            raise ValueError("Tournament Lab session persistence metadata mismatch")
        if item.scenario.source_kind != row.source_kind:
            raise ValueError("Tournament Lab session persistence source-kind mismatch")
        if item.scenario.source_reference != row.source_reference:
            raise ValueError("Tournament Lab session persistence source-reference mismatch")
        if item.scenario.source_fingerprint != row.source_fingerprint:
            raise ValueError("Tournament Lab session persistence source-fingerprint mismatch")
        if item.fingerprint != row.fingerprint:
            raise ValueError("Tournament Lab session persistence fingerprint mismatch")
        return item

    @staticmethod
    def _persist_session(session, item: TournamentLabSession) -> None:
        row = session.get(TournamentLabSessionModel, item.session_id)
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
            session.add(TournamentLabSessionModel(session_id=item.session_id, **values))
        else:
            for key, value in values.items():
                setattr(row, key, value)
        session.flush()

    def list_built_in_scenarios(self) -> tuple[BuiltInTournamentLabScenario, ...]:
        return BUILT_IN_TOURNAMENT_LAB_SCENARIOS

    def list_sessions(self) -> tuple[TournamentLabSession, ...]:
        self._require_persistence()
        from sqlalchemy import select

        with self._session_factory() as session:
            rows = session.scalars(
                select(TournamentLabSessionModel).order_by(
                    TournamentLabSessionModel.display_name,
                    TournamentLabSessionModel.session_id,
                )
            ).all()
            return tuple(self._load_session_row(row) for row in rows)

    def get_session(self, session_id: str) -> TournamentLabSession:
        self._require_persistence()
        with self._session_factory() as session:
            row = session.get(TournamentLabSessionModel, session_id)
            if row is None:
                raise KeyError("Tournament Lab session was not found")
            return self._load_session_row(row)

    def create_session(self, request: TournamentLabSessionCreateRequest) -> TournamentLabSession:
        self._require_persistence()
        from sqlalchemy import text

        if request.built_in_scenario_id is not None:
            built_in = BUILT_IN_TOURNAMENT_LAB_BY_ID.get(request.built_in_scenario_id)
            if built_in is None:
                raise KeyError("Built-in Tournament Lab scenario was not found")
            scenario = built_in.scenario.model_copy(
                update={
                    "scenario_id": f"session-copy:{built_in.scenario_id}",
                    "display_name": request.display_name,
                    "source_kind": "built_in_copy",
                    "source_reference": built_in.scenario_id,
                    "source_fingerprint": built_in.scenario_fingerprint,
                }
            )
        else:
            assert request.scenario is not None
            scenario = request.scenario

        session_id = self._id_factory("tournament-lab-session")
        item = TournamentLabSession(
            session_id=session_id,
            display_name=request.display_name,
            version=1,
            scenario=scenario,
        )
        with self._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            if session.get(TournamentLabSessionModel, session_id) is not None:
                raise ValueError("generated Tournament Lab session identity already exists")
            self._persist_session(session, item)
        return item

    def copy_saved_revision_tournament(
        self,
        request: TournamentLabSavedRevisionCopyRequest,
    ) -> TournamentLabSession:
        self._require_persistence()
        if self._repository is None:
            raise RuntimeError("Tournament Lab Saved Revision copy is not configured")

        history = RunSavedRevisionHistoryService(self._repository)
        try:
            detail = history.get_revision(
                run_id=request.product_run_id,
                branch_id=request.branch_id,
                revision_id=request.saved_revision_id,
            )
        except SavedRevisionHistoryNotFoundError as exc:
            raise KeyError(str(exc)) from exc
        except SavedRevisionHistoryConflictError as exc:
            raise ValueError(str(exc)) from exc

        revision = detail.saved_revision
        component = load_saved_simulation_slot_component(
            revision.payload,
            run_id=request.product_run_id,
            branch_id=request.branch_id,
        )
        if component is None:
            raise ValueError("Saved Revision has no validated simulation-slot tournament state")

        from beta_engine.domain.tournaments.entry_field import TournamentEntryField
        from beta_engine.domain.tournaments.format_authority import TournamentFormatAuthority
        from beta_engine.domain.tournaments.draw_input_authority import TournamentDrawInputAuthority
        from beta_engine.domain.tournaments.topology_authority import TournamentTopologyAuthority

        event_fields = [
            row for row in component.get("entry_fields", ())
            if row["event_id"] == request.event_id
        ]
        if not event_fields:
            raise ValueError("Saved Revision event has no Tournament Entry Field")
        latest_field_row = max(event_fields, key=lambda row: row["sequence"])
        entry_field = TournamentEntryField.model_validate_json(latest_field_row["payload_json"])

        format_rows = [
            row for row in component.get("format_authorities", ())
            if row["event_id"] == request.event_id
        ]
        if len(format_rows) != 1:
            raise ValueError("Saved Revision event requires exactly one Tournament Format authority")
        format_authority = TournamentFormatAuthority.model_validate_json(format_rows[0]["payload_json"])
        if format_authority.entry_field_fingerprint != entry_field.fingerprint:
            raise ValueError("Saved Revision Tournament Format does not bind the latest Entry Field")

        draw_rows = [
            row for row in component.get("draw_inputs", ())
            if row["event_id"] == request.event_id
        ]
        topology_rows = [
            row for row in component.get("topology_authorities", ())
            if row["event_id"] == request.event_id
        ]
        draw_input = (
            TournamentDrawInputAuthority.model_validate_json(draw_rows[0]["payload_json"])
            if len(draw_rows) == 1 else None
        )
        topology = (
            TournamentTopologyAuthority.model_validate_json(topology_rows[0]["payload_json"])
            if len(topology_rows) == 1 else None
        )

        if format_authority.format_kind == "knockout" and draw_input is None:
            raise ValueError("Historical knockout copy requires frozen Draw Input")
        if format_authority.format_kind != "knockout" and topology is None:
            raise ValueError("Historical group-format copy requires frozen Topology authority")

        if draw_input is not None:
            unsupported = (
                draw_input.wild_card_player_ids
                or draw_input.lucky_loser_placeholder_ids
                or draw_input.lucky_loser_player_ids
                or draw_input.replacement_source_authority_fingerprints
                or draw_input.released_wild_card_slot_ordinals
                or draw_input.released_qualifier_placeholder_ids
                or draw_input.late_bye_count
            )
            if unsupported:
                raise ValueError(
                    "Historical Tournament uses WC/LL/replacement repair not yet supported by Tournament Lab copy"
                )

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

        if format_authority.format_kind == "knockout":
            assert draw_input is not None
            active_ids = tuple(draw_input.direct_main_player_ids) + tuple(draw_input.qualification_player_ids)
            seed_prefix = tuple(draw_input.main_seed_player_ids) + tuple(draw_input.qualification_seed_player_ids)
            draw_seed = draw_input.draw_seed
            qualification_ids = tuple(draw_input.qualification_player_ids)
            capacity = draw_input.capacity
            topology_seed = None
        else:
            assert topology is not None
            active_ids = tuple(topology.participant_order_player_ids)
            seed_prefix = active_ids
            draw_seed = topology.topology_seed or 0
            qualification_ids = ()
            capacity = entry_field.capacity
            topology_seed = topology.topology_seed

        if len(active_ids) != len(set(active_ids)) or len(active_ids) < 2:
            raise ValueError("Historical Tournament participant field is incomplete or duplicated")
        seed_order = seed_prefix + tuple(player_id for player_id in active_ids if player_id not in seed_prefix)
        if set(seed_order) != set(active_ids) or len(seed_order) != len(active_ids):
            raise ValueError("Historical Tournament seed order cannot be represented without invention")

        profiles = {item.player_id: item for item in world.players}
        records = {item.player_id: item for item in sporting.players}
        season_start_year = 2000 + sporting.week.season_index
        position = season_week_to_calendar_position(season_start_year, sporting.week.week)
        participants = []
        projection_fingerprints = []
        for player_id in active_ids:
            profile = profiles.get(player_id)
            record = records.get(player_id)
            if profile is None:
                raise ValueError(
                    f"Saved Revision Tournament player {player_id} is not present in Initial World; prospect-profile copy is not supported by this slice"
                )
            if record is None:
                raise ValueError(
                    f"Saved Revision Tournament player {player_id} has no sporting record at the saved sporting head"
                )
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
            participants.append(
                MatchParticipantContext(
                    player=projected_engine_player(projection),
                    form_modifier=projection.form_modifier,
                    sharpness_modifier=projection.sharpness_modifier,
                    fatigue_modifier=projection.fatigue_modifier,
                )
            )
            projection_fingerprints.append(projection.fingerprint)

        evidence = TournamentLabRunSnapshotEvidence(
            product_run_id=request.product_run_id,
            branch_id=request.branch_id,
            saved_revision_id=request.saved_revision_id,
            saved_revision_content_hash=revision.content_hash,
            event_id=request.event_id,
            entry_field_fingerprint=entry_field.fingerprint,
            format_authority_fingerprint=format_authority.fingerprint,
            draw_input_fingerprint=draw_input.fingerprint if draw_input is not None else None,
            topology_authority_fingerprint=topology.fingerprint if topology is not None else None,
            sporting_state_fingerprint=sporting.fingerprint,
            sporting_week_ordinal=sporting.week.ordinal,
            participant_projection_fingerprints=tuple(projection_fingerprints),
        )

        group = format_authority.group_configuration
        scenario = TournamentLabScenario(
            scenario_id=f"run-copy:{request.event_id}:{request.saved_revision_id}",
            display_name=request.display_name,
            format_kind=format_authority.format_kind,
            participants=tuple(participants),
            main_draw_size=(
                group.participant_capacity if group is not None else capacity.main_draw_size
            ),
            group_count=group.group_count if group is not None else 0,
            group_size=group.group_size if group is not None else 0,
            seeded_slots_per_group=group.seeded_slots_per_group if group is not None else 0,
            group_seed_placements=group.group_seed_placements if group is not None else (),
            group_match_best_of=group.match_best_of if group is not None else None,
            advancing_per_group=group.advancing_per_group if group is not None else 0,
            knockout_crossings=group.knockout_crossings if group is not None else (),
            topology_seed=topology_seed,
            qualification_draw_size=(capacity.qualification_draw_size if draw_input is not None else 0),
            qualifier_spots=(capacity.qualifier_spots if draw_input is not None else 0),
            qualification_player_ids=qualification_ids,
            seed_order_player_ids=seed_order,
            draw_seed=draw_seed,
            match_seed=int(evidence.fingerprint[:16], 16),
            source_kind="run_snapshot_copy",
            source_reference=(
                f"{request.product_run_id}/{request.branch_id}/"
                f"{request.saved_revision_id}/{request.event_id}"
            ),
            source_fingerprint=evidence.fingerprint,
            source_snapshot=evidence,
        )
        return self.create_session(
            TournamentLabSessionCreateRequest(
                display_name=request.display_name,
                scenario=scenario,
            )
        )

    def update_session(
        self,
        session_id: str,
        request: TournamentLabSessionUpdateRequest,
    ) -> TournamentLabSession:
        self._require_persistence()
        from sqlalchemy import text

        with self._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            row = session.get(TournamentLabSessionModel, session_id)
            if row is None:
                raise KeyError("Tournament Lab session was not found")
            current = self._load_session_row(row)
            if current.fingerprint != request.expected_session_fingerprint:
                raise ValueError("Tournament Lab session changed since it was reviewed")
            updated = TournamentLabSession(
                session_id=current.session_id,
                display_name=request.display_name or current.display_name,
                version=current.version + 1,
                scenario=request.scenario,
            )
            self._persist_session(session, updated)
            return updated

    def export_session(self, session_id: str) -> TournamentLabSessionExport:
        current = self.get_session(session_id)
        payload = TournamentLabSessionExport.fingerprint_payload(
            current,
            session_fingerprint=current.fingerprint,
            scenario_fingerprint=current.scenario.fingerprint,
        )
        return TournamentLabSessionExport(
            session=current,
            session_fingerprint=current.fingerprint,
            scenario_fingerprint=current.scenario.fingerprint,
            export_fingerprint=_fingerprint(payload),
        )

    def import_session(
        self,
        request: TournamentLabSessionImportRequest,
    ) -> TournamentLabSession:
        exported = request.export_payload
        if request.expected_export_fingerprint != exported.export_fingerprint:
            raise ValueError("Tournament Lab export changed since it was reviewed")

        source = exported.session
        if source.fingerprint != exported.session_fingerprint:
            raise ValueError("Tournament Lab export session fingerprint mismatch")
        if source.scenario.fingerprint != exported.scenario_fingerprint:
            raise ValueError("Tournament Lab export scenario fingerprint mismatch")

        return self.create_session(
            TournamentLabSessionCreateRequest(
                display_name=request.display_name or source.display_name,
                scenario=source.scenario,
            )
        )

    def run_session(
        self,
        session_id: str,
        request: TournamentLabSessionRunRequest,
    ) -> TournamentLabResult:
        current = self.get_session(session_id)
        if current.fingerprint != request.expected_session_fingerprint:
            raise ValueError("Tournament Lab session changed since it was reviewed")
        return self.run(
            TournamentLabRequest(
                scenario=current.scenario,
                batch_match_seeds=request.batch_match_seeds,
            )
        )

    def inspect(self, scenario: TournamentLabScenario) -> TournamentLabCompatibility:
        issues: list[TournamentLabIssue] = []
        ids = tuple(item.player.player_id for item in scenario.participants)
        expected_order = set(ids)
        seed_order = scenario.seed_order_player_ids or ids
        if len(seed_order) != len(ids) or set(seed_order) != expected_order:
            issues.append(
                TournamentLabIssue(
                    severity="error",
                    code="SEED_ORDER_NOT_FIELD_PERMUTATION",
                    message="Seed order must contain every participant exactly once.",
                )
            )

        if scenario.format_kind in {"groups", "groups_knockout"}:
            if scenario.qualification_draw_size or scenario.qualifier_spots or scenario.qualification_player_ids:
                issues.append(
                    TournamentLabIssue(
                        severity="error",
                        code="GROUP_FORMAT_QUALIFICATION_UNSUPPORTED",
                        message="Group-format Tournament Lab currently requires one fully resolved participant field without Qualification.",
                    )
                )
            if scenario.group_count <= 0 or scenario.group_size <= 0:
                issues.append(
                    TournamentLabIssue(
                        severity="error",
                        code="GROUP_GEOMETRY_INCOMPLETE",
                        message="Group format requires positive group_count and group_size.",
                    )
                )
            elif scenario.group_count * scenario.group_size != len(ids):
                issues.append(
                    TournamentLabIssue(
                        severity="error",
                        code="GROUP_FIELD_NOT_EXACTLY_FILLED",
                        message="Group participant field must exactly fill equal configured groups.",
                    )
                )
            if scenario.main_draw_size != len(ids):
                issues.append(
                    TournamentLabIssue(
                        severity="warning",
                        code="GROUP_MAIN_DRAW_SIZE_IS_DISPLAY_ONLY",
                        message="For group formats main_draw_size is retained for scenario compatibility; group capacity is group_count × group_size.",
                    )
                )
            if scenario.group_match_best_of not in {3, 5}:
                issues.append(
                    TournamentLabIssue(
                        severity="error",
                        code="GROUP_MATCH_FORMAT_REQUIRED",
                        message="Group format requires explicit BO3 or BO5 group_match_best_of.",
                    )
                )
            expected_seeded = scenario.group_count * scenario.seeded_slots_per_group
            if len(scenario.group_seed_placements) != expected_seeded:
                issues.append(
                    TournamentLabIssue(
                        severity="error",
                        code="GROUP_SEED_PLACEMENTS_INCOMPLETE",
                        message="Group seed placements must be explicit for every configured seeded group slot.",
                    )
                )
            if scenario.topology_seed is None:
                issues.append(
                    TournamentLabIssue(
                        severity="error",
                        code="GROUP_TOPOLOGY_SEED_REQUIRED",
                        message="Group topology requires an explicit deterministic topology seed.",
                    )
                )
            if scenario.format_kind == "groups":
                if scenario.advancing_per_group or scenario.knockout_crossings:
                    issues.append(
                        TournamentLabIssue(
                            severity="error",
                            code="PURE_GROUPS_CANNOT_CARRY_KNOCKOUT",
                            message="Groups-only format cannot define knockout advancement or crossings.",
                        )
                    )
            else:
                if scenario.advancing_per_group <= 0:
                    issues.append(
                        TournamentLabIssue(
                            severity="error",
                            code="HYBRID_ADVANCEMENT_REQUIRED",
                            message="Groups+knockout requires advancing_per_group.",
                        )
                    )
                advancing = scenario.group_count * scenario.advancing_per_group
                if advancing < 2 or advancing & (advancing - 1):
                    issues.append(
                        TournamentLabIssue(
                            severity="error",
                            code="HYBRID_KNOCKOUT_FIELD_NOT_POWER_OF_TWO",
                            message="Configured hybrid knockout field must be a power of two.",
                        )
                    )
                if len(scenario.knockout_crossings) != advancing // 2:
                    issues.append(
                        TournamentLabIssue(
                            severity="error",
                            code="HYBRID_CROSSINGS_INCOMPLETE",
                            message="Groups+knockout requires explicit crossings that exactly fill the first knockout round.",
                        )
                    )
        elif scenario.format_kind == "knockout":
            qualification_ids = tuple(scenario.qualification_player_ids)
            qualification_set = set(qualification_ids)
            direct_main_ids = tuple(player_id for player_id in ids if player_id not in qualification_set)

            if scenario.main_draw_size & (scenario.main_draw_size - 1):
                issues.append(
                    TournamentLabIssue(
                        severity="error",
                        code="MAIN_DRAW_NOT_POWER_OF_TWO",
                        message="Classic knockout Main Draw capacity must be a power of two.",
                    )
                )
            if len(qualification_ids) != len(qualification_set):
                issues.append(
                    TournamentLabIssue(
                        severity="error",
                        code="QUALIFICATION_PLAYER_DUPLICATE",
                        message="Qualification player IDs must be unique.",
                    )
                )
            if not qualification_set.issubset(expected_order):
                issues.append(
                    TournamentLabIssue(
                        severity="error",
                        code="QUALIFICATION_PLAYER_OUTSIDE_FIELD",
                        message="Qualification contains a player outside the Tournament Lab participant field.",
                    )
                )
            has_qualification = bool(
                scenario.qualification_draw_size or scenario.qualifier_spots or qualification_ids
            )
            if has_qualification:
                if scenario.qualification_draw_size <= 0 or scenario.qualifier_spots <= 0:
                    issues.append(
                        TournamentLabIssue(
                            severity="error",
                            code="QUALIFICATION_GEOMETRY_INCOMPLETE",
                            message="Qualification requires both a positive draw size and qualifier spot count.",
                        )
                    )
                elif scenario.qualification_draw_size % scenario.qualifier_spots:
                    issues.append(
                        TournamentLabIssue(
                            severity="error",
                            code="QUALIFICATION_NOT_EQUAL_SECTIONS",
                            message="Qualification draw size must divide evenly across equal Q sections.",
                        )
                    )
                else:
                    section_size = scenario.qualification_draw_size // scenario.qualifier_spots
                    if section_size < 2 or section_size & (section_size - 1):
                        issues.append(
                            TournamentLabIssue(
                                severity="error",
                                code="QUALIFICATION_SECTION_NOT_POWER_OF_TWO",
                                message="Each Qualification section must have power-of-two capacity of at least two.",
                            )
                        )
                if len(qualification_ids) < scenario.qualifier_spots:
                    issues.append(
                        TournamentLabIssue(
                            severity="error",
                            code="QUALIFICATION_TOO_FEW_PLAYERS",
                            message="Qualification requires at least one real player per Q section.",
                        )
                    )
                if len(qualification_ids) > scenario.qualification_draw_size:
                    issues.append(
                        TournamentLabIssue(
                            severity="error",
                            code="QUALIFICATION_FIELD_EXCEEDS_CAPACITY",
                            message="Qualification player field exceeds configured Qualification draw size.",
                        )
                    )
            main_entrant_count = len(direct_main_ids) + scenario.qualifier_spots
            if main_entrant_count > scenario.main_draw_size:
                issues.append(
                    TournamentLabIssue(
                        severity="error",
                        code="FIELD_EXCEEDS_MAIN_DRAW",
                        message="Direct Main players plus qualifier places exceed Main Draw capacity.",
                    )
                )
            if main_entrant_count < 2:
                issues.append(
                    TournamentLabIssue(
                        severity="error",
                        code="MAIN_FIELD_TOO_SMALL",
                        message="Executable Main Draw requires at least two eventual entrants.",
                    )
                )
            if 2 <= main_entrant_count <= 128:
                canonical_capacity = 1 << (main_entrant_count - 1).bit_length()
                if scenario.main_draw_size != canonical_capacity:
                    issues.append(
                        TournamentLabIssue(
                            severity="warning",
                            code="NONCANONICAL_CLASSIC_CAPACITY",
                            message=(
                                f"Normal Run classic geometry would derive capacity {canonical_capacity} "
                                f"for {main_entrant_count} eventual Main entrants, not {scenario.main_draw_size}."
                            ),
                        )
                    )
        else:
            issues.append(
                TournamentLabIssue(
                    severity="error",
                    code="FORMAT_NOT_EXECUTABLE_V4",
                    message=f"Tournament Lab V4 does not execute format {scenario.format_kind!r}.",
                )
            )

        if scenario.format_kind == "knockout" and (
            scenario.match_format.best_of,
            scenario.match_format.games_to,
            scenario.match_format.win_by,
        ) != (5, 11, 2):
            issues.append(
                TournamentLabIssue(
                    severity="warning",
                    code="NONSTANDARD_MATCH_FORMAT",
                    message="Knockout Match format differs from normal BO5-to-11-win-by-2 baseline.",
                )
            )
        if scenario.source_kind == "run_snapshot_copy" and scenario.source_fingerprint is None:
            issues.append(
                TournamentLabIssue(
                    severity="warning",
                    code="UNVERIFIED_RUN_SNAPSHOT_COPY",
                    message="Run snapshot copy lacks source fingerprint provenance.",
                )
            )

        runnable = not any(item.severity == "error" for item in issues)
        normal_run_compatible = runnable and not issues
        shared = [
            "beta_engine.domain.tournaments.format_authority.TournamentFormatAuthority",
            "beta_engine.domain.matches.match_engine.MatchEngine.simulate",
        ]
        if scenario.format_kind == "knockout":
            shared.extend([
                "beta_engine.domain.tournaments.draw_input_authority.canonical_qualification_seed_count",
                "beta_engine.domain.tournaments.draw_authority.TournamentDrawAuthorityBuilder",
            ])
        else:
            shared.extend([
                "beta_engine.domain.tournaments.topology_authority.TournamentTopologyAuthorityBuilder",
                "beta_engine.domain.tournaments.group_match_schedule_authority.TournamentGroupMatchScheduleBuilder",
                "beta_engine.domain.tournaments.group_standings_authority.TournamentGroupStandingsBuilder",
            ])
            if scenario.format_kind == "groups_knockout":
                shared.extend([
                    "beta_engine.domain.tournaments.hybrid_knockout_entrants_authority.TournamentHybridKnockoutEntrantsBuilder",
                    "beta_engine.domain.tournaments.hybrid_knockout_bracket_authority.TournamentHybridKnockoutBracketBuilder",
                ])
        return TournamentLabCompatibility(
            runnable_in_lab=runnable,
            normal_run_compatible=normal_run_compatible,
            shared_authorities=tuple(shared),
            issues=tuple(issues),
        )

    def run(self, request: TournamentLabRequest) -> TournamentLabResult:
        scenario = request.scenario
        compatibility = self.inspect(scenario)
        request_fingerprint = _fingerprint(request.model_dump(mode="json"))
        if not compatibility.runnable_in_lab:
            return self._blocked_result(
                scenario=scenario,
                request_fingerprint=request_fingerprint,
                compatibility=compatibility,
            )
        if scenario.format_kind == "knockout":
            return self._run_knockout(
                request=request,
                compatibility=compatibility,
                request_fingerprint=request_fingerprint,
            )
        return self._run_groups(
            request=request,
            compatibility=compatibility,
            request_fingerprint=request_fingerprint,
        )

    @staticmethod
    def _blocked_result(
        *,
        scenario: TournamentLabScenario,
        request_fingerprint: str,
        compatibility: TournamentLabCompatibility,
    ) -> TournamentLabResult:
        return TournamentLabResult(
            scenario_id=scenario.scenario_id,
            scenario_fingerprint=scenario.fingerprint,
            request_fingerprint=request_fingerprint,
            compatibility=compatibility,
            diagnostics=TournamentLabBatchDiagnostics(
                run_count=0,
                completed_run_count=0,
                champions={},
                assertion_failure_count=0,
                average_played_match_count=0,
            ),
        )

    def _run_knockout(
        self,
        *,
        request: TournamentLabRequest,
        compatibility: TournamentLabCompatibility,
        request_fingerprint: str,
    ) -> TournamentLabResult:
        scenario = request.scenario
        format_authority, draw_input, draw = self._build_draw(scenario)
        runs = tuple(
            self._execute_draw(scenario, draw, match_seed=match_seed)
            for match_seed in request.effective_match_seeds
        )
        return self._result_from_runs(
            scenario=scenario,
            request_fingerprint=request_fingerprint,
            compatibility=compatibility,
            runs=runs,
            format_authority_fingerprint=format_authority.fingerprint,
            draw_input_fingerprint=draw_input.fingerprint,
            draw_authority_fingerprint=draw.fingerprint,
            draw=draw,
        )

    def _run_groups(
        self,
        *,
        request: TournamentLabRequest,
        compatibility: TournamentLabCompatibility,
        request_fingerprint: str,
    ) -> TournamentLabResult:
        scenario = request.scenario
        entry_field, rules, format_authority, topology, schedule = self._build_group_authorities(scenario)
        runs = tuple(
            self._execute_groups(
                scenario,
                topology=topology,
                schedule=schedule,
                match_seed=match_seed,
            )
            for match_seed in request.effective_match_seeds
        )
        return self._result_from_runs(
            scenario=scenario,
            request_fingerprint=request_fingerprint,
            compatibility=compatibility,
            runs=runs,
            format_authority_fingerprint=format_authority.fingerprint,
            topology_authority_fingerprint=topology.fingerprint,
            group_schedule_fingerprint=schedule.fingerprint,
            topology=topology,
            group_schedule=schedule,
        )

    @staticmethod
    def _result_from_runs(
        *,
        scenario: TournamentLabScenario,
        request_fingerprint: str,
        compatibility: TournamentLabCompatibility,
        runs: tuple[TournamentLabSingleRun, ...],
        format_authority_fingerprint: str,
        draw_input_fingerprint: str | None = None,
        draw_authority_fingerprint: str | None = None,
        topology_authority_fingerprint: str | None = None,
        group_schedule_fingerprint: str | None = None,
        draw: TournamentDrawAuthority | None = None,
        topology: TournamentTopologyAuthority | None = None,
        group_schedule: TournamentGroupMatchScheduleAuthority | None = None,
    ) -> TournamentLabResult:
        champions = Counter(
            row.champion_player_id for row in runs if row.champion_player_id is not None
        )
        failure_count = sum(
            assertion.status == "failed"
            for row in runs
            for assertion in row.assertions
        )
        return TournamentLabResult(
            scenario_id=scenario.scenario_id,
            scenario_fingerprint=scenario.fingerprint,
            request_fingerprint=request_fingerprint,
            compatibility=compatibility,
            format_authority_fingerprint=format_authority_fingerprint,
            draw_input_fingerprint=draw_input_fingerprint,
            draw_authority_fingerprint=draw_authority_fingerprint,
            topology_authority_fingerprint=topology_authority_fingerprint,
            group_schedule_fingerprint=group_schedule_fingerprint,
            draw=draw,
            topology=topology,
            group_schedule=group_schedule,
            runs=runs,
            diagnostics=TournamentLabBatchDiagnostics(
                run_count=len(runs),
                completed_run_count=sum(row.tournament_complete for row in runs),
                champions=dict(sorted(champions.items())),
                assertion_failure_count=failure_count,
                average_played_match_count=round(
                    mean(row.played_match_count for row in runs), 3
                ),
            ),
        )

    @staticmethod
    def _build_draw(
        scenario: TournamentLabScenario,
    ) -> tuple[TournamentFormatAuthority, TournamentDrawInputAuthority, TournamentDrawAuthority]:
        player_ids = tuple(item.player.player_id for item in scenario.participants)
        seed_order = scenario.seed_order_player_ids or player_ids
        qualification_set = set(scenario.qualification_player_ids)
        direct_main = tuple(
            player_id for player_id in seed_order if player_id not in qualification_set
        )
        qualification = tuple(
            player_id for player_id in seed_order if player_id in qualification_set
        )
        bye_slots = (
            scenario.main_draw_size
            - len(direct_main)
            - scenario.qualifier_spots
        )
        capacity = TournamentEntryFieldCapacity(
            main_draw_size=scenario.main_draw_size,
            qualification_draw_size=scenario.qualification_draw_size,
            qualifier_spots=scenario.qualifier_spots,
            bye_slots=bye_slots,
        )
        source_fp = _fingerprint(
            {"scenario_fingerprint": scenario.fingerprint, "scope": "tournament-lab-source"}
        )
        entry_fp = _fingerprint(
            {"scenario_fingerprint": scenario.fingerprint, "scope": "entry-field"}
        )
        format_authority = TournamentFormatAuthority(
            run_id=f"lab:{scenario.scenario_id}",
            branch_id="isolated",
            event_id=f"lab-event:{scenario.scenario_id}",
            target_season_index=0,
            configured_by_command_id="tournament-lab-format-v3",
            entry_field_fingerprint=entry_fp,
            format_kind="knockout",
        )
        main_seed_count = canonical_classic_seed_count(
            bracket_capacity=capacity.main_draw_size,
            actual_player_count=len(direct_main),
        )
        qualification_seed_count = canonical_qualification_seed_count(
            capacity=capacity,
            actual_player_count=len(qualification),
        )
        qualifier_placeholder_ids = tuple(
            f"Q{index}" for index in range(1, scenario.qualifier_spots + 1)
        )
        draw_input = TournamentDrawInputAuthority(
            schema_version="tournament_draw_input_authority.v2",
            run_id=f"lab:{scenario.scenario_id}",
            branch_id="isolated",
            event_id=f"lab-event:{scenario.scenario_id}",
            committed_by_command_id="tournament-lab-draw-input-v3",
            draw_seed=scenario.draw_seed,
            main_seed_count=main_seed_count,
            qualification_seed_count=qualification_seed_count,
            field_sequence=1,
            capacity=capacity,
            tournament_ranking_authority_fingerprint=source_fp,
            ranking_snapshot_fingerprint=source_fp,
            entry_field_fingerprint=entry_fp,
            direct_main_player_ids=direct_main,
            qualification_player_ids=qualification,
            qualifier_placeholder_ids=qualifier_placeholder_ids,
            withdrawn_player_ids=(),
            main_seed_player_ids=direct_main[:main_seed_count],
            qualification_seed_player_ids=qualification[:qualification_seed_count],
        )
        draw = TournamentDrawAuthorityBuilder.build(
            draw_input=draw_input,
            command_id="tournament-lab-draw-v3",
            algorithm_version="idealized_seed_tiers.v2",
        )
        return format_authority, draw_input, draw

    @staticmethod
    def _build_group_authorities(
        scenario: TournamentLabScenario,
    ) -> tuple[
        TournamentEntryField,
        TournamentGroupRulesPolicy,
        TournamentFormatAuthority,
        TournamentTopologyAuthority,
        TournamentGroupMatchScheduleAuthority,
    ]:
        ids = tuple(item.player.player_id for item in scenario.participants)
        seed_order = scenario.seed_order_player_ids or ids
        event_id = f"lab-event:{scenario.scenario_id}"
        run_id = f"lab:{scenario.scenario_id}"
        entry_fp_source = _fingerprint(
            {"scenario_fingerprint": scenario.fingerprint, "scope": "group-entry-source"}
        )
        entry_field = TournamentEntryField(
            run_id=run_id,
            branch_id="isolated",
            event_id=event_id,
            mode="initial",
            capacity=TournamentEntryFieldCapacity(
                geometry_kind="fixed_participant_field",
                main_draw_size=len(ids),
            ),
            tournament_ranking_authority_fingerprint=entry_fp_source,
            ranking_snapshot_fingerprint=entry_fp_source,
            applications_fingerprint=_fingerprint(
                {"scenario_fingerprint": scenario.fingerprint, "scope": "group-applications"}
            ),
            direct_main_player_ids=seed_order,
        )
        rules = TournamentGroupRulesPolicy(
            run_id=run_id,
            branch_id="isolated",
            effective_from_season_index=0,
            default_match_best_of=scenario.group_match_best_of,
            adopted_by_command_id="tournament-lab-group-rules-v4",
        )
        group = TournamentGroupFormatConfiguration(
            group_count=scenario.group_count,
            group_size=scenario.group_size,
            seeded_slots_per_group=scenario.seeded_slots_per_group,
            group_seed_placements=scenario.group_seed_placements,
            match_best_of=scenario.group_match_best_of,
            rules_source_kind="season_policy",
            group_rules_policy_fingerprint=rules.fingerprint,
            group_rules_effective_from_season_index=0,
            advancing_per_group=(
                scenario.advancing_per_group
                if scenario.format_kind == "groups_knockout"
                else 0
            ),
            knockout_crossings=(
                scenario.knockout_crossings
                if scenario.format_kind == "groups_knockout"
                else ()
            ),
        )
        format_authority = TournamentFormatAuthority(
            run_id=run_id,
            branch_id="isolated",
            event_id=event_id,
            target_season_index=0,
            configured_by_command_id="tournament-lab-format-v4",
            entry_field_fingerprint=entry_field.fingerprint,
            format_kind=scenario.format_kind,
            group_configuration=group,
        )
        topology = TournamentTopologyAuthorityBuilder.build_groups(
            format_authority=format_authority,
            entry_field=entry_field,
            participant_order_player_ids=seed_order,
            command_id="tournament-lab-topology-v4",
            topology_seed=scenario.topology_seed,
        )
        schedule = TournamentGroupMatchScheduleBuilder.build(
            format_authority=format_authority,
            topology_authority=topology,
            command_id="tournament-lab-group-schedule-v4",
        )
        return entry_field, rules, format_authority, topology, schedule

    def _execute_groups(
        self,
        scenario: TournamentLabScenario,
        *,
        topology: TournamentTopologyAuthority,
        schedule: TournamentGroupMatchScheduleAuthority,
        match_seed: int,
    ) -> TournamentLabSingleRun:
        participants = {item.player.player_id: item for item in scenario.participants}
        match_results: list[TournamentLabMatchResult] = []
        raw_results: list[tuple[object, MatchResult, str]] = []

        for scheduled in schedule.matches:
            player_a = participants[scheduled.top_player_id]
            player_b = participants[scheduled.bottom_player_id]
            fmt = scheduled.effective_match_format.format
            context = MatchContext(
                match_id=scheduled.match_id,
                player_a=player_a,
                player_b=player_b,
                best_of=fmt.best_of,
                games_to=fmt.games_to,
                win_by=fmt.win_by,
                upset_variance=scenario.match_format.upset_variance,
            )
            seed = self._node_seed(match_seed, scheduled.match_id)
            raw = MatchEngine(rng=DeterministicRng(seed)).simulate(context)
            fp = _fingerprint(raw.model_dump(mode="json"))
            match_results.append(
                TournamentLabMatchResult(
                    node_id=scheduled.match_id,
                    round_number=scheduled.match_day_ordinal,
                    round_sequence=scheduled.match_order,
                    player_a_id=raw.player_a_id,
                    player_b_id=raw.player_b_id,
                    winner_player_id=raw.winner_player_id,
                    loser_player_id=raw.loser_player_id,
                    status="played",
                    match_seed=seed,
                    result_fingerprint=fp,
                    set_scores=tuple(_set_score(raw, item.set_number) for item in raw.sets),
                    rally_count=len(raw.rally_log.events) if raw.rally_log is not None else 0,
                    elapsed_seconds=(
                        raw.timeline_log.total_elapsed_seconds
                        if raw.timeline_log is not None
                        else 0.0
                    ),
                )
            )
            raw_results.append((scheduled, raw, fp))

        blocking: TournamentLabIssue | None = None
        standings: TournamentGroupStandingsAuthority | None = None
        try:
            receipts = tuple(
                TournamentGroupStandingsBuilder.receipt_from_result(
                    scheduled_match=scheduled,
                    result=raw,
                    result_fingerprint=fp,
                )
                for scheduled, raw, fp in raw_results
            )
            standings = TournamentGroupStandingsBuilder.build(
                schedule=schedule,
                receipts=receipts,
                command_id="tournament-lab-group-standings-v4",
            )
        except TournamentGroupStandingsUnresolvedTie as exc:
            blocking = TournamentLabIssue(
                severity="error",
                code="GROUP_STANDINGS_ADMIN_TIE_RESOLUTION_REQUIRED",
                message=(
                    f"Group {exc.case.group_index} standings remain unresolved after all automatic criteria; "
                    f"explicit Admin resolution is required for case {exc.case.fingerprint}."
                ),
            )
        except TournamentGroupStandingsUnsupportedResult as exc:
            blocking = TournamentLabIssue(
                severity="error",
                code="GROUP_STANDINGS_RESULT_EFFECT_UNRESOLVED",
                message=str(exc),
            )

        group_stage = TournamentLabGroupStageResult(
            topology_fingerprint=topology.fingerprint,
            schedule_fingerprint=schedule.fingerprint,
            match_day_count=schedule.match_day_count,
            match_results=tuple(match_results),
            standings=standings,
            blocking_issue=blocking,
        )

        hybrid_bracket: TournamentHybridKnockoutBracketAuthority | None = None
        knockout_results: list[TournamentLabMatchResult] = []
        champion: str | None = None
        if (
            blocking is None
            and standings is not None
            and scenario.format_kind == "groups_knockout"
        ):
            entrants = TournamentHybridKnockoutEntrantsBuilder.build(
                topology=topology,
                standings=standings,
                command_id="tournament-lab-hybrid-entrants-v4",
            )
            hybrid_bracket = TournamentHybridKnockoutBracketBuilder.build(
                entrants=entrants,
                command_id="tournament-lab-hybrid-bracket-v4",
            )
            knockout_results, champion = self._execute_hybrid_bracket(
                scenario,
                hybrid_bracket,
                participants=participants,
                match_seed=match_seed,
            )

        complete = blocking is None and (
            scenario.format_kind == "groups" or champion is not None
        )
        played = len(match_results) + len(knockout_results)
        assertions = self._assertions(
            scenario,
            champion=champion,
            played_match_count=played,
            tournament_complete=complete,
        )
        payload = {
            "scenario_fingerprint": scenario.fingerprint,
            "topology_fingerprint": topology.fingerprint,
            "schedule_fingerprint": schedule.fingerprint,
            "match_seed": match_seed,
            "group_stage": group_stage.model_dump(mode="json"),
            "hybrid_bracket": (
                hybrid_bracket.model_dump(mode="json") if hybrid_bracket else None
            ),
            "knockout_results": [
                item.model_dump(mode="json") for item in knockout_results
            ],
            "assertions": [item.model_dump(mode="json") for item in assertions],
        }
        return TournamentLabSingleRun(
            match_seed=match_seed,
            completed_rounds=(
                min(
                    scenario.stop_after_round or hybrid_bracket.round_count,
                    hybrid_bracket.round_count,
                )
                if hybrid_bracket is not None
                else 0
            ),
            tournament_complete=complete,
            champion_player_id=champion,
            played_match_count=played,
            bye_advance_count=0,
            group_stage=group_stage,
            hybrid_knockout_bracket=hybrid_bracket,
            match_results=tuple(knockout_results),
            assertions=assertions,
            run_fingerprint=_fingerprint(payload),
        )

    def _execute_hybrid_bracket(
        self,
        scenario: TournamentLabScenario,
        bracket: TournamentHybridKnockoutBracketAuthority,
        *,
        participants: dict[str, MatchParticipantContext],
        match_seed: int,
    ) -> tuple[list[TournamentLabMatchResult], str | None]:
        winners: dict[str, str] = {}
        results: list[TournamentLabMatchResult] = []

        def resolve(source: str) -> str:
            if source.startswith("player:"):
                return source.removeprefix("player:")
            if source.startswith("winner:"):
                return winners[source.removeprefix("winner:")]
            raise ValueError("Unsupported hybrid knockout source")

        effective_stop = min(
            scenario.stop_after_round or bracket.round_count,
            bracket.round_count,
        )
        for node in sorted(
            bracket.matches, key=lambda value: (value.round_number, value.match_index)
        ):
            if node.round_number > effective_stop:
                break
            player_a_id = resolve(node.participant_sources[0])
            player_b_id = resolve(node.participant_sources[1])
            player_a = participants[player_a_id]
            player_b = participants[player_b_id]
            context = MatchContext(
                match_id=node.match_id,
                player_a=player_a,
                player_b=player_b,
                best_of=scenario.match_format.best_of,
                games_to=scenario.match_format.games_to,
                win_by=scenario.match_format.win_by,
                upset_variance=scenario.match_format.upset_variance,
            )
            seed = self._node_seed(match_seed, node.match_id)
            raw = MatchEngine(rng=DeterministicRng(seed)).simulate(context)
            winners[node.match_id] = raw.winner_player_id
            results.append(
                TournamentLabMatchResult(
                    node_id=node.match_id,
                    round_number=node.round_number,
                    round_sequence=node.match_index,
                    player_a_id=raw.player_a_id,
                    player_b_id=raw.player_b_id,
                    winner_player_id=raw.winner_player_id,
                    loser_player_id=raw.loser_player_id,
                    status="played",
                    match_seed=seed,
                    result_fingerprint=_fingerprint(raw.model_dump(mode="json")),
                    set_scores=tuple(_set_score(raw, item.set_number) for item in raw.sets),
                    rally_count=len(raw.rally_log.events) if raw.rally_log is not None else 0,
                    elapsed_seconds=(
                        raw.timeline_log.total_elapsed_seconds
                        if raw.timeline_log is not None
                        else 0.0
                    ),
                )
            )
        champion = (
            winners.get(bracket.terminal_match_id)
            if effective_stop == bracket.round_count
            else None
        )
        return results, champion

    @staticmethod
    def _node_seed(match_seed: int, node_id: str) -> int:
        digest = sha256(f"{match_seed}|{node_id}".encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big", signed=False)

    def _execute_draw(
        self,
        scenario: TournamentLabScenario,
        draw: TournamentDrawAuthority,
        *,
        match_seed: int,
    ) -> TournamentLabSingleRun:
        participants = {
            item.player.player_id: item for item in scenario.participants
        }

        qualification_results: list[TournamentLabQualificationSectionResult] = []
        qualifier_winners: dict[str, str] = {}
        for bracket in draw.qualification_brackets:
            section_id = bracket.section_id or "Q1"
            q_results, q_winner = self._execute_bracket(
                scenario,
                bracket,
                participants=participants,
                match_seed=match_seed,
                qualifier_winners={},
                stop_after_round=None,
            )
            if q_winner is None:
                raise ValueError(
                    f"Tournament Lab Qualification section {section_id} did not resolve a winner"
                )
            qualifier_winners[section_id] = q_winner
            qualification_results.append(
                TournamentLabQualificationSectionResult(
                    section_id=section_id,
                    bracket_size=bracket.bracket_size,
                    winner_player_id=q_winner,
                    played_match_count=sum(item.status == "played" for item in q_results),
                    bye_advance_count=sum(item.status == "bye_advance" for item in q_results),
                    match_results=tuple(q_results),
                )
            )

        max_round = max(node.round_number for node in draw.main.nodes)
        stop_round = min(scenario.stop_after_round or max_round, max_round)
        main_results, champion = self._execute_bracket(
            scenario,
            draw.main,
            participants=participants,
            match_seed=match_seed,
            qualifier_winners=qualifier_winners,
            stop_after_round=stop_round,
        )

        tournament_complete = stop_round == max_round
        if not tournament_complete:
            champion = None
        qualification_played = sum(item.played_match_count for item in qualification_results)
        main_played = sum(item.status == "played" for item in main_results)
        played = qualification_played + main_played
        bye_advances = (
            sum(item.bye_advance_count for item in qualification_results)
            + sum(item.status == "bye_advance" for item in main_results)
        )
        assertions = self._assertions(
            scenario,
            champion=champion,
            played_match_count=played,
            tournament_complete=tournament_complete,
        )
        payload = {
            "scenario_fingerprint": scenario.fingerprint,
            "draw_fingerprint": draw.fingerprint,
            "match_seed": match_seed,
            "completed_rounds": stop_round,
            "champion": champion,
            "results": [item.model_dump(mode="json") for item in main_results],
            "assertions": [item.model_dump(mode="json") for item in assertions],
        }
        if qualification_results:
            payload["qualification_results"] = [
                item.model_dump(mode="json") for item in qualification_results
            ]
        return TournamentLabSingleRun(
            match_seed=match_seed,
            completed_rounds=stop_round,
            tournament_complete=tournament_complete,
            champion_player_id=champion,
            played_match_count=played,
            bye_advance_count=bye_advances,
            qualification_results=tuple(qualification_results),
            match_results=tuple(main_results),
            assertions=assertions,
            run_fingerprint=_fingerprint(payload),
        )

    def _execute_bracket(
        self,
        scenario: TournamentLabScenario,
        bracket: TournamentDrawBracket,
        *,
        participants: dict[str, MatchParticipantContext],
        match_seed: int,
        qualifier_winners: dict[str, str],
        stop_after_round: int | None,
    ) -> tuple[list[TournamentLabMatchResult], str | None]:
        slots: dict[int, str | None] = {}
        for slot in bracket.slots:
            if slot.entrant_kind == "player":
                slots[slot.slot_index] = slot.player_id
            elif slot.entrant_kind == "qualifier_placeholder":
                slots[slot.slot_index] = (
                    qualifier_winners.get(slot.placeholder_id or "")
                )
            else:
                slots[slot.slot_index] = None

        winners: dict[str, str | None] = {}
        results: list[TournamentLabMatchResult] = []
        max_round = max(node.round_number for node in bracket.nodes)
        effective_stop = min(stop_after_round or max_round, max_round)

        def resolve(source: str) -> str | None:
            if source.startswith("slot:"):
                return slots[int(source.removeprefix("slot:"))]
            if source.startswith("winner:"):
                return winners.get(source.removeprefix("winner:"))
            raise ValueError("Tournament Lab draw contains unsupported participant source")

        for node in sorted(
            bracket.nodes, key=lambda value: (value.round_number, value.round_sequence)
        ):
            if node.round_number > effective_stop:
                break
            player_a_id = resolve(node.source_top)
            player_b_id = resolve(node.source_bottom)
            if player_a_id is None and player_b_id is None:
                winners[node.node_id] = None
                results.append(
                    TournamentLabMatchResult(
                        node_id=node.node_id,
                        round_number=node.round_number,
                        round_sequence=node.round_sequence,
                        player_a_id=None,
                        player_b_id=None,
                        winner_player_id=None,
                        loser_player_id=None,
                        status="empty_advance",
                    )
                )
                continue
            if player_a_id is None or player_b_id is None:
                winner = player_b_id if player_a_id is None else player_a_id
                winners[node.node_id] = winner
                results.append(
                    TournamentLabMatchResult(
                        node_id=node.node_id,
                        round_number=node.round_number,
                        round_sequence=node.round_sequence,
                        player_a_id=player_a_id,
                        player_b_id=player_b_id,
                        winner_player_id=winner,
                        loser_player_id=None,
                        status="bye_advance",
                    )
                )
                continue

            player_a = participants[player_a_id]
            player_b = participants[player_b_id]
            context = MatchContext(
                match_id=f"{scenario.scenario_id}:{node.node_id}",
                player_a=player_a,
                player_b=player_b,
                best_of=scenario.match_format.best_of,
                games_to=scenario.match_format.games_to,
                win_by=scenario.match_format.win_by,
                upset_variance=scenario.match_format.upset_variance,
            )
            seed = self._node_seed(match_seed, node.node_id)
            raw = MatchEngine(rng=DeterministicRng(seed)).simulate(context)
            winners[node.node_id] = raw.winner_player_id
            results.append(self._match_result(node, raw, seed=seed))

        final_node = max(
            bracket.nodes, key=lambda value: (value.round_number, value.round_sequence)
        )
        bracket_complete = effective_stop == max_round
        winner = winners.get(final_node.node_id) if bracket_complete else None
        return results, winner

    @staticmethod
    def _match_result(node, raw: MatchResult, *, seed: int) -> TournamentLabMatchResult:
        return TournamentLabMatchResult(
            node_id=node.node_id,
            round_number=node.round_number,
            round_sequence=node.round_sequence,
            player_a_id=raw.player_a_id,
            player_b_id=raw.player_b_id,
            winner_player_id=raw.winner_player_id,
            loser_player_id=raw.loser_player_id,
            status="played",
            match_seed=seed,
            result_fingerprint=_fingerprint(raw.model_dump(mode="json")),
            set_scores=tuple(_set_score(raw, item.set_number) for item in raw.sets),
            rally_count=len(raw.rally_log.events) if raw.rally_log is not None else 0,
            elapsed_seconds=(
                raw.timeline_log.total_elapsed_seconds
                if raw.timeline_log is not None
                else 0.0
            ),
        )

    @staticmethod
    def _assertions(
        scenario: TournamentLabScenario,
        *,
        champion: str | None,
        played_match_count: int,
        tournament_complete: bool,
        champion_applicable: bool = True,
    ) -> tuple[TournamentLabAssertionResult, ...]:
        rows: list[TournamentLabAssertionResult] = []
        expected_champion = scenario.assertions.expected_champion_player_id
        if expected_champion is not None:
            if not tournament_complete or not champion_applicable:
                status: Literal["passed", "failed", "not_evaluated"] = "not_evaluated"
            else:
                status = "passed" if champion == expected_champion else "failed"
            rows.append(
                TournamentLabAssertionResult(
                    assertion="expected_champion_player_id",
                    status=status,
                    expected=expected_champion,
                    actual=champion,
                )
            )
        expected_matches = scenario.assertions.expected_played_match_count
        if expected_matches is not None:
            rows.append(
                TournamentLabAssertionResult(
                    assertion="expected_played_match_count",
                    status="passed" if played_match_count == expected_matches else "failed",
                    expected=str(expected_matches),
                    actual=str(played_match_count),
                )
            )
        return tuple(rows)


def _set_score(result: MatchResult, set_number: int) -> str:
    item = result.sets[set_number - 1]
    if item.winner_player_id == result.player_a_id:
        return f"{item.winner_games}-{item.loser_games}"
    return f"{item.loser_games}-{item.winner_games}"


def _lab_participant(player_id: str, base: int) -> MatchParticipantContext:
    from beta_engine.domain.players import HiddenCareerTraits, Player

    player = Player(
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
    return MatchParticipantContext(player=player)


def _built_ins() -> tuple[BuiltInTournamentLabScenario, ...]:
    participants = tuple(
        _lab_participant(f"TL-P{index}", 90 - index * 3)
        for index in range(1, 9)
    )
    scenario = TournamentLabScenario(
        scenario_id="standard-eight-player-knockout",
        display_name="Standard 8-player knockout",
        format_kind="knockout",
        participants=participants,
        main_draw_size=8,
        seed_order_player_ids=tuple(item.player.player_id for item in participants),
        draw_seed=20261002,
        match_seed=7001,
        assertions=TournamentLabAssertions(expected_played_match_count=7),
    )
    unusual = scenario.model_copy(
        update={
            "scenario_id": "oversized-eight-player-lab-bracket",
            "display_name": "8 players in a 16-slot Lab bracket",
            "main_draw_size": 16,
            "draw_seed": 20261003,
            "match_seed": 7002,
        }
    )
    qualification_participants = tuple(
        _lab_participant(f"TLQ-P{index}", 96 - index * 2)
        for index in range(1, 15)
    )
    qualification = TournamentLabScenario(
        scenario_id="qualification-two-sections-to-eight-main",
        display_name="2× Qualification sections → 8-player Main",
        format_kind="knockout",
        participants=qualification_participants,
        main_draw_size=8,
        qualification_draw_size=8,
        qualifier_spots=2,
        qualification_player_ids=tuple(
            item.player.player_id for item in qualification_participants[6:]
        ),
        seed_order_player_ids=tuple(
            item.player.player_id for item in qualification_participants
        ),
        draw_seed=20261004,
        match_seed=7003,
        assertions=TournamentLabAssertions(expected_played_match_count=13),
    )
    group_participants = tuple(
        _lab_participant(f"TLG-P{index}", 100 - index * 5)
        for index in range(1, 9)
    )
    group_seed_placements = (
        TournamentGroupSeedPlacement(seed_number=1, group_index=1, slot_index=1),
        TournamentGroupSeedPlacement(seed_number=2, group_index=2, slot_index=1),
        TournamentGroupSeedPlacement(seed_number=3, group_index=2, slot_index=2),
        TournamentGroupSeedPlacement(seed_number=4, group_index=1, slot_index=2),
    )
    pure_groups = TournamentLabScenario(
        scenario_id="two-groups-of-four",
        display_name="2 groups × 4 players",
        format_kind="groups",
        participants=group_participants,
        main_draw_size=8,
        group_count=2,
        group_size=4,
        seeded_slots_per_group=2,
        group_seed_placements=group_seed_placements,
        group_match_best_of=5,
        topology_seed=20261005,
        seed_order_player_ids=tuple(item.player.player_id for item in group_participants),
        draw_seed=20261005,
        match_seed=7004,
        match_format=TournamentLabMatchFormat(upset_variance=0.0),
        assertions=TournamentLabAssertions(expected_played_match_count=12),
    )
    hybrid = pure_groups.model_copy(
        update={
            "scenario_id": "two-groups-to-four-player-knockout",
            "display_name": "2 groups × 4 → 4-player knockout",
            "format_kind": "groups_knockout",
            "advancing_per_group": 2,
            "knockout_crossings": (
                TournamentGroupCrossingMatch(
                    match_index=1,
                    top={"group_index": 1, "finishing_position": 1},
                    bottom={"group_index": 2, "finishing_position": 2},
                ),
                TournamentGroupCrossingMatch(
                    match_index=2,
                    top={"group_index": 2, "finishing_position": 1},
                    bottom={"group_index": 1, "finishing_position": 2},
                ),
            ),
            "topology_seed": 20261006,
            "match_seed": 7005,
            "assertions": TournamentLabAssertions(expected_played_match_count=15),
        }
    )
    definitions = (
        (
            scenario,
            "Normal classic knockout baseline using shared draw and Match Engine kernels.",
        ),
        (
            unusual,
            "Runnable Lab-only geometry that deliberately differs from normal Run capacity derivation.",
        ),
        (
            qualification,
            "Two equal canonical Q sections resolve Q1/Q2 before the shared 8-player Main Draw.",
        ),
        (
            pure_groups,
            "Two equal round-robin groups using shared topology, schedule and standings authorities.",
        ),
        (
            hybrid,
            "Two round-robin groups feeding explicit A1/B2 and B1/A2 configured crossings into a shared hybrid knockout bracket.",
        ),
    )
    return tuple(
        BuiltInTournamentLabScenario(
            scenario_id=item.scenario_id,
            display_name=item.display_name,
            description=description,
            scenario_fingerprint=item.fingerprint,
            scenario=item,
        )
        for item, description in definitions
    )


BUILT_IN_TOURNAMENT_LAB_SCENARIOS = _built_ins()
BUILT_IN_TOURNAMENT_LAB_BY_ID = {
    item.scenario_id: item for item in BUILT_IN_TOURNAMENT_LAB_SCENARIOS
}

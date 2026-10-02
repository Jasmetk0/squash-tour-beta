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
from beta_engine.domain.tournaments.draw_authority import (
    TournamentDrawAuthority,
    TournamentDrawAuthorityBuilder,
)
from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthority,
    canonical_classic_seed_count,
)
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldCapacity
from beta_engine.domain.tournaments.format_authority import TournamentFormatAuthority
from beta_engine.infrastructure.db.models import TournamentLabSessionModel


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


class TournamentLabScenario(BaseModel):
    """Portable Tournament Lab draft; validation diagnostics decide whether it can execute."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["tournament_test_lab_scenario.v1"] = TOURNAMENT_LAB_SCENARIO_VERSION
    scenario_id: str = Field(min_length=1, max_length=160)
    display_name: str = Field(min_length=1, max_length=160)
    format_kind: str = Field(min_length=1, max_length=80)
    participants: tuple[MatchParticipantContext, ...] = Field(min_length=2, max_length=128)
    main_draw_size: int = Field(ge=2, le=128)
    seed_order_player_ids: tuple[str, ...] = ()
    draw_seed: int
    match_seed: int
    match_format: TournamentLabMatchFormat = TournamentLabMatchFormat()
    stop_after_round: int | None = Field(default=None, ge=1, le=7)
    assertions: TournamentLabAssertions = TournamentLabAssertions()
    source_kind: Literal["portable", "built_in_copy", "run_snapshot_copy"] = "portable"
    source_reference: str | None = Field(default=None, max_length=500)
    source_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

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
    draw: TournamentDrawAuthority | None = None
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


class TournamentLabSessionUpdateRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_session_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    scenario: TournamentLabScenario


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
    ):
        self._session_factory = session_factory
        self._id_factory = id_factory

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

        if scenario.format_kind != "knockout":
            issues.append(
                TournamentLabIssue(
                    severity="error",
                    code="FORMAT_NOT_EXECUTABLE_V1",
                    message=(
                        f"Tournament Lab V1 does not yet execute {scenario.format_kind!r}; "
                        "the draft remains inspectable and no authoritative-looking result is fabricated."
                    ),
                )
            )

        if scenario.main_draw_size & (scenario.main_draw_size - 1):
            issues.append(
                TournamentLabIssue(
                    severity="error",
                    code="MAIN_DRAW_NOT_POWER_OF_TWO",
                    message="Classic knockout Main Draw capacity must be a power of two.",
                )
            )
        if len(ids) > scenario.main_draw_size:
            issues.append(
                TournamentLabIssue(
                    severity="error",
                    code="FIELD_EXCEEDS_MAIN_DRAW",
                    message="Participant field exceeds configured Main Draw capacity.",
                )
            )

        seed_order = scenario.seed_order_player_ids or ids
        if len(seed_order) != len(ids) or set(seed_order) != expected_order:
            issues.append(
                TournamentLabIssue(
                    severity="error",
                    code="SEED_ORDER_NOT_FIELD_PERMUTATION",
                    message="Seed order must contain every participant exactly once.",
                )
            )

        canonical_capacity = 1 << (len(ids) - 1).bit_length()
        if scenario.main_draw_size != canonical_capacity:
            issues.append(
                TournamentLabIssue(
                    severity="warning",
                    code="NONCANONICAL_CLASSIC_CAPACITY",
                    message=(
                        f"Normal Run classic geometry would derive capacity {canonical_capacity} "
                        f"for {len(ids)} entrants, not {scenario.main_draw_size}."
                    ),
                )
            )

        if (
            scenario.match_format.best_of,
            scenario.match_format.games_to,
            scenario.match_format.win_by,
        ) != (5, 11, 2):
            issues.append(
                TournamentLabIssue(
                    severity="warning",
                    code="NONSTANDARD_MATCH_FORMAT",
                    message=(
                        "The Match Engine supports this Lab format, but normal FAX Run "
                        "compatibility requires BO5 to 11, win by 2 unless an effective "
                        "Tournament Edition override explicitly supports otherwise."
                    ),
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
        return TournamentLabCompatibility(
            runnable_in_lab=runnable,
            normal_run_compatible=normal_run_compatible,
            shared_authorities=(
                "beta_engine.domain.tournaments.format_authority.TournamentFormatAuthority",
                "beta_engine.domain.tournaments.draw_authority.TournamentDrawAuthorityBuilder",
                "beta_engine.domain.matches.match_engine.MatchEngine.simulate",
            ),
            issues=tuple(issues),
        )

    def run(self, request: TournamentLabRequest) -> TournamentLabResult:
        scenario = request.scenario
        compatibility = self.inspect(scenario)
        request_fingerprint = _fingerprint(request.model_dump(mode="json"))
        if not compatibility.runnable_in_lab:
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

        format_authority, draw_input, draw = self._build_draw(scenario)
        runs = tuple(
            self._execute_draw(scenario, draw, match_seed=match_seed)
            for match_seed in request.effective_match_seeds
        )
        champions = Counter(
            row.champion_player_id
            for row in runs
            if row.champion_player_id is not None
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
            format_authority_fingerprint=format_authority.fingerprint,
            draw_input_fingerprint=draw_input.fingerprint,
            draw_authority_fingerprint=draw.fingerprint,
            draw=draw,
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
        capacity = TournamentEntryFieldCapacity(
            main_draw_size=scenario.main_draw_size,
            bye_slots=scenario.main_draw_size - len(player_ids),
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
            configured_by_command_id="tournament-lab-format-v1",
            entry_field_fingerprint=entry_fp,
            format_kind="knockout",
        )
        seed_count = canonical_classic_seed_count(
            bracket_capacity=capacity.main_draw_size,
            actual_player_count=len(player_ids),
        )
        draw_input = TournamentDrawInputAuthority(
            schema_version="tournament_draw_input_authority.v2",
            run_id=f"lab:{scenario.scenario_id}",
            branch_id="isolated",
            event_id=f"lab-event:{scenario.scenario_id}",
            committed_by_command_id="tournament-lab-draw-input-v1",
            draw_seed=scenario.draw_seed,
            main_seed_count=seed_count,
            qualification_seed_count=0,
            field_sequence=1,
            capacity=capacity,
            tournament_ranking_authority_fingerprint=source_fp,
            ranking_snapshot_fingerprint=source_fp,
            entry_field_fingerprint=entry_fp,
            direct_main_player_ids=seed_order,
            qualification_player_ids=(),
            qualifier_placeholder_ids=(),
            withdrawn_player_ids=(),
            main_seed_player_ids=seed_order[:seed_count],
            qualification_seed_player_ids=(),
        )
        draw = TournamentDrawAuthorityBuilder.build(
            draw_input=draw_input,
            command_id="tournament-lab-draw-v1",
            algorithm_version="idealized_seed_tiers.v2",
        )
        return format_authority, draw_input, draw

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
        slots = {
            slot.slot_index: (
                slot.player_id if slot.entrant_kind == "player" else None
            )
            for slot in draw.main.slots
        }
        winners: dict[str, str | None] = {}
        results: list[TournamentLabMatchResult] = []
        max_round = max(node.round_number for node in draw.main.nodes)
        stop_round = min(scenario.stop_after_round or max_round, max_round)

        def resolve(source: str) -> str | None:
            if source.startswith("slot:"):
                return slots[int(source.removeprefix("slot:"))]
            if source.startswith("winner:"):
                return winners.get(source.removeprefix("winner:"))
            raise ValueError("Tournament Lab draw contains unsupported participant source")

        for node in sorted(
            draw.main.nodes, key=lambda value: (value.round_number, value.round_sequence)
        ):
            if node.round_number > stop_round:
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

        tournament_complete = stop_round == max_round
        final_node = max(
            draw.main.nodes, key=lambda value: (value.round_number, value.round_sequence)
        )
        champion = winners.get(final_node.node_id) if tournament_complete else None
        played = sum(item.status == "played" for item in results)
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
            "results": [item.model_dump(mode="json") for item in results],
            "assertions": [item.model_dump(mode="json") for item in assertions],
        }
        return TournamentLabSingleRun(
            match_seed=match_seed,
            completed_rounds=stop_round,
            tournament_complete=tournament_complete,
            champion_player_id=champion,
            played_match_count=played,
            bye_advance_count=sum(item.status == "bye_advance" for item in results),
            match_results=tuple(results),
            assertions=assertions,
            run_fingerprint=_fingerprint(payload),
        )

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
    ) -> tuple[TournamentLabAssertionResult, ...]:
        rows: list[TournamentLabAssertionResult] = []
        expected_champion = scenario.assertions.expected_champion_player_id
        if expected_champion is not None:
            if not tournament_complete:
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
    definitions = (
        (
            scenario,
            "Normal classic knockout baseline using shared draw and Match Engine kernels.",
        ),
        (
            unusual,
            "Runnable Lab-only geometry that deliberately differs from normal Run capacity derivation.",
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

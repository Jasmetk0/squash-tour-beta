"""Independent, optimistic-concurrency Player Lab sessions."""

from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator
from sqlalchemy import select, text

from beta_engine.application.historical_lab_source import historical_lab_source
from beta_engine.application.player_test_lab_service import (
    PlayerLabScenario,
    PlayerLabScenarioV2,
    PlayerLabVariant,
    parse_player_lab_scenario,
)
from beta_engine.domain.players.calendar_sporting_week import (
    CalendarAnnualDevelopmentPolicy,
)
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.calendar_tour import effective_policy
from beta_engine.infrastructure.db.models import PlayerLabSessionModel


class PlayerLabSession(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    session_id: str
    display_name: str = Field(min_length=1, max_length=160)
    version: int = Field(ge=1)
    scenario: PlayerLabScenario | PlayerLabScenarioV2

    @computed_field
    @property
    def session_fingerprint(self) -> str:
        return canonical_hash(
            self.model_dump(mode="json", exclude={"session_fingerprint"})
        )


class PlayerLabSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(min_length=1, max_length=160)
    scenario: PlayerLabScenario | PlayerLabScenarioV2
    expected_session_fingerprint: str | None = None

    @field_validator("scenario", mode="before")
    @classmethod
    def normalize_scenario(cls, value):
        return parse_player_lab_scenario(value)


class PlayerLabHistoricalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_run_id: str = Field(min_length=1, max_length=128)
    branch_id: str = Field(min_length=1, max_length=128)
    saved_revision_id: str = Field(min_length=1, max_length=128)
    player_id: str = Field(min_length=1, max_length=128)
    duration_weeks: int = Field(default=8, ge=1, le=61)
    seed: int = 1


class PlayerLabSessionService:
    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def _read(row):
        if row is None:
            raise KeyError("Player Lab session was not found")
        item = PlayerLabSession.model_validate_json(row.payload_json)
        if (
            item.session_id != row.session_id
            or item.session_fingerprint != row.fingerprint
        ):
            raise ValueError("Player Lab session integrity mismatch")
        return item

    def list_sessions(self):
        with self.repository._session_factory() as session:
            return [
                self._read(row)
                for row in session.scalars(
                    select(PlayerLabSessionModel).order_by(
                        PlayerLabSessionModel.session_id
                    )
                )
            ]

    def get(self, session_id):
        with self.repository._session_factory() as session:
            return self._read(session.get(PlayerLabSessionModel, session_id))

    def save(self, request, session_id=None):
        with self.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            previous = (
                self._read(session.get(PlayerLabSessionModel, session_id))
                if session_id
                else None
            )
            if (
                previous
                and previous.session_fingerprint != request.expected_session_fingerprint
            ):
                raise ValueError("Player Lab session changed since it was reviewed")
            item = PlayerLabSession(
                session_id=session_id or str(uuid4()),
                display_name=request.display_name,
                version=previous.version + 1 if previous else 1,
                scenario=request.scenario,
            )
            row = (
                session.get(PlayerLabSessionModel, item.session_id)
                if previous
                else PlayerLabSessionModel(session_id=item.session_id)
            )
            row.fingerprint = item.session_fingerprint
            row.payload_json = item.model_dump_json(exclude={"session_fingerprint"})
            session.add(row)
            return item

    def import_player(self, request):
        with historical_lab_source(
            self.repository,
            run_id=request.product_run_id,
            branch_id=request.branch_id,
            revision_id=request.saved_revision_id,
        ) as source:
            snapshot = source.player(request.player_id)
            if snapshot.health is None:
                raise ValueError(
                    "Player Lab requires a stored Health authority; absent Health cannot be replaced with a healthy profile"
                )
            from beta_engine.domain.rankings.official import RankingWeek

            if isinstance(source.sporting.week, RankingWeek):
                return PlayerLabScenario(
                    scenario_id=f"history:{request.saved_revision_id}:{request.player_id}",
                    player=snapshot.player,
                    birth_year=snapshot.biography["birth_year"],
                    birth_year_week=snapshot.biography["birth_year_week"],
                    start_week=source.sporting.week,
                    development_policy=source.sporting.effective_development_policy,
                    source_kind="run_snapshot_copy",
                    source_reference=f"{request.product_run_id}/{request.branch_id}/{request.saved_revision_id}",
                    source_fingerprint=snapshot.fingerprint,
                    source_snapshot=snapshot,
                    variants=tuple(
                        PlayerLabVariant(
                            variant_id=name,
                            display_name=label,
                            competitive_match_counts=(count,) * request.duration_weeks,
                            health_timeline=(snapshot.health,)
                            * (request.duration_weeks + 1),
                        )
                        for name, label, count in (
                            ("active", "One competitive match per week", 1),
                            ("idle", "No competitive matches", 0),
                        )
                    ),
                )
            policy = (
                effective_policy(source.inputs.tour, source.week).development
                if source.inputs.tour is not None
                else CalendarAnnualDevelopmentPolicy()
            )
            return PlayerLabScenarioV2(
                scenario_id=f"history:{request.saved_revision_id}:{request.player_id}",
                player=snapshot.player,
                birth_year=snapshot.biography["birth_year"],
                birth_year_week=snapshot.biography["birth_year_week"],
                start_week=source.week,
                development_policy=policy,
                seed=request.seed,
                initial_health=snapshot.health,
                source_snapshot=snapshot,
                variants=tuple(
                    PlayerLabVariant(
                        variant_id=name,
                        display_name=label,
                        competitive_match_counts=(count,) * request.duration_weeks,
                    )
                    for name, label, count in (
                        ("active", "One competitive match per week", 1),
                        ("idle", "No competitive matches", 0),
                    )
                ),
            )

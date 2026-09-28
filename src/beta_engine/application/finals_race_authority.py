"""Application boundary for canonical World Tour Finals Race season authority."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field

from beta_engine.application.calendar_package_run_adapter import CalendarPackageRunAdapter
from beta_engine.application.finals_race_projection import (
    build_canonical_world_tour_finals_race_snapshot,
)
from beta_engine.domain.finals import (
    WorldTourFinalsRaceConfiguration,
    WorldTourFinalsRaceSnapshot,
)
from beta_engine.domain.rankings.official import (
    FrozenInput,
    RankingWeek,
    load_official_ranking_snapshot,
)
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
from beta_engine.infrastructure.db.finals_race_authority import (
    WorldTourFinalsRaceAuthorityStore,
)
from beta_engine.infrastructure.db.models import (
    PublishedOfficialRankingModel,
    RankingTransitionAuthorityModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.run_package_state import get_run_package_state


class WorldTourFinalsRaceConfigurationCommand(FrozenInput):
    schema_version: str = "world_tour_finals_race_configuration_command.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    target_season_index: int = Field(ge=0, le=49)
    finals_event_id: str = Field(min_length=1)
    best_n: int = Field(ge=1)
    eligible_categories: tuple[str, ...]
    cutoff_week: RankingWeek
    command_id: str = Field(min_length=1, max_length=128)


@dataclass(slots=True)
class WorldTourFinalsRaceAuthorityService:
    factory: object

    @staticmethod
    def _season_label(season_index: int) -> str:
        start = 2000 + season_index
        return f"{start}/{start + 1}"

    def _calendar(
        self,
        session,
        *,
        run_id: str,
        branch_id: str,
        target_season_index: int,
    ):
        state = get_run_package_state(
            session,
            run_id=run_id,
            branch_id=branch_id,
        )
        if state is None:
            raise ValueError("Canonical Finals Race requires Run Package state")
        season = self._season_label(target_season_index)
        return CalendarPackageRunAdapter.project_calendar(
            state,
            package_id=CalendarPackageRunAdapter.package_id_for_season(season),
        )

    @staticmethod
    def _publication(
        session,
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
    ):
        row = session.get(
            PublishedOfficialRankingModel,
            (run_id, branch_id, week.ordinal),
        )
        if row is None:
            raise ValueError(
                "Finals Race cutoff requires an existing published Official Ranking"
            )
        return load_official_ranking_snapshot(
            row.payload_json,
            expected_fingerprint=row.snapshot_fingerprint,
            run_id=run_id,
            branch_id=branch_id,
            week=week,
        )

    @staticmethod
    def _transition(
        session,
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
    ) -> RankingTransitionAuthority:
        row = session.get(
            RankingTransitionAuthorityModel,
            (run_id, branch_id, week.ordinal),
        )
        if row is None:
            raise ValueError("Finals Race cutoff requires Ranking Transition authority")
        authority = RankingTransitionAuthority.model_validate_json(row.payload_json)
        if (
            authority.run_id,
            authority.branch_id,
            authority.target_week,
            authority.fingerprint,
        ) != (
            run_id,
            branch_id,
            week,
            row.fingerprint,
        ):
            raise ValueError("Finals Race Ranking Transition identity mismatch")
        return authority

    @staticmethod
    def _validate_cutoff_pair(publication, transition: RankingTransitionAuthority) -> None:
        if publication.policy != transition.policy:
            raise ValueError(
                "Finals Race cutoff publication policy differs from Ranking Transition"
            )
        transition_ids = {player.player_id for player in transition.players}
        if any(row.player_id not in transition_ids for row in publication.rows):
            raise ValueError(
                "Finals Race published cutoff roster differs from Ranking Transition"
            )

    def create_configuration(
        self,
        command: WorldTourFinalsRaceConfigurationCommand,
    ) -> WorldTourFinalsRaceConfiguration:
        if command.cutoff_week.season_index != command.target_season_index:
            raise ValueError("Finals Race cutoff week must belong to configured season")

        raw_categories = tuple(value.strip() for value in command.eligible_categories)
        if (
            not raw_categories
            or any(not value for value in raw_categories)
            or len(raw_categories) != len(set(raw_categories))
        ):
            raise ValueError(
                "Finals Race eligible categories must be unique and non-empty"
            )
        categories = tuple(sorted(raw_categories))

        with self.factory.begin() as session:
            calendar = self._calendar(
                session,
                run_id=command.run_id,
                branch_id=command.branch_id,
                target_season_index=command.target_season_index,
            )
            events = {event.event_id: event for event in calendar.calendar.events}
            finals_event = events.get(command.finals_event_id)
            if finals_event is None:
                raise ValueError(
                    "Finals Race configuration requires a Finals Edition in frozen Calendar"
                )
            if finals_event.season != calendar.season:
                raise ValueError("Finals Race Edition belongs to another Calendar season")
            if command.cutoff_week.week > finals_event.season_week:
                raise ValueError(
                    "Finals Race cutoff cannot be later than the configured Finals Edition"
                )
            available_categories = {
                event.category for event in calendar.calendar.events
            }
            missing = sorted(set(categories) - available_categories)
            if missing:
                raise ValueError(
                    "Finals Race categories are absent from frozen Run Calendar: "
                    + ", ".join(missing)
                )

            publication = self._publication(
                session,
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=command.cutoff_week,
            )
            transition = self._transition(
                session,
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=command.cutoff_week,
            )
            self._validate_cutoff_pair(publication, transition)

            configuration = WorldTourFinalsRaceConfiguration(
                run_id=command.run_id,
                branch_id=command.branch_id,
                target_season_index=command.target_season_index,
                finals_event_id=command.finals_event_id,
                eligible_categories=categories,
                best_n=command.best_n,
                cutoff_week=command.cutoff_week,
                cutoff_official_ranking_fingerprint=publication.fingerprint,
                cutoff_transition_fingerprint=transition.fingerprint,
                calendar_content_fingerprint=calendar.content_fingerprint,
                adopted_by_command_id=command.command_id,
            )
            return WorldTourFinalsRaceAuthorityStore(session).put_configuration(
                configuration
            )

    def build_snapshot(
        self,
        *,
        run_id: str,
        branch_id: str,
        target_season_index: int,
    ) -> WorldTourFinalsRaceSnapshot:
        with self.factory.begin() as session:
            store = WorldTourFinalsRaceAuthorityStore(session)
            existing = store.get_snapshot(
                run_id=run_id,
                branch_id=branch_id,
                target_season_index=target_season_index,
            )
            if existing is not None:
                return existing

            configuration = store.get_configuration(
                run_id=run_id,
                branch_id=branch_id,
                target_season_index=target_season_index,
            )
            if configuration is None:
                raise ValueError(
                    "Finals Race snapshot requires persisted season configuration"
                )

            calendar = self._calendar(
                session,
                run_id=run_id,
                branch_id=branch_id,
                target_season_index=target_season_index,
            )
            if calendar.content_fingerprint != configuration.calendar_content_fingerprint:
                raise ValueError(
                    "Finals Race Calendar changed after season configuration"
                )

            publication = self._publication(
                session,
                run_id=run_id,
                branch_id=branch_id,
                week=configuration.cutoff_week,
            )
            if (
                publication.fingerprint
                != configuration.cutoff_official_ranking_fingerprint
            ):
                raise ValueError(
                    "Finals Race cutoff publication changed after configuration"
                )

            transition = self._transition(
                session,
                run_id=run_id,
                branch_id=branch_id,
                week=configuration.cutoff_week,
            )
            if transition.fingerprint != configuration.cutoff_transition_fingerprint:
                raise ValueError(
                    "Finals Race cutoff transition changed after configuration"
                )
            self._validate_cutoff_pair(publication, transition)

            sources = OwnedTournamentRankingSourceStore(session).history(
                run_id=run_id,
                branch_id=branch_id,
            )
            snapshot = build_canonical_world_tour_finals_race_snapshot(
                configuration=configuration,
                calendar=calendar,
                cutoff_publication=publication,
                transition_authority=transition,
                tournament_sources=sources,
            )
            return store.put_snapshot(snapshot)

    def inspect(
        self,
        *,
        run_id: str,
        branch_id: str,
        target_season_index: int,
    ) -> tuple[
        WorldTourFinalsRaceConfiguration | None,
        WorldTourFinalsRaceSnapshot | None,
    ]:
        with self.factory() as session:
            store = WorldTourFinalsRaceAuthorityStore(session)
            return (
                store.get_configuration(
                    run_id=run_id,
                    branch_id=branch_id,
                    target_season_index=target_season_index,
                ),
                store.get_snapshot(
                    run_id=run_id,
                    branch_id=branch_id,
                    target_season_index=target_season_index,
                ),
            )

"""Explicit Admin application boundary for canonical World Tour Finals Race."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field

from beta_engine.application.calendar_package_run_adapter import CalendarPackageRunAdapter
from beta_engine.application.finals_race_projection import (
    project_canonical_finals_race_snapshot,
)
from beta_engine.domain.finals import FinalsRaceConfiguration, FinalsRaceSnapshot
from beta_engine.domain.rankings.official import (
    FrozenInput,
    RankingWeek,
    load_official_ranking_snapshot,
)
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
from beta_engine.infrastructure.db.finals_race_authority import (
    FinalsRaceAuthorityStore,
)
from beta_engine.infrastructure.db.models import (
    PublishedOfficialRankingModel,
    RankingTransitionAuthorityModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.run_package_state import get_run_package_state


class FinalsRaceConfigurationCommand(FrozenInput):
    schema_version: str = "finals_race_configuration_command.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    season_index: int = Field(ge=0, le=49)
    best_n_results: int = Field(ge=1)
    eligible_categories: tuple[str, ...]
    cutoff_ranking_week: RankingWeek
    command_id: str = Field(min_length=1, max_length=128)


@dataclass(slots=True)
class FinalsRaceAuthorityService:
    factory: object

    @staticmethod
    def _season_label(season_index: int) -> str:
        start = 2000 + season_index
        return f"{start}/{start + 1}"

    def _calendar(self, session, *, run_id: str, branch_id: str, season_index: int):
        state = get_run_package_state(
            session,
            run_id=run_id,
            branch_id=branch_id,
        )
        if state is None:
            raise ValueError(
                "Canonical Finals Race requires Run Package state"
            )
        season = self._season_label(season_index)
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
            raise ValueError(
                "Finals Race cutoff requires Ranking Transition authority"
            )
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

    def create_configuration(
        self,
        command: FinalsRaceConfigurationCommand,
    ) -> FinalsRaceConfiguration:
        if command.cutoff_ranking_week.season_index != command.season_index:
            raise ValueError(
                "Finals Race cutoff week must belong to configured season"
            )
        categories = tuple(value.strip() for value in command.eligible_categories)
        if categories != tuple(sorted(set(categories))) or not categories or any(
            not value for value in categories
        ):
            raise ValueError(
                "Finals Race eligible categories must be unique, sorted and non-empty"
            )

        with self.factory.begin() as session:
            calendar = self._calendar(
                session,
                run_id=command.run_id,
                branch_id=command.branch_id,
                season_index=command.season_index,
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
                week=command.cutoff_ranking_week,
            )
            transition = self._transition(
                session,
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=command.cutoff_ranking_week,
            )
            if publication.policy != transition.policy:
                raise ValueError(
                    "Finals Race cutoff publication policy differs from Ranking Transition"
                )
            configuration = FinalsRaceConfiguration(
                run_id=command.run_id,
                branch_id=command.branch_id,
                season_index=command.season_index,
                best_n_results=command.best_n_results,
                eligible_categories=categories,
                cutoff_ranking_week=command.cutoff_ranking_week,
                cutoff_ranking_snapshot_fingerprint=publication.fingerprint,
                cutoff_transition_fingerprint=transition.fingerprint,
                calendar_content_fingerprint=calendar.content_fingerprint,
                adopted_by_command_id=command.command_id,
            )
            return FinalsRaceAuthorityStore(session).put_configuration(
                configuration
            )

    def build_snapshot(
        self,
        *,
        run_id: str,
        branch_id: str,
        season_index: int,
    ) -> FinalsRaceSnapshot:
        with self.factory.begin() as session:
            store = FinalsRaceAuthorityStore(session)
            existing = store.get_snapshot(
                run_id=run_id,
                branch_id=branch_id,
                season_index=season_index,
            )
            if existing is not None:
                return existing
            configuration = store.get_configuration(
                run_id=run_id,
                branch_id=branch_id,
                season_index=season_index,
            )
            if configuration is None:
                raise ValueError(
                    "Finals Race snapshot requires persisted configuration"
                )
            calendar = self._calendar(
                session,
                run_id=run_id,
                branch_id=branch_id,
                season_index=season_index,
            )
            publication = self._publication(
                session,
                run_id=run_id,
                branch_id=branch_id,
                week=configuration.cutoff_ranking_week,
            )
            if (
                publication.fingerprint
                != configuration.cutoff_ranking_snapshot_fingerprint
            ):
                raise ValueError(
                    "Finals Race cutoff publication changed after configuration"
                )
            transition = self._transition(
                session,
                run_id=run_id,
                branch_id=branch_id,
                week=configuration.cutoff_ranking_week,
            )
            if transition.fingerprint != configuration.cutoff_transition_fingerprint:
                raise ValueError(
                    "Finals Race cutoff transition changed after configuration"
                )
            if publication.policy != transition.policy:
                raise ValueError(
                    "Finals Race cutoff publication policy differs from Ranking Transition"
                )
            sources = OwnedTournamentRankingSourceStore(session).history(
                run_id=run_id,
                branch_id=branch_id,
            )
            snapshot = project_canonical_finals_race_snapshot(
                configuration=configuration,
                calendar=calendar,
                tournament_sources=sources,
                transition_authority=transition,
            )
            return store.put_snapshot(snapshot)

    def inspect(
        self,
        *,
        run_id: str,
        branch_id: str,
        season_index: int,
    ) -> tuple[FinalsRaceConfiguration | None, FinalsRaceSnapshot | None]:
        with self.factory() as session:
            store = FinalsRaceAuthorityStore(session)
            return (
                store.get_configuration(
                    run_id=run_id,
                    branch_id=branch_id,
                    season_index=season_index,
                ),
                store.get_snapshot(
                    run_id=run_id,
                    branch_id=branch_id,
                    season_index=season_index,
                ),
            )

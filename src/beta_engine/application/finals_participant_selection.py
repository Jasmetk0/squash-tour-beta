"""Application authority for canonical World Tour Finals participant selection."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field

from beta_engine.application.calendar_package_run_adapter import CalendarPackageRunAdapter
from beta_engine.domain.finals import (
    WorldTourFinalsParticipantSelectionConfiguration,
    WorldTourFinalsParticipantSelectionSnapshot,
    WorldTourFinalsRaceSnapshot,
    select_world_tour_finals_participants,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.infrastructure.db.finals_participant_selection import (
    WorldTourFinalsParticipantSelectionStore,
)
from beta_engine.infrastructure.db.finals_race_authority import (
    WorldTourFinalsRaceAuthorityStore,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.run_package_state import get_run_package_state


class WorldTourFinalsParticipantSelectionConfigurationCommand(FrozenInput):
    schema_version: str = (
        "world_tour_finals_participant_selection_configuration_command.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    target_season_index: int = Field(ge=0, le=49)
    direct_entry_event_ids: tuple[str, ...] = ()
    command_id: str = Field(min_length=1, max_length=128)


def resolve_world_tour_finals_direct_entry_winners(
    *,
    configuration: WorldTourFinalsParticipantSelectionConfiguration,
    race_snapshot: WorldTourFinalsRaceSnapshot,
    tournament_sources: tuple[object, ...],
) -> tuple[tuple[str, str], ...]:
    """Resolve configured direct-entry champions from frozen canonical results only."""

    by_event: dict[str, list[object]] = {
        event_id: [] for event_id in configuration.direct_entry_event_ids
    }
    for source in tournament_sources:
        binding = source.binding
        if (binding.run_id, binding.branch_id) != (
            configuration.run_id,
            configuration.branch_id,
        ):
            raise ValueError("Finals direct-entry tournament source scope mismatch")
        if binding.event_id in by_event:
            by_event[binding.event_id].append(source)

    resolved: list[tuple[str, str]] = []
    for event_id in configuration.direct_entry_event_ids:
        matches = by_event[event_id]
        if len(matches) != 1:
            raise ValueError(
                "Finals direct-entry event requires exactly one canonical tournament source"
            )
        source = matches[0]
        binding = source.binding
        result = source.canonical_result
        if result is None:
            raise ValueError(
                "Finals direct-entry event requires canonical Tournament Result authority"
            )
        if binding.completed_week.season_index != configuration.target_season_index:
            raise ValueError("Finals direct-entry result belongs to another season")
        if (
            binding.first_publication_week is None
            or binding.first_publication_week.ordinal > race_snapshot.cutoff_week.ordinal
        ):
            raise ValueError(
                "Finals direct-entry result was not public by the configured Race cutoff"
            )
        if (
            result.run_id,
            result.branch_id,
            result.event_id,
            result.completed_week,
            result.fingerprint,
        ) != (
            configuration.run_id,
            configuration.branch_id,
            event_id,
            binding.completed_week,
            binding.expected_result_fingerprint,
        ):
            raise ValueError("Finals direct-entry canonical result evidence mismatch")
        resolved.append((event_id, result.champion_player_id))
    return tuple(resolved)


@dataclass(slots=True)
class WorldTourFinalsParticipantSelectionAuthorityService:
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
            raise ValueError(
                "Canonical Finals participant selection requires Run Package state"
            )
        season = self._season_label(target_season_index)
        return CalendarPackageRunAdapter.project_calendar(
            state,
            package_id=CalendarPackageRunAdapter.package_id_for_season(season),
        )

    def create_configuration(
        self,
        command: WorldTourFinalsParticipantSelectionConfigurationCommand,
    ) -> WorldTourFinalsParticipantSelectionConfiguration:
        raw_event_ids = tuple(value.strip() for value in command.direct_entry_event_ids)
        if any(not value for value in raw_event_ids) or len(raw_event_ids) != len(
            set(raw_event_ids)
        ):
            raise ValueError(
                "Finals direct-entry event IDs must be unique and non-empty"
            )
        direct_entry_event_ids = tuple(sorted(raw_event_ids))

        with self.factory.begin() as session:
            race_store = WorldTourFinalsRaceAuthorityStore(session)
            race_configuration = race_store.get_configuration(
                run_id=command.run_id,
                branch_id=command.branch_id,
                target_season_index=command.target_season_index,
            )
            race_snapshot = race_store.get_snapshot(
                run_id=command.run_id,
                branch_id=command.branch_id,
                target_season_index=command.target_season_index,
            )
            if race_configuration is None or race_snapshot is None:
                raise ValueError(
                    "Finals participant selection requires persisted canonical Race authority"
                )

            calendar = self._calendar(
                session,
                run_id=command.run_id,
                branch_id=command.branch_id,
                target_season_index=command.target_season_index,
            )
            if calendar.content_fingerprint != race_configuration.calendar_content_fingerprint:
                raise ValueError(
                    "Finals participant selection Calendar differs from Race configuration"
                )

            events = {event.event_id: event for event in calendar.calendar.events}
            finals_event = events.get(race_configuration.finals_event_id)
            if finals_event is None:
                raise ValueError(
                    "Configured Finals Edition is absent from frozen Run Calendar"
                )
            participant_capacity = finals_event.main_draw_size
            if participant_capacity < 1:
                raise ValueError("Configured Finals Edition has no participant capacity")

            for event_id in direct_entry_event_ids:
                event = events.get(event_id)
                if event is None:
                    raise ValueError(
                        "Finals direct-entry event is absent from frozen Run Calendar"
                    )
                if event.event_id == finals_event.event_id:
                    raise ValueError("Finals Edition cannot grant its own direct entry")
                if event.season != finals_event.season:
                    raise ValueError(
                        "Finals direct-entry event belongs to another season"
                    )
                if event.season_week >= finals_event.season_week:
                    raise ValueError(
                        "Finals direct-entry event must precede the Finals Edition"
                    )

            configuration = WorldTourFinalsParticipantSelectionConfiguration(
                run_id=command.run_id,
                branch_id=command.branch_id,
                target_season_index=command.target_season_index,
                finals_event_id=finals_event.event_id,
                participant_capacity=participant_capacity,
                direct_entry_event_ids=direct_entry_event_ids,
                race_snapshot_fingerprint=race_snapshot.fingerprint,
                calendar_content_fingerprint=calendar.content_fingerprint,
                adopted_by_command_id=command.command_id,
            )
            return WorldTourFinalsParticipantSelectionStore(
                session
            ).put_configuration(configuration)

    def build_snapshot(
        self,
        *,
        run_id: str,
        branch_id: str,
        target_season_index: int,
    ) -> WorldTourFinalsParticipantSelectionSnapshot:
        with self.factory.begin() as session:
            selection_store = WorldTourFinalsParticipantSelectionStore(session)
            existing = selection_store.get_snapshot(
                run_id=run_id,
                branch_id=branch_id,
                target_season_index=target_season_index,
            )
            if existing is not None:
                return existing

            configuration = selection_store.get_configuration(
                run_id=run_id,
                branch_id=branch_id,
                target_season_index=target_season_index,
            )
            if configuration is None:
                raise ValueError(
                    "Finals participant-selection snapshot requires stored configuration"
                )

            race_snapshot = WorldTourFinalsRaceAuthorityStore(session).get_snapshot(
                run_id=run_id,
                branch_id=branch_id,
                target_season_index=target_season_index,
            )
            if race_snapshot is None:
                raise ValueError(
                    "Finals participant selection requires persisted Race snapshot"
                )
            if race_snapshot.fingerprint != configuration.race_snapshot_fingerprint:
                raise ValueError(
                    "Finals Race snapshot changed after participant configuration"
                )

            calendar = self._calendar(
                session,
                run_id=run_id,
                branch_id=branch_id,
                target_season_index=target_season_index,
            )
            if calendar.content_fingerprint != configuration.calendar_content_fingerprint:
                raise ValueError(
                    "Finals Calendar changed after participant configuration"
                )

            tournament_sources = OwnedTournamentRankingSourceStore(session).history(
                run_id=run_id,
                branch_id=branch_id,
            )
            winners = resolve_world_tour_finals_direct_entry_winners(
                configuration=configuration,
                race_snapshot=race_snapshot,
                tournament_sources=tournament_sources,
            )
            snapshot = select_world_tour_finals_participants(
                configuration=configuration,
                race_snapshot=race_snapshot,
                direct_entry_winners=winners,
            )
            return selection_store.put_snapshot(snapshot)

    def inspect(
        self,
        *,
        run_id: str,
        branch_id: str,
        target_season_index: int,
    ) -> tuple[
        WorldTourFinalsParticipantSelectionConfiguration | None,
        WorldTourFinalsParticipantSelectionSnapshot | None,
    ]:
        with self.factory() as session:
            store = WorldTourFinalsParticipantSelectionStore(session)
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

"""Application service for canonical World Tour Finals Race snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.application.calendar_package_run_adapter import CalendarPackageRunAdapter
from beta_engine.domain.finals.race import (
    WorldTourFinalsRaceEventAwards,
    WorldTourFinalsRacePlayerAward,
    WorldTourFinalsRaceSnapshot,
    calculate_world_tour_finals_race,
)
from beta_engine.domain.rankings.official import RankingWeek, load_official_ranking_snapshot
from beta_engine.infrastructure.db.models import PublishedOfficialRankingModel
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.run_package_state import get_run_package_state
from beta_engine.infrastructure.db.world_tour_finals_race import (
    WorldTourFinalsRaceSnapshotStore,
)


def _season_label(season_index: int) -> str:
    start = 2000 + season_index
    return f"{start}/{start + 1}"


@dataclass(slots=True)
class WorldTourFinalsRaceService:
    session_factory: object

    def get(
        self, *, run_id: str, branch_id: str, season_index: int
    ) -> WorldTourFinalsRaceSnapshot | None:
        with self.session_factory() as session:
            return WorldTourFinalsRaceSnapshotStore(session).get(
                run_id=run_id, branch_id=branch_id, season_index=season_index
            )

    def create(
        self,
        *,
        run_id: str,
        branch_id: str,
        season_index: int,
        cutoff_week: RankingWeek,
        best_result_count: int,
        eligible_event_ids: tuple[str, ...],
        command_id: str,
    ) -> WorldTourFinalsRaceSnapshot:
        if not command_id.strip():
            raise ValueError("World Tour Finals Race requires a command ID")
        if cutoff_week.season_index != season_index:
            raise ValueError("World Tour Finals Race cutoff belongs to another season")
        eligible_event_ids = tuple(sorted(set(eligible_event_ids)))
        if not eligible_event_ids:
            raise ValueError("World Tour Finals Race requires eligible events")

        with self.session_factory.begin() as session:
            publication = session.get(
                PublishedOfficialRankingModel,
                (run_id, branch_id, cutoff_week.ordinal),
            )
            if publication is None:
                raise ValueError(
                    "World Tour Finals Race cutoff requires a published Official Ranking"
                )
            cutoff = load_official_ranking_snapshot(
                publication.payload_json,
                expected_fingerprint=publication.snapshot_fingerprint,
                run_id=run_id,
                branch_id=branch_id,
                week=cutoff_week,
            )
            package_state = get_run_package_state(
                session, run_id=run_id, branch_id=branch_id
            )
            if package_state is None:
                raise ValueError("World Tour Finals Race requires Run Package state")
            season = _season_label(season_index)
            projection = CalendarPackageRunAdapter.project_calendar(
                package_state,
                package_id=CalendarPackageRunAdapter.package_id_for_season(season),
            )
            calendar_ids = {event.event_id for event in projection.calendar.events}
            missing = sorted(set(eligible_event_ids) - calendar_ids)
            if missing:
                raise ValueError(
                    f"World Tour Finals Race eligible events are absent from Run-owned Calendar: {missing}"
                )

            event_sources = []
            seen_events = set()
            for source in OwnedTournamentRankingSourceStore(session).history(
                run_id=run_id, branch_id=branch_id
            ):
                if source is None:
                    raise ValueError("World Tour Finals Race tournament source identity is missing")
                binding = source.binding
                if (
                    binding.event_id not in eligible_event_ids
                    or binding.completed_week.season_index != season_index
                    or binding.first_publication_week is None
                    or binding.first_publication_week.ordinal > cutoff_week.ordinal
                ):
                    continue
                if binding.event_id in seen_events:
                    raise ValueError("World Tour Finals Race has ambiguous tournament source identity")
                seen_events.add(binding.event_id)
                awards = source.canonical_awards
                if awards is None:
                    raise ValueError(
                        "World Tour Finals Race eligible tournament lacks canonical point awards"
                    )
                if awards.event_id != binding.event_id or awards.completed_week != binding.completed_week:
                    raise ValueError("World Tour Finals Race point-award authority boundary mismatch")
                event_sources.append(
                    WorldTourFinalsRaceEventAwards(
                        event_id=binding.event_id,
                        completed_week=binding.completed_week,
                        first_publication_week=binding.first_publication_week,
                        source_fingerprint=source.fingerprint,
                        awards=tuple(
                            WorldTourFinalsRacePlayerAward(
                                player_id=award.player_id,
                                race_points=award.race_points_awarded,
                                award_fingerprint=award.award_fingerprint,
                            )
                            for award in awards.awards
                        ),
                    )
                )

            snapshot = calculate_world_tour_finals_race(
                run_id=run_id,
                branch_id=branch_id,
                season_index=season_index,
                cutoff_week=cutoff_week,
                cutoff_ranking_fingerprint=cutoff.fingerprint,
                best_result_count=best_result_count,
                eligible_event_ids=eligible_event_ids,
                calendar_projection_fingerprint=projection.content_fingerprint,
                event_sources=tuple(event_sources),
                command_id=command_id.strip(),
            )
            return WorldTourFinalsRaceSnapshotStore(session).append(snapshot)

"""Reviewed bulk Tournament Ranking Snapshot adoption for the copied-FAX current week.

This helper intentionally automates only a provenance-preserving mechanical step:
bind each current-week World Tour Edition to the latest already-published Official
Ranking at or before that week. It does not build Entry Fields, choose applications,
Wild Cards, Draws or any other sporting policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.application.calendar_package_run_adapter import CalendarPackageRunAdapter
from beta_engine.application.canonical_tournament_preparation import (
    CanonicalTournamentPreparationService,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import fingerprint
from beta_engine.infrastructure.db.models import AuthoritativeWorldStateModel
from beta_engine.infrastructure.db.run_package_state import get_run_package_state
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)


class PreAlphaFaxCurrentWeekRankingSnapshotPreview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[
        "pre_alpha_fax_current_week_ranking_snapshot_preview.v1"
    ] = "pre_alpha_fax_current_week_ranking_snapshot_preview.v1"
    run_id: str
    branch_id: str
    current_week: RankingWeek
    event_ids: tuple[str, ...]
    ranking_week: RankingWeek
    ranking_snapshot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_phases: dict[str, str]
    event_ids_requiring_adoption: tuple[str, ...]
    preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class PreAlphaFaxCurrentWeekRankingSnapshotApplyRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    command_id: str = Field(min_length=1, max_length=128)
    expected_preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class PreAlphaFaxCurrentWeekRankingSnapshotApplyResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[
        "pre_alpha_fax_current_week_ranking_snapshot_apply.v1"
    ] = "pre_alpha_fax_current_week_ranking_snapshot_apply.v1"
    run_id: str
    branch_id: str
    current_week: RankingWeek
    ranking_week: RankingWeek
    ranking_snapshot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_ids: tuple[str, ...]
    adopted_event_ids: tuple[str, ...]
    exact_retry_event_ids: tuple[str, ...]
    post_apply_phases: dict[str, str]
    all_ranking_snapshots_ready: bool
    application_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


@dataclass(slots=True)
class PreAlphaFaxCurrentWeekRankingSnapshotService:
    factory: sessionmaker[Session]

    @staticmethod
    def _current_week(session: Session, *, run_id: str, branch_id: str) -> RankingWeek:
        world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
        if world is None:
            raise ValueError(
                "Copied-FAX current-week ranking bootstrap requires an authoritative world head"
            )
        if not 0 <= world.current_ordinal < 50 * 61:
            raise ValueError("Authoritative world head has an invalid week ordinal")
        return RankingWeek(
            season_index=world.current_ordinal // 61,
            week=world.current_ordinal % 61 + 1,
        )

    @staticmethod
    def _calendar_events(
        session: Session,
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
    ):
        state = get_run_package_state(session, run_id=run_id, branch_id=branch_id)
        if state is None:
            raise ValueError("Copied-FAX current-week ranking bootstrap requires Run Package state")
        season = f"{2000 + week.season_index}/{2001 + week.season_index}"
        package_id = CalendarPackageRunAdapter.package_id_for_season(season)
        projection = CalendarPackageRunAdapter.project_calendar(
            state, package_id=package_id
        )
        return tuple(
            sorted(
                (
                    event
                    for event in projection.calendar.events
                    if event.season_week == week.week
                    and event.tour_level == "WORLD_TOUR"
                ),
                key=lambda event: event.event_id,
            )
        )

    @staticmethod
    def _latest_publication(
        session: Session,
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
    ):
        snapshots = TournamentRankingSnapshotAuthorityStore(session).published_rankings(
            run_id=run_id,
            branch_id=branch_id,
        )
        eligible = tuple(snapshot for snapshot in snapshots if snapshot.week.ordinal <= week.ordinal)
        if not eligible:
            raise ValueError(
                "Current-week Tournament Ranking Snapshot bootstrap has no eligible published Official Ranking"
            )
        return eligible[-1]

    @classmethod
    def _preview_in_session(
        cls,
        session: Session,
        *,
        run_id: str,
        branch_id: str,
    ) -> PreAlphaFaxCurrentWeekRankingSnapshotPreview:
        week = cls._current_week(
            session,
            run_id=run_id,
            branch_id=branch_id,
        )
        events = cls._calendar_events(
            session,
            run_id=run_id,
            branch_id=branch_id,
            week=week,
        )
        if not events:
            raise ValueError("Current copied-FAX week has no World Tour Editions")
        ranking = cls._latest_publication(
            session,
            run_id=run_id,
            branch_id=branch_id,
            week=week,
        )
        phases: dict[str, str] = {}
        requiring: list[str] = []
        for event in events:
            preparation = CanonicalTournamentPreparationService.inspect_in_session(
                session,
                run_id=run_id,
                branch_id=branch_id,
                event_id=event.event_id,
            )
            phases[event.event_id] = preparation.phase
            if preparation.phase == "ranking_snapshot_required":
                requiring.append(event.event_id)

        event_ids = tuple(event.event_id for event in events)
        frozen = {
            "schema_version": "pre_alpha_fax_current_week_ranking_snapshot_preview.v1",
            "run_id": run_id,
            "branch_id": branch_id,
            "current_week": week.model_dump(mode="json"),
            "event_ids": list(event_ids),
            "ranking_week": ranking.week.model_dump(mode="json"),
            "ranking_snapshot_fingerprint": ranking.fingerprint,
        }
        return PreAlphaFaxCurrentWeekRankingSnapshotPreview(
            run_id=run_id,
            branch_id=branch_id,
            current_week=week,
            event_ids=event_ids,
            ranking_week=ranking.week,
            ranking_snapshot_fingerprint=ranking.fingerprint,
            event_phases=phases,
            event_ids_requiring_adoption=tuple(requiring),
            preview_fingerprint=fingerprint(frozen),
        )

    def preview(
        self,
        *,
        run_id: str,
        branch_id: str,
    ) -> PreAlphaFaxCurrentWeekRankingSnapshotPreview:
        with self.factory() as session:
            return self._preview_in_session(
                session,
                run_id=run_id,
                branch_id=branch_id,
            )

    def apply(
        self,
        *,
        run_id: str,
        branch_id: str,
        request: PreAlphaFaxCurrentWeekRankingSnapshotApplyRequest,
    ) -> PreAlphaFaxCurrentWeekRankingSnapshotApplyResult:
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            preview = self._preview_in_session(
                session,
                run_id=run_id,
                branch_id=branch_id,
            )
            if preview.preview_fingerprint != request.expected_preview_fingerprint:
                raise ValueError(
                    "Copied-FAX current-week ranking snapshot preview changed since review"
                )

            store = TournamentRankingSnapshotAuthorityStore(session)
            adopted: list[str] = []
            exact_retry: list[str] = []
            for event_id in preview.event_ids:
                existing = store.get(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id=event_id,
                )
                if existing is not None:
                    if (
                        existing.ranking_week != preview.ranking_week
                        or existing.ranking_snapshot_fingerprint
                        != preview.ranking_snapshot_fingerprint
                    ):
                        raise ValueError(
                            f"Tournament {event_id} already froze a different ranking snapshot"
                        )
                    exact_retry.append(event_id)
                    continue
                store.adopt(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id=event_id,
                    ranking_week=preview.ranking_week,
                    command_id=f"{request.command_id}:{event_id}",
                )
                adopted.append(event_id)

            post_phases = {
                event_id: CanonicalTournamentPreparationService.inspect_in_session(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id=event_id,
                ).phase
                for event_id in preview.event_ids
            }
            if any(phase == "ranking_snapshot_required" for phase in post_phases.values()):
                raise ValueError(
                    "Current-week Tournament Ranking Snapshot bootstrap did not advance every event"
                )

            result_payload = {
                "run_id": run_id,
                "branch_id": branch_id,
                "current_week": preview.current_week.model_dump(mode="json"),
                "ranking_week": preview.ranking_week.model_dump(mode="json"),
                "ranking_snapshot_fingerprint": preview.ranking_snapshot_fingerprint,
                "event_ids": list(preview.event_ids),
                "adopted_event_ids": adopted,
                "exact_retry_event_ids": exact_retry,
                "post_apply_phases": post_phases,
                "all_ranking_snapshots_ready": True,
            }
            return PreAlphaFaxCurrentWeekRankingSnapshotApplyResult(
                **result_payload,
                application_fingerprint=fingerprint(result_payload),
            )

"""Authenticated as-of standings for one real Signed calendar knockout.

Not Official Ranking: initial pool has no proven Tour entry, original
Category/Edition policy is not verified and no native Week Transition has
been executed. This deliberately cannot grant publication or sporting time.
"""
from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field
from sqlalchemy import text

from beta_engine.application.calendar_standalone_match_service import (
    CalendarStandaloneMatchService,
)
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_knockout_awards_state import (
    CalendarScoredOpeningKnockout, derive_knockout_prepared_awards,
)
from beta_engine.infrastructure.db.calendar_standalone_match_state import (
    load_match_rows, load_saved_calendar_match,
)
from beta_engine.infrastructure.db.player_lifecycle_state import load_saved_lifecycle

BLOCKERS = (
    "calendar_tour_entry_not_initialized",
    "original_edition_category_point_configuration_not_authenticated",
    "calendar_native_week_transition_not_executed",
)


class KnockoutStandingsRow(FrozenInput):
    player_id: str = Field(min_length=1)
    player_name: str = Field(min_length=1)
    nationality: str = Field(min_length=1)
    tournament_place: int = Field(ge=1, le=3)
    reached_stage: str = Field(min_length=1)
    awarded_main_points: int = Field(ge=0)
    as_of_counted_points: int = Field(ge=0)
    points_rank: int | None = Field(default=None, ge=1)


class SignedKnockoutStandings(FrozenInput):
    schema_version: str = "calendar_signed_knockout_standings.v1"
    run_id: str
    branch_id: str
    saved_head_revision_id: str
    saved_head_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_knockout_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    scored_evidence_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_point_policy_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    as_of: RunWeekPosition
    source_completed_week: RunWeekPosition
    proposed_first_publication_week: RunWeekPosition
    expiration_week_exclusive: RunWeekPosition
    validity_weeks: int = Field(ge=1)
    rows: tuple[KnockoutStandingsRow, ...]
    points_in_period: bool
    publication_status: str = "not_official_no_week_transition"
    official_ready: bool = False
    blockers: tuple[str, ...] = BLOCKERS
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


@dataclass(slots=True)
class CalendarSignedKnockoutStandingsService:
    repository: object

    def inspect(self, *, run_id: str, branch_id: str,
                expected_saved_head: str, season_index: int, week: int) -> dict:
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            clock, revision, world = CalendarStandaloneMatchService(
                self.repository
            )._context(session, run_id=run_id, branch_id=branch_id)
            if revision.saved_head_revision_id != expected_saved_head:
                raise ValueError("Standings requested against stale Signed Saved HEAD")
            as_of = RunWeekPosition(
                calendar=clock, season_index=season_index, week=week,
            )
            rows = load_match_rows(session, run_id=run_id, branch_id=branch_id)
            saved = load_saved_calendar_match(
                revision.saved_revision.payload,
                run_id=run_id, branch_id=branch_id,
            )
            if (
                len(rows) != 1
                or not isinstance(rows[0], CalendarScoredOpeningKnockout)
                or not isinstance(saved, CalendarScoredOpeningKnockout)
                or rows[0].fingerprint != saved.fingerprint
            ):
                raise ValueError("Standings require an unchanged Signed Saved scored knockout")
            scored = saved
            if (
                scored.source_initial_world_fingerprint != world.fingerprint
                or scored.knockout_fingerprint != scored.knockout.fingerprint
                or scored.policy.validity_weeks != clock.weeks_per_year
            ):
                raise ValueError("Standings Saved scored knockout source/clock mismatch")
            lifecycle = load_saved_lifecycle(
                revision.saved_revision.payload, run_id=run_id, branch_id=branch_id,
            )
            if (
                lifecycle is None or len(lifecycle) != 1
                or lifecycle[0].initialization_stage != "population_only"
                or lifecycle[0].source_initial_world_fingerprint != world.fingerprint
            ):
                raise ValueError("Standings require exact Saved population-only lifecycle evidence")

            first = scored.first_publication_week
            if (
                first.calendar.weeks_per_year != clock.weeks_per_year
                or first.calendar.season_start_year_week != clock.season_start_year_week
                or first.calendar.start_year != clock.start_year
                or first.calendar.season_count > clock.season_count
                or first.ordinal != 1
            ):
                raise ValueError("First-points week has unsupported calendar provenance")
            # Future match scores MUST NOT leak into any pre-publication query.
            if as_of.ordinal < first.ordinal:
                raise ValueError("Signed event points are not eligible as of this week")
            expires_at_ordinal = first.ordinal + scored.policy.validity_weeks
            expires_at = RunWeekPosition(
                calendar=clock,
                season_index=expires_at_ordinal // clock.weeks_per_year,
                week=expires_at_ordinal % clock.weeks_per_year + 1,
            )
            included = as_of.ordinal < expires_at_ordinal
            awards = derive_knockout_prepared_awards(scored.knockout, scored.policy)
            if tuple(awards) != scored.awards:
                raise ValueError("Saved award placement differs from real MatchEngine results")
            profiles = {p.player_id: p for p in world.players}
            stage_place = {"champion": 1, "finalist": 2, "semifinal": 3}
            ordering = sorted(
                awards, key=lambda a: (
                    -a.main_points, stage_place[a.reached_stage], a.player_id
                ),
            )
            standings_rows = []
            previous_points = None
            points_rank = 0
            for i, award in enumerate(ordering, start=1):
                if award.player_id not in profiles:
                    raise ValueError("Saved point award has an unknown initial player")
                points = award.main_points if included else 0
                if included and points != previous_points:
                    points_rank = i
                previous_points = points
                profile = profiles[award.player_id]
                standings_rows.append(KnockoutStandingsRow(
                    player_id=award.player_id,
                    player_name=profile.name,
                    nationality=profile.nationality,
                    tournament_place=stage_place[award.reached_stage],
                    reached_stage=award.reached_stage,
                    awarded_main_points=award.main_points,
                    as_of_counted_points=points,
                    points_rank=points_rank if included and points > 0 else None,
                ))
            payload = {
                "schema_version": "calendar_signed_knockout_standings.v1",
                "run_id": run_id, "branch_id": branch_id,
                "saved_head_revision_id": expected_saved_head,
                "saved_head_content_hash": revision.saved_revision.content_hash,
                "source_knockout_fingerprint": scored.knockout.fingerprint,
                "scored_evidence_fingerprint": scored.fingerprint,
                "source_point_policy_fingerprint": scored.policy.fingerprint,
                "source_initial_world_fingerprint": world.fingerprint,
                "as_of": as_of.model_dump(mode="json"),
                "source_completed_week": scored.week.model_dump(mode="json"),
                "proposed_first_publication_week": first.model_dump(mode="json"),
                "expiration_week_exclusive": expires_at.model_dump(mode="json"),
                "validity_weeks": scored.policy.validity_weeks,
                "rows": [r.model_dump(mode="json") for r in standings_rows],
                "points_in_period": included,
                "publication_status": "not_official_no_week_transition",
                "official_ready": False,
                "blockers": BLOCKERS,
            }
            result = SignedKnockoutStandings(
                **payload, fingerprint=canonical_hash(payload)
            )
            return result.model_dump(mode="json")

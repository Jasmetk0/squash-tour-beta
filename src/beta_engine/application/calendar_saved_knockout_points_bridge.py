"""Read-only joint Signed Saved Match+Point evidence for a FAX knockout ranking.

This path combines the *actual* hash-verified Saved Simulation Slot/Group
MatchEngine results (plus live SQLite parity), with a separate Saved/Owned
canonical Tournament Result + Point Award authority (plus live SQLite parity).
It does not invent points or trust a caller-edited event table. It does not
publish sporting state, and legacy source hashes remain untouched.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field

from sqlalchemy.orm import Session

from beta_engine.application.calendar_saved_match_knockout_bridge import (
    saved_slot_verified_knockout_evidence,
)
from beta_engine.application.calendar_saved_tournament_ranking_bridge import (
    saved_canonical_tournament_ranking_sources,
)
from beta_engine.application.calendar_official_ranking_preview import (
    preview_calendar_official_ranking_from_saved_source_versions,
)
from beta_engine.application.run_calendar_read_authority import resolve_saved_run_calendar
from beta_engine.domain.rankings.calendar_official import (
    CalendarOfficialRankingSnapshot,
    CalendarRankingPlayer,
    CalendarRankingResult,
    CalendarRankingWeek,
)
from beta_engine.domain.rankings.calendar_source_history import CalendarRankingResultVersion
from beta_engine.domain.rankings.official import FrozenInput, OfficialRankingPolicy
from beta_engine.domain.tournaments.calendar_knockout_ranking_evidence import (
    CalendarKnockoutRankingEvidence,
)
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.saved_revision_rankings import (
    load_saved_ranking_component,
)


def _hash(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class SavedKnockoutPointSourceManifest(FrozenInput):
    """One candidate's Saved origin, not an Official publication receipt."""

    schema_version: Literal["saved_knockout_point_source_manifest.v1"] = (
        "saved_knockout_point_source_manifest.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    edition_id: str = Field(min_length=1)
    saved_head_revision_id: str = Field(min_length=1)
    saved_head_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    saved_match_witness_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    saved_tournament_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    saved_point_award_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    saved_point_distribution_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


def saved_slot_and_points_knockout_sources(
    session: Session,
    *,
    bracket: CalendarKnockoutRankingEvidence,
    expected_saved_head_revision_id: str,
) -> tuple[tuple[CalendarRankingResultVersion, ...], SavedKnockoutPointSourceManifest]:
    """Return one complete immutable candidate source from TWO Saved components.

    The known legacy W61 Slot executor has no calendar-native result ownership,
    so W52/W80, Closing-only, forks and incomplete event histories fail closed.
    The supplied bracket must reproduce the exact Saved point policy: calling
    code cannot alter values, source labels, validity or completion/publication
    time and still obtain a candidate. Run/Branch and head are checked inside
    one physical SQLite read snapshot.
    """
    bracket = CalendarKnockoutRankingEvidence.model_validate_json(
        bracket.model_dump_json()
    )
    run_id, branch_id, edition_id = (
        bracket.run_id, bracket.branch_id, bracket.edition_id
    )
    witnessed = saved_slot_verified_knockout_evidence(
        session, bracket=bracket,
        expected_saved_head_revision_id=expected_saved_head_revision_id,
    )
    # This established Saved ranking adapter authenticates canonical Owned
    # award/binding receipts AND their live SQLite rows, including signed
    # historical result records where present.
    saved_sources = saved_canonical_tournament_ranking_sources(
        session, run_id=run_id, branch_id=branch_id,
        expected_saved_head_revision_id=expected_saved_head_revision_id,
        edition_id=edition_id,
    )
    clock = resolve_saved_run_calendar(
        session, run_id=run_id, branch_id=branch_id,
    )
    revision = session.get(BranchSavedRevisionModel, expected_saved_head_revision_id)
    if revision is None:
        raise ValueError("Saved knockout point source revision is missing")
    ranking_state = load_saved_ranking_component(
        json.loads(revision.payload_json), run_id=run_id, branch_id=branch_id,
    )
    if ranking_state is None:
        raise ValueError("Signed Saved Revision lacks canonical ranking component")
    owned = tuple(
        source for source in ranking_state.tournament_sources
        if source.binding.edition_id == edition_id
    )
    if len(owned) != 1:
        raise ValueError("Saved knockout Edition lacks a unique canonical source")
    source = owned[0]
    binding = source.binding
    result = source.canonical_result
    awards = source.canonical_awards
    if (
        result is None or awards is None
        or result.schema_version != "tournament_result_authority.v1"
        or awards.schema_version not in {
            "tournament_point_award_authority.v1",
            "tournament_point_award_authority.v2",
        }
        or binding.event_id != edition_id
        or binding.closing_only
        or result.qualification_winner_ids
        or len(result.matches) != len(bracket.matches)
        or len(result.players) != len(bracket.entrants_by_bracket_position)
        or any(player.draw_type != "main" or player.qualifier or player.byes_received
               or player.walkovers_received or player.retired_or_walkover_loss
               for player in result.players)
    ):
        raise ValueError("Saved ranking source is not a complete main-only knockout")
    if (
        (binding.completed_week.season_index, binding.completed_week.week)
        != (bracket.completed_week.season_index, bracket.completed_week.week)
        or binding.first_publication_week is None
        or (binding.first_publication_week.season_index,
            binding.first_publication_week.week)
        != (bracket.first_publication_week.season_index,
            bracket.first_publication_week.week)
        or bracket.validity_weeks != binding.validity_weeks
    ):
        raise ValueError("Saved ranking timing or validity differs from knockout bracket")
    if (
        tuple(sorted(bracket.point_distribution))
        != awards.point_distribution
        or bracket.point_distribution_source != awards.point_distribution_source
    ):
        raise ValueError("Saved canonical point distribution contradicts knockout bracket")
    if (
        set(p.player_id for p in result.players)
        != set(bracket.entrants_by_bracket_position)
        or result.champion_player_id != bracket.matches[-1].winner_player_id
        or result.finalist_player_id != bracket.matches[-1].loser_player_id
    ):
        raise ValueError("Saved canonical ranking player placements disagree with match bracket")
    expected_matches = tuple((
        m.match_id, m.round_number, m.bracket_position,
        m.winner_player_id, m.loser_player_id, m.scoreline,
        witness.authoritative_result_fingerprint,
    ) for m, witness in zip(bracket.matches, witnessed.witnesses, strict=True))
    saved_matches = tuple((
        m.match_id, m.round_number, m.bracket_position,
        m.winner_player_id, m.loser_player_id, m.scoreline,
        m.result_fingerprint,
    ) for m in result.matches)
    if saved_matches != expected_matches:
        raise ValueError("Saved canonical Tournament Result is not the exact signed Slot match history")

    # Each player's Saved point award must match both the authenticated
    # bracket elimination position and the canonical point table. Legacy
    # canonical awards contain independent, checked player-result hashes.
    stage_by_player = {
        bracket.matches[-1].winner_player_id: "champion",
    }
    # Elimination stages use the number of players still present at
    # *that* round, not a fixed W61 or fixed 4-player stage mapping.
    for match in bracket.matches:
        active = len(bracket.entrants_by_bracket_position) // (2 ** (match.round_number - 1))
        stage_by_player[match.loser_player_id] = {
            2: "finalist", 4: "semifinal", 8: "quarterfinal",
            16: "round_of_16", 32: "round_of_32", 64: "round_of_64",
            128: "round_of_128",
        }[active]
    dist = dict(awards.point_distribution)
    by_player = {a.player_id: a for a in awards.awards}
    saved_versions = {v.result.player_id: v for v in saved_sources}
    if (
        set(stage_by_player) != set(bracket.entrants_by_bracket_position)
        or set(by_player) != set(stage_by_player)
        or set(saved_versions) != set(stage_by_player)
    ):
        raise ValueError("Saved knockout point awards do not cover the exact field")
    for player_id, stage in stage_by_player.items():
        awarded = by_player[player_id]
        canonical = saved_versions[player_id].result
        if (
            awarded.reached_stage != stage
            or awarded.point_stage not in {None, stage}
            or awarded.qualification_point_stage is not None
            or awarded.qualification_points_awarded is not None
            or awarded.ranking_points_awarded != dist[stage]
            or awarded.race_points_awarded != dist[stage]
            or canonical.qualification_points != 0
            or canonical.main_points != dist[stage]
            or canonical.validity_weeks != binding.validity_weeks
        ):
            raise ValueError("Saved ranking award amounts or stages contradict completed matches")

    # Distinct from historical Owned source hashes; no old ranking revision
    # fingerprint or Signed Saved data is reinterpreted or rewritten.
    manifest = SavedKnockoutPointSourceManifest(
        run_id=run_id, branch_id=branch_id, edition_id=edition_id,
        saved_head_revision_id=expected_saved_head_revision_id,
        saved_head_content_hash=revision.content_hash,
        saved_match_witness_fingerprint=witnessed.fingerprint,
        saved_tournament_source_fingerprint=source.fingerprint,
        saved_point_award_fingerprint=awards.fingerprint,
        saved_point_distribution_fingerprint=awards.point_distribution_fingerprint,
    )
    versions = tuple(
        CalendarRankingResultVersion(
            run_id=run_id, branch_id=branch_id,
            effective_week=bracket.first_publication_week,
            previous_fingerprint=None,
            result=CalendarRankingResult(
                edition_id=edition_id, player_id=player_id,
                source_fingerprint=manifest.fingerprint,
                completed_week=bracket.completed_week,
                first_publication_week=bracket.first_publication_week,
                main_points=dist[stage], qualification_points=0,
                validity_weeks=binding.validity_weeks,
            ),
        )
        for player_id, stage in sorted(stage_by_player.items())
    )
    return versions, manifest


def preview_saved_slot_and_points_knockout_ranking(
    session: Session,
    *,
    bracket: CalendarKnockoutRankingEvidence,
    expected_saved_head_revision_id: str,
    week: CalendarRankingWeek,
    policy: OfficialRankingPolicy,
    players: tuple[CalendarRankingPlayer, ...],
    previous: CalendarOfficialRankingSnapshot | None = None,
):
    """Read-only rank candidate with independently Saved-proven match+point inputs."""
    sources, manifest = saved_slot_and_points_knockout_sources(
        session, bracket=bracket,
        expected_saved_head_revision_id=expected_saved_head_revision_id,
    )
    candidate, resolved = preview_calendar_official_ranking_from_saved_source_versions(
        session, run_id=bracket.run_id, branch_id=bracket.branch_id,
        expected_saved_head_revision_id=expected_saved_head_revision_id,
        week=week, policy=policy, players=players,
        result_versions=sources, previous=previous,
    )
    return candidate, resolved, manifest

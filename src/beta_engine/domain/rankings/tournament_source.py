"""Frozen, independently owned evidence for a supported tournament source."""

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.application.ranking_tournament_ingestion import TournamentRankingBinding
from beta_engine.application.season_event_results_service import SeasonEventResultPackage
from beta_engine.application.season_point_awards_service import EventPointAwardPackage
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.result_authority import TournamentResultAuthority


class OwnedTournamentRankingSource(FrozenInput):
    schema_version: Literal[
        "owned_tournament_ranking_source.v1",
        "owned_tournament_ranking_source.v2",
    ] = "owned_tournament_ranking_source.v1"
    binding: TournamentRankingBinding
    result: SeasonEventResultPackage
    awards: EventPointAwardPackage
    canonical_result: TournamentResultAuthority | None = None
    adopted_by_command_id: str = Field(min_length=1, max_length=128)
    provenance_kind: Literal[
        "explicit_legacy_tournament_adoption",
        "canonical_run_owned_tournament_result",
    ] = "explicit_legacy_tournament_adoption"

    @model_validator(mode="after")
    def validate_identity(self):
        if self.binding.event_id != self.result.event_id or self.binding.event_id != self.awards.event_id:
            raise ValueError("Owned tournament source event identity mismatch")
        if self.schema_version == "owned_tournament_ranking_source.v1":
            if self.canonical_result is not None:
                raise ValueError("Historical v1 tournament source cannot carry canonical result")
        else:
            if self.canonical_result is None:
                raise ValueError("Canonical v2 tournament source requires canonical result")
            if (
                self.canonical_result.run_id,
                self.canonical_result.branch_id,
                self.canonical_result.event_id,
                self.canonical_result.completed_week,
                self.canonical_result.champion_player_id,
                self.canonical_result.finalist_player_id,
            ) != (
                self.binding.run_id,
                self.binding.branch_id,
                self.binding.event_id,
                self.binding.completed_week,
                self.result.summary.champion_player_id,
                self.result.summary.finalist_player_id,
            ):
                raise ValueError("Canonical tournament result binding mismatch")
            if self.provenance_kind != "canonical_run_owned_tournament_result":
                raise ValueError("Canonical v2 source requires canonical provenance")
            if (
                self.result.metadata.draw_package_fingerprint
                != self.canonical_result.draw_authority_fingerprint
                or self.result.metadata.match_package_fingerprint
                != self.canonical_result.match_package_fingerprint
            ):
                raise ValueError("Canonical tournament result provenance mismatch")

            canonical_matches = {
                match.match_id: (
                    match.draw_type,
                    match.round_number,
                    match.bracket_position,
                    match.winner_player_id,
                    match.loser_player_id,
                    match.scoreline,
                    match.result_fingerprint,
                )
                for match in self.canonical_result.matches
            }
            compatibility_matches = {
                match.match_id: (
                    match.draw_type,
                    match.round_number,
                    match.bracket_position,
                    match.winner_player_id,
                    match.loser_player_id,
                    match.scoreline,
                    match.result_fingerprint,
                )
                for match in self.result.match_result_refs
            }
            if canonical_matches != compatibility_matches:
                raise ValueError("Canonical tournament match-result projection mismatch")

            canonical_players = {
                player.player_id: (
                    player.draw_type,
                    player.seed_number,
                    player.qualifier,
                    player.reached_stage,
                    player.final_round_number,
                    player.eliminated_by_player_id,
                    player.last_match_id,
                    player.wins,
                    player.losses,
                    player.byes_received,
                )
                for player in self.canonical_result.players
            }
            compatibility_players = {
                player.player_id: (
                    player.draw_type,
                    player.seed_number,
                    player.qualifier,
                    player.reached_stage,
                    player.final_round_number,
                    player.eliminated_by_player_id,
                    player.last_match_id,
                    player.wins,
                    player.losses,
                    player.byes_received,
                )
                for player in self.result.player_results
            }
            if canonical_players != compatibility_players:
                raise ValueError("Canonical tournament player-result projection mismatch")
            if tuple(
                item.player_id for item in self.result.qualification_winners
            ) != self.canonical_result.qualification_winner_ids:
                raise ValueError("Canonical Qualification winner projection mismatch")
        return self

    @property
    def fingerprint(self) -> str:
        payload = self.model_dump(mode="json")
        if self.schema_version == "owned_tournament_ranking_source.v1":
            # Preserve the exact historical v1 fingerprint contract. This field
            # did not exist before v2 and must not appear as an injected null.
            payload.pop("canonical_result", None)
        return hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()

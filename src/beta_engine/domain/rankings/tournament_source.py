"""Frozen, independently owned evidence for a supported tournament source."""

import hashlib
import json
from typing import Literal

from pydantic import Field, model_serializer, model_validator

from beta_engine.application.ranking_tournament_ingestion import TournamentRankingBinding
from beta_engine.application.season_event_results_service import SeasonEventResultPackage
from beta_engine.application.season_point_awards_service import EventPointAwardPackage
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.point_award_authority import (
    TournamentPointAwardAuthority,
)
from beta_engine.domain.tournaments.prize_money_award_authority import (
    TournamentPrizeMoneyAwardAuthority,
)
from beta_engine.domain.tournaments.result_authority import TournamentResultAuthority


class OwnedTournamentRankingSource(FrozenInput):
    schema_version: Literal[
        "owned_tournament_ranking_source.v1",
        "owned_tournament_ranking_source.v2",
        "owned_tournament_ranking_source.v3",
        "owned_tournament_ranking_source.v4",
        "owned_tournament_ranking_source.v5",
    ] = "owned_tournament_ranking_source.v1"
    binding: TournamentRankingBinding
    result: SeasonEventResultPackage | None = None
    awards: EventPointAwardPackage | None = None
    canonical_result: TournamentResultAuthority | None = None
    canonical_awards: TournamentPointAwardAuthority | None = None
    canonical_prize_awards: TournamentPrizeMoneyAwardAuthority | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    adopted_by_command_id: str = Field(min_length=1, max_length=128)
    provenance_kind: Literal[
        "explicit_legacy_tournament_adoption",
        "canonical_run_owned_tournament_result",
        "canonical_run_owned_tournament_result_and_points",
        "canonical_run_owned_tournament_authorities",
        "canonical_run_owned_tournament_authorities_and_prize_money",
    ] = "explicit_legacy_tournament_adoption"

    @model_serializer(mode="wrap")
    def serialize_source(self, handler):
        payload = handler(self)
        if self.schema_version in {
            "owned_tournament_ranking_source.v4",
            "owned_tournament_ranking_source.v5",
        }:
            # Canonical v4+ does not persist compatibility DTO copies.
            payload.pop("result", None)
            payload.pop("awards", None)
        return payload

    @model_validator(mode="after")
    def validate_identity(self):
        version = self.schema_version

        if version == "owned_tournament_ranking_source.v1":
            self._require_legacy_compatibility()
            if (
                self.canonical_result is not None
                or self.canonical_awards is not None
                or self.canonical_prize_awards is not None
            ):
                raise ValueError(
                    "Historical v1 tournament source cannot carry canonical authority"
                )
            if self.provenance_kind != "explicit_legacy_tournament_adoption":
                raise ValueError("Historical v1 tournament source provenance mismatch")
            return self

        if self.canonical_result is None:
            raise ValueError("Canonical tournament source requires canonical result")

        if version == "owned_tournament_ranking_source.v2":
            self._require_legacy_compatibility()
            if (
                self.canonical_awards is not None
                or self.canonical_prize_awards is not None
            ):
                raise ValueError(
                    "Historical v2 tournament source cannot carry later canonical awards"
                )
            if self.provenance_kind != "canonical_run_owned_tournament_result":
                raise ValueError("Canonical v2 source requires v2 canonical provenance")
            self._validate_canonical_result_projection()
            return self

        if self.canonical_awards is None:
            raise ValueError("Canonical tournament source requires canonical point awards")
        self._validate_canonical_authority_binding()

        if version == "owned_tournament_ranking_source.v3":
            self._require_legacy_compatibility()
            if self.canonical_prize_awards is not None:
                raise ValueError(
                    "Historical v3 tournament source cannot carry prize-money authority"
                )
            if (
                self.provenance_kind
                != "canonical_run_owned_tournament_result_and_points"
            ):
                raise ValueError("Canonical v3 source requires v3 canonical provenance")
            self._validate_canonical_result_projection()
            self._validate_canonical_award_projection()
            return self

        if self.result is not None or self.awards is not None:
            raise ValueError(
                "Canonical v4+ source cannot persist legacy compatibility DTOs"
            )

        if version == "owned_tournament_ranking_source.v4":
            if self.canonical_prize_awards is not None:
                raise ValueError(
                    "Historical v4 tournament source cannot carry prize-money authority"
                )
            if self.provenance_kind != "canonical_run_owned_tournament_authorities":
                raise ValueError("Canonical v4 source requires canonical-only provenance")
            return self

        if self.canonical_prize_awards is None:
            raise ValueError("Canonical v5 source requires prize-money authority")
        if (
            self.provenance_kind
            != "canonical_run_owned_tournament_authorities_and_prize_money"
        ):
            raise ValueError("Canonical v5 source requires prize-money provenance")
        self._validate_canonical_prize_award_binding()
        return self

    def _require_legacy_compatibility(self) -> None:
        if self.result is None or self.awards is None:
            raise ValueError("Historical tournament source requires compatibility DTOs")
        if (
            self.binding.event_id != self.result.event_id
            or self.binding.event_id != self.awards.event_id
        ):
            raise ValueError("Owned tournament source event identity mismatch")

    def _validate_canonical_authority_binding(self) -> None:
        if self.canonical_result is None or self.canonical_awards is None:
            raise ValueError("Canonical tournament authority is incomplete")
        if (
            self.canonical_result.run_id,
            self.canonical_result.branch_id,
            self.canonical_result.event_id,
            self.canonical_result.completed_week,
        ) != (
            self.binding.run_id,
            self.binding.branch_id,
            self.binding.event_id,
            self.binding.completed_week,
        ):
            raise ValueError("Canonical tournament result binding mismatch")
        if (
            self.canonical_awards.run_id,
            self.canonical_awards.branch_id,
            self.canonical_awards.event_id,
            self.canonical_awards.completed_week,
            self.canonical_awards.tournament_result_fingerprint,
        ) != (
            self.binding.run_id,
            self.binding.branch_id,
            self.binding.event_id,
            self.binding.completed_week,
            self.canonical_result.fingerprint,
        ):
            raise ValueError("Canonical point-award authority binding mismatch")
        if (
            self.binding.expected_result_fingerprint
            != self.canonical_result.fingerprint
            or self.binding.expected_award_fingerprint
            != self.canonical_awards.fingerprint
        ):
            raise ValueError("Canonical source binding fingerprint mismatch")

        canonical_result_players = {
            player.player_id: player for player in self.canonical_result.players
        }
        if {award.player_id for award in self.canonical_awards.awards} != set(
            canonical_result_players
        ):
            raise ValueError(
                "Canonical point awards do not cover tournament result players"
            )
        for award in self.canonical_awards.awards:
            player = canonical_result_players[award.player_id]
            player_fingerprint = hashlib.sha256(
                json.dumps(
                    player.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                ).encode()
            ).hexdigest()
            if award.source_player_result_fingerprint != player_fingerprint:
                raise ValueError(
                    "Canonical point award player-result provenance mismatch"
                )

    def _validate_canonical_prize_award_binding(self) -> None:
        if self.canonical_result is None or self.canonical_prize_awards is None:
            raise ValueError("Canonical prize-money authority is incomplete")
        authority = self.canonical_prize_awards
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.completed_week,
            authority.tournament_result_fingerprint,
        ) != (
            self.binding.run_id,
            self.binding.branch_id,
            self.binding.event_id,
            self.binding.completed_week,
            self.canonical_result.fingerprint,
        ):
            raise ValueError("Canonical prize-money authority binding mismatch")

        result_players = {
            player.player_id: player
            for player in self.canonical_result.players
        }
        if {award.player_id for award in authority.awards} != set(result_players):
            raise ValueError(
                "Canonical prize-money awards do not cover tournament result players"
            )
        for award in authority.awards:
            player = result_players[award.player_id]
            player_fingerprint = hashlib.sha256(
                json.dumps(
                    player.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                ).encode()
            ).hexdigest()
            if award.source_player_result_fingerprint != player_fingerprint:
                raise ValueError(
                    "Canonical prize-money player-result provenance mismatch"
                )

    def _validate_canonical_result_projection(self) -> None:
        if self.canonical_result is None or self.result is None:
            raise ValueError("Canonical result compatibility projection is missing")
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

    def _validate_canonical_award_projection(self) -> None:
        if self.canonical_awards is None or self.awards is None or self.result is None:
            raise ValueError("Canonical point-award compatibility projection is missing")
        if (
            self.awards.metadata.result_package_fingerprint
            != self.result.metadata.build_fingerprint
            or self.awards.metadata.point_distribution_fingerprint
            != self.canonical_awards.point_distribution_fingerprint
            or self.awards.metadata.point_distribution_source
            != self.canonical_awards.point_distribution_source
        ):
            raise ValueError("Canonical point-award compatibility provenance mismatch")

        canonical_awards = {
            award.player_id: (
                award.reached_stage,
                award.qualifier,
                award.seed_number,
                award.ranking_points_awarded,
                award.race_points_awarded,
            )
            for award in self.canonical_awards.awards
        }
        compatibility_awards = {
            award.player_id: (
                award.reached_stage,
                award.qualifier,
                award.seed_number,
                award.ranking_points_awarded,
                award.race_points_awarded,
            )
            for award in self.awards.awards
        }
        if canonical_awards != compatibility_awards:
            raise ValueError("Canonical point-award compatibility projection mismatch")
        if (
            self.awards.summary.total_ranking_points
            != self.canonical_awards.total_ranking_points
            or self.awards.summary.total_race_points
            != self.canonical_awards.total_race_points
        ):
            raise ValueError("Canonical point-award compatibility totals mismatch")

    @property
    def fingerprint(self) -> str:
        payload = self.model_dump(mode="json")
        if self.schema_version == "owned_tournament_ranking_source.v1":
            # Preserve the exact historical v1 fingerprint contract.
            payload.pop("canonical_result", None)
            payload.pop("canonical_awards", None)
            payload.pop("canonical_prize_awards", None)
        elif self.schema_version == "owned_tournament_ranking_source.v2":
            # v2 introduced canonical_result, but later award authorities did not exist.
            payload.pop("canonical_awards", None)
            payload.pop("canonical_prize_awards", None)
        elif self.schema_version in {
            "owned_tournament_ranking_source.v3",
            "owned_tournament_ranking_source.v4",
        }:
            # Prize-money authority was introduced only in v5.
            payload.pop("canonical_prize_awards", None)
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

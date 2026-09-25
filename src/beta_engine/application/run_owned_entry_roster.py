"""Read-only Run-owned player projection for first-season Entry decisions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from beta_engine.application.season_player_bootstrap_service import (
    SeasonActivePlayersResponse,
    SeasonBootstrapSummary,
)
from beta_engine.domain.rankings.official import RankingWeek, load_official_ranking_snapshot
from beta_engine.infrastructure.db.initial_world_state import get_initial_world
from beta_engine.infrastructure.db.models import PublishedOfficialRankingModel
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
from beta_engine.infrastructure.db.player_sporting_state import get_sporting


@dataclass(slots=True)
class RunOwnedInitialEntryRosterService:
    """Project the owned Week-1 roster into the legacy Entry DTO without file reads.

    The compatibility Entry engine still consumes SeasonActivePlayer objects.
    This adapter deliberately reuses only the immutable InitialWorld profile for
    those fields while authoritative lifecycle/sporting state decides which player
    identities are active. Later-season prospect/profile projection is intentionally
    outside this bridge and fails closed instead of falling back to JSON registries.
    """

    session: object
    run_id: str
    branch_id: str
    week: RankingWeek

    def get_active_players(self, *, season: str) -> SeasonActivePlayersResponse:
        if self.week.season_index != 0 or season != "2000/2001":
            raise ValueError(
                "Run-owned initial Entry roster currently supports only Season 2000/2001"
            )

        world = get_initial_world(
            self.session, run_id=self.run_id, branch_id=self.branch_id
        )
        lifecycle = get_lifecycle(
            self.session, run_id=self.run_id, branch_id=self.branch_id, week=self.week
        )
        sporting = get_sporting(
            self.session, run_id=self.run_id, branch_id=self.branch_id, week=self.week
        )
        if world is None or lifecycle is None or sporting is None:
            raise ValueError(
                "Run-owned Entry roster requires InitialWorld, lifecycle and sporting state"
            )

        world_by_id = {player.player_id: player for player in world.players}
        sporting_ids = {player.player_id for player in sporting.players}
        active = tuple(
            player
            for player in lifecycle.players
            if player.status == "active" and player.player_id in sporting_ids
        )
        missing_profiles = sorted(
            player.player_id for player in active if player.player_id not in world_by_id
        )
        if missing_profiles:
            raise ValueError(
                "Run-owned initial Entry roster lacks InitialWorld profile for active player(s): "
                + ", ".join(missing_profiles)
            )

        ranking_points: dict[str, int] = {}
        publication = self.session.get(
            PublishedOfficialRankingModel,
            (self.run_id, self.branch_id, self.week.ordinal),
        )
        ranking_fingerprint = None
        if publication is not None:
            snapshot = load_official_ranking_snapshot(
                publication.payload_json,
                expected_fingerprint=publication.snapshot_fingerprint,
                run_id=self.run_id,
                branch_id=self.branch_id,
                week=self.week,
            )
            ranking_points = {row.player_id: row.points for row in snapshot.rows}
            ranking_fingerprint = snapshot.fingerprint

        players = []
        for identity in sorted(active, key=lambda item: item.player_id):
            source = world_by_id[identity.player_id]
            fingerprint = hashlib.sha256(
                json.dumps(
                    {
                        "mode": "run_owned_initial_entry_roster.v1",
                        "run_id": self.run_id,
                        "branch_id": self.branch_id,
                        "week_ordinal": self.week.ordinal,
                        "initial_world_fingerprint": world.fingerprint,
                        "lifecycle_fingerprint": lifecycle.fingerprint,
                        "sporting_fingerprint": sporting.fingerprint,
                        "ranking_fingerprint": ranking_fingerprint,
                        "player_id": identity.player_id,
                        "source_bootstrap_fingerprint": source.bootstrap_fingerprint,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            players.append(
                source.model_copy(
                    update={
                        "age_years_at_season_start": identity.age,
                        "ranking_points": ranking_points.get(identity.player_id, 0),
                        "active_status": "active",
                        "bootstrap_fingerprint": fingerprint,
                    }
                )
            )

        return SeasonActivePlayersResponse(
            players=players,
            summary=self._summary(players),
            metadata=None,
            warnings=[],
        )

    @staticmethod
    def _summary(players) -> SeasonBootstrapSummary:
        if not players:
            return SeasonBootstrapSummary()
        return SeasonBootstrapSummary(
            total_active_players=len(players),
            countries_represented=len({player.country_code for player in players}),
            manual_players=sum(1 for player in players if player.manual_override),
            generated_players=sum(
                1 for player in players if player.source_generation == "initial_pool"
            ),
            locked_from_initial_pool=sum(
                1 for player in players if player.locked_from_initial_pool
            ),
            average_current_ability=round(
                sum(player.current_ability for player in players) / len(players), 2
            ),
            average_potential_ability=round(
                sum(player.potential_ability for player in players) / len(players), 2
            ),
            by_potential_tier={
                tier: sum(1 for player in players if player.potential_tier == tier)
                for tier in sorted({player.potential_tier for player in players})
            },
        )

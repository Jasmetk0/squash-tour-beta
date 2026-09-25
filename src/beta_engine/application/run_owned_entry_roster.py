"""Run-owned compatibility roster projection for authoritative Entry decisions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import select

from beta_engine.application.season_player_bootstrap_service import (
    SeasonActivePlayer,
    SeasonActivePlayersResponse,
    SeasonBootstrapSummary,
)
from beta_engine.domain.players.attribute_catalog import ATTRIBUTE_GROUPS
from beta_engine.domain.players.initial_pool import GeneratedPlayerAttributes
from beta_engine.domain.players.models import HiddenCareerTraits
from beta_engine.domain.rankings.official import RankingWeek, load_official_ranking_snapshot
from beta_engine.infrastructure.db.initial_world_state import get_initial_world
from beta_engine.infrastructure.db.models import (
    PublishedOfficialRankingModel,
    RunProspectModel,
)
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
from beta_engine.infrastructure.db.player_sporting_state import get_sporting


COMPATIBILITY_POLICY_ID = "run-owned-entry-roster-projection.v2"


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _legacy_scale(value: int) -> int:
    return max(1, min(99, round(value * 99 / 200)))


def _stable_fraction(seed: str, label: str) -> float:
    raw = hashlib.sha256(f"{seed}|{label}".encode()).digest()
    return round(int.from_bytes(raw[:8], "big") / ((1 << 64) - 1), 6)


def _career_stage(age: int) -> str:
    if age < 18:
        return "junior"
    if age < 21:
        return "developing"
    if age < 24:
        return "breakthrough"
    if age < 30:
        return "prime"
    if age < 35:
        return "veteran"
    return "late_career"


def _potential_tier(potential_ovr: int) -> str:
    if potential_ovr >= 175:
        return "S"
    if potential_ovr >= 155:
        return "A"
    if potential_ovr >= 135:
        return "B"
    if potential_ovr >= 115:
        return "C"
    return "D"


def _legacy_attributes(sporting) -> GeneratedPlayerAttributes:
    values = dict(sporting.attributes)

    def average(group: str) -> int:
        names = ATTRIBUTE_GROUPS[group]
        return round(sum(values[name] for name in names) / len(names))

    return GeneratedPlayerAttributes(
        technique=_legacy_scale(average("Technical")),
        movement=_legacy_scale(average("Move")),
        physical=_legacy_scale(average("Physical")),
        mental=_legacy_scale(average("Mental")),
        consistency=_legacy_scale(values["Consistency"]),
        clutch=_legacy_scale(
            round(
                (
                    values["Composure"]
                    + values["Confidence"]
                    + values["Toughness"]
                )
                / 3
            )
        ),
        recovery=_legacy_scale(
            round((values["Endurance"] + values["Durability"]) / 2)
        ),
    )


@dataclass(slots=True)
class RunOwnedEntryRosterService:
    """Project current Run-owned player truth into the legacy Entry DTO.

    Lifecycle decides active identity and age. Sporting state supplies the current
    57-attribute ability profile. InitialWorld supplies stable identity/career metadata
    for original players; RunProspect supplies it for generated prospects. The adapter
    is read-only and never consults or mutates season_active_players.json.
    """

    session: object
    run_id: str
    branch_id: str
    week: RankingWeek

    def get_active_players(self, *, season: str) -> SeasonActivePlayersResponse:
        expected_season = (
            f"{2000 + self.week.season_index}/{2001 + self.week.season_index}"
        )
        if season != expected_season:
            raise ValueError(
                "Run-owned Entry roster season differs from authoritative RankingWeek"
            )

        world = get_initial_world(
            self.session, run_id=self.run_id, branch_id=self.branch_id
        )
        lifecycle = get_lifecycle(
            self.session,
            run_id=self.run_id,
            branch_id=self.branch_id,
            week=self.week,
        )
        sporting = get_sporting(
            self.session,
            run_id=self.run_id,
            branch_id=self.branch_id,
            week=self.week,
        )
        if world is None or lifecycle is None or sporting is None:
            raise ValueError(
                "Run-owned Entry roster requires InitialWorld, lifecycle and sporting state"
            )

        world_by_id = {player.player_id: player for player in world.players}
        sporting_by_id = {player.player_id: player for player in sporting.players}
        active = tuple(
            player
            for player in lifecycle.players
            if player.status == "active" and player.player_id in sporting_by_id
        )

        prospect_ids = tuple(
            sorted(
                player.player_id
                for player in active
                if player.player_id not in world_by_id
            )
        )
        prospect_rows = tuple(
            self.session.scalars(
                select(RunProspectModel)
                .where(
                    RunProspectModel.run_id == self.run_id,
                    RunProspectModel.prospect_id.in_(prospect_ids),
                )
                .order_by(RunProspectModel.prospect_id)
            )
        ) if prospect_ids else ()
        prospects_by_id = {row.prospect_id: row for row in prospect_rows}
        missing_profiles = sorted(set(prospect_ids) - set(prospects_by_id))
        if missing_profiles:
            raise ValueError(
                "Run-owned Entry roster lacks Run prospect metadata for active player(s): "
                + ", ".join(missing_profiles)
            )

        ranking_points, ranking_fingerprint = self._ranking_points()
        players = [
            self._project_player(
                identity=identity,
                sporting=sporting_by_id[identity.player_id],
                initial=world_by_id.get(identity.player_id),
                prospect=prospects_by_id.get(identity.player_id),
                season=season,
                ranking_points=ranking_points.get(identity.player_id, 0),
                world_fingerprint=world.fingerprint,
                lifecycle_fingerprint=lifecycle.fingerprint,
                sporting_fingerprint=sporting.fingerprint,
                ranking_fingerprint=ranking_fingerprint,
            )
            for identity in sorted(active, key=lambda item: item.player_id)
        ]

        return SeasonActivePlayersResponse(
            players=players,
            summary=self._summary(players),
            metadata=None,
            warnings=[],
        )

    def _ranking_points(self) -> tuple[dict[str, int], str | None]:
        publication = self.session.get(
            PublishedOfficialRankingModel,
            (self.run_id, self.branch_id, self.week.ordinal),
        )
        if publication is None:
            return {}, None
        snapshot = load_official_ranking_snapshot(
            publication.payload_json,
            expected_fingerprint=publication.snapshot_fingerprint,
            run_id=self.run_id,
            branch_id=self.branch_id,
            week=self.week,
        )
        return (
            {row.player_id: row.points for row in snapshot.rows},
            snapshot.fingerprint,
        )

    def _project_player(
        self,
        *,
        identity,
        sporting,
        initial,
        prospect,
        season: str,
        ranking_points: int,
        world_fingerprint: str,
        lifecycle_fingerprint: str,
        sporting_fingerprint: str,
        ranking_fingerprint: str | None,
    ) -> SeasonActivePlayer:
        attributes = _legacy_attributes(sporting)
        current_ability = _legacy_scale(sporting.ovr)
        potential_ability = max(
            current_ability,
            _legacy_scale(sporting.potential_ovr),
        )

        if initial is not None:
            name = initial.name
            country_code = initial.country_code
            nationality = initial.nationality
            play_style = initial.play_style
            archetype = initial.archetype
            hidden = initial.hidden_career_traits.model_copy(
                update={
                    "potential_ceiling": max(
                        initial.hidden_career_traits.potential_ceiling,
                        potential_ability,
                    )
                }
            )
            source_pool_player_id = initial.source_pool_player_id
            source_generation = initial.source_generation
            manual_override = initial.manual_override
            locked = initial.locked_from_initial_pool
            source_profile_fingerprint = initial.source_generation_fingerprint
            source_kind = "initial_world"
            bootstrap_seed = initial.bootstrap_seed
            bootstrap_id = initial.bootstrap_id
        else:
            if prospect is None:
                raise ValueError(
                    "Run-owned Entry roster active player has no identity profile"
                )
            name = prospect.display_name
            country_code = prospect.country_code
            nationality = prospect.country_code
            play_style = f"{COMPATIBILITY_POLICY_ID}:prospect"
            archetype = f"{COMPATIBILITY_POLICY_ID}:prospect"
            growth_curve = {
                "Early Bloomer": "early",
                "Standard": "steady",
                "Late Bloomer": "late",
            }[sporting.development_timing]
            hidden = HiddenCareerTraits(
                potential_ceiling=potential_ability,
                growth_curve=growth_curve,
                professionalism=_stable_fraction(
                    prospect.trait_seed, "professionalism"
                ),
                ambition=_stable_fraction(prospect.trait_seed, "ambition"),
                travel_tolerance=_stable_fraction(
                    prospect.trait_seed, "travel_tolerance"
                ),
                schedule_aggression=_stable_fraction(
                    prospect.trait_seed, "schedule_aggression"
                ),
                injury_proneness=_stable_fraction(
                    prospect.trait_seed, "injury_proneness"
                ),
                resilience=_stable_fraction(prospect.trait_seed, "resilience"),
            )
            source_pool_player_id = prospect.prospect_id
            source_generation = "annual_intake"
            manual_override = False
            locked = False
            source_profile_fingerprint = _fingerprint(
                {
                    "profile_json": prospect.profile_json,
                    "development_json": prospect.development_json,
                    "potential_json": prospect.potential_json,
                    "trait_seed": prospect.trait_seed,
                }
            )
            source_kind = "run_prospect"
            bootstrap_seed = 0
            bootstrap_id = f"run-prospect:{prospect.prospect_id}"

        bootstrap_fingerprint = _fingerprint(
            {
                "policy_id": COMPATIBILITY_POLICY_ID,
                "run_id": self.run_id,
                "branch_id": self.branch_id,
                "week_ordinal": self.week.ordinal,
                "season": season,
                "player_id": identity.player_id,
                "source_kind": source_kind,
                "source_profile_fingerprint": source_profile_fingerprint,
                "world_fingerprint": world_fingerprint,
                "lifecycle_fingerprint": lifecycle_fingerprint,
                "sporting_fingerprint": sporting_fingerprint,
                "ranking_fingerprint": ranking_fingerprint,
                "attributes": attributes.model_dump(mode="json"),
                "ranking_points": ranking_points,
            }
        )

        return SeasonActivePlayer(
            player_id=identity.player_id,
            name=name,
            country_code=country_code,
            nationality=nationality or country_code,
            birth_year=identity.birth_year,
            birth_year_week=identity.birth_year_week,
            age_years_at_season_start=identity.age,
            age_weeks_at_season_start=identity.age * 61,
            current_ability=current_ability,
            potential_ability=potential_ability,
            potential_tier=_potential_tier(sporting.potential_ovr),
            career_stage=_career_stage(identity.age),
            play_style=play_style,
            archetype=archetype,
            attributes=attributes,
            hidden_career_traits=hidden,
            health_status="fresh",
            active_status="active",
            ranking_points=ranking_points,
            race_points=0,
            protected_ranking_points=0,
            season=season,
            source_pool_player_id=source_pool_player_id,
            source_generation_fingerprint=source_profile_fingerprint,
            source_generation=source_generation,
            manual_override=manual_override,
            locked_from_initial_pool=locked,
            bootstrap_fingerprint=bootstrap_fingerprint,
            bootstrap_seed=bootstrap_seed,
            bootstrap_id=bootstrap_id,
        )

    @staticmethod
    def _summary(players: list[SeasonActivePlayer]) -> SeasonBootstrapSummary:
        if not players:
            return SeasonBootstrapSummary()
        tiers = sorted({player.potential_tier for player in players})
        return SeasonBootstrapSummary(
            total_active_players=len(players),
            countries_represented=len({player.country_code for player in players}),
            manual_players=sum(1 for player in players if player.manual_override),
            generated_players=sum(
                1
                for player in players
                if player.source_generation in {"initial_pool", "annual_intake"}
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
                for tier in tiers
            },
        )


# Temporary import compatibility for code/tests introduced in #982.
RunOwnedInitialEntryRosterService = RunOwnedEntryRosterService

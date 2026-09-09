"""Validated initial ingestion of ordinary completed main-draw awards."""

import hashlib
import json
from typing import Literal, Protocol

from pydantic import Field

from beta_engine.application.season_event_results_service import (
    SeasonEventResultPackage,
)
from beta_engine.application.season_point_awards_service import (
    EventPointAwardPackage,
    SeasonPointAwardsService,
)
from beta_engine.domain.rankings.official import (
    FrozenInput,
    OfficialRankingResult,
    RankingWeek,
)
from beta_engine.domain.rankings.result_history import RankingResultVersion


class TournamentRankingBinding(FrozenInput):
    """Trusted caller binding: legacy files do not carry product Run/Branch IDs."""

    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    edition_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    completed_week: RankingWeek
    first_publication_week: RankingWeek
    validity_weeks: int = Field(ge=1)
    ranking_status: Literal["ranked"]
    expected_result_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_award_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class RankingSourceWriter(Protocol):
    def append(self, version: RankingResultVersion) -> RankingResultVersion: ...


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def prepare_tournament_ranking_sources(
    binding: TournamentRankingBinding,
    result: SeasonEventResultPackage,
    awards: EventPointAwardPackage,
) -> tuple[RankingResultVersion, ...]:
    """Validate the entire package before producing any persistence writes."""
    binding = TournamentRankingBinding.model_validate_json(binding.model_dump_json())
    result = SeasonEventResultPackage.model_validate_json(result.model_dump_json())
    awards = EventPointAwardPackage.model_validate_json(awards.model_dump_json())
    season_start = 2000 + binding.completed_week.season_index
    season = f"{season_start}/{season_start + 1}"
    for package in (result, awards):
        if (package.event_id, package.metadata.event_id, package.summary.event_id) != (
            binding.event_id,
        ) * 3:
            raise ValueError("Tournament source event identity mismatch")
        if package.season != season or package.metadata.season != season:
            raise ValueError("Tournament source season mismatch")
        if (
            not package.persisted
            or not package.metadata.persisted
            or package.dry_run
            or package.metadata.dry_run
        ):
            raise ValueError("Tournament sources must be persisted, not previews")
        if package.validation_errors or package.summary.validation_error_count:
            raise ValueError("Tournament source has validation errors")
        if package.seed != package.metadata.seed:
            raise ValueError("Tournament source seed mismatch")
    if (
        result.season_week != binding.completed_week.week
        or result.template_id != awards.template_id
    ):
        raise ValueError("Tournament source week/template mismatch")
    if (
        result.completion_status != "complete"
        or result.summary.completion_status != "complete"
        or result.summary.incomplete_matches
    ):
        raise ValueError("Tournament must be complete")
    if (
        result.qualification_winners
        or result.summary.qualification_player_count
        or any(
            p.draw_type != "main"
            or p.qualifier
            or p.byes_received
            or p.walkovers_received
            or p.retired_or_walkover_loss
            for p in result.player_results
        )
        or any(m.draw_type != "main" for m in result.match_result_refs)
    ):
        raise ValueError("Qualification/BYE/W/O/RET requires a dedicated award adapter")
    if (
        awards.metadata.point_distribution_source.startswith("fallback")
        or awards.metadata.point_distribution_source == "calendar_event.unranked"
    ):
        raise ValueError("Ranking ingestion requires authored ranked awards")
    player_ids = [p.player_id for p in result.player_results]
    award_ids = [a.player_id for a in awards.awards]
    if (
        not player_ids
        or len(set(player_ids)) != len(player_ids)
        or len(set(award_ids)) != len(award_ids)
        or set(player_ids) != set(award_ids)
    ):
        raise ValueError("Tournament awards must cover each result player exactly once")
    if result.summary.player_count != len(
        player_ids
    ) or awards.summary.player_count != len(award_ids):
        raise ValueError("Tournament player count mismatch")
    refs = result.match_result_refs
    if (
        len(refs) != len(player_ids) - 1
        or len({m.match_id for m in refs}) != len(refs)
        or result.summary.completed_matches != len(refs)
        or result.champion is None
        or result.finalist is None
        or any(
            m.winner_player_id not in player_ids
            or m.loser_player_id not in player_ids
            or m.winner_player_id == m.loser_player_id
            or not m.scoreline
            or m.scoreline in {"BYE", "W/O", "RET"}
            for m in refs
        )
    ):
        raise ValueError("Incomplete or unsupported main-draw match references")
    result_fp = _hash(
        {
            "event_id": result.event_id,
            "seed": result.seed,
            "match_package_fingerprint": result.metadata.match_package_fingerprint,
            "champion": result.champion.model_dump(mode="json")
            if result.champion
            else None,
            "finalist": result.finalist.model_dump(mode="json")
            if result.finalist
            else None,
            "player_results": [
                p.model_dump(mode="json") for p in result.player_results
            ],
            "match_refs": [m.model_dump(mode="json") for m in result.match_result_refs],
        }
    )
    if (
        result_fp != binding.expected_result_fingerprint
        or result_fp != result.metadata.build_fingerprint
        or result_fp != awards.metadata.result_package_fingerprint
    ):
        raise ValueError("Tournament result fingerprint mismatch")
    award_fp = _hash(
        {
            "event_id": awards.event_id,
            "seed": awards.seed,
            "result_package_fingerprint": result_fp,
            "point_distribution_fingerprint": awards.metadata.point_distribution_fingerprint,
            "awards": [
                a.model_dump(mode="json")
                for a in sorted(awards.awards, key=lambda a: a.player_id)
            ],
        }
    )
    if (
        award_fp != binding.expected_award_fingerprint
        or award_fp != awards.metadata.build_fingerprint
    ):
        raise ValueError("Tournament award fingerprint mismatch")
    by_id = {p.player_id: p for p in result.player_results}
    versions = []
    for award in sorted(awards.awards, key=lambda a: a.player_id):
        player = by_id[award.player_id]
        if (
            award.reached_stage != player.reached_stage
            or award.qualifier
            or award.source_result_fingerprint != result_fp
            or award.source_player_result_fingerprint
            != _hash(player.model_dump(mode="json"))
        ):
            raise ValueError("Player award provenance mismatch")
        versions.append(
            RankingResultVersion(
                run_id=binding.run_id,
                branch_id=binding.branch_id,
                effective_week=binding.first_publication_week,
                previous_fingerprint=None,
                result=OfficialRankingResult(
                    edition_id=binding.edition_id,
                    player_id=award.player_id,
                    completed_week=binding.completed_week,
                    first_publication_week=binding.first_publication_week,
                    validity_weeks=binding.validity_weeks,
                    main_points=award.ranking_points_awarded,
                    source_fingerprint=_hash(
                        {
                            "binding": binding.model_dump(mode="json"),
                            "award": award.award_fingerprint,
                        }
                    ),
                ),
            )
        )
    return tuple(versions)


def ingest_tournament_ranking_sources(
    service: SeasonPointAwardsService,
    writer: RankingSourceWriter,
    binding: TournamentRankingBinding,
) -> tuple[RankingResultVersion, ...]:
    """Read persisted packages and stage all sources in the caller's transaction.

    Any write failure requires whole-transaction rollback; never catch and commit
    a partial batch. The JSON sources are read-only and not transaction-owned.
    """
    result = service.result_service.get_event_result(
        event_id=binding.event_id
    ).result_package
    awards = service.get_event_point_awards(event_id=binding.event_id).award_package
    if result is None or awards is None:
        raise ValueError("Persisted tournament results and awards are required")
    versions = prepare_tournament_ranking_sources(binding, result, awards)
    return tuple(writer.append(version) for version in versions)

"""Fail-closed, pure rebind of one canonical Season Closing Ranking archive.

This is a prerequisite for post-Season-Transition Saved Revision forks, not an
authorization to install a cross-season fork. The calling transaction must
separately verify target-local ranking/result/zero/Week-61 publication sources,
season-closure marker, player states and the Season Transition World Event.
"""

from __future__ import annotations

from collections.abc import Mapping

from beta_engine.domain.rankings.official import (
    DisciplinaryZero,
    OfficialRankingPlayer,
    OfficialRankingResult,
    OfficialRankingSnapshot,
)
from beta_engine.domain.rankings.season_closing import (
    SeasonClosingRankingSnapshot,
    calculate_season_closing_ranking,
)


class SeasonClosingForkProofError(ValueError):
    """Closing archive or its paired target authority cannot be proven."""


def _reject(reason: str) -> None:
    raise SeasonClosingForkProofError(reason)


def _sporting_result(result: OfficialRankingResult) -> dict:
    data = result.model_dump(mode="json")
    data.pop("source_fingerprint")
    return data


def _sporting_zero(zero: DisciplinaryZero) -> dict:
    data = zero.model_dump(mode="json")
    data.pop("branch_id")
    data.pop("source_fingerprint")
    return data


def _sporting_rows(snapshot) -> tuple:
    return tuple(
        (
            row.rank,
            row.player_id,
            row.points,
            tuple(_sporting_result(x) for x in row.counted_results),
            tuple(_sporting_zero(x) for x in row.disciplinary_zeros),
        )
        for row in snapshot.rows
    )


def _prove_fingerprint_map(
    originals: tuple,
    targets: tuple,
    fingerprint_map: Mapping[str, str],
    *,
    field: str,
) -> None:
    """Require the caller's independently proven, complete 1:1 source map."""
    source_keys = [item.source_fingerprint for item in originals]
    target_keys = [item.source_fingerprint for item in targets]
    if (
        not isinstance(fingerprint_map, Mapping)
        # One Tournament may own results for multiple players, so repeated
        # *item* fingerprints are legal; only the distinct provenance map
        # itself must remain one-to-one.
        or set(fingerprint_map) != set(source_keys)
        or set(fingerprint_map.values()) != set(target_keys)
        or len(set(fingerprint_map.values())) != len(fingerprint_map)
    ):
        _reject(f"Season Closing {field} fingerprint provenance is not bijective")
    for source, target in zip(originals, targets, strict=True):
        if fingerprint_map[source.source_fingerprint] != target.source_fingerprint:
            _reject(f"Season Closing {field} provenance order differs")


def rebind_verified_season_closing_ranking(
    source: SeasonClosingRankingSnapshot,
    *,
    source_predecessor: OfficialRankingSnapshot,
    target_predecessor: OfficialRankingSnapshot,
    source_players: tuple[OfficialRankingPlayer, ...],
    target_players: tuple[OfficialRankingPlayer, ...],
    source_results: tuple[OfficialRankingResult, ...],
    target_results: tuple[OfficialRankingResult, ...],
    source_zeros: tuple[DisciplinaryZero, ...] = (),
    target_zeros: tuple[DisciplinaryZero, ...] = (),
    result_fingerprint_map: Mapping[str, str],
    zero_fingerprint_map: Mapping[str, str],
    target_branch_id: str,
) -> SeasonClosingRankingSnapshot:
    """Regenerate source and target Season Closing Ranking from frozen inputs.

    A branch-id replacement on an archived snapshot is *not* proof: the source
    input fingerprint, Week-61 predecessor and every result/zero must first be
    recomputed. Target result and disciplinary source fingerprints must follow
    the caller's independently verified mappings. Never re-use the source
    archive fingerprint as target authority.
    """
    source = SeasonClosingRankingSnapshot.model_validate_json(source.model_dump_json())
    source_predecessor = OfficialRankingSnapshot.model_validate_json(
        source_predecessor.model_dump_json()
    )
    target_predecessor = OfficialRankingSnapshot.model_validate_json(
        target_predecessor.model_dump_json()
    )
    if (
        not target_branch_id
        or source.branch_id == target_branch_id
        or source.run_id != source_predecessor.run_id
        or source.branch_id != source_predecessor.branch_id
        or target_predecessor.run_id != source.run_id
        or target_predecessor.branch_id != target_branch_id
        or source_predecessor.week != source.completed_week
        or target_predecessor.week != source.completed_week
        or source.completed_week.week != 61
        or source.policy != source_predecessor.policy
        or target_predecessor.policy != source.policy
        or source.predecessor_official_fingerprint != source_predecessor.fingerprint
    ):
        _reject("Season Closing fork source/target Week-61 authority scope differs")
    if (
        tuple(source_players) != tuple(target_players)
        or _sporting_rows(source_predecessor) != _sporting_rows(target_predecessor)
    ):
        _reject("Season Closing fork changed player roster or Week-61 sporting ranking")

    original_results = tuple(sorted(source_results, key=lambda r: (r.edition_id, r.player_id)))
    rebound_results = tuple(sorted(target_results, key=lambda r: (r.edition_id, r.player_id)))
    original_zeros = tuple(sorted(source_zeros, key=lambda z: z.zero_id))
    rebound_zeros = tuple(sorted(target_zeros, key=lambda z: z.zero_id))
    if (
        len(original_results) != len(rebound_results)
        or len(original_zeros) != len(rebound_zeros)
        or tuple(_sporting_result(r) for r in original_results)
        != tuple(_sporting_result(r) for r in rebound_results)
        or tuple(_sporting_zero(z) for z in original_zeros)
        != tuple(_sporting_zero(z) for z in rebound_zeros)
        or any(
            z.run_id != source.run_id or z.branch_id != source.branch_id
            for z in original_zeros
        )
        or any(
            z.run_id != source.run_id or z.branch_id != target_branch_id
            for z in rebound_zeros
        )
    ):
        _reject("Season Closing fork results or disciplinary decisions changed")
    _prove_fingerprint_map(
        original_results, rebound_results, result_fingerprint_map, field="result"
    )
    _prove_fingerprint_map(
        original_zeros, rebound_zeros, zero_fingerprint_map, field="zero"
    )
    try:
        original = calculate_season_closing_ranking(
            run_id=source.run_id,
            branch_id=source.branch_id,
            completed_week=source.completed_week,
            policy=source.policy,
            players=tuple(source_players),
            results=original_results,
            predecessor=source_predecessor,
            disciplinary_zeros=original_zeros,
        )
        if original != source:
            _reject("Archived Season Closing Ranking differs from canonical source inputs")
        rebound = calculate_season_closing_ranking(
            run_id=source.run_id,
            branch_id=target_branch_id,
            completed_week=source.completed_week,
            policy=source.policy,
            players=tuple(target_players),
            results=rebound_results,
            predecessor=target_predecessor,
            disciplinary_zeros=rebound_zeros,
        )
    except ValueError as exc:
        if isinstance(exc, SeasonClosingForkProofError):
            raise
        raise SeasonClosingForkProofError(
            f"Season Closing fork canonical recalculation failed: {exc}"
        ) from exc
    if _sporting_rows(original) != _sporting_rows(rebound):
        _reject("Season Closing fork recalculated a different sporting outcome")
    if rebound.fingerprint == source.fingerprint:
        _reject("Season Closing fork retained the source archive fingerprint")
    return rebound

"""Safe branch-identity remapping for the first ranking-bearing fork slice.

This module intentionally supports only the narrow bootstrap-only ranking state that can
be reconstructed from its complete stored command payload without inventing policy.

Later ranking history with tournament sources, zeros, Week/Season Transition state or
archive authorities remains fail-closed until dedicated remap adapters exist.
"""

from __future__ import annotations

import hashlib
import json

from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.initial_world import (
    InitialWorldState,
    derive_initial_ranking_inputs,
)
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.application.ranking_tournament_ingestion import (
    prepare_canonical_tournament_ranking_sources,
)
from beta_engine.domain.rankings.input_manifest import RankingInputManifest
from beta_engine.domain.rankings.official import calculate_official_ranking
from beta_engine.domain.rankings.result_history import RankingResultVersion
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
from beta_engine.domain.tournaments.ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthority,
)
from beta_engine.domain.rankings.zero_history import (
    RankingZeroVersion,
    resolve_zero_versions,
)
from beta_engine.domain.rankings.revision_state import (
    RankingRevisionEntry,
    RankingRevisionReceipt,
    RankingRevisionState,
)


class RankingForkRemapUnsupportedError(ValueError):
    """Raised when a ranking bundle is outside the supported fork-remap slice."""


def _remap_publication_world_state(
    state: dict | None,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    source_entries: tuple[RankingRevisionEntry, ...],
    target_entries: tuple[RankingRevisionEntry, ...],
) -> dict | None:
    """Rebind publication rows and world head to target ranking snapshot identity.

    Week/Season Transition receipts and World Events are intentionally excluded here:
    those carry lifecycle/sporting or Season Closing evidence outside the ranking-only
    fork bundle and must be remapped together with those owning authorities.
    """
    if state is None:
        return None
    if state["receipts"] or state["events"]:
        raise RankingForkRemapUnsupportedError(
            "Authoritative transition receipts/events require lifecycle/sporting remapping first"
        )

    source_by_ordinal = {
        entry.snapshot.week.ordinal: entry.snapshot for entry in source_entries
    }
    target_by_ordinal = {
        entry.snapshot.week.ordinal: entry.snapshot for entry in target_entries
    }
    publications: list[dict] = []
    for row in state["publications"]:
        if (row["run_id"], row["branch_id"]) != (run_id, source_branch_id):
            raise RankingForkRemapUnsupportedError(
                "Official Ranking publication scope does not match the source Branch"
            )
        ordinal = row["week_ordinal"]
        source_snapshot = source_by_ordinal.get(ordinal)
        target_snapshot = target_by_ordinal.get(ordinal)
        if source_snapshot is None or target_snapshot is None:
            raise RankingForkRemapUnsupportedError(
                "Official Ranking publication has no matching ranking history entry"
            )
        if (
            row["snapshot_fingerprint"] != source_snapshot.fingerprint
            or row["payload_json"] != source_snapshot.model_dump_json()
        ):
            raise RankingForkRemapUnsupportedError(
                "Official Ranking publication differs from frozen source ranking history"
            )
        publications.append(
            {
                "run_id": run_id,
                "branch_id": target_branch_id,
                "week_ordinal": ordinal,
                "snapshot_fingerprint": target_snapshot.fingerprint,
                "payload_json": target_snapshot.model_dump_json(),
            }
        )

    world = state["world"]
    target_world = None
    if world is not None:
        if (world["run_id"], world["branch_id"]) != (run_id, source_branch_id):
            raise RankingForkRemapUnsupportedError(
                "Authoritative world scope does not match the source Branch"
            )
        target_snapshot = target_by_ordinal.get(world["current_ordinal"])
        source_snapshot = source_by_ordinal.get(world["current_ordinal"])
        if (
            source_snapshot is None
            or target_snapshot is None
            or world["ranking_fingerprint"] != source_snapshot.fingerprint
        ):
            raise RankingForkRemapUnsupportedError(
                "Authoritative world head differs from frozen source ranking history"
            )
        if (
            not publications
            or publications[-1]["week_ordinal"] != world["current_ordinal"]
        ):
            raise RankingForkRemapUnsupportedError(
                "Authoritative world head is not the latest Official Ranking publication"
            )
        target_world = {
            "run_id": run_id,
            "branch_id": target_branch_id,
            "current_ordinal": world["current_ordinal"],
            "ranking_fingerprint": target_snapshot.fingerprint,
        }

    return {
        "world": target_world,
        "publications": publications,
        "receipts": [],
        "events": [],
    }


def _remap_transition_authorities(
    authorities: tuple[RankingTransitionAuthority, ...],
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    target_base_revision_id: str,
) -> tuple[
    tuple[RankingTransitionAuthority, ...],
    dict[str, RankingTransitionAuthority],
]:
    """Rebind immutable Week Transition ranking inputs to target fork identity.

    Sporting roster, policy, provenance and audit stay immutable. Branch and Saved
    Revision ownership are target-local, so the fingerprint is intentionally rebuilt.
    """
    if not target_base_revision_id.strip():
        raise RankingForkRemapUnsupportedError(
            "Ranking transition authority remap requires a target Saved Revision id"
        )

    remapped: list[RankingTransitionAuthority] = []
    by_source_fingerprint: dict[str, RankingTransitionAuthority] = {}
    previous_target_ordinal = None

    for authority in authorities:
        if (authority.run_id, authority.branch_id) != (run_id, source_branch_id):
            raise RankingForkRemapUnsupportedError(
                "Ranking transition authority scope does not match the source Branch"
            )
        if (
            previous_target_ordinal is not None
            and authority.target_week.ordinal <= previous_target_ordinal
        ):
            raise RankingForkRemapUnsupportedError(
                "Ranking transition authority history is not in canonical target-week order"
            )

        target = RankingTransitionAuthority.model_validate_json(
            authority.model_copy(
                update={
                    "branch_id": target_branch_id,
                    "base_revision_id": target_base_revision_id,
                }
            ).model_dump_json()
        )
        by_source_fingerprint[authority.fingerprint] = target
        remapped.append(target)
        previous_target_ordinal = authority.target_week.ordinal

    return tuple(remapped), by_source_fingerprint


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _remap_point_awards(authority, *, target_branch_id: str, result_fingerprint: str):
    awards = []
    for award in authority.awards:
        payload = {
            "schema_version": (
                "tournament_player_point_award_authority.v3"
                if award.qualification_point_stage is not None
                else (
                    "tournament_player_point_award_authority.v2"
                    if award.point_stage is not None
                    else "tournament_player_point_award_authority.v1"
                )
            ),
            "event_id": authority.event_id,
            "seed": authority.seed,
            "player_id": award.player_id,
            "reached_stage": award.reached_stage,
            "qualifier": award.qualifier,
            "seed_number": award.seed_number,
            "ranking_points_awarded": award.ranking_points_awarded,
            "race_points_awarded": award.race_points_awarded,
            "source_tournament_result_fingerprint": result_fingerprint,
            "source_player_result_fingerprint": award.source_player_result_fingerprint,
        }
        if award.point_stage is not None:
            payload["point_stage"] = award.point_stage
        if award.qualification_point_stage is not None:
            payload["qualification_point_stage"] = award.qualification_point_stage
            payload["qualification_points_awarded"] = award.qualification_points_awarded
        awards.append(award.model_copy(update={"award_fingerprint": _hash(payload)}))
    return authority.__class__.model_validate_json(
        authority.model_copy(
            update={
                "branch_id": target_branch_id,
                "tournament_result_fingerprint": result_fingerprint,
                "awards": tuple(awards),
            }
        ).model_dump_json()
    )


def _remap_prize_awards(authority, *, target_branch_id: str, result_fingerprint: str):
    awards = []
    for award in authority.awards:
        award_fingerprint = _hash(
            {
                "schema_version": "tournament_player_prize_money_award_authority.v1",
                "event_id": authority.event_id,
                "player_id": award.player_id,
                "reached_stage": award.reached_stage,
                "payout_status": award.payout_status,
                "amount": award.amount,
                "currency": award.currency,
                "source_tournament_result_fingerprint": result_fingerprint,
                "source_player_result_fingerprint": award.source_player_result_fingerprint,
                "edition_prize_money_config_fingerprint": authority.edition_prize_money_config_fingerprint,
            }
        )
        awards.append(award.model_copy(update={"award_fingerprint": award_fingerprint}))
    return authority.__class__.model_validate_json(
        authority.model_copy(
            update={
                "branch_id": target_branch_id,
                "tournament_result_fingerprint": result_fingerprint,
                "awards": tuple(awards),
            }
        ).model_dump_json()
    )


def _remap_tournament_sources(
    sources: tuple[OwnedTournamentRankingSource, ...],
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
) -> tuple[
    tuple[OwnedTournamentRankingSource, ...],
    dict[str, OwnedTournamentRankingSource],
    dict[str, RankingResultVersion],
    set[str],
]:
    remapped_sources: list[OwnedTournamentRankingSource] = []
    by_edition: dict[str, OwnedTournamentRankingSource] = {}
    result_version_map: dict[str, RankingResultVersion] = {}
    tournament_editions: set[str] = set()

    for source in sources:
        binding = source.binding
        if (binding.run_id, binding.branch_id) != (run_id, source_branch_id):
            raise RankingForkRemapUnsupportedError(
                "Owned tournament source scope does not match the source Branch"
            )
        if source.schema_version not in {
            "owned_tournament_ranking_source.v4",
            "owned_tournament_ranking_source.v5",
        }:
            raise RankingForkRemapUnsupportedError(
                "Ranking fork supports only canonical v4/v5 tournament sources"
            )
        if source.canonical_result is None or source.canonical_awards is None:
            raise RankingForkRemapUnsupportedError(
                "Canonical tournament source authority bundle is incomplete"
            )

        target_result = source.canonical_result.__class__.model_validate_json(
            source.canonical_result.model_copy(
                update={"branch_id": target_branch_id}
            ).model_dump_json()
        )
        target_awards = _remap_point_awards(
            source.canonical_awards,
            target_branch_id=target_branch_id,
            result_fingerprint=target_result.fingerprint,
        )
        target_prize = None
        if source.canonical_prize_awards is not None:
            target_prize = _remap_prize_awards(
                source.canonical_prize_awards,
                target_branch_id=target_branch_id,
                result_fingerprint=target_result.fingerprint,
            )
        target_binding = binding.model_copy(
            update={
                "branch_id": target_branch_id,
                "expected_result_fingerprint": target_result.fingerprint,
                "expected_award_fingerprint": target_awards.fingerprint,
            }
        )
        target_source = OwnedTournamentRankingSource.model_validate_json(
            source.model_copy(
                update={
                    "binding": target_binding,
                    "canonical_result": target_result,
                    "canonical_awards": target_awards,
                    "canonical_prize_awards": target_prize,
                }
            ).model_dump_json()
        )

        original_versions = prepare_canonical_tournament_ranking_sources(
            source.binding,
            source.canonical_result,
            source.canonical_awards,
        )
        target_versions = prepare_canonical_tournament_ranking_sources(
            target_source.binding,
            target_result,
            target_awards,
        )
        if len(original_versions) != len(target_versions):
            raise RankingForkRemapUnsupportedError(
                "Canonical tournament ranking projection changed during remap"
            )
        for original_version, target_version in zip(
            original_versions, target_versions, strict=True
        ):
            result_version_map[original_version.fingerprint] = target_version

        tournament_editions.add(binding.edition_id)
        by_edition[binding.edition_id] = target_source
        remapped_sources.append(target_source)

    return (
        tuple(remapped_sources),
        by_edition,
        result_version_map,
        tournament_editions,
    )


def _remap_result_sources(
    source_versions: tuple[RankingResultVersion, ...],
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    tournament_version_map: dict[str, RankingResultVersion] | None = None,
    tournament_editions: set[str] | None = None,
) -> tuple[
    tuple[RankingResultVersion, ...],
    dict[str, RankingResultVersion],
]:
    remapped: list[RankingResultVersion] = []
    by_source_fingerprint: dict[str, RankingResultVersion] = {}
    latest_by_key: dict[tuple[str, str], RankingResultVersion] = {}
    latest_source_by_key: dict[tuple[str, str], RankingResultVersion] = {}
    tournament_version_map = tournament_version_map or {}
    tournament_editions = tournament_editions or set()

    for version in source_versions:
        if (version.run_id, version.branch_id) != (run_id, source_branch_id):
            raise RankingForkRemapUnsupportedError(
                "Ranking result source scope does not match the source Branch"
            )
        key = (version.result.edition_id, version.result.player_id)
        canonical_tournament_version = tournament_version_map.get(version.fingerprint)
        previous = latest_by_key.get(key)
        source_previous = latest_source_by_key.get(key)
        expected_source_previous_fingerprint = (
            source_previous.fingerprint if source_previous is not None else None
        )
        if version.previous_fingerprint != expected_source_previous_fingerprint:
            raise RankingForkRemapUnsupportedError(
                "Ranking result correction predecessor differs from source history"
            )

        if canonical_tournament_version is not None:
            remapped_version = canonical_tournament_version
            if previous is not None:
                raise RankingForkRemapUnsupportedError(
                    "Canonical tournament source must be the first version for its player"
                )
        else:
            if version.result.edition_id in tournament_editions and previous is None:
                raise RankingForkRemapUnsupportedError(
                    "Canonical tournament correction is missing its remapped base result"
                )
            remapped_version = RankingResultVersion(
                run_id=run_id,
                branch_id=target_branch_id,
                effective_week=version.effective_week,
                result=version.result,
                previous_fingerprint=(
                    previous.fingerprint if previous is not None else None
                ),
            )
        by_source_fingerprint[version.fingerprint] = remapped_version
        latest_by_key[key] = remapped_version
        latest_source_by_key[key] = version
        remapped.append(remapped_version)

    return tuple(remapped), by_source_fingerprint


def _resolve_result_versions(
    versions: tuple[RankingResultVersion, ...],
    *,
    week,
):
    latest: dict[tuple[str, str], object] = {}
    for version in versions:
        if version.effective_week.ordinal <= week.ordinal:
            latest[(version.result.edition_id, version.result.player_id)] = (
                version.result
            )
    return tuple(latest[key] for key in sorted(latest))


def _remap_command_corrections(
    versions: tuple[RankingResultVersion, ...],
    *,
    mapped_by_source_fingerprint: dict[str, RankingResultVersion],
) -> tuple[RankingResultVersion, ...]:
    remapped: list[RankingResultVersion] = []
    for version in versions:
        mapped = mapped_by_source_fingerprint.get(version.fingerprint)
        if mapped is None:
            raise RankingForkRemapUnsupportedError(
                "Ranking command references result history outside the Saved Revision"
            )
        remapped.append(mapped)
    return tuple(remapped)


def _remap_zero_sources(
    source_versions: tuple[RankingZeroVersion, ...],
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
) -> tuple[
    tuple[RankingZeroVersion, ...],
    dict[str, RankingZeroVersion],
]:
    remapped: list[RankingZeroVersion] = []
    by_source_fingerprint: dict[str, RankingZeroVersion] = {}
    latest_by_zero_id: dict[str, RankingZeroVersion] = {}

    for version in source_versions:
        zero = version.zero
        if (zero.run_id, zero.branch_id) != (run_id, source_branch_id):
            raise RankingForkRemapUnsupportedError(
                "Ranking zero source scope does not match the source Branch"
            )
        previous = latest_by_zero_id.get(zero.zero_id)
        expected_previous = previous.fingerprint if previous is not None else None
        remapped_version = RankingZeroVersion(
            effective_week=version.effective_week,
            zero=zero.model_copy(update={"branch_id": target_branch_id}),
            previous_fingerprint=expected_previous,
        )
        by_source_fingerprint[version.fingerprint] = remapped_version
        latest_by_zero_id[zero.zero_id] = remapped_version
        remapped.append(remapped_version)

    return tuple(remapped), by_source_fingerprint


def _remap_command_zero_versions(
    versions: tuple[RankingZeroVersion, ...],
    *,
    mapped_by_source_fingerprint: dict[str, RankingZeroVersion],
) -> tuple[RankingZeroVersion, ...]:
    remapped: list[RankingZeroVersion] = []
    for version in versions:
        mapped = mapped_by_source_fingerprint.get(version.fingerprint)
        if mapped is None:
            raise RankingForkRemapUnsupportedError(
                "Ranking command references zero history outside the Saved Revision"
            )
        remapped.append(mapped)
    return tuple(remapped)


def _remap_tournament_ranking_snapshot_authorities(
    authorities: tuple[TournamentRankingSnapshotAuthority, ...],
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    source_entries: tuple[RankingRevisionEntry, ...],
    target_entries: tuple[RankingRevisionEntry, ...],
) -> tuple[
    tuple[TournamentRankingSnapshotAuthority, ...],
    dict[str, TournamentRankingSnapshotAuthority],
]:
    source_by_week = {
        entry.snapshot.week.ordinal: entry.snapshot for entry in source_entries
    }
    target_by_week = {
        entry.snapshot.week.ordinal: entry.snapshot for entry in target_entries
    }
    remapped = []
    by_source_fingerprint = {}
    for authority in authorities:
        if (authority.run_id, authority.branch_id) != (run_id, source_branch_id):
            raise RankingForkRemapUnsupportedError(
                "Tournament Ranking Snapshot authority scope differs from source Branch"
            )
        source_snapshot = source_by_week.get(authority.ranking_week.ordinal)
        target_snapshot = target_by_week.get(authority.ranking_week.ordinal)
        if (
            source_snapshot is None
            or target_snapshot is None
            or authority.ranking_snapshot != source_snapshot
        ):
            raise RankingForkRemapUnsupportedError(
                "Tournament Ranking Snapshot authority differs from frozen ranking history"
            )
        target = TournamentRankingSnapshotAuthority.model_validate_json(
            authority.model_copy(
                update={
                    "branch_id": target_branch_id,
                    "ranking_snapshot": target_snapshot,
                }
            ).model_dump_json()
        )
        by_source_fingerprint[authority.fingerprint] = target
        remapped.append(target)
    return tuple(remapped), by_source_fingerprint


def remap_source_free_ranking_state_for_branch(
    source: RankingRevisionState,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    target_base_revision_id: str | None = None,
    source_initial_world: InitialWorldState | None = None,
    target_initial_world: InitialWorldState | None = None,
) -> RankingRevisionState:
    """Rebuild one result-free ranking lineage, including versioned zero history.

    Tournament/correction results and transition/publication authorities remain outside
    this adapter. Stored disciplinary-zero decisions are replayed from their complete
    immutable versions and receive target-Branch identity/fingerprint chains.
    """
    if (source.run_id, source.branch_id) != (run_id, source_branch_id):
        raise RankingForkRemapUnsupportedError(
            "Ranking fork source scope does not match the selected Run/Branch"
        )
    if not source.entries or source.entries[0].snapshot.week.ordinal != 0:
        raise RankingForkRemapUnsupportedError(
            "Ranking-bearing fork requires a complete Week-1 ranking root"
        )
    if source.season_closing_rankings:
        raise RankingForkRemapUnsupportedError(
            "Ranking-bearing fork does not yet support Season Closing authorities"
        )
    if source.transition_authorities and target_base_revision_id is None:
        raise RankingForkRemapUnsupportedError(
            "Transition-bearing ranking fork requires the target materialized Saved Revision id"
        )

    remapped_transition_authorities, transition_by_source_fingerprint = (
        _remap_transition_authorities(
            source.transition_authorities,
            run_id=run_id,
            source_branch_id=source_branch_id,
            target_branch_id=target_branch_id,
            target_base_revision_id=target_base_revision_id or "",
        )
        if source.transition_authorities
        else ((), {})
    )
    source_transition_by_fingerprint = {
        authority.fingerprint: authority for authority in source.transition_authorities
    }

    (
        remapped_tournament_sources,
        remapped_tournament_by_edition,
        tournament_version_map,
        tournament_editions,
    ) = _remap_tournament_sources(
        source.tournament_sources,
        run_id=run_id,
        source_branch_id=source_branch_id,
        target_branch_id=target_branch_id,
    )
    source_tournament_by_edition = {
        item.binding.edition_id: item for item in source.tournament_sources
    }
    remapped_result_sources, result_by_source_fingerprint = _remap_result_sources(
        source.sources,
        run_id=run_id,
        source_branch_id=source_branch_id,
        target_branch_id=target_branch_id,
        tournament_version_map=tournament_version_map,
        tournament_editions=tournament_editions,
    )
    remapped_zero_sources, zero_by_source_fingerprint = _remap_zero_sources(
        source.zero_sources,
        run_id=run_id,
        source_branch_id=source_branch_id,
        target_branch_id=target_branch_id,
    )
    referenced_zero_fingerprints: set[str] = set()
    referenced_tournament_editions: set[str] = set()
    referenced_transition_fingerprints: set[str] = set()

    remapped_entries: list[RankingRevisionEntry] = []
    previous = None
    for index, entry in enumerate(source.entries):
        if len(entry.receipts) != 1:
            raise RankingForkRemapUnsupportedError(
                "Ranking-bearing fork requires one complete command receipt per week"
            )
        receipt = entry.receipts[0]
        if receipt.request_payload_json is None:
            raise RankingForkRemapUnsupportedError(
                "Ranking fork requires every original stored command payload"
            )
        try:
            payload = json.loads(receipt.request_payload_json)
        except json.JSONDecodeError as exc:
            raise RankingForkRemapUnsupportedError(
                "Ranking command payload is invalid"
            ) from exc
        if not isinstance(payload, dict):
            raise RankingForkRemapUnsupportedError("Ranking command payload is invalid")

        if index == 0:
            original = RankingBootstrapCommand.model_validate_json(
                receipt.request_payload_json
            )
            if (
                original.run_id != run_id
                or original.branch_id != source_branch_id
                or original.command_id != receipt.command_id
                or original.target_week != entry.snapshot.week
                or original.policy != entry.snapshot.policy
                or original.players != entry.inputs.players
            ):
                raise RankingForkRemapUnsupportedError(
                    "Ranking bootstrap command does not exactly match frozen evidence"
                )
            if original.initial_world_fingerprint is not None:
                if source_initial_world is None or target_initial_world is None:
                    raise RankingForkRemapUnsupportedError(
                        "InitialWorld-backed ranking fork requires both validated worlds"
                    )
                if (
                    (source_initial_world.run_id, source_initial_world.branch_id)
                    != (run_id, source_branch_id)
                    or (target_initial_world.run_id, target_initial_world.branch_id)
                    != (run_id, target_branch_id)
                    or original.initial_world_fingerprint
                    != source_initial_world.fingerprint
                ):
                    raise RankingForkRemapUnsupportedError(
                        "Ranking bootstrap InitialWorld linkage does not match the fork worlds"
                    )
                try:
                    source_policy, source_players = derive_initial_ranking_inputs(
                        source_initial_world
                    )
                    target_policy, target_players = derive_initial_ranking_inputs(
                        target_initial_world
                    )
                except ValueError as exc:
                    raise RankingForkRemapUnsupportedError(str(exc)) from exc
                if (
                    original.policy != source_policy
                    or original.players != source_players
                    or entry.inputs.players != source_players
                    or target_players != source_players
                    or target_policy != source_policy
                ):
                    raise RankingForkRemapUnsupportedError(
                        "Ranking bootstrap players/policy do not derive from InitialWorld"
                    )
                target_initial_world_fingerprint = target_initial_world.fingerprint
            else:
                if source_initial_world is not None or target_initial_world is not None:
                    raise RankingForkRemapUnsupportedError(
                        "Captured InitialWorld is not linked by the ranking bootstrap"
                    )
                target_initial_world_fingerprint = None
            if original.discipline == "resolved_zeros":
                raise RankingForkRemapUnsupportedError(
                    "Ranking bootstrap fork supports only none/stored_zeros discipline"
                )
            command_zero_versions = _remap_command_zero_versions(
                original.zero_versions,
                mapped_by_source_fingerprint=zero_by_source_fingerprint,
            )
            referenced_zero_fingerprints.update(
                version.fingerprint for version in original.zero_versions
            )
            command = RankingBootstrapCommand.model_validate_json(
                original.model_copy(
                    update={
                        "branch_id": target_branch_id,
                        "zero_versions": command_zero_versions,
                        "initial_world_fingerprint": target_initial_world_fingerprint,
                    }
                ).model_dump_json()
            )
            resolved_zeros = (
                resolve_zero_versions(
                    remapped_zero_sources,
                    command.target_week,
                )
                if command.discipline == "stored_zeros"
                else ()
            )
            original_resolved_zeros = (
                resolve_zero_versions(source.zero_sources, original.target_week)
                if original.discipline == "stored_zeros"
                else ()
            )
            if entry.inputs.zeros_from_history != (
                original.discipline == "stored_zeros"
            ) or entry.inputs.disciplinary_zeros != tuple(
                sorted(original_resolved_zeros, key=lambda z: z.zero_id)
            ):
                raise RankingForkRemapUnsupportedError(
                    "Ranking bootstrap zero manifest does not match stored zero history"
                )
            original_results = _resolve_result_versions(
                source.sources,
                week=original.target_week,
            )
            if entry.inputs.results != original_results:
                raise RankingForkRemapUnsupportedError(
                    "Ranking bootstrap result manifest does not match stored result history"
                )
            resolved_results = _resolve_result_versions(
                remapped_result_sources,
                week=command.target_week,
            )
            snapshot = calculate_official_ranking(
                run_id=run_id,
                branch_id=target_branch_id,
                week=command.target_week,
                policy=command.policy,
                players=command.players,
                results=resolved_results,
                previous=None,
                disciplinary_zeros=resolved_zeros,
            )
            inputs = RankingInputManifest(
                players=command.players,
                results=resolved_results,
                disciplinary_zeros=tuple(
                    sorted(resolved_zeros, key=lambda z: z.zero_id)
                ),
                zeros_from_history=(command.discipline == "stored_zeros"),
                command_request_fingerprint=command.fingerprint,
            )
        else:
            original = RankingWeekCommand.model_validate_json(
                receipt.request_payload_json
            )
            if (
                original.command_id != receipt.command_id
                or original.context.run_id != run_id
                or original.context.branch_id != source_branch_id
                or original.context.target_week != entry.snapshot.week
                or original.context.policy != entry.snapshot.policy
                or original.context.players != entry.inputs.players
            ):
                raise RankingForkRemapUnsupportedError(
                    "Ranking weekly command does not exactly match frozen evidence"
                )
            if original.context.discipline == "resolved_zeros":
                raise RankingForkRemapUnsupportedError(
                    "Ranking weekly fork supports only none/stored_zeros discipline"
                )
            target_authority = None
            if original.authority_fingerprint is None:
                if original.audit is not None:
                    raise RankingForkRemapUnsupportedError(
                        "Audited ranking command is missing its transition authority"
                    )
            else:
                source_authority = source_transition_by_fingerprint.get(
                    original.authority_fingerprint
                )
                target_authority = transition_by_source_fingerprint.get(
                    original.authority_fingerprint
                )
                if source_authority is None or target_authority is None:
                    raise RankingForkRemapUnsupportedError(
                        "Ranking command transition authority is not owned by the Saved Revision"
                    )
                if (
                    source_authority.completed_week != original.context.completed_week
                    or source_authority.target_week != original.context.target_week
                    or source_authority.players != original.context.players
                    or source_authority.policy != original.context.policy
                    or source_authority.audit != original.audit
                ):
                    raise RankingForkRemapUnsupportedError(
                        "Ranking command transition authority does not match frozen command evidence"
                    )
                referenced_transition_fingerprints.add(original.authority_fingerprint)
            if previous is None or original.context.completed_week != previous.week:
                raise RankingForkRemapUnsupportedError(
                    "Ranking weekly command lineage is not consecutive"
                )

            command_zero_versions = _remap_command_zero_versions(
                original.zero_versions,
                mapped_by_source_fingerprint=zero_by_source_fingerprint,
            )
            command_corrections = _remap_command_corrections(
                original.corrections,
                mapped_by_source_fingerprint=result_by_source_fingerprint,
            )
            command_tournaments = []
            for binding in original.tournaments:
                source_tournament = source_tournament_by_edition.get(binding.edition_id)
                target_tournament = remapped_tournament_by_edition.get(
                    binding.edition_id
                )
                if (
                    source_tournament is None
                    or target_tournament is None
                    or source_tournament.binding != binding
                ):
                    raise RankingForkRemapUnsupportedError(
                        "Ranking command tournament binding is not owned by the Saved Revision"
                    )
                command_tournaments.append(target_tournament.binding)
                referenced_tournament_editions.add(binding.edition_id)
            referenced_zero_fingerprints.update(
                version.fingerprint for version in original.zero_versions
            )
            command = RankingWeekCommand.model_validate_json(
                original.model_copy(
                    update={
                        "context": original.context.model_copy(
                            update={"branch_id": target_branch_id}
                        ),
                        "zero_versions": command_zero_versions,
                        "corrections": command_corrections,
                        "tournaments": tuple(command_tournaments),
                        "authority_fingerprint": (
                            target_authority.fingerprint
                            if target_authority is not None
                            else None
                        ),
                    }
                ).model_dump_json()
            )
            resolved_zeros = (
                resolve_zero_versions(
                    remapped_zero_sources,
                    command.context.target_week,
                )
                if command.context.discipline == "stored_zeros"
                else ()
            )
            original_resolved_zeros = (
                resolve_zero_versions(
                    source.zero_sources,
                    original.context.target_week,
                )
                if original.context.discipline == "stored_zeros"
                else ()
            )
            if entry.inputs.zeros_from_history != (
                original.context.discipline == "stored_zeros"
            ) or entry.inputs.disciplinary_zeros != tuple(
                sorted(original_resolved_zeros, key=lambda z: z.zero_id)
            ):
                raise RankingForkRemapUnsupportedError(
                    "Ranking weekly zero manifest does not match stored zero history"
                )
            original_results = _resolve_result_versions(
                source.sources,
                week=original.context.target_week,
            )
            if entry.inputs.results != original_results:
                raise RankingForkRemapUnsupportedError(
                    "Ranking weekly result manifest does not match stored result history"
                )
            resolved_results = _resolve_result_versions(
                remapped_result_sources,
                week=command.context.target_week,
            )
            snapshot = calculate_official_ranking(
                run_id=run_id,
                branch_id=target_branch_id,
                week=command.context.target_week,
                policy=command.context.policy,
                players=command.context.players,
                results=resolved_results,
                previous=previous,
                disciplinary_zeros=resolved_zeros,
            )
            inputs = RankingInputManifest(
                players=command.context.players,
                results=resolved_results,
                disciplinary_zeros=tuple(
                    sorted(resolved_zeros, key=lambda z: z.zero_id)
                ),
                zeros_from_history=(command.context.discipline == "stored_zeros"),
                command_request_fingerprint=command.fingerprint,
            )

        inputs.verify(snapshot, previous)
        remapped_entries.append(
            RankingRevisionEntry(
                snapshot=snapshot,
                inputs=inputs,
                receipts=(
                    RankingRevisionReceipt(
                        command_id=command.command_id,
                        request_fingerprint=command.fingerprint,
                        request_payload_json=command.canonical_request_json,
                    ),
                ),
            )
        )
        previous = snapshot

    source_zero_fingerprints = {version.fingerprint for version in source.zero_sources}
    if referenced_zero_fingerprints != source_zero_fingerprints:
        raise RankingForkRemapUnsupportedError(
            "Saved zero history is not completely owned by stored ranking commands"
        )
    if referenced_tournament_editions != tournament_editions:
        raise RankingForkRemapUnsupportedError(
            "Saved tournament sources are not completely owned by stored ranking commands"
        )
    source_transition_fingerprints = {
        authority.fingerprint for authority in source.transition_authorities
    }
    if referenced_transition_fingerprints != source_transition_fingerprints:
        raise RankingForkRemapUnsupportedError(
            "Saved transition authorities are not completely owned by stored ranking commands"
        )

    remapped_entries_tuple = tuple(remapped_entries)
    (
        remapped_tournament_ranking_snapshot_authorities,
        _tournament_ranking_snapshot_authority_map,
    ) = _remap_tournament_ranking_snapshot_authorities(
        source.tournament_ranking_snapshot_authorities,
        run_id=run_id,
        source_branch_id=source_branch_id,
        target_branch_id=target_branch_id,
        source_entries=source.entries,
        target_entries=remapped_entries_tuple,
    )
    remapped_transition_state = _remap_publication_world_state(
        source.authoritative_transition_state,
        run_id=run_id,
        source_branch_id=source_branch_id,
        target_branch_id=target_branch_id,
        source_entries=source.entries,
        target_entries=remapped_entries_tuple,
    )

    return RankingRevisionState(
        schema_version=(
            "ranking_revision_state.v5"
            if remapped_tournament_ranking_snapshot_authorities
            else "ranking_revision_state.v4"
        ),
        run_id=run_id,
        branch_id=target_branch_id,
        entries=remapped_entries_tuple,
        sources=remapped_result_sources,
        zero_sources=remapped_zero_sources,
        tournament_sources=remapped_tournament_sources,
        transition_authorities=remapped_transition_authorities,
        tournament_ranking_snapshot_authorities=(
            remapped_tournament_ranking_snapshot_authorities
        ),
        authoritative_transition_state=remapped_transition_state,
    )


# Backward-compatible internal alias for callers/tests from the bootstrap-only slice.
remap_bootstrap_ranking_state_for_branch = remap_source_free_ranking_state_for_branch

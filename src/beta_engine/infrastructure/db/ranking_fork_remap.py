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
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.application.ranking_tournament_ingestion import (
    prepare_canonical_tournament_ranking_sources,
)
from beta_engine.domain.rankings.input_manifest import RankingInputManifest
from beta_engine.domain.rankings.official import calculate_official_ranking
from beta_engine.domain.rankings.result_history import RankingResultVersion
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
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
        awards.append(
            award.model_copy(update={"award_fingerprint": _hash(payload)})
        )
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
        awards.append(
            award.model_copy(update={"award_fingerprint": award_fingerprint})
        )
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
            latest[
                (version.result.edition_id, version.result.player_id)
            ] = version.result
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
        expected_previous = (
            previous.fingerprint if previous is not None else None
        )
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


def remap_source_free_ranking_state_for_branch(
    source: RankingRevisionState,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
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
    if (
        source.transition_authorities
        or source.tournament_ranking_snapshot_authorities
        or source.season_closing_rankings
        or source.authoritative_transition_state is not None
    ):
        raise RankingForkRemapUnsupportedError(
            "Ranking-bearing fork does not yet support transition/publication authorities"
        )

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
                raise RankingForkRemapUnsupportedError(
                    "Ranking bootstrap tied to InitialWorld requires player-snapshot remapping first"
                )
            if original.audit is not None or original.discipline == "resolved_zeros":
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
            if (
                entry.inputs.zeros_from_history
                != (original.discipline == "stored_zeros")
                or entry.inputs.disciplinary_zeros
                != tuple(sorted(original_resolved_zeros, key=lambda z: z.zero_id))
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
            if (
                original.audit is not None
                or original.authority_fingerprint is not None
                or original.context.discipline == "resolved_zeros"
            ):
                raise RankingForkRemapUnsupportedError(
                    "Ranking weekly fork does not yet support audited or transition-authority commands"
                )
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
                target_tournament = remapped_tournament_by_edition.get(binding.edition_id)
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
            if (
                entry.inputs.zeros_from_history
                != (original.context.discipline == "stored_zeros")
                or entry.inputs.disciplinary_zeros
                != tuple(sorted(original_resolved_zeros, key=lambda z: z.zero_id))
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

    source_zero_fingerprints = {
        version.fingerprint for version in source.zero_sources
    }
    if referenced_zero_fingerprints != source_zero_fingerprints:
        raise RankingForkRemapUnsupportedError(
            "Saved zero history is not completely owned by stored ranking commands"
        )
    if referenced_tournament_editions != tournament_editions:
        raise RankingForkRemapUnsupportedError(
            "Saved tournament sources are not completely owned by stored ranking commands"
        )

    return RankingRevisionState(
        schema_version="ranking_revision_state.v4",
        run_id=run_id,
        branch_id=target_branch_id,
        entries=tuple(remapped_entries),
        sources=remapped_result_sources,
        zero_sources=remapped_zero_sources,
        tournament_sources=remapped_tournament_sources,
    )


# Backward-compatible internal alias for callers/tests from the bootstrap-only slice.
remap_bootstrap_ranking_state_for_branch = remap_source_free_ranking_state_for_branch

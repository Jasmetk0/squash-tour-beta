"""Safe branch-identity remapping for the first ranking-bearing fork slice.

This module intentionally supports only the narrow bootstrap-only ranking state that can
be reconstructed from its complete stored command payload without inventing policy.

Later ranking history with tournament sources, zeros, Week/Season Transition state or
archive authorities remains fail-closed until dedicated remap adapters exist.
"""

from __future__ import annotations

import json

from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.domain.rankings.input_manifest import RankingInputManifest
from beta_engine.domain.rankings.official import calculate_official_ranking
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
        source.sources
        or source.tournament_sources
        or source.transition_authorities
        or source.tournament_ranking_snapshot_authorities
        or source.season_closing_rankings
        or source.authoritative_transition_state is not None
    ):
        raise RankingForkRemapUnsupportedError(
            "Ranking-bearing fork does not yet support result or transition authorities"
        )

    remapped_zero_sources, zero_by_source_fingerprint = _remap_zero_sources(
        source.zero_sources,
        run_id=run_id,
        source_branch_id=source_branch_id,
        target_branch_id=target_branch_id,
    )
    referenced_zero_fingerprints: set[str] = set()

    remapped_entries: list[RankingRevisionEntry] = []
    previous = None
    for index, entry in enumerate(source.entries):
        if entry.inputs.results or len(entry.receipts) != 1:
            raise RankingForkRemapUnsupportedError(
                "Ranking-bearing fork currently requires result-free command history"
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
            command = original.model_copy(
                update={
                    "branch_id": target_branch_id,
                    "zero_versions": command_zero_versions,
                }
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
            snapshot = calculate_official_ranking(
                run_id=run_id,
                branch_id=target_branch_id,
                week=command.target_week,
                policy=command.policy,
                players=command.players,
                results=(),
                previous=None,
                disciplinary_zeros=resolved_zeros,
            )
            inputs = RankingInputManifest(
                players=command.players,
                results=(),
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
                original.tournaments
                or original.corrections
                or original.audit is not None
                or original.authority_fingerprint is not None
                or original.context.discipline == "resolved_zeros"
            ):
                raise RankingForkRemapUnsupportedError(
                    "Ranking weekly fork supports result-free none/stored_zeros commands"
                )
            if previous is None or original.context.completed_week != previous.week:
                raise RankingForkRemapUnsupportedError(
                    "Ranking weekly command lineage is not consecutive"
                )

            command_zero_versions = _remap_command_zero_versions(
                original.zero_versions,
                mapped_by_source_fingerprint=zero_by_source_fingerprint,
            )
            referenced_zero_fingerprints.update(
                version.fingerprint for version in original.zero_versions
            )
            command = original.model_copy(
                update={
                    "context": original.context.model_copy(
                        update={"branch_id": target_branch_id}
                    ),
                    "zero_versions": command_zero_versions,
                }
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
            snapshot = calculate_official_ranking(
                run_id=run_id,
                branch_id=target_branch_id,
                week=command.context.target_week,
                policy=command.context.policy,
                players=command.context.players,
                results=(),
                previous=previous,
                disciplinary_zeros=resolved_zeros,
            )
            inputs = RankingInputManifest(
                players=command.context.players,
                results=(),
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

    return RankingRevisionState(
        schema_version="ranking_revision_state.v4",
        run_id=run_id,
        branch_id=target_branch_id,
        entries=tuple(remapped_entries),
        sources=(),
        zero_sources=remapped_zero_sources,
    )


# Backward-compatible internal alias for callers/tests from the bootstrap-only slice.
remap_bootstrap_ranking_state_for_branch = remap_source_free_ranking_state_for_branch

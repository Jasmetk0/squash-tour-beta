"""Branch-identity remapping for recoverable ranking-bearing forks.

The adapter reconstructs complete ranking evidence from stored canonical commands.
It currently supports result-free histories, including versioned disciplinary-zero
history. Tournament/correction results, transition/publication authorities,
InitialWorld-bound ranking and archive authorities remain fail-closed.
"""

from __future__ import annotations

import json

from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.domain.rankings.input_manifest import RankingInputManifest
from beta_engine.domain.rankings.official import calculate_official_ranking
from beta_engine.domain.rankings.revision_state import (
    RankingRevisionEntry,
    RankingRevisionReceipt,
    RankingRevisionState,
)
from beta_engine.domain.rankings.zero_history import (
    RankingZeroVersion,
    resolve_zero_versions,
)


class RankingForkRemapUnsupportedError(ValueError):
    """Raised when a ranking bundle is outside the supported fork-remap slice."""


def _remap_zero_source_history(
    versions: tuple[RankingZeroVersion, ...],
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
) -> tuple[
    tuple[RankingZeroVersion, ...],
    dict[str, RankingZeroVersion],
]:
    latest: dict[str, RankingZeroVersion] = {}
    by_source_fingerprint: dict[str, RankingZeroVersion] = {}
    remapped: list[RankingZeroVersion] = []
    for source_version in versions:
        zero = source_version.zero
        if (zero.run_id, zero.branch_id) != (run_id, source_branch_id):
            raise RankingForkRemapUnsupportedError(
                "Ranking zero source scope is inconsistent"
            )
        previous = latest.get(zero.zero_id)
        if previous is None:
            if source_version.previous_fingerprint is not None:
                raise RankingForkRemapUnsupportedError(
                    "Ranking zero source lineage is incomplete"
                )
            previous_fingerprint = None
        else:
            previous_fingerprint = previous.fingerprint
        remapped_version = RankingZeroVersion(
            effective_week=source_version.effective_week,
            previous_fingerprint=previous_fingerprint,
            zero=zero.model_copy(update={"branch_id": target_branch_id}),
        )
        latest[zero.zero_id] = remapped_version
        by_source_fingerprint[source_version.fingerprint] = remapped_version
        remapped.append(remapped_version)
    return tuple(remapped), by_source_fingerprint


def _remap_command_zero_batch(
    raw_versions: object,
    *,
    by_source_fingerprint: dict[str, RankingZeroVersion],
) -> list[dict[str, object]]:
    if raw_versions is None:
        return []
    if not isinstance(raw_versions, list):
        raise RankingForkRemapUnsupportedError(
            "Ranking zero command batch must be a list"
        )
    remapped: list[RankingZeroVersion] = []
    for raw in raw_versions:
        try:
            source = RankingZeroVersion.model_validate(raw)
        except ValueError as exc:
            raise RankingForkRemapUnsupportedError(
                "Ranking zero command batch is invalid"
            ) from exc
        target = by_source_fingerprint.get(source.fingerprint)
        if target is None:
            raise RankingForkRemapUnsupportedError(
                "Ranking zero command batch is missing from saved zero history"
            )
        remapped.append(target)
    return [item.model_dump(mode="json") for item in remapped]


def _remap_resolved_zeros(
    zeros,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
):
    remapped = []
    for zero in zeros:
        if (zero.run_id, zero.branch_id) != (run_id, source_branch_id):
            raise RankingForkRemapUnsupportedError(
                "Resolved ranking zero scope is inconsistent"
            )
        remapped.append(zero.model_copy(update={"branch_id": target_branch_id}))
    return tuple(remapped)


def remap_result_free_ranking_state_for_branch(
    source: RankingRevisionState,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
) -> RankingRevisionState:
    """Rebuild one complete result-free ranking lineage for a fork target.

    Every historical command is revalidated from its stored canonical request.
    Branch identity and zero-version fingerprint lineage are rebuilt. Tournament
    result/correction and authority evidence is never inferred or copied.
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

    remapped_zero_sources, zero_fingerprint_map = _remap_zero_source_history(
        source.zero_sources,
        run_id=run_id,
        source_branch_id=source_branch_id,
        target_branch_id=target_branch_id,
    )

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
            if payload.get("kind") != "initial_ranking.v1":
                raise RankingForkRemapUnsupportedError(
                    "Ranking fork root must be initial_ranking.v1"
                )
            if (
                payload.get("run_id") != run_id
                or payload.get("branch_id") != source_branch_id
                or payload.get("command_id") != receipt.command_id
            ):
                raise RankingForkRemapUnsupportedError(
                    "Ranking bootstrap command payload scope is inconsistent"
                )
            remapped_payload = dict(payload)
            remapped_payload["branch_id"] = target_branch_id
            if "disciplinary_zeros" in remapped_payload:
                remapped_payload["disciplinary_zeros"] = [
                    {**zero, "branch_id": target_branch_id}
                    for zero in remapped_payload["disciplinary_zeros"]
                ]
            if "zero_versions" in remapped_payload:
                remapped_payload["zero_versions"] = _remap_command_zero_batch(
                    remapped_payload["zero_versions"],
                    by_source_fingerprint=zero_fingerprint_map,
                )
            command = RankingBootstrapCommand.model_validate_json(
                json.dumps(remapped_payload, sort_keys=True, separators=(",", ":"))
            )
            if (
                command.target_week != entry.snapshot.week
                or command.policy != entry.snapshot.policy
                or command.players != entry.inputs.players
            ):
                raise RankingForkRemapUnsupportedError(
                    "Ranking bootstrap command does not exactly match the frozen ranking inputs"
                )
            if command.initial_world_fingerprint is not None:
                raise RankingForkRemapUnsupportedError(
                    "Ranking bootstrap tied to InitialWorld requires player-snapshot remapping first"
                )

            if command.discipline == "stored_zeros":
                disciplinary_zeros = resolve_zero_versions(
                    remapped_zero_sources,
                    command.target_week,
                )
            else:
                disciplinary_zeros = command.disciplinary_zeros
            expected_manifest_zeros = _remap_resolved_zeros(
                entry.inputs.disciplinary_zeros,
                run_id=run_id,
                source_branch_id=source_branch_id,
                target_branch_id=target_branch_id,
            )
            if disciplinary_zeros != expected_manifest_zeros:
                raise RankingForkRemapUnsupportedError(
                    "Ranking bootstrap zero history does not match the frozen manifest"
                )

            snapshot = calculate_official_ranking(
                run_id=run_id,
                branch_id=target_branch_id,
                week=command.target_week,
                policy=command.policy,
                players=command.players,
                results=(),
                previous=None,
                disciplinary_zeros=disciplinary_zeros,
            )
            inputs = RankingInputManifest(
                players=command.players,
                results=(),
                disciplinary_zeros=disciplinary_zeros,
                zeros_from_history=entry.inputs.zeros_from_history,
                command_request_fingerprint=command.fingerprint,
            )
        else:
            if payload.get("command_id") != receipt.command_id:
                raise RankingForkRemapUnsupportedError(
                    "Ranking weekly command payload identity is inconsistent"
                )
            context = payload.get("context")
            if (
                not isinstance(context, dict)
                or context.get("run_id") != run_id
                or context.get("branch_id") != source_branch_id
            ):
                raise RankingForkRemapUnsupportedError(
                    "Ranking weekly command payload scope is inconsistent"
                )
            remapped_payload = dict(payload)
            remapped_context = dict(context)
            remapped_context["branch_id"] = target_branch_id
            if "disciplinary_zeros" in remapped_context:
                remapped_context["disciplinary_zeros"] = [
                    {**zero, "branch_id": target_branch_id}
                    for zero in remapped_context["disciplinary_zeros"]
                ]
            remapped_payload["context"] = remapped_context
            if "zero_versions" in remapped_payload:
                remapped_payload["zero_versions"] = _remap_command_zero_batch(
                    remapped_payload["zero_versions"],
                    by_source_fingerprint=zero_fingerprint_map,
                )
            command = RankingWeekCommand.model_validate_json(
                json.dumps(remapped_payload, sort_keys=True, separators=(",", ":"))
            )
            if (
                command.tournaments
                or command.corrections
                or command.audit is not None
                or command.authority_fingerprint is not None
            ):
                raise RankingForkRemapUnsupportedError(
                    "Ranking weekly fork does not yet support tournament/correction or authority inputs"
                )
            if (
                previous is None
                or command.context.completed_week != previous.week
                or command.context.target_week != entry.snapshot.week
                or command.context.policy != entry.snapshot.policy
                or command.context.players != entry.inputs.players
            ):
                raise RankingForkRemapUnsupportedError(
                    "Ranking weekly command does not exactly match the frozen ranking inputs"
                )

            if command.context.discipline == "stored_zeros":
                disciplinary_zeros = resolve_zero_versions(
                    remapped_zero_sources,
                    command.context.target_week,
                )
            else:
                disciplinary_zeros = command.context.disciplinary_zeros
            expected_manifest_zeros = _remap_resolved_zeros(
                entry.inputs.disciplinary_zeros,
                run_id=run_id,
                source_branch_id=source_branch_id,
                target_branch_id=target_branch_id,
            )
            if disciplinary_zeros != expected_manifest_zeros:
                raise RankingForkRemapUnsupportedError(
                    "Ranking weekly zero history does not match the frozen manifest"
                )

            snapshot = calculate_official_ranking(
                run_id=run_id,
                branch_id=target_branch_id,
                week=command.context.target_week,
                policy=command.context.policy,
                players=command.context.players,
                results=(),
                previous=previous,
                disciplinary_zeros=disciplinary_zeros,
            )
            inputs = RankingInputManifest(
                players=command.context.players,
                results=(),
                disciplinary_zeros=disciplinary_zeros,
                zeros_from_history=entry.inputs.zeros_from_history,
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

    return RankingRevisionState(
        schema_version="ranking_revision_state.v4",
        run_id=run_id,
        branch_id=target_branch_id,
        entries=tuple(remapped_entries),
        sources=(),
        zero_sources=remapped_zero_sources,
    )


# Backward-compatible internal alias for callers/tests from the bootstrap-only slice.
remap_source_free_ranking_state_for_branch = remap_result_free_ranking_state_for_branch
remap_bootstrap_ranking_state_for_branch = remap_result_free_ranking_state_for_branch

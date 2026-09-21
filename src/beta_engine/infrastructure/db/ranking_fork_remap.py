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
from beta_engine.domain.rankings.revision_state import (
    RankingRevisionEntry,
    RankingRevisionReceipt,
    RankingRevisionState,
)


class RankingForkRemapUnsupportedError(ValueError):
    """Raised when a ranking bundle is outside the supported fork-remap slice."""


def remap_source_free_ranking_state_for_branch(
    source: RankingRevisionState,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
) -> RankingRevisionState:
    """Rebuild one complete source-free ranking lineage for a fork target.

    Every historical command is revalidated from its stored canonical request.
    Only Branch identity is changed; no tournament, correction, zero, authority,
    InitialWorld or publication evidence is inferred or copied.
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
        or source.zero_sources
        or source.tournament_sources
        or source.transition_authorities
        or source.tournament_ranking_snapshot_authorities
        or source.season_closing_rankings
        or source.authoritative_transition_state is not None
    ):
        raise RankingForkRemapUnsupportedError(
            "Ranking-bearing fork does not yet support historical sources or transition authorities"
        )

    remapped_entries: list[RankingRevisionEntry] = []
    previous = None
    for index, entry in enumerate(source.entries):
        if (
            entry.inputs.results
            or entry.inputs.disciplinary_zeros
            or entry.inputs.zeros_from_history
            or len(entry.receipts) != 1
        ):
            raise RankingForkRemapUnsupportedError(
                "Ranking-bearing fork currently requires source-free command history"
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
            command = RankingBootstrapCommand.model_validate_json(
                json.dumps(remapped_payload, sort_keys=True, separators=(",", ":"))
            )
            if (
                command.target_week != entry.snapshot.week
                or command.policy != entry.snapshot.policy
                or command.players != entry.inputs.players
                or command.discipline != "none"
            ):
                raise RankingForkRemapUnsupportedError(
                    "Ranking bootstrap command does not exactly match the frozen ranking inputs"
                )
            if command.initial_world_fingerprint is not None:
                raise RankingForkRemapUnsupportedError(
                    "Ranking bootstrap tied to InitialWorld requires player-snapshot remapping first"
                )
            if command.zero_versions or command.disciplinary_zeros:
                raise RankingForkRemapUnsupportedError(
                    "Ranking bootstrap with disciplinary history is not yet remappable"
                )
            snapshot = calculate_official_ranking(
                run_id=run_id,
                branch_id=target_branch_id,
                week=command.target_week,
                policy=command.policy,
                players=command.players,
                results=(),
                previous=None,
                disciplinary_zeros=(),
            )
            inputs = RankingInputManifest(
                players=command.players,
                results=(),
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
            remapped_payload["context"] = remapped_context
            command = RankingWeekCommand.model_validate_json(
                json.dumps(remapped_payload, sort_keys=True, separators=(",", ":"))
            )
            if (
                command.tournaments
                or command.corrections
                or command.zero_versions
                or command.audit is not None
                or command.authority_fingerprint is not None
                or command.context.discipline != "none"
                or command.context.disciplinary_zeros
            ):
                raise RankingForkRemapUnsupportedError(
                    "Ranking weekly fork supports only source-free, unauthoritied commands"
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
            snapshot = calculate_official_ranking(
                run_id=run_id,
                branch_id=target_branch_id,
                week=command.context.target_week,
                policy=command.context.policy,
                players=command.context.players,
                results=(),
                previous=previous,
                disciplinary_zeros=(),
            )
            inputs = RankingInputManifest(
                players=command.context.players,
                results=(),
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
    )


# Backward-compatible internal alias for callers/tests from the bootstrap-only slice.
remap_bootstrap_ranking_state_for_branch = remap_source_free_ranking_state_for_branch

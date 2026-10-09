"""Pure, fail-closed audit remapping for supported Week Transition forks.

The caller must supply independently verified Branch-owned ranking, tournament,
player and Saved Revision identities. Installation is performed separately, inside
one SQLite transaction, and must recapture the full target ranking state.
"""

from __future__ import annotations

from collections.abc import Mapping

from beta_engine.application.ranking_tournament_ingestion import TournamentRankingBinding
from beta_engine.application.authoritative_week_transition import (
    AuthoritativeWeekTransitionCommand,
    AuthoritativeWeekTransitionResult,
)
from beta_engine.infrastructure.db.authoritative_week_transition import (
    _world_event_payload,
)


class WeekTransitionForkAuditUnsupportedError(ValueError):
    """The frozen source evidence cannot be rebuilt under target ownership."""


def _mapped(mapping: Mapping[str, str], source: str, label: str) -> str:
    value = mapping.get(source)
    if not isinstance(value, str) or not value.strip():
        raise WeekTransitionForkAuditUnsupportedError(
            f"Missing target {label} for source {source!r}"
        )
    return value


def remap_event_free_week_transition_audit(
    state: dict,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    base_revision_ids: Mapping[str, str],
    ranking_authorities: Mapping[str, str],
    ranking_snapshots: Mapping[str, str],
    lifecycle_states: Mapping[str, str],
    sporting_states: Mapping[str, str],
    health_states: Mapping[str, str],
    tournament_bindings: Mapping[str, TournamentRankingBinding] | None = None,
) -> dict[str, list[dict]]:
    """Reconstruct receipts and World Events from fully verified source commands.

    Every changed identifier/fingerprint must have an explicitly supplied
    validated target counterpart. No source receipt bytes or embedded references
    are copied blindly, and every source Event must match its original command
    and result exactly. At most one completed standard tournament is supported
    across the entire transition history. The caller must prove both owned
    tournament sources and provide the exact target-local binding.
    """
    if (
        not run_id or not source_branch_id or not target_branch_id
        or source_branch_id == target_branch_id
        or not isinstance(state, dict)
        or set(state) != {"receipts", "events"}
        or not isinstance(state["receipts"], list)
        or not isinstance(state["events"], list)
    ):
        raise WeekTransitionForkAuditUnsupportedError(
            "Invalid Week Transition fork audit scope"
        )

    event_by_id: dict[str, dict] = {}
    for event in state["events"]:
        if not isinstance(event, dict) or not isinstance(event.get("command_id"), str):
            raise WeekTransitionForkAuditUnsupportedError("Invalid source World Event")
        if event["command_id"] in event_by_id:
            raise WeekTransitionForkAuditUnsupportedError("Duplicate source World Event")
        event_by_id[event["command_id"]] = event

    receipts = []
    events = []
    seen: set[str] = set()
    ordinals: set[int] = set()
    bindings = tournament_bindings if tournament_bindings is not None else {}
    if not isinstance(bindings, Mapping) or len(bindings) > 1:
        raise WeekTransitionForkAuditUnsupportedError(
            "Only one verified tournament binding is supported"
        )
    used_tournaments: set[str] = set()
    for row in state["receipts"]:
        try:
            if not isinstance(row, dict):
                raise ValueError("receipt must be an object")
            original = AuthoritativeWeekTransitionCommand.model_validate_json(
                row["request_payload_json"]
            )
            result = AuthoritativeWeekTransitionResult.model_validate_json(
                row["result_json"]
            )
            if (
                (row["run_id"], row["branch_id"], row["command_id"])
                != (run_id, source_branch_id, original.command_id)
                or (original.run_id, original.branch_id)
                != (run_id, source_branch_id)
                or row["request_payload_json"] != original.canonical_request_json
                or row["request_fingerprint"] != original.fingerprint
                or (
                    result.run_id, result.branch_id, result.command_id,
                    result.completed_week, result.target_week,
                ) != (
                    run_id, source_branch_id, original.command_id,
                    original.completed_week, original.target_week,
                )
                or result.world_event_kind != "week_transition_completed"
            ):
                raise ValueError("source Week Transition receipt identity mismatch")
            if original.corrections or original.zero_versions:
                raise ValueError("corrections and disciplinary zeros are not supported")
            target_tournaments = ()
            if original.tournaments:
                if len(original.tournaments) != 1:
                    raise ValueError("multiple tournaments in one Week Transition are unsupported")
                source_binding = original.tournaments[0]
                edition_id = source_binding.edition_id
                target_binding = bindings.get(edition_id)
                if (
                    edition_id in used_tournaments
                    or not isinstance(target_binding, TournamentRankingBinding)
                    or source_binding.run_id != run_id
                    or source_binding.branch_id != source_branch_id
                    or target_binding.run_id != run_id
                    or target_binding.branch_id != target_branch_id
                    or source_binding.completed_week != original.completed_week
                    or target_binding.completed_week != original.completed_week
                    or source_binding.closing_only
                    or target_binding.closing_only
                    or (
                        source_binding.edition_id, source_binding.event_id,
                        source_binding.validity_weeks, source_binding.ranking_status,
                        source_binding.first_publication_week,
                    ) != (
                        target_binding.edition_id, target_binding.event_id,
                        target_binding.validity_weeks, target_binding.ranking_status,
                        target_binding.first_publication_week,
                    )
                    or target_binding.first_publication_week != original.target_week
                ):
                    raise ValueError("tournament binding has no matching target ownership")
                used_tournaments.add(edition_id)
                target_tournaments = (target_binding,)
            if original.command_id in seen:
                raise ValueError("duplicate transition command")
            seen.add(original.command_id)
            if original.target_week.ordinal in ordinals:
                raise ValueError("duplicate target week")
            ordinals.add(original.target_week.ordinal)

            event = event_by_id.get(original.command_id)
            if event is None or (
                event.get("run_id"), event.get("branch_id"),
                event.get("command_id"), event.get("week_ordinal"),
                event.get("event_kind"),
            ) != (
                run_id, source_branch_id, original.command_id,
                original.target_week.ordinal, "week_transition_completed",
            ) or event.get("payload_json") != _world_event_payload(
                original,
                result.official_ranking_fingerprint,
                result.player_lifecycle_fingerprint,
                result.player_sporting_fingerprint,
                result.player_health_fingerprint,
            ):
                raise ValueError("source World Event differs from receipt")

            target_command = AuthoritativeWeekTransitionCommand.model_validate_json(
                original.model_copy(
                    update={
                        "branch_id": target_branch_id,
                        "base_revision_id": _mapped(
                            base_revision_ids, original.base_revision_id,
                            "Saved Revision",
                        ),
                        "authority_fingerprint": _mapped(
                            ranking_authorities, original.authority_fingerprint,
                            "ranking authority",
                        ),
                        "tournaments": target_tournaments,
                    }
                ).model_dump_json()
            )
            health_fingerprint = (
                _mapped(
                    health_states, result.player_health_fingerprint,
                    "player health",
                )
                if result.player_health_fingerprint is not None
                else None
            )
            target_result = AuthoritativeWeekTransitionResult(
                run_id=run_id,
                branch_id=target_branch_id,
                command_id=original.command_id,
                completed_week=original.completed_week,
                target_week=original.target_week,
                official_ranking_fingerprint=_mapped(
                    ranking_snapshots, result.official_ranking_fingerprint,
                    "Official Ranking",
                ),
                player_lifecycle_fingerprint=_mapped(
                    lifecycle_states, result.player_lifecycle_fingerprint,
                    "player lifecycle",
                ),
                player_sporting_fingerprint=_mapped(
                    sporting_states, result.player_sporting_fingerprint,
                    "player sporting",
                ),
                player_health_fingerprint=health_fingerprint,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise WeekTransitionForkAuditUnsupportedError(
                f"Cannot remap source Week Transition audit: {exc}"
            ) from exc

        receipts.append({
            "run_id": run_id,
            "branch_id": target_branch_id,
            "command_id": original.command_id,
            "request_fingerprint": target_command.fingerprint,
            "request_payload_json": target_command.canonical_request_json,
            "result_json": target_result.model_dump_json(),
        })
        events.append({
            "run_id": run_id,
            "branch_id": target_branch_id,
            "command_id": original.command_id,
            "week_ordinal": original.target_week.ordinal,
            "event_kind": "week_transition_completed",
            "payload_json": _world_event_payload(
                target_command,
                target_result.official_ranking_fingerprint,
                target_result.player_lifecycle_fingerprint,
                target_result.player_sporting_fingerprint,
                target_result.player_health_fingerprint,
            ),
        })

    if set(bindings) != used_tournaments:
        raise WeekTransitionForkAuditUnsupportedError(
            "Tournament source/Week Transition coverage is incomplete"
        )
    if set(event_by_id) != seen:
        raise WeekTransitionForkAuditUnsupportedError(
            "Source World Event/receipt identities do not match"
        )
    if ordinals and sorted(ordinals) != list(
        range(min(ordinals), max(ordinals) + 1)
    ):
        raise WeekTransitionForkAuditUnsupportedError(
            "Source Week Transition audit has a chronological gap"
        )
    return {
        "receipts": sorted(receipts, key=lambda row: row["command_id"]),
        "events": sorted(events, key=lambda row: row["command_id"]),
    }

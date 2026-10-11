"""Verified cross-Branch remapping for an ordinary Season Transition World Event.

The original configuration fingerprint remains immutable *historical* source
provenance: the Season Transition writer did not persist its complete original
configuration command, so a new target-Branch configuration must not be invented.
Every branch-owned output fingerprint is rebound from separately verified
target-owned ranking, closure, lifecycle, sporting and health evidence.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from beta_engine.domain.rankings.official import RankingWeek


class SeasonTransitionForkEventError(ValueError):
    """The source season boundary cannot be verified in the target Branch."""


def _require_map(mapping: Mapping[str, str], key: str, label: str) -> str:
    result = mapping.get(key)
    if (
        not isinstance(result, str)
        or len(result) != 64
        or any(c not in "0123456789abcdef" for c in result)
    ):
        raise SeasonTransitionForkEventError(
            f"Missing verified target Season Transition {label} fingerprint"
        )
    return result


def rebind_verified_season_transition_event(
    source_event: dict,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    source_revision_id: str,
    target_revision_id: str,
    source_closure,
    target_closure,
    source_ranking,
    target_ranking,
    lifecycle_fingerprint_map: Mapping[str, str],
    sporting_fingerprint_map: Mapping[str, str],
    health_fingerprint_map: Mapping[str, str],
) -> dict:
    """Recreate one saved Season Transition World Event with verified lineage.

    Closure components must already have been authenticated against their exact
    source and target Saved Revision IDs by the caller, in the same transaction.
    The ranking states are immutable source/target remap output; the remaining
    player fingerprint maps must originate from independently verified player
    state. An unverified arbitrary map must not be accepted by the outer writer.
    """
    if (
        not isinstance(source_event, dict)
        or (source_event.get("run_id"), source_event.get("branch_id"))
        != (run_id, source_branch_id)
        or source_branch_id == target_branch_id
        or not source_revision_id
        or not target_revision_id
        or source_revision_id == target_revision_id
        or (source_ranking.run_id, source_ranking.branch_id)
        != (run_id, source_branch_id)
        or (target_ranking.run_id, target_ranking.branch_id)
        != (run_id, target_branch_id)
    ):
        raise SeasonTransitionForkEventError("Invalid source/target Season Transition scope")

    try:
        event = json.loads(source_event["payload_json"])
        original_summary = source_closure.parsed_summary
        original_marker = source_closure.parsed_marker
        mapped_summary = target_closure.parsed_summary
        mapped_marker = target_closure.parsed_marker
        completed = RankingWeek.model_validate(event["completed_week"])
        target_week = RankingWeek.model_validate(event["target_week"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SeasonTransitionForkEventError(
            "Season Transition saved event or closure is invalid"
        ) from exc
    if (
        not isinstance(event, dict)
        or event.get("schema_version") != "season_transition_world_event.v1"
        or source_event.get("event_kind") != "season_transition_completed"
        or source_event.get("command_id") != event.get("command_id")
        or source_event.get("week_ordinal") != target_week.ordinal
        or completed.week != 61
        or completed.season_index >= 49
        or target_week != RankingWeek(
            season_index=completed.season_index + 1, week=1
        )
        or event.get("saved_revision_id") != source_revision_id
        or original_marker.final_saved_revision_id != source_revision_id
        or mapped_marker.final_saved_revision_id != target_revision_id
        or original_summary.completed_week != completed
        or mapped_summary.completed_week != completed
        or original_summary.closing_ranking_fingerprint
        != event.get("closing_ranking_fingerprint")
        or original_summary.fingerprint != event.get("season_summary_fingerprint")
        or original_marker.fingerprint != event.get("closure_marker_fingerprint")
        or mapped_summary.closing_ranking_fingerprint
        == original_summary.closing_ranking_fingerprint
        or original_marker.rule_versions != mapped_marker.rule_versions
    ):
        raise SeasonTransitionForkEventError(
            "Season Transition event differs from committed Season Closure"
        )
    original_ranks = {
        entry.snapshot.week.ordinal: entry.snapshot
        for entry in source_ranking.entries
    }
    rebound_ranks = {
        entry.snapshot.week.ordinal: entry.snapshot
        for entry in target_ranking.entries
    }
    old = original_ranks.get(target_week.ordinal)
    new = rebound_ranks.get(target_week.ordinal)
    if (
        old is None or new is None
        or len(original_ranks) != len(source_ranking.entries)
        or len(rebound_ranks) != len(target_ranking.entries)
        or old.fingerprint != event.get("official_ranking_fingerprint")
        or old.week != new.week
        or tuple((r.rank, r.player_id, r.points) for r in old.rows)
        != tuple((r.rank, r.player_id, r.points) for r in new.rows)
        or not isinstance(event.get("configuration_fingerprint"), str)
        or len(event["configuration_fingerprint"]) != 64
        or any(c not in "0123456789abcdef" for c in event["configuration_fingerprint"])
    ):
        raise SeasonTransitionForkEventError(
            "Season Transition published ranking or configuration provenance differs"
        )

    rebound = dict(event)
    rebound.update({
        "saved_revision_id": target_revision_id,
        "closing_ranking_fingerprint": mapped_summary.closing_ranking_fingerprint,
        "season_summary_fingerprint": mapped_summary.fingerprint,
        "closure_marker_fingerprint": mapped_marker.fingerprint,
        "official_ranking_fingerprint": new.fingerprint,
        "player_lifecycle_fingerprint": _require_map(
            lifecycle_fingerprint_map, event.get("player_lifecycle_fingerprint", ""),
            "lifecycle",
        ),
        "player_sporting_fingerprint": _require_map(
            sporting_fingerprint_map, event.get("player_sporting_fingerprint", ""),
            "sporting",
        ),
    })
    if "player_health_fingerprint" in event:
        rebound["player_health_fingerprint"] = _require_map(
            health_fingerprint_map,
            event["player_health_fingerprint"],
            "health",
        )
    # Preserve the original configuration fingerprint as historical provenance.
    # The target Branch's *new* configuration may diverge after the fork.
    return {
        "run_id": run_id,
        "branch_id": target_branch_id,
        "command_id": source_event["command_id"],
        "week_ordinal": target_week.ordinal,
        "event_kind": "season_transition_completed",
        "payload_json": json.dumps(
            rebound, sort_keys=True, separators=(",", ":")
        ),
    }

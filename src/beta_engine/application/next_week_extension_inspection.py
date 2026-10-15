"""Read-only proof of append-only changes to a previously reviewed Next Week.

This is an inspection contract only: it cannot extend or execute a frozen command.
"""

from __future__ import annotations

from collections.abc import Collection

from beta_engine.domain.simulation_slots import WeekSimulationSchedule


def inspect_frozen_next_week_extension(
    frozen: dict,
    current: WeekSimulationSchedule | None,
    base: WeekSimulationSchedule | None,
    hybrid_match_keys: Collection[tuple[str, str]],
) -> dict:
    """Fail closed unless an immutable old schedule is a strict match-slot prefix.

    A positive finding is diagnostic evidence, NOT permission to rewrite the
    original child review. It is checked without modifying parent or sport rows.
    """
    if frozen.get("schema_version") != "authoritative_week_operation.v1":
        raise ValueError("Invalid frozen Next Week operation schema")
    old_fingerprint = frozen.get("schedule_fingerprint")
    if not isinstance(old_fingerprint, str) or len(old_fingerprint) != 64 or any(
        c not in "0123456789abcdef" for c in old_fingerprint
    ):
        raise ValueError("Frozen Next Week schedule fingerprint is invalid")
    original_ordinals = frozen.get("target_slot_ordinals")
    original_groups = frozen.get("target_group_ids")
    child_commands = frozen.get("child_commands")
    if (
        not isinstance(original_ordinals, list)
        or not original_ordinals
        or any(type(n) is not int or n < 1 for n in original_ordinals)
        or original_ordinals != sorted(set(original_ordinals))
        or not isinstance(original_groups, list)
        or any(not isinstance(g, str) or not g for g in original_groups)
        or not isinstance(child_commands, dict)
        or set(child_commands) != {str(n) for n in original_ordinals}
    ):
        raise ValueError("Frozen Next Week sporting range is corrupt")
    if any(
        value is not None and (
            not isinstance(value, dict) or not isinstance(value.get("command_id"), str)
            or not value["command_id"]
        )
        for value in child_commands.values()
    ):
        raise ValueError("Frozen Next Week child identity is corrupt")

    def outcome(status: str, reason: str, slots: list[dict] | None = None) -> dict:
        return {
            "status": status,
            "reason": reason,
            "old_schedule_fingerprint": old_fingerprint,
            "current_schedule_fingerprint": current.fingerprint if current else None,
            "original_slot_count": len(original_ordinals),
            "new_slots": slots or [],
            "read_only": True,
            "automatic_rebase": False,
        }

    if frozen.get("week_transition") is not None:
        return outcome("blocked", "week_transition_already_frozen")
    if current is None or base is None:
        return outcome("blocked", "authoritative_schedule_missing")
    if current.schema_version != "week_simulation_schedule.v2" or base.schema_version != "week_simulation_schedule.v2":
        return outcome("blocked", "schedule_version_unsupported")
    if (
        current.run_id != frozen.get("run_id")
        or current.branch_id != frozen.get("branch_id")
        or current.week.model_dump(mode="json") != frozen.get("week")
        or base.run_id != current.run_id
        or base.branch_id != current.branch_id
        or base.week != current.week
    ):
        return outcome("blocked", "scope_or_week_changed")
    if current.fingerprint == old_fingerprint:
        return outcome("unchanged", "schedule_still_matches_original_review")

    old_max = original_ordinals[-1]
    original_slots = tuple(s for s in current.slots if s.ordinal <= old_max)
    new_slots = tuple(s for s in current.slots if s.ordinal > old_max)
    if not original_slots or not new_slots:
        return outcome("blocked", "not_a_strict_append_only_extension")
    if any(s.ordinal <= max(s.ordinal for s in base.slots) for s in new_slots):
        return outcome("blocked", "base_week_schedule_changed")
    try:
        original_schedule = WeekSimulationSchedule(
            schema_version=current.schema_version,
            run_id=current.run_id,
            branch_id=current.branch_id,
            week=current.week,
            slots=original_slots,
        )
    except ValueError:
        return outcome("blocked", "frozen_schedule_prefix_invalid")
    if original_schedule.fingerprint != old_fingerprint:
        return outcome("blocked", "frozen_schedule_prefix_changed")
    remaining = tuple(s for s in original_slots if s.ordinal >= original_ordinals[0])
    if (
        [s.ordinal for s in remaining] != original_ordinals
        or [g for s in remaining for g in s.group_ids] != original_groups
    ):
        return outcome("blocked", "frozen_child_range_changed")
    if any(
        s.draw_phase != "main"
        or len(s.group_ids) != 1
        or s.event_id is None
        or (s.event_id, s.group_ids[0]) not in hybrid_match_keys
        for s in new_slots
    ):
        return outcome("blocked", "new_slots_not_from_frozen_hybrid_bracket")
    if (
        new_slots[0].ordinal != old_max + 1
        or [s.ordinal for s in new_slots] != list(
            range(new_slots[0].ordinal, new_slots[-1].ordinal + 1)
        )
    ):
        return outcome("blocked", "new_slots_cross_reserved_global_ordinals")
    return outcome("append_only_proven", "operator_re_review_still_required", [
        {
            "ordinal": slot.ordinal,
            "group_id": slot.group_ids[0],
            "event_id": slot.event_id,
            "round_number": slot.round_number,
        }
        for slot in new_slots
    ])

"""Unit DTO contracts, not evidence of accepted sporting execution."""

import pytest
from pydantic import ValidationError

from beta_engine.application.native_full_simulation import (
    NativeFullSimulationCommand,
    child_id,
    child_seed,
    parse_full_simulation_command,
    validate_native_child,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar

pytestmark = pytest.mark.pr_critical


def command(clock):
    return {"schema_version": "authoritative_full_simulation_command.v2", "command_id": "native",
        "run_id": "run", "branch_id": "branch", "operator_label": "Admin", "audit_reason": "Unit DTO boundary",
        "seed": 231, "execution_calendar": clock.to_metadata(), "expected_start_week": {"season_index": 0, "week": 1},
        "target_week": {"season_index": clock.season_count - 1, "week": clock.weeks_per_year},
        "expected_revision_id": "saved", "expected_position_fingerprint": "a" * 64,
        "expected_preview_fingerprint": "b" * 64}


@pytest.mark.parametrize("clock", [RunCalendar(52, 35, 2030, 2), RunCalendar(61, 37, 2000, 50), RunCalendar(80, 80, 2100, 120)])
def test_native_command_uses_its_own_week_and_horizon_without_clamping(clock):
    raw = command(clock)
    parsed = parse_full_simulation_command(raw)
    assert isinstance(parsed, NativeFullSimulationCommand)
    assert parsed.model_dump(mode="json") == raw
    assert parsed.target_week.ordinal(clock) == clock.weeks_per_year * clock.season_count - 1
    for bad in ({"season_index": clock.season_count, "week": 1}, {"season_index": 0, "week": clock.weeks_per_year + 1}, {"season_index": 0, "week": True}):
        with pytest.raises((ValueError, ValidationError)):
            NativeFullSimulationCommand.model_validate({**raw, "target_week": bad})


def test_legacy_command_bytes_and_week_guard_keep_their_meaning():
    raw = {k: v for k, v in command(RunCalendar(80, 1, 2100, 120)).items()
        if k not in {"schema_version", "execution_calendar", "target_week", "seed"}}
    parsed = parse_full_simulation_command(raw)
    assert parsed.model_dump(mode="json") == raw
    with pytest.raises(ValidationError):
        parse_full_simulation_command({**raw, "expected_start_week": {"season_index": 0, "week": 80}})
    with pytest.raises(ValidationError):
        parse_full_simulation_command({**raw, "schema_version": "authoritative_full_simulation_command.v999"})


@pytest.mark.parametrize("seed", [True, -1, 2**53, 3.5])
def test_native_seed_is_exact_and_safe_for_the_http_admin_contract(seed):
    with pytest.raises(ValidationError):
        NativeFullSimulationCommand.model_validate({**command(RunCalendar(52, 35, 2030, 3)), "seed": seed})


@pytest.mark.parametrize("changed", [{"seed": 0}, {"operator_label": "Other"}, {"audit_reason": "Changed"}, {"command_id": "another"}, {"action": "approve"}, {"data": {"player_ids": ["p"]}}])
def test_native_child_cannot_replace_immutable_seed_audit_or_approve_for_the_operator(changed):
    original = NativeFullSimulationCommand.model_validate(command(RunCalendar(80, 80, 2100, 120)))
    child = {"action": "transition", "command_id": child_id(original, 0), "seed": child_seed(original, 0),
        "expected_saved_head": "saved", "expected_checkpoint_fingerprint": "c" * 64,
        "operator_label": original.operator_label, "audit_reason": original.audit_reason}
    request = {"command": child, "expected_preview_fingerprint": "d" * 64, "explicit_confirmation": True}
    validate_native_child(original, 0, request)
    with pytest.raises(ValueError):
        validate_native_child(original, 0, {**request, "command": {**child, **changed}})

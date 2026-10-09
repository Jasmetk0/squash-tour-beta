"""Deterministic, side-effect-free evidence remap for an eventual Week-4 fork."""

from copy import deepcopy
import json

import pytest

from beta_engine.application.ranking_tournament_ingestion import TournamentRankingBinding
from beta_engine.application.authoritative_week_transition import (
    AuthoritativeWeekTransitionCommand,
    AuthoritativeWeekTransitionResult,
)
from beta_engine.domain.rankings.command_audit import RankingCommandAudit
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.authoritative_week_transition import _world_event_payload
from beta_engine.infrastructure.db.week_transition_fork_audit import (
    WeekTransitionForkAuditUnsupportedError,
    remap_event_free_week_transition_audit,
)

pytestmark = pytest.mark.pr_critical


def _fingerprint(n: int) -> str:
    return f"{n:064x}"


def _case():
    state = {"receipts": [], "events": []}
    maps = {
        "base_revision_ids": {},
        "ranking_authorities": {},
        "ranking_snapshots": {},
        "lifecycle_states": {},
        "sporting_states": {},
        "health_states": {},
    }
    for week in (1, 2):
        command = AuthoritativeWeekTransitionCommand(
            command_id=f"transition-{week}",
            run_id="run",
            branch_id="source",
            base_revision_id=f"saved-{week}",
            completed_week=RankingWeek(season_index=0, week=week),
            target_week=RankingWeek(season_index=0, week=week + 1),
            authority_fingerprint=_fingerprint(100 + week),
            audit=RankingCommandAudit(
                actor_label="Admin",
                reason="Deterministic empty-week transition",
            ),
        )
        result = AuthoritativeWeekTransitionResult(
            run_id="run",
            branch_id="source",
            command_id=command.command_id,
            completed_week=command.completed_week,
            target_week=command.target_week,
            official_ranking_fingerprint=_fingerprint(200 + week),
            player_lifecycle_fingerprint=_fingerprint(300 + week),
            player_sporting_fingerprint=_fingerprint(400 + week),
            player_health_fingerprint=(
                _fingerprint(500 + week) if week == 1 else None
            ),
        )
        state["receipts"].append({
            "run_id": "run",
            "branch_id": "source",
            "command_id": command.command_id,
            "request_fingerprint": command.fingerprint,
            "request_payload_json": command.canonical_request_json,
            "result_json": result.model_dump_json(),
        })
        state["events"].append({
            "run_id": "run",
            "branch_id": "source",
            "command_id": command.command_id,
            "week_ordinal": command.target_week.ordinal,
            "event_kind": "week_transition_completed",
            "payload_json": _world_event_payload(
                command,
                result.official_ranking_fingerprint,
                result.player_lifecycle_fingerprint,
                result.player_sporting_fingerprint,
                result.player_health_fingerprint,
            ),
        })
        maps["base_revision_ids"][command.base_revision_id] = f"target-saved-{week}"
        maps["ranking_authorities"][command.authority_fingerprint] = _fingerprint(600 + week)
        maps["ranking_snapshots"][result.official_ranking_fingerprint] = _fingerprint(700 + week)
        maps["lifecycle_states"][result.player_lifecycle_fingerprint] = _fingerprint(800 + week)
        maps["sporting_states"][result.player_sporting_fingerprint] = _fingerprint(900 + week)
        if result.player_health_fingerprint:
            maps["health_states"][result.player_health_fingerprint] = _fingerprint(1000 + week)
    return state, maps


def _remap(state, maps):
    return remap_event_free_week_transition_audit(
        state,
        run_id="run",
        source_branch_id="source",
        target_branch_id="fork",
        **maps,
    )


def test_two_week_audit_rebinds_exact_verified_dependencies_without_mutation():
    state, maps = _case()
    source_copy = deepcopy(state)
    target = _remap(state, maps)

    assert target == _remap(state, maps)
    assert state == source_copy
    assert len(target["receipts"]) == len(target["events"]) == 2

    for source_row, target_row, target_event in zip(
        state["receipts"], target["receipts"], target["events"], strict=True
    ):
        source_command = AuthoritativeWeekTransitionCommand.model_validate_json(
            source_row["request_payload_json"]
        )
        source_result = AuthoritativeWeekTransitionResult.model_validate_json(
            source_row["result_json"]
        )
        command = AuthoritativeWeekTransitionCommand.model_validate_json(
            target_row["request_payload_json"]
        )
        result = AuthoritativeWeekTransitionResult.model_validate_json(
            target_row["result_json"]
        )
        assert command.branch_id == result.branch_id == "fork"
        assert command.base_revision_id == maps["base_revision_ids"][
            source_command.base_revision_id
        ]
        assert command.authority_fingerprint == maps["ranking_authorities"][
            source_command.authority_fingerprint
        ]
        assert command.fingerprint == target_row["request_fingerprint"]
        assert result.official_ranking_fingerprint == maps["ranking_snapshots"][
            source_result.official_ranking_fingerprint
        ]
        assert result.player_lifecycle_fingerprint == maps["lifecycle_states"][
            source_result.player_lifecycle_fingerprint
        ]
        assert result.player_sporting_fingerprint == maps["sporting_states"][
            source_result.player_sporting_fingerprint
        ]
        assert target_event["branch_id"] == "fork"
        assert target_event["payload_json"] == _world_event_payload(
            command, result.official_ranking_fingerprint,
            result.player_lifecycle_fingerprint,
            result.player_sporting_fingerprint,
            result.player_health_fingerprint,
        )
        assert target_event["payload_json"] != state["events"][
            int(source_command.completed_week.week) - 1
        ]["payload_json"]


@pytest.mark.parametrize(
    "corruption",
    [
        "receipt_hash", "receipt_payload", "result_scope", "event_payload",
        "event_scope", "missing_event", "extra_event", "duplicate_receipt",
        "duplicate_week", "missing_authority", "missing_revision",
        "missing_lifecycle", "missing_health", "missing_sporting",
    ],
)
def test_partial_or_tampered_transition_audit_fails_closed(corruption):
    state, maps = _case()
    if corruption == "receipt_hash":
        state["receipts"][0]["request_fingerprint"] = _fingerprint(12)
    elif corruption == "receipt_payload":
        state["receipts"][0]["request_payload_json"] += " "
    elif corruption == "result_scope":
        result = json.loads(state["receipts"][0]["result_json"])
        result["branch_id"] = "another"
        state["receipts"][0]["result_json"] = json.dumps(result)
    elif corruption == "event_payload":
        state["events"][0]["payload_json"] = "{}"
    elif corruption == "event_scope":
        state["events"][0]["branch_id"] = "other"
    elif corruption == "missing_event":
        state["events"].pop()
    elif corruption == "extra_event":
        state["events"].append({**state["events"][0], "command_id": "phantom"})
    elif corruption == "duplicate_receipt":
        state["receipts"].append(state["receipts"][0].copy())
    elif corruption == "duplicate_week":
        state["receipts"][1]["command_id"] = "other-week"
        state["events"][1]["command_id"] = "other-week"
        # The original canonical command id still remains in payload.
    elif corruption == "missing_authority":
        maps["ranking_authorities"].clear()
    elif corruption == "missing_revision":
        maps["base_revision_ids"].clear()
    elif corruption == "missing_lifecycle":
        maps["lifecycle_states"].clear()
    elif corruption == "missing_health":
        maps["health_states"].clear()
    elif corruption == "missing_sporting":
        maps["sporting_states"].clear()
    with pytest.raises(WeekTransitionForkAuditUnsupportedError):
        _remap(state, maps)


def test_mismatched_or_identical_branch_scope_cannot_be_remapped():
    state, maps = _case()
    with pytest.raises(WeekTransitionForkAuditUnsupportedError):
        remap_event_free_week_transition_audit(
            state, run_id="run",
            source_branch_id="source", target_branch_id="source", **maps,
        )
    with pytest.raises(WeekTransitionForkAuditUnsupportedError):
        remap_event_free_week_transition_audit(
            state, run_id="another-run",
            source_branch_id="source", target_branch_id="fork", **maps,
        )


def _one_tournament_case():
    state, maps = _case()
    source = TournamentRankingBinding(
        run_id="run",
        branch_id="source",
        edition_id="completed-standard",
        event_id="week-one-classic",
        completed_week=RankingWeek(season_index=0, week=1),
        first_publication_week=RankingWeek(season_index=0, week=2),
        validity_weeks=52,
        ranking_status="ranked",
        expected_result_fingerprint=_fingerprint(2001),
        expected_award_fingerprint=_fingerprint(2002),
    )
    target = source.model_copy(update={
        "branch_id": "fork",
        "expected_result_fingerprint": _fingerprint(3001),
        "expected_award_fingerprint": _fingerprint(3002),
    })
    original = AuthoritativeWeekTransitionCommand.model_validate_json(
        state["receipts"][0]["request_payload_json"]
    )
    updated = AuthoritativeWeekTransitionCommand.model_validate(
        original.model_copy(update={"tournaments": (source,)}).model_dump(mode="python")
    )
    state["receipts"][0]["request_payload_json"] = updated.canonical_request_json
    state["receipts"][0]["request_fingerprint"] = updated.fingerprint
    maps["tournament_bindings"] = {source.edition_id: target}
    return state, maps, source, target


def test_single_completed_tournament_rebinds_and_preserves_original_audit():
    state, maps, source, target_binding = _one_tournament_case()
    frozen = deepcopy(state)
    rebound = _remap(state, maps)
    assert state == frozen
    assert len(rebound["receipts"]) == len(rebound["events"]) == 2
    source_command = AuthoritativeWeekTransitionCommand.model_validate_json(
        state["receipts"][0]["request_payload_json"]
    )
    target_command = AuthoritativeWeekTransitionCommand.model_validate_json(
        rebound["receipts"][0]["request_payload_json"]
    )
    assert source_command.tournaments == (source,)
    assert target_command.tournaments == (target_binding,)
    assert target_command.branch_id == "fork"
    assert target_command.fingerprint == rebound["receipts"][0]["request_fingerprint"]
    assert _remap(state, maps) == rebound


@pytest.mark.parametrize(
    "corruption",
    [
        "missing_target", "wrong_target_branch", "wrong_event",
        "wrong_publication_week", "wrong_completed_week",
        "extra_source", "duplicate_historical_tournament",
        "source_corrections",
    ],
)
def test_one_tournament_audit_rejects_missing_or_forged_sources(corruption):
    state, maps, source, target = _one_tournament_case()
    if corruption == "missing_target":
        maps["tournament_bindings"].clear()
    elif corruption == "wrong_target_branch":
        maps["tournament_bindings"][source.edition_id] = target.model_copy(
            update={"branch_id": "stranger"}
        )
    elif corruption == "wrong_event":
        maps["tournament_bindings"][source.edition_id] = target.model_copy(
            update={"event_id": "fake-event"}
        )
    elif corruption == "wrong_publication_week":
        maps["tournament_bindings"][source.edition_id] = target.model_copy(
            update={"first_publication_week": RankingWeek(season_index=0, week=3)}
        )
    elif corruption == "wrong_completed_week":
        maps["tournament_bindings"][source.edition_id] = target.model_copy(
            update={"completed_week": RankingWeek(season_index=0, week=2)}
        )
    elif corruption == "extra_source":
        maps["tournament_bindings"]["phantom"] = target
    elif corruption in {"duplicate_historical_tournament", "source_corrections"}:
        row = state["receipts"][int(corruption == "duplicate_historical_tournament")]
        original = AuthoritativeWeekTransitionCommand.model_validate_json(
            row["request_payload_json"]
        )
        changes = (
            {"tournaments": (source,)}
            if corruption == "duplicate_historical_tournament"
            else {"corrections": ({"forged": "data"},)}
        )
        # A correction without a valid authoritative source must be rejected
        # before it can create any target audit record.
        if corruption == "source_corrections":
            row["request_payload_json"] = json.dumps({
                **original.model_dump(mode="json"),
                "corrections": [{"forged": "data"}],
            }, sort_keys=True, separators=(",", ":"))
        else:
            modified = original.model_copy(update=changes)
            row["request_payload_json"] = modified.canonical_request_json
        # Keep the receipt's stored request hash stale to test fail-closed.
    with pytest.raises(WeekTransitionForkAuditUnsupportedError):
        _remap(state, maps)


@pytest.mark.parametrize("forgery", ["source_branch", "source_event"])
def test_semantically_forged_tournament_fails_even_with_valid_receipt_hash(forgery):
    state, maps, source, target = _one_tournament_case()
    row = state["receipts"][0]
    original = AuthoritativeWeekTransitionCommand.model_validate_json(
        row["request_payload_json"]
    )
    tampered = source.model_copy(update={
        "branch_id": "foreign-branch",
    }) if forgery == "source_branch" else source.model_copy(update={
        "event_id": "phantom-completed-tournament",
    })
    command = AuthoritativeWeekTransitionCommand.model_validate_json(
        original.model_copy(update={"tournaments": (tampered,)}).model_dump_json()
    )
    row["request_payload_json"] = command.canonical_request_json
    row["request_fingerprint"] = command.fingerprint
    # Retain the correct World Event: its v1 payload cites the ranking/player
    # snapshots and audit, not the tournament tuple. Hash-only checks therefore
    # cannot detect this forged but syntactically valid tournament identity.
    with pytest.raises(
        WeekTransitionForkAuditUnsupportedError,
        match="tournament binding has no matching target ownership",
    ):
        _remap(state, maps)


def _two_distinct_tournament_weeks():
    state, maps, first_source, first_target = _one_tournament_case()
    second_source = first_source.model_copy(update={
        "edition_id": "completed-standard-week-2",
        "event_id": "week-two-classic",
        "completed_week": RankingWeek(season_index=0, week=2),
        "first_publication_week": RankingWeek(season_index=0, week=3),
        "expected_result_fingerprint": _fingerprint(2101),
        "expected_award_fingerprint": _fingerprint(2102),
    })
    second_target = second_source.model_copy(update={
        "branch_id": "fork",
        "expected_result_fingerprint": _fingerprint(3101),
        "expected_award_fingerprint": _fingerprint(3102),
    })
    row = state["receipts"][1]
    original = AuthoritativeWeekTransitionCommand.model_validate_json(
        row["request_payload_json"]
    )
    second = AuthoritativeWeekTransitionCommand.model_validate_json(
        original.model_copy(update={
            "tournaments": (second_source,)
        }).model_dump_json()
    )
    row["request_payload_json"] = second.canonical_request_json
    row["request_fingerprint"] = second.fingerprint
    maps["tournament_bindings"][second_source.edition_id] = second_target
    return state, maps, (first_source, second_source), (first_target, second_target)


def test_two_distinct_tournament_weeks_have_complete_independent_rebound():
    state, maps, sources, targets = _two_distinct_tournament_weeks()
    immutable = deepcopy(state)
    remapped = _remap(state, maps)
    assert state == immutable
    assert _remap(state, maps) == remapped
    assert len(remapped["receipts"]) == len(remapped["events"]) == 2
    for index, (src, dst) in enumerate(zip(sources, targets, strict=True)):
        command = AuthoritativeWeekTransitionCommand.model_validate_json(
            remapped["receipts"][index]["request_payload_json"]
        )
        assert command.tournaments == (dst,)
        assert command.tournaments[0].edition_id == src.edition_id
        assert remapped["events"][index]["branch_id"] == "fork"
        assert remapped["receipts"][index]["request_fingerprint"] == command.fingerprint


@pytest.mark.parametrize(
    "corruption",
    ["missing_second", "wrong_second_week", "duplicate_edition", "two_in_one_week"],
)
def test_two_tournament_weeks_fail_closed_on_incomplete_or_ambiguous_sources(corruption):
    state, maps, sources, targets = _two_distinct_tournament_weeks()
    if corruption == "missing_second":
        del maps["tournament_bindings"][sources[1].edition_id]
    elif corruption == "wrong_second_week":
        maps["tournament_bindings"][sources[1].edition_id] = (
            targets[1].model_copy(update={
                "completed_week": RankingWeek(season_index=0, week=1)
            })
        )
    else:
        index = 1 if corruption == "duplicate_edition" else 0
        row = state["receipts"][index]
        command = AuthoritativeWeekTransitionCommand.model_validate_json(
            row["request_payload_json"]
        )
        replacement = sources[0] if corruption == "duplicate_edition" else None
        replacement_tournaments = (
            (replacement,) if replacement is not None
            else (sources[0], sources[1])
        )
        modified = AuthoritativeWeekTransitionCommand.model_validate_json(
            command.model_copy(update={
                "tournaments": replacement_tournaments
            }).model_dump_json()
        )
        row["request_payload_json"] = modified.canonical_request_json
        row["request_fingerprint"] = modified.fingerprint
    with pytest.raises(WeekTransitionForkAuditUnsupportedError):
        _remap(state, maps)


def _two_simultaneous_tournament_events():
    state, maps, first, first_target = _one_tournament_case()
    second = first.model_copy(update={
        "edition_id": "independent-second-week-one-edition",
        "event_id": "independent-second-week-one-event",
        "expected_result_fingerprint": _fingerprint(2201),
        "expected_award_fingerprint": _fingerprint(2202),
    })
    second_target = second.model_copy(update={
        "branch_id": "fork",
        "expected_result_fingerprint": _fingerprint(3201),
        "expected_award_fingerprint": _fingerprint(3202),
    })
    original = AuthoritativeWeekTransitionCommand.model_validate_json(
        state["receipts"][0]["request_payload_json"]
    )
    command = AuthoritativeWeekTransitionCommand.model_validate_json(
        original.model_copy(
            update={"tournaments": (first, second)}
        ).model_dump_json()
    )
    state["receipts"][0]["request_payload_json"] = command.canonical_request_json
    state["receipts"][0]["request_fingerprint"] = command.fingerprint
    maps["tournament_bindings"][second.edition_id] = second_target
    return state, maps, (first, second), (first_target, second_target)


def test_two_same_week_tournaments_rebind_both_full_receipt_bindings_without_mutation():
    state, maps, sources, targets = _two_simultaneous_tournament_events()
    source_copy = deepcopy(state)
    rebound = _remap(state, maps)
    assert state == source_copy
    assert _remap(state, maps) == rebound
    first_command = AuthoritativeWeekTransitionCommand.model_validate_json(
        rebound["receipts"][0]["request_payload_json"]
    )
    assert first_command.tournaments == targets
    assert tuple(x.edition_id for x in first_command.tournaments) == tuple(
        x.edition_id for x in sources
    )
    assert all(x.branch_id == "fork" for x in first_command.tournaments)
    assert rebound["receipts"][0]["request_fingerprint"] == first_command.fingerprint
    second_command = AuthoritativeWeekTransitionCommand.model_validate_json(
        rebound["receipts"][1]["request_payload_json"]
    )
    assert second_command.tournaments == ()
    assert len(rebound["events"]) == 2


@pytest.mark.parametrize("corruption", [
    "missing_second", "foreign_second", "forged_second_event",
    "duplicate_edition", "duplicate_event", "third_tournament",
    "second_completion_week", "extra_source",
])
def test_two_same_week_tournaments_reject_incomplete_or_forged_provenance(corruption):
    state, maps, sources, targets = _two_simultaneous_tournament_events()
    original = AuthoritativeWeekTransitionCommand.model_validate_json(
        state["receipts"][0]["request_payload_json"]
    )
    tournaments = list(original.tournaments)
    if corruption == "missing_second":
        maps["tournament_bindings"].pop(sources[1].edition_id)
    elif corruption == "foreign_second":
        maps["tournament_bindings"][sources[1].edition_id] = targets[1].model_copy(
            update={"branch_id": "foreign"}
        )
    elif corruption == "extra_source":
        maps["tournament_bindings"]["phantom-edition"] = targets[1]
    else:
        if corruption == "forged_second_event":
            tournaments[1] = tournaments[1].model_copy(
                update={"event_id": "phantom-event"}
            )
        elif corruption == "duplicate_edition":
            tournaments[1] = tournaments[0]
        elif corruption == "duplicate_event":
            tournaments[1] = tournaments[1].model_copy(
                update={"event_id": tournaments[0].event_id}
            )
        elif corruption == "third_tournament":
            tournaments.append(tournaments[1].model_copy(update={
                "edition_id": "third-independent-tournament",
                "event_id": "third-independent-event",
            }))
        elif corruption == "second_completion_week":
            # Keep the forged binding schema-valid: publish in Week 3 after
            # its alleged Week-2 completion. Only the source Week-1 receipt
            # can prove this tournament is not actually part of Week 1.
            tournaments[1] = tournaments[1].model_copy(update={
                "completed_week": RankingWeek(season_index=0, week=2),
                "first_publication_week": RankingWeek(season_index=0, week=3),
            })
        replaced = AuthoritativeWeekTransitionCommand.model_validate_json(
            original.model_copy(update={
                "tournaments": tuple(tournaments)
            }).model_dump_json()
        )
        state["receipts"][0]["request_payload_json"] = replaced.canonical_request_json
        state["receipts"][0]["request_fingerprint"] = replaced.fingerprint
    with pytest.raises(WeekTransitionForkAuditUnsupportedError):
        _remap(state, maps)

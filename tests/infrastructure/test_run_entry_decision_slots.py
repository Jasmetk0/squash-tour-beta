import pytest

from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeSlotMatchExecutor,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import SimulationMatchEventPlan
from beta_engine.domain.tournaments.application_validation_authority import (
    ResolvedApplicationValidationSlot,
    TournamentApplicationValidationAuthority,
)
from beta_engine.domain.tournaments.run_entry_decision_slot import (
    EntryDecisionEvidence,
    RunEntryDecisionSlotAuthority,
)
from beta_engine.domain.tournaments.wild_card_authority import (
    TournamentWildCardAuthority,
    TournamentWildCardSlotResolution,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    TournamentWildCardAuthorityModel,
)
from beta_engine.infrastructure.db.application_validation_slots import (
    ApplicationValidationSlotStore,
)
from beta_engine.infrastructure.db.run_entry_decision_slots import (
    RUN_ENTRY_DECISION_SLOT_COMPONENT_KEY,
    RunEntryDecisionSlotConflict,
    RunEntryDecisionSlotStore,
    capture_saved_run_entry_decision_slots,
    load_saved_run_entry_decision_slots,
    restore_saved_run_entry_decision_slots,
    validate_saved_entry_match_slot_collisions,
)
from test_authoritative_slot_matches import session_at


WEEK = RankingWeek(season_index=0, week=1)


def _ensure_scope(session):
    if session.get(RunContainerModel, "run") is None:
        session.add(
            RunContainerModel(
                run_id="run",
                display_name="Run",
                storage_kind="custom_local",
                read_only=0,
                timeline_start_season=2000,
                timeline_end_season=2049,
                official_branch_id="branch",
                status="working",
            )
        )
    if session.get(RunBranchModel, "branch") is None:
        session.add(
            RunBranchModel(
                run_id="run",
                branch_id="branch",
                display_name="Timeline 1",
                status="active",
                read_only=0,
            )
        )
    session.flush()


def _entry_slot(**overrides):
    payload = {
        "run_id": "run",
        "branch_id": "branch",
        "week": WEEK,
        "decision_slot_ordinal": 1,
        "source_entry_batch_fingerprint": "a" * 64,
        "source_application_decisions_fingerprint": "b" * 64,
        "source_active_players_fingerprint": "c" * 64,
        "decisions": (
            EntryDecisionEvidence(
                event_id="entry-event",
                player_id="a",
                target="MAIN",
                source_decision_fingerprint="d" * 64,
            ),
        ),
    }
    payload.update(overrides)
    return RunEntryDecisionSlotAuthority(**payload)


def _resolve_entry_slot(session, authority):
    decision = authority.decisions[0]
    validation = TournamentApplicationValidationAuthority(
        validation_id=f"validation-{authority.decision_slot_ordinal}",
        application_id=f"application-{authority.decision_slot_ordinal}",
        run_id=authority.run_id,
        branch_id=authority.branch_id,
        week=authority.week,
        decision_slot_ordinal=authority.decision_slot_ordinal,
        source_slot_fingerprint=authority.fingerprint,
        event_id=decision.event_id,
        player_id=decision.player_id,
        entry_window="main" if decision.target == "MAIN" else "qualification",
        source_decision_fingerprint=decision.source_decision_fingerprint,
        outcome="invalid",
        nr_tie_break_token=None,
        validation_policy_id="test-policy.v1",
        validation_policy_fingerprint="f" * 64,
        reasons=("test_invalid",),
        provenance="entry-slot chronology test",
    )
    resolved = ResolvedApplicationValidationSlot(
        slot=authority,
        validations=(validation,),
    )
    ApplicationValidationSlotStore(session).append(resolved)
    return resolved


def _match_plan(executor, *, ordinal=1):
    return executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id=f"match-slot-{ordinal}",
        ordinal=ordinal,
        group_ids=(f"group-{ordinal}",),
        match_events=(
            SimulationMatchEventPlan(
                group_id=f"group-{ordinal}",
                event_id="match-event",
                match_id=f"match-{ordinal}",
                direct_player_ids=("a", "b"),
            ),
        ),
    )


def _install_wc_slot(session, *, ordinal=1, event_id="wc-event"):
    authority = TournamentWildCardAuthority(
        schema_version="tournament_wild_card_authority.v2",
        run_id="run",
        branch_id="branch",
        event_id=event_id,
        resolved_by_command_id=f"wc-command-{ordinal}",
        entry_field_fingerprint="1" * 64,
        field_sequence=1,
        decision_week=WEEK,
        decision_slot_ordinal=ordinal,
        original_wild_card_player_ids=(None,),
        reserve_wild_card_player_ids=(),
        unavailable_player_ids=(),
        slots=(
            TournamentWildCardSlotResolution(
                wildcard_index=1,
                source="unfilled",
            ),
        ),
        adjusted_qualification_player_ids=(),
        adjusted_below_qualification_cut_player_ids=(),
    )
    session.add(
        TournamentWildCardAuthorityModel(
            run_id=authority.run_id,
            branch_id=authority.branch_id,
            event_id=authority.event_id,
            command_id=authority.resolved_by_command_id,
            request_fingerprint="2" * 64,
            authority_fingerprint=authority.fingerprint,
            entry_field_fingerprint=authority.entry_field_fingerprint,
            field_sequence=authority.field_sequence,
            payload_json=authority.model_dump_json(),
        )
    )
    session.flush()
    return authority


@pytest.mark.pr_critical
def test_wc_slot_then_entry_slot_collision_fails_closed(tmp_path):
    session = session_at(tmp_path / "wc-entry-collision.sqlite")
    _ensure_scope(session)
    try:
        _install_wc_slot(session)
        with pytest.raises(
            RunEntryDecisionSlotConflict,
            match="already belongs to a WC-decision slot",
        ):
            RunEntryDecisionSlotStore(session).append(_entry_slot())
    finally:
        session.close()


@pytest.mark.pr_critical
def test_wc_slot_then_match_slot_collision_fails_closed(tmp_path):
    session = session_at(tmp_path / "wc-match-collision.sqlite")
    _ensure_scope(session)
    try:
        _install_wc_slot(session)
        with pytest.raises(
            ValueError,
            match="already belongs to a WC-decision slot",
        ):
            _match_plan(AuthoritativeSlotMatchExecutor(session), ordinal=1)
    finally:
        session.close()


@pytest.mark.pr_critical
def test_completed_wc_slot_satisfies_prior_global_ordinal_for_entry(tmp_path):
    session = session_at(tmp_path / "wc-entry-order.sqlite")
    _ensure_scope(session)
    try:
        _install_wc_slot(session, ordinal=1)
        second = _entry_slot(
            decision_slot_ordinal=2,
            source_entry_batch_fingerprint="e" * 64,
            source_application_decisions_fingerprint="f" * 64,
        )
        assert RunEntryDecisionSlotStore(session).append(second) == second
    finally:
        session.close()


@pytest.mark.pr_critical
def test_saved_revision_rejects_wc_entry_global_slot_collision(tmp_path):
    session = session_at(tmp_path / "saved-wc-entry-collision.sqlite")
    _ensure_scope(session)
    try:
        entry = _entry_slot()
        RunEntryDecisionSlotStore(session).append(entry)
        payload = {"content": {}}
        capture_saved_run_entry_decision_slots(
            session,
            payload,
            run_id="run",
            branch_id="branch",
        )
        wc = TournamentWildCardAuthority(
            schema_version="tournament_wild_card_authority.v3",
            run_id="run",
            branch_id="branch",
            event_id="wc-event",
            resolved_by_command_id="wc-command-1",
            entry_field_fingerprint="1" * 64,
            field_sequence=1,
            decision_week=WEEK,
            decision_slot_ordinal=1,
            selection_policy_id="explicit_admin_wild_card_selection.v1",
            operator_label="Commissioner",
            audit_reason="Saved Revision v3 collision regression",
            original_wild_card_player_ids=(None,),
            slots=(TournamentWildCardSlotResolution(wildcard_index=1, source="unfilled"),),
            adjusted_qualification_player_ids=(),
            adjusted_below_qualification_cut_player_ids=(),
        )
        payload["content"]["simulation_slot_match_state"] = {
            "slots": [],
            "wild_card_authorities": [
                {
                    "run_id": "run",
                    "branch_id": "branch",
                    "event_id": "wc-event",
                    "command_id": wc.resolved_by_command_id,
                    "entry_field_fingerprint": wc.entry_field_fingerprint,
                    "field_sequence": wc.field_sequence,
                    "authority_fingerprint": wc.fingerprint,
                    "payload_json": wc.model_dump_json(),
                }
            ],
        }
        with pytest.raises(
            ValueError,
            match="WC decision and another slot claim the same global position",
        ):
            validate_saved_entry_match_slot_collisions(
                payload,
                run_id="run",
                branch_id="branch",
            )
    finally:
        session.close()


@pytest.mark.pr_critical
def test_entry_slot_store_is_idempotent_and_immutable(tmp_path):
    session = session_at(tmp_path / "entry-slot.sqlite")
    _ensure_scope(session)
    try:
        store = RunEntryDecisionSlotStore(session)
        authority = _entry_slot()
        assert store.append(authority) == authority
        assert store.append(authority) == authority
        assert store.list(run_id="run", branch_id="branch") == (authority,)

        conflicting = _entry_slot(source_entry_batch_fingerprint="e" * 64)
        with pytest.raises(
            RunEntryDecisionSlotConflict,
            match="already has different authority",
        ):
            store.append(conflicting)
    finally:
        session.close()


@pytest.mark.pr_critical
def test_match_slot_then_entry_slot_collision_fails_closed(tmp_path):
    session = session_at(tmp_path / "match-first.sqlite")
    _ensure_scope(session)
    try:
        executor = AuthoritativeSlotMatchExecutor(session)
        _match_plan(executor, ordinal=1)

        with pytest.raises(
            RunEntryDecisionSlotConflict,
            match="already belongs to a match slot",
        ):
            RunEntryDecisionSlotStore(session).append(_entry_slot())
    finally:
        session.close()


@pytest.mark.pr_critical
def test_entry_slot_then_match_slot_collision_fails_closed(tmp_path):
    session = session_at(tmp_path / "entry-first.sqlite")
    _ensure_scope(session)
    try:
        RunEntryDecisionSlotStore(session).append(_entry_slot())

        with pytest.raises(
            ValueError,
            match="already belongs to an entry-decision slot",
        ):
            _match_plan(AuthoritativeSlotMatchExecutor(session), ordinal=1)
    finally:
        session.close()


@pytest.mark.pr_critical
def test_later_entry_slot_requires_prior_entry_validation_completion(tmp_path):
    session = session_at(tmp_path / "entry-validation-order.sqlite")
    _ensure_scope(session)
    try:
        store = RunEntryDecisionSlotStore(session)
        first = _entry_slot(decision_slot_ordinal=1)
        store.append(first)

        second = _entry_slot(
            decision_slot_ordinal=2,
            source_entry_batch_fingerprint="e" * 64,
            source_application_decisions_fingerprint="f" * 64,
        )
        with pytest.raises(
            RunEntryDecisionSlotConflict,
            match=r"missing completed ordinals \[1\]",
        ):
            store.append(second)

        _resolve_entry_slot(session, first)
        assert store.append(second) == second
    finally:
        session.close()


@pytest.mark.pr_critical
def test_match_after_entry_slot_requires_validation_completion(tmp_path):
    session = session_at(tmp_path / "entry-validation-before-match.sqlite")
    _ensure_scope(session)
    try:
        authority = _entry_slot(decision_slot_ordinal=1)
        RunEntryDecisionSlotStore(session).append(authority)
        executor = AuthoritativeSlotMatchExecutor(session)

        with pytest.raises(
            ValueError,
            match=r"unresolved entry-decision slots: \[1\]",
        ):
            _match_plan(executor, ordinal=2)

        _resolve_entry_slot(session, authority)
        plan = _match_plan(executor, ordinal=2)
        assert plan.ordinal == 2
    finally:
        session.close()


@pytest.mark.pr_critical
def test_saved_component_round_trip_restores_entry_slots(tmp_path):
    session = session_at(tmp_path / "saved-entry-slots.sqlite")
    _ensure_scope(session)
    try:
        empty_payload = {"content": {}}
        capture_saved_run_entry_decision_slots(
            session,
            empty_payload,
            run_id="run",
            branch_id="branch",
        )
        assert empty_payload["content"][RUN_ENTRY_DECISION_SLOT_COMPONENT_KEY][
            "slots"
        ] == []

        authority = _entry_slot()
        RunEntryDecisionSlotStore(session).append(authority)
        current_payload = {"content": {}}
        capture_saved_run_entry_decision_slots(
            session,
            current_payload,
            run_id="run",
            branch_id="branch",
        )
        assert load_saved_run_entry_decision_slots(
            current_payload,
            run_id="run",
            branch_id="branch",
        ) == (authority,)

        restore_saved_run_entry_decision_slots(
            session,
            current_payload=current_payload,
            target_payload=empty_payload,
            run_id="run",
            branch_id="branch",
        )
        assert RunEntryDecisionSlotStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == ()

        restore_saved_run_entry_decision_slots(
            session,
            current_payload=empty_payload,
            target_payload=current_payload,
            run_id="run",
            branch_id="branch",
        )
        assert RunEntryDecisionSlotStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == (authority,)
    finally:
        session.close()


@pytest.mark.pr_critical
def test_saved_revision_target_rejects_entry_match_global_slot_collision(tmp_path):
    session = session_at(tmp_path / "saved-collision.sqlite")
    _ensure_scope(session)
    try:
        authority = _entry_slot()
        RunEntryDecisionSlotStore(session).append(authority)
        payload = {"content": {}}
        capture_saved_run_entry_decision_slots(
            session,
            payload,
            run_id="run",
            branch_id="branch",
        )
        payload["content"]["simulation_slot_match_state"] = {
            "slots": [
                {
                    "run_id": "run",
                    "branch_id": "branch",
                    "week_ordinal": WEEK.ordinal,
                    "slot_ordinal": 1,
                }
            ]
        }

        with pytest.raises(
            ValueError,
            match="claim the same global position",
        ):
            validate_saved_entry_match_slot_collisions(
                payload,
                run_id="run",
                branch_id="branch",
            )
    finally:
        session.close()

@pytest.mark.pr_critical
def test_saved_revision_rejects_unowned_sparse_match_gap(tmp_path):
    session = session_at(tmp_path / "saved-unowned-gap.sqlite")
    _ensure_scope(session)
    try:
        payload = {
            "content": {
                "simulation_slot_match_state": {
                    "slots": [
                        {
                            "run_id": "run",
                            "branch_id": "branch",
                            "week_ordinal": WEEK.ordinal,
                            "slot_ordinal": 2,
                        }
                    ]
                }
            }
        }
        with pytest.raises(
            ValueError,
            match="global-slot gap not owned by an entry-decision slot",
        ):
            validate_saved_entry_match_slot_collisions(
                payload,
                run_id="run",
                branch_id="branch",
            )
    finally:
        session.close()

@pytest.mark.pr_critical
def test_entry_slot_cannot_overtake_missing_prior_global_slot(tmp_path):
    session = session_at(tmp_path / "entry-overtake.sqlite")
    _ensure_scope(session)
    try:
        with pytest.raises(
            RunEntryDecisionSlotConflict,
            match=r"missing completed ordinals \[1\]",
        ):
            RunEntryDecisionSlotStore(session).append(
                _entry_slot(decision_slot_ordinal=2)
            )
        assert RunEntryDecisionSlotStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == ()
    finally:
        session.close()


@pytest.mark.pr_critical
def test_saved_revision_rejects_entry_only_global_gap(tmp_path):
    session = session_at(tmp_path / "saved-entry-only-gap.sqlite")
    _ensure_scope(session)
    try:
        authority = _entry_slot(decision_slot_ordinal=2)
        payload = {
            "content": {
                RUN_ENTRY_DECISION_SLOT_COMPONENT_KEY: {
                    "fingerprint": "",
                    "slots": [authority.model_dump(mode="json")],
                }
            }
        }
        # Rebuild the component through the real capture helper so its fingerprint is
        # valid, then alter only the chronological ordinal.
        RunEntryDecisionSlotStore(session).append(
            _entry_slot(decision_slot_ordinal=1)
        )
        captured = {"content": {}}
        capture_saved_run_entry_decision_slots(
            session,
            captured,
            run_id="run",
            branch_id="branch",
        )
        component = captured["content"][RUN_ENTRY_DECISION_SLOT_COMPONENT_KEY]
        component["slots"][0]["decision_slot_ordinal"] = 2

        # The component fingerprint must correspond to the tampered semantic payload
        # before the cross-component chronology validator can inspect chronology.
        import hashlib
        import json
        component["fingerprint"] = hashlib.sha256(
            json.dumps(
                component["slots"],
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

        with pytest.raises(
            ValueError,
            match="global Simulation Slot chronology is not contiguous",
        ):
            validate_saved_entry_match_slot_collisions(
                captured,
                run_id="run",
                branch_id="branch",
            )
    finally:
        session.close()


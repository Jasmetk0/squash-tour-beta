import pytest
from pydantic import ValidationError

from beta_engine.domain.players.tour_entry import PlayerTourEntryTrigger
from beta_engine.domain.rankings.official import RankingWeek


def _trigger(**overrides):
    payload = {
        "run_id": "run",
        "branch_id": "branch",
        "player_id": "prospect-1",
        "event_id": "event-1",
        "trigger_kind": "valid_tournament_application",
        "trigger_week": RankingWeek(season_index=3, week=17),
        "decision_slot_ordinal": 4,
        "source_evidence_id": "application-1",
        "source_evidence_fingerprint": "a" * 64,
        "provenance": "canonical application-submission authority",
    }
    payload.update(overrides)
    return PlayerTourEntryTrigger(**payload)


@pytest.mark.pr_critical
def test_tour_entry_trigger_is_exact_stable_chronological_evidence():
    trigger = _trigger()

    assert trigger.tour_entry_week == RankingWeek(season_index=3, week=17)
    assert trigger.decision_position == (trigger.trigger_week.ordinal, 4)
    assert len(trigger.fingerprint) == 64
    assert trigger == _trigger()
    assert trigger.fingerprint == _trigger().fingerprint


@pytest.mark.pr_critical
def test_application_and_definitive_wc_are_distinct_master_triggers():
    application = _trigger()
    wildcard = _trigger(
        trigger_kind="definitive_wild_card_assignment",
        source_evidence_id="wc-assignment-1",
        source_evidence_fingerprint="b" * 64,
        provenance="canonical definitive Wild Card authority",
    )

    assert application.trigger_kind == "valid_tournament_application"
    assert wildcard.trigger_kind == "definitive_wild_card_assignment"
    assert application.fingerprint != wildcard.fingerprint
    assert application.tour_entry_week == wildcard.tour_entry_week


@pytest.mark.pr_critical
def test_tour_entry_trigger_fingerprint_binds_scope_time_and_source_authority():
    baseline = _trigger()

    variants = (
        _trigger(branch_id="other-branch"),
        _trigger(player_id="prospect-2"),
        _trigger(event_id="event-2"),
        _trigger(trigger_week=RankingWeek(season_index=3, week=18)),
        _trigger(decision_slot_ordinal=5),
        _trigger(source_evidence_id="application-2"),
        _trigger(source_evidence_fingerprint="c" * 64),
    )
    assert all(item.fingerprint != baseline.fingerprint for item in variants)


@pytest.mark.pr_critical
def test_tour_entry_trigger_rejects_unowned_or_malformed_evidence():
    with pytest.raises(ValidationError):
        _trigger(source_evidence_id="")
    with pytest.raises(ValidationError):
        _trigger(source_evidence_fingerprint="not-a-fingerprint")
    with pytest.raises(ValidationError):
        _trigger(decision_slot_ordinal=-1)
    with pytest.raises(ValidationError):
        _trigger(trigger_kind="field_cut_acceptance")

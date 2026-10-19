"""Persist/reopen/restore the v11 component derived from genuine HTTP inputs.

The candidate is deliberately not installed as a Signed Revision: the coupled
Tour receipt executor remains a separate gate. No World or MatchEngine mocks.
"""
from copy import deepcopy
import json

import pytest

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_native_health_transition import prepare_native_health_history
from beta_engine.domain.players.calendar_native_sporting_checkpoint import append_native_sporting_week
from beta_engine.domain.players.calendar_native_sporting_intake import project_native_sporting_birth_advance
from beta_engine.domain.players.calendar_prospect_admission_bundle import build_native_prospect_admission_bundle
from beta_engine.domain.players.calendar_sporting_week import played_counts
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.calendar_tour import (
    CalendarTourState, CalendarTourTransition, calculate_tour_ranking, effective_policy,
)
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
    COMPONENT_KEY, load_checkpoint, put_checkpoint, replace_checkpoint,
    restore_checkpoint, saved_checkpoint,
)
from beta_engine.infrastructure.db.calendar_standalone_match_state import decode_prevalidated_calendar_sources
from beta_engine.infrastructure.db.calendar_tour import verify_tour
from beta_engine.infrastructure.db.engine import DatabaseSettings, create_sqlite_engine, create_session_factory
from beta_engine.infrastructure.db.models import CalendarPlayerSportingCheckpointModel
from beta_engine.infrastructure.db.player_health_state import _component, load_saved_health
from beta_engine.infrastructure.db.player_lifecycle_state import load_saved_lifecycle
from beta_engine.infrastructure.db.run_prospect_source_state import load_saved_run_prospect_source


def exercise_checkpoint_component(repo, world, proposal, tmp_path):
    run, branch = world.run_id, world.branch_id
    head = proposal["saved_head_revision_id"]
    assert repo.verify_branch_saved_revision_hash(revision_id=head)
    original = repo.get_branch_saved_revision(revision_id=head).payload
    evidence, root, tour = decode_prevalidated_calendar_sources(original,run_id=run,branch_id=branch)
    knockout = getattr(evidence,"knockout",evidence)
    life = load_saved_lifecycle(original,run_id=run,branch_id=branch)
    source = load_saved_run_prospect_source(original,run_id=run)
    health = load_saved_health(original,run_id=run,branch_id=branch)
    target = RunWeekPosition.model_validate_json(json.dumps(proposal["target_week"]))
    bundle = build_native_prospect_admission_bundle(predecessor=life[-1],checkpoint=root,
        health=health[-1],source=source,target=target,world_package_id=world.world_package_id,
        saved_head_revision_id=head,submissions=tuple(s for a in tour.editions for s in a.submissions))
    prepared_health=prepare_native_health_history(saved_health=health,signed_lifecycle=life,
        next_lifecycle=bundle.lifecycle)
    sport=project_native_sporting_birth_advance(checkpoint=root,predecessor=life[-1],
        birth_event=bundle.event,seed=proposal["sporting_week_projection"]["seed"],
        policy=effective_policy(tour,root.week).development,played_counts=played_counts(root,knockout))
    state=append_native_sporting_week(root,sport,lifecycle_fingerprint=bundle.lifecycle.fingerprint,
        health_fingerprint=prepared_health[-1].fingerprint,
        health_history_fingerprint=_component(prepared_health)["fingerprint"])
    assert state.fingerprint==proposal["sporting_week_projection"]["durable_sporting"]["checkpoint_fingerprint"]
    # A read-only candidate of the three component owners, never a signed Save.
    candidate=deepcopy(original)
    candidate["content"][COMPONENT_KEY]={"fingerprint":state.fingerprint,"state":state.model_dump(mode="json")}
    new_life=(*life,bundle.lifecycle)
    candidate["content"]["player_lifecycle"]={
        "fingerprint":canonical_hash([s.model_dump(mode="json") for s in new_life]),
        "states":[s.model_dump(mode="json") for s in new_life],
    }
    candidate["content"]["player_health_state"]=_component(prepared_health)
    retired=tuple(p.player_id for p in bundle.lifecycle.players if p.status=="retired")
    ranking=calculate_tour_ranking(tour,root,target=target,retired=retired)
    transition=CalendarTourTransition(command_id="component-only-preview",
        completed_week=root.week.model_copy(update={"calendar":target.calendar}),target_week=target,
        sporting_advance_fingerprint=sport.fingerprint,ranking_fingerprint=ranking.fingerprint,
        health_fingerprint=prepared_health[-1].fingerprint,
        ages=tuple((p.player_id,p.age) for p in bundle.lifecycle.players),retired_player_ids=retired,
        public_event={"kind":"week_transition_completed"})
    target_tour=tour.model_copy(update={"week":target,"checkpoint_fingerprint":state.fingerprint,
        "lifecycle_fingerprint":bundle.lifecycle.fingerprint,"rankings":(*tour.rankings,ranking),
        "transitions":(*tour.transitions,transition)})
    target_tour=CalendarTourState.model_validate_json(target_tour.model_dump_json())
    candidate["content"]["calendar_tour_authority"]={
        "fingerprint":target_tour.fingerprint,"state":target_tour.model_dump(mode="json")}
    assert saved_checkpoint(candidate,evidence,run_id=run,branch_id=branch)==state
    with pytest.raises(ValueError,match="coupled Tour transition receipt authority"):
        verify_tour(target_tour,state,world)

    for attack in ("development","counts","health","source","policy","tour_hash"):
        forged=deepcopy(candidate)
        component=forged["content"][COMPONENT_KEY]
        entry=component["state"]["native_weeks"][0]
        if attack=="development": entry["advance"]["developed_players"][0]["attributes"][0][1]^=1
        elif attack=="counts": entry["advance"]["played_counts"][0][1]+=1
        elif attack=="health": entry["health_fingerprint"]="0"*64
        elif attack=="source": del forged["content"]["run_prospect_source"]
        elif attack=="policy":
            forged["content"]["calendar_tour_authority"]["state"]["policies"][0]["development"]["annual_change_basis_points"]+=1
        component["fingerprint"]=canonical_hash(component["state"])
        tour_component=forged["content"]["calendar_tour_authority"]
        tour_component["state"]["checkpoint_fingerprint"]=component["fingerprint"]
        tour_component["fingerprint"]=canonical_hash(tour_component["state"])
        if attack=="tour_hash": tour_component["fingerprint"]="0"*64
        with pytest.raises(ValueError):
            saved_checkpoint(forged,evidence,run_id=run,branch_id=branch)

    # Real SQLite component writer, transaction rollback, process reopen and
    # production restore adapter in an isolated disposable component database.
    url=f"sqlite:///{tmp_path / 'native-checkpoint-component.db'}"
    engine=create_sqlite_engine(DatabaseSettings(url=url))
    CalendarPlayerSportingCheckpointModel.__table__.create(engine)
    sessions=create_session_factory(engine)
    try:
        with sessions.begin() as session:
            put_checkpoint(session,root)
        with pytest.raises(RuntimeError,match="late failure"):
            with sessions.begin() as session:
                replace_checkpoint(session,previous=root,successor=state)
                raise RuntimeError("late failure")
        with sessions.begin() as session:
            assert load_checkpoint(session,run_id=run,branch_id=branch)==root
            replace_checkpoint(session,previous=root,successor=state)
    finally:
        engine.dispose()
    engine=create_sqlite_engine(DatabaseSettings(url=url))
    try:
        with create_session_factory(engine).begin() as session:
            assert load_checkpoint(session,run_id=run,branch_id=branch)==state
            restore_checkpoint(session,current_payload=candidate,target_payload=original,
                current=evidence,target=evidence,run_id=run,branch_id=branch)
            assert load_checkpoint(session,run_id=run,branch_id=branch)==root
            restore_checkpoint(session,current_payload=original,target_payload=candidate,
                current=evidence,target=evidence,run_id=run,branch_id=branch)
            assert load_checkpoint(session,run_id=run,branch_id=branch)==state
    finally:
        engine.dispose()
    assert repo.get_branch_saved_revision(revision_id=head).payload==original

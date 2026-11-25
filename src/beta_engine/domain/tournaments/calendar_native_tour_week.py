"""Pure complete birth-week preparation shared by execution and Signed replay."""

from collections import OrderedDict
from threading import Lock

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_lifecycle import advance_calendar_lifecycle
from beta_engine.domain.players.calendar_native_competition import (
    CalendarNativeCompetitionCheckpoint,
)
from beta_engine.domain.players.calendar_native_health_transition import (
    prepare_native_health_history,
)
from beta_engine.domain.players.calendar_native_ranking_bridge import (
    calculate_native_ranking_from_signed_lifecycle,
)
from beta_engine.domain.players.calendar_native_sporting_checkpoint import (
    CalendarNativeSportingCheckpoint,
    append_native_sporting_week,
)
from beta_engine.domain.players.calendar_native_sporting_intake import (
    project_native_sporting_birth_advance,
)
from beta_engine.domain.players.calendar_prospect_birth import (
    advance_calendar_lifecycle_with_prospects,
    build_calendar_prospect_birth_event,
)
from beta_engine.domain.players.calendar_sporting_week import played_counts
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.calendar_tour import (
    effective_policy,
    published_edition_results,
)


def _native_turn_pro(*, state, checkpoint, world, lifecycle, target, submissions, seed, model):
    """Countries from the InitialWorld and earlier signed birth events."""
    if not lifecycle[-1].policy.requires_turn_pro:
        # Historical rule: touch no extra inputs, so earlier callers are unchanged.
        if model is not None:
            raise ValueError("Turn Pro model requires the v87 lifecycle policy")
        return (), None
    countries = {p.player_id: p.country_code for p in world.players}
    for state_ in lifecycle:
        for birth in getattr(getattr(state_, "birth_event", None), "births", ()):
            countries[birth.player_id] = birth.country_code
    from beta_engine.domain.players.turn_pro_model import traits_from_world

    return native_turn_pro_decisions(
        tour_state=state, predecessor=lifecycle[-1], checkpoint=checkpoint,
        countries=countries, target=target, submissions=submissions, seed=seed,
        model=model, traits_by_player=traits_from_world(world),
    )


def native_turn_pro_decisions(
    *, tour_state, predecessor, checkpoint, countries, target, submissions, seed, model,
    traits_by_player=None,
):
    """Master v87 Turn Pro at a native Week Transition (pure; replayed on verify).

    Inputs are the lifecycle and sporting checkpoint of the completed week and the
    players' countries. ``model`` is the recorded policy on replay, else None for
    the current default. Returns ``((), None)`` under the historical rule.
    """
    from beta_engine.domain.players.turn_pro_model import (
        decide_turn_pro,
        default_turn_pro_model_policy,
        turn_pro_candidates_for,
    )
    from beta_engine.domain.tournaments.calendar_tour import turn_pro_home_opportunities

    if not predecessor.policy.requires_turn_pro:
        if model is not None:
            raise ValueError("Turn Pro model requires the v87 lifecycle policy")
        return (), None
    model = model or default_turn_pro_model_policy()
    plain = advance_calendar_lifecycle(predecessor, target, submissions)
    decisions = decide_turn_pro(
        predecessor=predecessor,
        target=target,
        policy=model,
        seed=seed,
        candidates=turn_pro_candidates_for(
            model,
            predecessor,
            plain,
            checkpoint.players,
            seed=seed,
            target=target,
            traits_by_player=traits_by_player,
            home_opportunity_by_player=turn_pro_home_opportunities(
                tour_state, target, countries
            ),
        ),
    )
    return decisions, model


# Published Official Ranking results recorded under the exact canonical
# fingerprints of the complete Tour state and sporting checkpoint they were
# derived from (see ``_results_key``). Values are deeply immutable frozen
# models (strings, integers, booleans and frozen weeks), about 2.3 KB each.
# One entry already serves Preview, Execute and the post-write replay of one
# Week Transition; a longer history above the result bound is not retained,
# i.e. it keeps the original full path (at most about 150 MB retained).
_VERIFIED_RESULTS = OrderedDict()
_VERIFIED_RESULTS_LOCK = Lock()
_MAX_VERIFIED_RESULT_ENTRIES = 4
_MAX_VERIFIED_RESULTS = 65536


def _results_key(state, checkpoint, target, clock):
    """The complete input identity, or None: then the full path always runs.

    Only inside a private replay scope, only for the exact native global-slot
    Tour v5 / checkpoint v13 types, and only from canonical hashes THIS
    operation has already computed or primed from its authenticated Saved
    context (a missing hash is never computed here). The results are a pure
    function of these two complete values, the Run clock and the target week.
    """
    from beta_engine.domain.tournaments.calendar_global_slots import (
        GlobalCompetitionCheckpoint,
        GlobalTourState,
        _replay_projections,
    )

    scope = _replay_projections.get()
    if (
        scope is None
        or type(state) is not GlobalTourState
        or type(checkpoint) is not GlobalCompetitionCheckpoint
        or type(clock) is not RunCalendar
    ):
        return None
    memo = scope["fingerprints"]
    known = [memo.get((id(value), False)) for value in (state, checkpoint)]
    if any(item is None or item[0] is not value for item, value in zip(known, (state, checkpoint))):
        return None
    return (
        state.schema_version, checkpoint.schema_version, state.run_id, state.branch_id,
        known[0][1], known[1][1], target.ordinal, clock,
    )


def native_results_cache_stats():
    """Measurement only: retained entries and result models."""
    with _VERIFIED_RESULTS_LOCK:
        return {
            "entries": len(_VERIFIED_RESULTS),
            "results": sum(len(v) for v in _VERIFIED_RESULTS.values()),
        }


_UNSET = object()


def native_confirmed_results(state, checkpoint, target, clock, *, key=_UNSET):
    """Every published result of each confirmed Edition completed before ``target``.

    Expired results stay in this tuple: they may stop counting, but their
    sources remain part of the ranking proof. The same complete verified
    inputs (identical canonical state and checkpoint hashes) reuse the results
    that the full path derived and validated for them, e.g. in Preview, Execute
    and its post-write replay of one Week Transition. A failure is never kept.
    """
    if key is _UNSET:
        key = _results_key(state, checkpoint, target, clock)
    if key is not None:
        with _VERIFIED_RESULTS_LOCK:
            known = _VERIFIED_RESULTS.get(key)
            if known is not None:
                _VERIFIED_RESULTS.move_to_end(key)
                return known
    results = _native_confirmed_results(state, checkpoint, target, clock)
    if key is not None and len(results) <= _MAX_VERIFIED_RESULTS:
        with _VERIFIED_RESULTS_LOCK:
            _VERIFIED_RESULTS[key] = results
            _VERIFIED_RESULTS.move_to_end(key)
            while len(_VERIFIED_RESULTS) > _MAX_VERIFIED_RESULT_ENTRIES or (
                sum(len(v) for v in _VERIFIED_RESULTS.values()) > _MAX_VERIFIED_RESULTS
            ):
                _VERIFIED_RESULTS.popitem(last=False)
    return results


def _native_confirmed_results(state, checkpoint, target, clock):
    events = {t.tournament_id: t for t in checkpoint.tournaments}
    return tuple(
        r
        for a in state.editions
        if a.result_confirmed and a.edition.week.ordinal < target.ordinal
        for r in published_edition_results(a, events[a.edition.edition_id], clock)
    )


def prepare_native_tour_week(
    *, state, checkpoint, world, source, lifecycle, health, clock, knockout, command,
    turn_pro_model=None,
):
    """Return None for a pre-birth natural week; preserve the old writer there.

    ``turn_pro_model`` is the recorded Master v87 model when replaying Signed
    history; new transitions use the current default calibration.
    """
    ordinal = checkpoint.week.ordinal + 1
    if ordinal >= clock.season_count * clock.weeks_per_year:
        raise ValueError("Native Tour target exceeds the Run horizon")
    position = clock.position_at_ordinal(ordinal)
    target = RunWeekPosition(
        calendar=clock, season_index=position.season_index, week=position.season_week
    )
    # Identify the complete verified inputs before later hashing can evict
    # the caller's already computed state/checkpoint fingerprints.
    results_key = _results_key(state, checkpoint, target, clock)
    season = checkpoint.week.week == clock.weeks_per_year
    if command["action"] != ("season-transition" if season else "transition"):
        raise ValueError("Native Tour command does not own this Week/Season boundary")
    if not lifecycle or lifecycle[-1].week != checkpoint.week:
        raise ValueError(
            "Native transition requires the exact current Signed lifecycle"
        )
    # A birthday consumes one effective snapshot; ranking replays ALL earlier
    # lifecycle weeks and must retain the complete immutable source epoch chain.
    event = build_calendar_prospect_birth_event(
        predecessor=lifecycle[-1],
        target=target,
        source=source.for_week(target.ordinal),
        world_package_id=world.world_package_id,
    )
    if not event.births and not isinstance(
        checkpoint, (CalendarNativeSportingCheckpoint, CalendarNativeCompetitionCheckpoint)
    ):
        return None
    submissions = tuple(s for a in state.editions for s in a.submissions)
    decisions, model = _native_turn_pro(
        state=state, checkpoint=checkpoint, world=world, lifecycle=lifecycle,
        target=target, submissions=submissions, seed=command["seed"],
        model=turn_pro_model,
    )
    successor_life = (
        advance_calendar_lifecycle_with_prospects(
            lifecycle[-1], event, submissions, decisions
        )
        if event.births
        else advance_calendar_lifecycle(lifecycle[-1], target, submissions, decisions)
    )
    prepared_health = prepare_native_health_history(
        saved_health=health, signed_lifecycle=lifecycle, next_lifecycle=successor_life
    )
    counts = played_counts(checkpoint, knockout) if isinstance(checkpoint, CalendarNativeCompetitionCheckpoint) else (
        tuple((p.player_id, 0) for p in checkpoint.players)
        if isinstance(checkpoint, CalendarNativeSportingCheckpoint)
        else played_counts(checkpoint, knockout)
    )
    sport = project_native_sporting_birth_advance(
        checkpoint=checkpoint,
        predecessor=lifecycle[-1],
        birth_event=event,
        seed=command["seed"],
        policy=effective_policy(state, checkpoint.week).development,
        played_counts=counts,
    )
    successor = append_native_sporting_week(
        checkpoint,
        sport,
        lifecycle_fingerprint=successor_life.fingerprint,
        health_fingerprint=prepared_health[-1].fingerprint,
        health_history_fingerprint=canonical_hash(
            [h.model_dump(mode="json") for h in prepared_health]
        ),
    )
    results = native_confirmed_results(state, checkpoint, target, clock, key=results_key)
    ranking, proof = calculate_native_ranking_from_signed_lifecycle(
        states=(*lifecycle, successor_life),
        source=source,
        world_package_id=world.world_package_id,
        submissions=submissions,
        previous=state.rankings[-1],
        policy=effective_policy(state, target).ranking,
        results=results,
    )
    changes = [
        {
            "player_id": a.player_id,
            "changed_attributes": sum(
                x != y for x, y in zip(a.attributes, b.attributes)
            ),
            "form_before": a.current_form,
            "form_after": b.current_form,
            "sharpness_before": a.match_sharpness,
            "sharpness_after": b.match_sharpness,
            "fatigue_before": a.long_term_fatigue,
            "fatigue_after": b.long_term_fatigue,
        }
        for a, b in zip(sport.completed_players, sport.recovered_players)
        if a != b
    ]
    sporting = {
        "schema_version": "native_tour_sporting_week_preview.v1",
        "completed_week": sport.completed_week.model_dump(mode="json"),
        "target_week": target.model_dump(mode="json"),
        "developed_players_fingerprint": sport.developed_players_fingerprint,
        "recovered_players_fingerprint": sport.recovered_players_fingerprint,
        "target_players_fingerprint": sport.target_players_fingerprint,
        "advance_fingerprint": sport.fingerprint,
        "checkpoint_fingerprint": successor.fingerprint,
        "player_count": len(successor.players),
        "changed_player_count": len(changes),
        "attribute_change_count": sum(c["changed_attributes"] for c in changes),
        "changes": changes,
    }
    sporting["preview_fingerprint"] = canonical_hash(sporting)
    return {
        "native_transition": True,
        "source_health_state_count": len(health),
        "completed_week": checkpoint.week.model_copy(
            update={"calendar": clock}
        ).model_dump(mode="json"),
        "target_week": target.model_dump(mode="json"),
        "development_policy": sport.policy.model_dump(mode="json"),
        "target_ranking_policy": effective_policy(state, target).ranking.model_dump(
            mode="json"
        ),
        "sporting": sporting,
        "ranking": ranking.model_dump(mode="json"),
        "ranking_fingerprint": ranking.fingerprint,
        "ranking_adoption_fingerprint": proof.fingerprint,
        "ages": tuple((p.player_id, p.age) for p in successor_life.players),
        "retired_player_ids": tuple(
            p.player_id for p in successor_life.players if p.status == "retired"
        ),
        "admitted_player_ids": tuple(b.player_id for b in event.births),
        "health_fingerprint": prepared_health[-1].fingerprint,
        "health_states": tuple(
            h.model_dump(mode="json") for h in prepared_health[len(health) :]
        ),
        "lifecycle": successor_life.model_dump(mode="json"),
        "lifecycle_fingerprint": successor_life.fingerprint,
        # Master v87 only, so every historical native impact keeps its bytes.
        **(
            {
                "turn_pro_decisions": [d.model_dump(mode="json") for d in decisions],
                "turn_pro_model": model.model_dump(mode="json"),
            }
            if model is not None
            else {}
        ),
    }, successor

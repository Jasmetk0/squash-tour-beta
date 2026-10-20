"""Pure complete birth-week preparation shared by execution and Signed replay."""

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
    edition_results,
    effective_policy,
)


def prepare_native_tour_week(
    *, state, checkpoint, world, source, lifecycle, health, clock, knockout, command
):
    """Return None for a pre-birth natural week; preserve the old writer there."""
    ordinal = checkpoint.week.ordinal + 1
    if ordinal >= clock.season_count * clock.weeks_per_year:
        raise ValueError("Native Tour target exceeds the Run horizon")
    position = clock.position_at_ordinal(ordinal)
    target = RunWeekPosition(
        calendar=clock, season_index=position.season_index, week=position.season_week
    )
    season = checkpoint.week.week == clock.weeks_per_year
    if command["action"] != ("season-transition" if season else "transition"):
        raise ValueError("Native Tour command does not own this Week/Season boundary")
    if not lifecycle or lifecycle[-1].week != checkpoint.week:
        raise ValueError(
            "Native transition requires the exact current Signed lifecycle"
        )
    event = build_calendar_prospect_birth_event(
        predecessor=lifecycle[-1],
        target=target,
        source=source,
        world_package_id=world.world_package_id,
    )
    if not event.births and not isinstance(
        checkpoint, (CalendarNativeSportingCheckpoint, CalendarNativeCompetitionCheckpoint)
    ):
        return None
    submissions = tuple(s for a in state.editions for s in a.submissions)
    successor_life = (
        advance_calendar_lifecycle_with_prospects(lifecycle[-1], event, submissions)
        if event.births
        else advance_calendar_lifecycle(lifecycle[-1], target, submissions)
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
    events = {t.tournament_id: t for t in checkpoint.tournaments}
    results = tuple(
        r
        for a in state.editions
        if a.result_confirmed and a.edition.week.ordinal < target.ordinal
        for r in edition_results(a, events[a.edition.edition_id])
    )
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
    }, successor
